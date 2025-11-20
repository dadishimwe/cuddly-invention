#!/usr/bin/env python3
"""
CSV Import Utility
Import service lines and client mappings from CSV files
"""

import argparse
import csv
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database


def import_service_lines(csv_path: str, db: Database):
    """
    Import service lines from CSV
    
    CSV Format:
    account_number,service_line_id,nickname,service_line_number,active
    """
    print(f"📥 Importing service lines from {csv_path}...")
    
    imported = 0
    skipped = 0
    errors = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Normalize fields (trim whitespace)
                for key in list(row.keys()):
                    if isinstance(row[key], str):
                        row[key] = row[key].strip()

                # Backfill service_line_id from service_line_number if missing
                if (not row.get('service_line_id')) and row.get('service_line_number'):
                    row['service_line_id'] = row['service_line_number']

                # Validate required field
                if not row.get('service_line_id'):
                    print(f"❌ Error: Missing service_line_id for row with account_number={row.get('account_number')} nickname={row.get('nickname')}. Skipping.")
                    errors += 1
                    continue

                # Check if already exists
                existing = db.get_service_line(row['service_line_id'])
                if existing:
                    print(f"⚠️  Skipping {row['service_line_id']} - already exists")
                    skipped += 1
                    continue
                
                # Convert active to boolean
                active = row.get('active', 'true').lower() in ('true', '1', 'yes')
                
                db.add_service_line(
                    account_number=row['account_number'],
                    service_line_id=row['service_line_id'],
                    nickname=row.get('nickname') or None,
                    service_line_number=row.get('service_line_number') or None,
                    active=active
                )
                
                print(f"✅ Imported: {row['service_line_id']} ({row.get('nickname', 'No nickname')})")
                imported += 1
                
            except Exception as e:
                print(f"❌ Error importing row {row}: {e}")
                errors += 1
    
    print(f"\n📊 Summary: {imported} imported, {skipped} skipped, {errors} errors")
    return imported, skipped, errors


def import_client_mappings(csv_path: str, db: Database):
    """
    Import client mappings from CSV
    
    CSV Format:
    client_name,service_line_id,primary_email,cc_emails,active,report_frequency
    
    NOTE: This imports to the legacy client_mappings table.
    For v2 features (multi-kit, installations, portal accounts), use:
    python3 scripts/import_clients_v2.py instead
    """
    print(f"📥 Importing client mappings from {csv_path}...")
    print("ℹ️  Note: Using legacy client_mappings table.")
    print("   For v2 features, use: python3 scripts/import_clients_v2.py")
    print()
    
    imported = 0
    skipped = 0
    errors = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Normalize fields
                for key in list(row.keys()):
                    if isinstance(row[key], str):
                        row[key] = row[key].strip()
                
                # Check if service line exists
                service_line = db.get_service_line(row['service_line_id'])
                if not service_line:
                    print(f"⚠️  Warning: Service line {row['service_line_id']} not found. Import service lines first.")
                    skipped += 1
                    continue
                
                # Convert active to boolean
                active = row.get('active', 'true').lower() in ('true', '1', 'yes')
                
                db.add_client_mapping(
                    client_name=row['client_name'],
                    service_line_id=row['service_line_id'],
                    primary_email=row['primary_email'],
                    cc_emails=row.get('cc_emails') or None,
                    active=active,
                    report_frequency=row.get('report_frequency', 'on_demand')
                )
                
                print(f"✅ Imported: {row['client_name']} -> {row['primary_email']}")
                imported += 1
                
            except Exception as e:
                print(f"❌ Error importing row {row}: {e}")
                errors += 1
    
    print(f"\n📊 Summary: {imported} imported, {skipped} skipped, {errors} errors")
    print("\n💡 Tip: These mappings work with both v1 and v2 databases.")
    print("   They're kept for backward compatibility.")
    return imported, skipped, errors


def main():
    parser = argparse.ArgumentParser(
        description="Import data from CSV files into the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import service lines
  python import_csv.py service-lines ../config/service_lines.csv

  # Import client mappings
  python import_csv.py client-mappings ../config/client_mappings.csv

  # Import both (service lines first, then mappings)
  python import_csv.py service-lines ../config/service_lines.csv
  python import_csv.py client-mappings ../config/client_mappings.csv
        """
    )
    
    parser.add_argument(
        'type',
        choices=['service-lines', 'client-mappings'],
        help='Type of data to import'
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to CSV file'
    )
    
    parser.add_argument(
        '--db',
        default='../data/starlink.db',
        help='Path to database file (default: ../data/starlink.db)'
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"❌ Error: CSV file not found: {args.csv_file}")
        sys.exit(1)
    
    # Initialize database
    db = Database(args.db)
    
    try:
        if args.type == 'service-lines':
            import_service_lines(args.csv_file, db)
        elif args.type == 'client-mappings':
            import_client_mappings(args.csv_file, db)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
