#!/usr/bin/env python3
"""
Import Historical Usage Data
Fetches and stores historical usage data from Starlink API with improved error handling
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2
from starlink.StarlinkClient import StarlinkClient
from dotenv import load_dotenv

load_dotenv()


def import_historical_usage(
    db: DatabaseV2,
    client: StarlinkClient,
    service_line_id: str,
    days_back: int = 90,
    batch_size: int = 7
):
    """
    Import historical usage data for a service line
    
    Args:
        db: Database instance
        client: Starlink API client
        service_line_id: Service line ID to fetch data for
        days_back: Number of days of history to fetch
        batch_size: Number of days to fetch per API call (smaller = more reliable)
    """
    print(f"📥 Importing historical usage for {service_line_id}")
    print(f"   Days back: {days_back}, Batch size: {batch_size} days")
    print("=" * 80)
    
    # Get service line info
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM service_lines WHERE service_line_id = ?", (service_line_id,))
        service_line = cursor.fetchone()
        
        if not service_line:
            print(f"❌ Service line {service_line_id} not found")
            return
        
        service_line = dict(service_line)
    
    account_number = service_line['account_number']
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"Date range: {start_date} to {end_date}")
    print(f"Account: {account_number}")
    print()
    
    # Fetch data in batches
    current_date = start_date
    total_days_imported = 0
    total_errors = 0
    
    while current_date < end_date:
        batch_end = min(current_date + timedelta(days=batch_size), end_date)
        
        print(f"📦 Fetching batch: {current_date} to {batch_end}...")
        
        try:
            # Fetch usage data from API
            usage_data = client.usage.get_live_usage_data(
                account_number,
                service_lines=[service_line_id],
                cycles_to_fetch=1  # Get current cycle
            )
            
            if service_line_id not in usage_data:
                print(f"⚠️  No data returned for {service_line_id}")
                current_date = batch_end
                continue
            
            sl_data = usage_data[service_line_id]
            daily_usage = sl_data.get('daily_usage', [])
            
            if not daily_usage:
                print(f"⚠️  No daily usage data in response")
                current_date = batch_end
                continue
            
            # Filter to batch date range
            batch_usage = [
                day for day in daily_usage
                if current_date <= datetime.strptime(day.get('date', ''), '%Y-%m-%d').date() < batch_end
            ]
            
            if not batch_usage:
                print(f"ℹ️  No usage data in this batch")
                current_date = batch_end
                continue
            
            # Import into database
            imported_count = 0
            for day in batch_usage:
                try:
                    date = day.get('date')
                    if not date:
                        continue
                    
                    # Check if already exists
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id FROM usage_history
                            WHERE service_line_id = ? AND date = ?
                        """, (service_line_id, date))
                        
                        if cursor.fetchone():
                            continue  # Skip if already exists
                        
                        # Insert usage data
                        cursor.execute("""
                            INSERT INTO usage_history (
                                service_line_id,
                                date,
                                download_gb,
                                upload_gb,
                                total_gb,
                                billing_cycle_start,
                                billing_cycle_end,
                                created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            service_line_id,
                            date,
                            day.get('download_gb', 0),
                            day.get('upload_gb', 0),
                            day.get('total_gb', day.get('usage_gb', 0)),
                            sl_data.get('billing_cycle_start_date'),
                            sl_data.get('billing_cycle_end_date'),
                            datetime.now().isoformat()
                        ))
                        conn.commit()
                        imported_count += 1
                
                except Exception as e:
                    print(f"   ⚠️  Error importing day {day.get('date')}: {e}")
                    total_errors += 1
            
            print(f"   ✅ Imported {imported_count} days")
            total_days_imported += imported_count
            
            # Rate limiting - be nice to the API
            time.sleep(2)
        
        except Exception as e:
            print(f"   ❌ Error fetching batch: {e}")
            total_errors += 1
            
            # Check for rate limiting
            if '429' in str(e) or 'rate limit' in str(e).lower():
                print("   ⏳ Rate limited. Waiting 60 seconds...")
                time.sleep(60)
            else:
                time.sleep(5)
        
        current_date = batch_end
    
    print()
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total days imported: {total_days_imported}")
    print(f"Errors: {total_errors}")
    print("=" * 80)


def import_all_service_lines(db: DatabaseV2, client: StarlinkClient, days_back: int = 90):
    """Import historical usage for all active service lines"""
    print("📥 Importing historical usage for ALL service lines")
    print("=" * 80)
    
    # Get all active service lines
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT service_line_id FROM service_lines WHERE active = 1")
        service_lines = [row['service_line_id'] for row in cursor.fetchall()]
    
    print(f"Found {len(service_lines)} active service lines")
    print()
    
    for idx, service_line_id in enumerate(service_lines, 1):
        print(f"\n[{idx}/{len(service_lines)}] Processing {service_line_id}")
        print("-" * 80)
        
        try:
            import_historical_usage(db, client, service_line_id, days_back=days_back)
        except Exception as e:
            print(f"❌ Failed to import {service_line_id}: {e}")
        
        # Wait between service lines
        if idx < len(service_lines):
            print(f"\n⏳ Waiting 10 seconds before next service line...")
            time.sleep(10)
    
    print("\n" + "=" * 80)
    print("✅ ALL IMPORTS COMPLETE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Import historical usage data from Starlink API"
    )
    parser.add_argument(
        '--service-line',
        help='Specific service line ID to import (optional, imports all if not specified)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days of history to fetch (default: 90)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=7,
        help='Days per API call batch (default: 7, smaller = more reliable)'
    )
    
    args = parser.parse_args()
    
    # Initialize
    db = DatabaseV2()
    client = StarlinkClient(
        client_id=os.getenv('STARLINK_CLIENT_ID'),
        client_secret=os.getenv('STARLINK_CLIENT_SECRET')
    )
    
    if not os.getenv('STARLINK_CLIENT_ID') or not os.getenv('STARLINK_CLIENT_SECRET'):
        print("❌ Error: Starlink credentials not configured in .env")
        sys.exit(1)
    
    try:
        if args.service_line:
            import_historical_usage(
                db, client, args.service_line,
                days_back=args.days,
                batch_size=args.batch_size
            )
        else:
            import_all_service_lines(db, client, days_back=args.days)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
