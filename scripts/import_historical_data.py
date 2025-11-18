#!/usr/bin/env python3
"""
Historical Data Import Script
Import usage data from October 2024 onwards for all service lines
Handles rate limiting and edge cases
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from time import sleep
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2
from starlink.StarlinkClient import StarlinkClient

# Load environment variables
load_dotenv()


class HistoricalDataImporter:
    """Import historical usage data with rate limiting and error handling"""
    
    def __init__(self, db: DatabaseV2, client: StarlinkClient):
        self.db = db
        self.client = client
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    def import_for_service_line(self, account_number: str, service_line_id: str, 
                                start_date: date, cycles_to_fetch: int = 12):
        """
        Import historical data for a single service line
        
        Args:
            account_number: Starlink account number
            service_line_id: Service line ID
            start_date: Start date for import (e.g., 2024-10-01)
            cycles_to_fetch: Number of billing cycles to fetch
        """
        print(f"\n📊 Importing data for {service_line_id}")
        print(f"   Account: {account_number}")
        print(f"   Cycles to fetch: {cycles_to_fetch}")
        
        try:
            # Fetch usage data from Starlink API
            print(f"   Fetching data from Starlink API...")
            usage_data = self.client.usage.get_live_usage_data(
                account_number,
                service_lines=[service_line_id],
                cycles_to_fetch=cycles_to_fetch
            )
            
            if service_line_id not in usage_data:
                print(f"   ⚠️  No data returned for this service line")
                self.error_count += 1
                return
            
            sl_data = usage_data[service_line_id]
            daily_usage = sl_data.get('daily_usage', [])
            
            if not daily_usage:
                print(f"   ⚠️  No daily usage data found")
                self.error_count += 1
                return
            
            print(f"   Found {len(daily_usage)} days of usage data")
            
            # Import each day
            imported = 0
            skipped = 0
            
            for day in daily_usage:
                usage_date = day.get('date')
                
                # Skip if before start date
                if usage_date < str(start_date):
                    continue
                
                total_gb = day.get('total_gb', 0)
                priority_gb = day.get('priority_gb', 0)
                standard_gb = day.get('standard_gb', 0)
                billing_cycle_start = day.get('billing_cycle_start')
                billing_cycle_end = day.get('billing_cycle_end')
                
                # Import to database
                success = self.db.add_daily_usage(
                    service_line_id=service_line_id,
                    usage_date=usage_date,
                    total_gb=total_gb,
                    priority_gb=priority_gb,
                    standard_gb=standard_gb,
                    billing_cycle_start=billing_cycle_start,
                    billing_cycle_end=billing_cycle_end
                )
                
                if success:
                    imported += 1
                else:
                    skipped += 1
            
            self.imported_count += imported
            self.skipped_count += skipped
            
            print(f"   ✅ Imported: {imported} days")
            if skipped > 0:
                print(f"   ⏭️  Skipped: {skipped} days (already exists)")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.error_count += 1
    
    def import_all_service_lines(self, start_date: date, cycles_to_fetch: int = 12,
                                 delay_between_requests: int = 2):
        """
        Import historical data for all active service lines
        
        Args:
            start_date: Start date for import
            cycles_to_fetch: Number of billing cycles to fetch per service line
            delay_between_requests: Delay in seconds between API requests (rate limiting)
        """
        print("\n" + "="*60)
        print("🚀 Historical Data Import - All Service Lines")
        print("="*60)
        
        # Get all active service lines
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT account_number, service_line_id, nickname
                FROM service_lines
                WHERE active = TRUE
                ORDER BY account_number, service_line_id
            """)
            service_lines = [dict(row) for row in cursor.fetchall()]
        
        if not service_lines:
            print("\n⚠️  No active service lines found")
            return
        
        print(f"\nFound {len(service_lines)} active service line(s)")
        print(f"Start date: {start_date}")
        print(f"Cycles per service line: {cycles_to_fetch}")
        print(f"Rate limit delay: {delay_between_requests}s between requests\n")
        
        # Confirm before proceeding
        response = input("Proceed with import? (yes/no): ")
        if response.lower() != 'yes':
            print("Import cancelled")
            return
        
        # Import each service line
        for idx, sl in enumerate(service_lines, 1):
            print(f"\n[{idx}/{len(service_lines)}]")
            
            self.import_for_service_line(
                account_number=sl['account_number'],
                service_line_id=sl['service_line_id'],
                start_date=start_date,
                cycles_to_fetch=cycles_to_fetch
            )
            
            # Rate limiting delay (except for last request)
            if idx < len(service_lines):
                print(f"   ⏳ Waiting {delay_between_requests}s before next request...")
                sleep(delay_between_requests)
        
        # Summary
        print("\n" + "="*60)
        print("✅ Import Complete!")
        print("="*60)
        print(f"📊 Summary:")
        print(f"   Service lines processed: {len(service_lines)}")
        print(f"   Days imported: {self.imported_count}")
        print(f"   Days skipped (duplicates): {self.skipped_count}")
        print(f"   Errors: {self.error_count}")
        print("="*60 + "\n")


def main():
    """Main import function"""
    parser = argparse.ArgumentParser(description='Import historical Starlink usage data')
    parser.add_argument('--start-date', type=str, default='2024-10-01',
                       help='Start date for import (YYYY-MM-DD), default: 2024-10-01')
    parser.add_argument('--cycles', type=int, default=12,
                       help='Number of billing cycles to fetch per service line, default: 12')
    parser.add_argument('--delay', type=int, default=2,
                       help='Delay in seconds between API requests, default: 2')
    parser.add_argument('--service-line', type=str,
                       help='Import for specific service line only')
    parser.add_argument('--account', type=str,
                       help='Account number (required if --service-line is specified)')
    
    args = parser.parse_args()
    
    # Parse start date
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ Invalid date format: {args.start_date}. Use YYYY-MM-DD")
        sys.exit(1)
    
    # Initialize
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Zuba Broadband - Historical Data Import                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    db = DatabaseV2()
    client = StarlinkClient(
        client_id=os.getenv('STARLINK_CLIENT_ID'),
        client_secret=os.getenv('STARLINK_CLIENT_SECRET')
    )
    
    importer = HistoricalDataImporter(db, client)
    
    # Import
    if args.service_line:
        if not args.account:
            print("❌ --account is required when using --service-line")
            sys.exit(1)
        
        importer.import_for_service_line(
            account_number=args.account,
            service_line_id=args.service_line,
            start_date=start_date,
            cycles_to_fetch=args.cycles
        )
    else:
        importer.import_all_service_lines(
            start_date=start_date,
            cycles_to_fetch=args.cycles,
            delay_between_requests=args.delay
        )


if __name__ == '__main__':
    main()
