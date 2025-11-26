#!/usr/bin/env python3
"""
Improved CSV Import Script
Uses pandas for robust CSV parsing to prevent data corruption
"""

import argparse
import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2


def validate_email(email):
    """Basic email validation"""
    if not email:
        return False
    return '@' in email and '.' in email.split('@')[1]


def import_clients_from_csv(csv_path: str, db: DatabaseV2, create_portal_accounts: bool = True, dry_run: bool = False):
    """
    Import clients with all related data from CSV using pandas for robust parsing
    
    Expected CSV columns:
    - company_name (required)
    - service_line_id (required)
    - primary_contact_name
    - primary_contact_email
    - primary_contact_phone
    - status
    - service_start_date
    - billing_address
    - service_address
    - installation_date
    - technician_name
    - installation_address
    - peplink_router_installed
    - peplink_model
    - peplink_serial_number
    - starlink_dish_serial
    - installation_notes
    - portal_account_email
    - portal_account_password
    - portal_account_name
    """
    print(f"📥 Importing clients from {csv_path}...")
    print("=" * 80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made to the database")
        print("=" * 80)
    
    # Read CSV with pandas (immutable, prevents file modification)
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        df = df.copy()  # Ensure we're working with a copy
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return
    
    # Expected columns
    required_columns = ['company_name', 'service_line_id']
    optional_columns = [
        'primary_contact_name', 'primary_contact_email', 'primary_contact_phone',
        'status', 'service_start_date', 'billing_address', 'service_address',
        'installation_date', 'technician_name', 'installation_address',
        'peplink_router_installed', 'peplink_model', 'peplink_serial_number',
        'starlink_dish_serial', 'installation_notes',
        'portal_account_email', 'portal_account_password', 'portal_account_name'
    ]
    
    # Validate required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"❌ Missing required columns: {', '.join(missing_columns)}")
        print(f"Available columns: {', '.join(df.columns)}")
        return
    
    print(f"✅ CSV file loaded: {len(df)} rows")
    print(f"Columns: {', '.join(df.columns)}")
    print("=" * 80)
    
    # Clean data
    df = df.replace('None', '')
    df = df.replace('none', '')
    df = df.fillna('')
    
    # Strip whitespace from all string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # Statistics
    imported_clients = {}
    imported_service_lines = 0
    imported_contacts = 0
    imported_accounts = 0
    errors = 0
    
    # Process each row
    for idx, row in df.iterrows():
        row_num = idx + 2  # Account for header row
        
        try:
            company_name = row.get('company_name', '').strip()
            service_line_id = row.get('service_line_id', '').strip()
            portal_email = row.get('portal_account_email', '').strip()
            portal_password = row.get('portal_account_password', '').strip()
            portal_name = row.get('portal_account_name', '').strip()
            
            # Validate required fields
            if not company_name:
                print(f"⚠️  Row {row_num}: Missing company_name, skipping")
                errors += 1
                continue
            
            if not service_line_id:
                print(f"⚠️  Row {row_num}: Missing service_line_id, skipping")
                errors += 1
                continue
            
            # Validate portal email
            if portal_email and not validate_email(portal_email):
                print(f"⚠️  Row {row_num}: Invalid portal_email '{portal_email}', skipping portal account creation")
                portal_email = ''
            
            # Check if service line exists
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM service_lines WHERE service_line_id = ?", (service_line_id,))
                service_line = cursor.fetchone()
                
                if not service_line:
                    print(f"⚠️  Row {row_num}: Service line {service_line_id} not found in database. Skipping.")
                    errors += 1
                    continue
            
            # Group by portal_email (same email = one client with multiple kits)
            client_key = portal_email if portal_email else company_name
            
            # Create or get client
            if client_key not in imported_clients:
                # Check if client already exists
                if portal_email:
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT c.id, c.company_name 
                            FROM clients c
                            JOIN client_accounts ca ON c.id = ca.client_id
                            WHERE ca.email = ?
                            LIMIT 1
                        """, (portal_email,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            client_id = existing['id']
                            print(f"  ℹ️  Using existing client (portal: {portal_email}): {existing['company_name']} (ID: {client_id})")
                        else:
                            # Create new client
                            if not dry_run:
                                client_id = db.create_client(
                                    company_name=company_name,
                                    status=row.get('status', 'active') or 'active',
                                    service_start_date=row.get('service_start_date') or None,
                                    billing_address=row.get('billing_address') or None,
                                    service_address=row.get('service_address') or None,
                                    notes=f"Imported from CSV on {datetime.now().strftime('%Y-%m-%d')}"
                                )
                                print(f"  ✅ Created client: {company_name} (ID: {client_id})")
                            else:
                                client_id = -1
                                print(f"  [DRY RUN] Would create client: {company_name}")
                else:
                    # No portal email - check by company name
                    existing_clients = db.get_all_clients()
                    existing_client = next((c for c in existing_clients if c['company_name'].lower() == company_name.lower()), None)
                    
                    if existing_client:
                        client_id = existing_client['id']
                        print(f"  ℹ️  Using existing client: {company_name} (ID: {client_id})")
                    else:
                        # Create new client
                        if not dry_run:
                            client_id = db.create_client(
                                company_name=company_name,
                                status=row.get('status', 'active') or 'active',
                                service_start_date=row.get('service_start_date') or None,
                                billing_address=row.get('billing_address') or None,
                                service_address=row.get('service_address') or None,
                                notes=f"Imported from CSV on {datetime.now().strftime('%Y-%m-%d')}"
                            )
                            print(f"  ✅ Created client: {company_name} (ID: {client_id})")
                        else:
                            client_id = -1
                            print(f"  [DRY RUN] Would create client: {company_name}")
                
                imported_clients[client_key] = {
                    'id': client_id,
                    'company_name': company_name,
                    'primary_contact_added': False,
                    'portal_account_added': False
                }
            else:
                client_id = imported_clients[client_key]['id']
            
            # Link service line to client
            if not dry_run:
                try:
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR IGNORE INTO client_service_lines (client_id, service_line_id, assigned_at)
                            VALUES (?, ?, ?)
                        """, (client_id, service_line_id, datetime.now().isoformat()))
                        conn.commit()
                    
                    if cursor.rowcount > 0:
                        print(f"  ✅ Linked service line {service_line_id} to client (ID: {client_id})")
                        imported_service_lines += 1
                    else:
                        print(f"  ℹ️  Service line {service_line_id} already linked to this client")
                except Exception as e:
                    print(f"  ⚠️  Error linking service line: {e}")
            else:
                print(f"  [DRY RUN] Would link service line {service_line_id} to client")
                imported_service_lines += 1
            
            # Add primary contact (only once per client)
            if not imported_clients[client_key]['primary_contact_added']:
                contact_name = row.get('primary_contact_name', '').strip()
                primary_contact_email = portal_email or row.get('primary_contact_email', '').split(',')[0].strip()
                contact_phone = row.get('primary_contact_phone', '').strip()
                
                if contact_name or primary_contact_email:
                    if not dry_run:
                        try:
                            db.add_client_contact(
                                client_id=client_id,
                                name=contact_name or company_name,
                                email=primary_contact_email,
                                phone=contact_phone or None,
                                role='primary',
                                is_primary=True
                            )
                            print(f"  ✅ Added primary contact: {contact_name or 'N/A'} ({primary_contact_email})")
                            imported_contacts += 1
                        except Exception as e:
                            print(f"  ⚠️  Error adding contact: {e}")
                    else:
                        print(f"  [DRY RUN] Would add primary contact: {contact_name or 'N/A'} ({primary_contact_email})")
                        imported_contacts += 1
                    
                    imported_clients[client_key]['primary_contact_added'] = True
            
            # Create portal account (only once per client)
            if create_portal_accounts and portal_email and not imported_clients[client_key]['portal_account_added']:
                if not portal_password:
                    portal_password = 'ChangeMe123!'  # Default password
                
                if not dry_run:
                    try:
                        password_hash = generate_password_hash(portal_password)
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT OR IGNORE INTO client_accounts 
                                (client_id, email, password_hash, name, active, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (client_id, portal_email, password_hash, 
                                  portal_name or contact_name or company_name, 
                                  True, datetime.now().isoformat()))
                            conn.commit()
                        
                        if cursor.rowcount > 0:
                            print(f"  ✅ Created portal account: {portal_email}")
                            imported_accounts += 1
                        else:
                            print(f"  ℹ️  Portal account {portal_email} already exists")
                    except Exception as e:
                        print(f"  ⚠️  Error creating portal account: {e}")
                else:
                    print(f"  [DRY RUN] Would create portal account: {portal_email}")
                    imported_accounts += 1
                
                imported_clients[client_key]['portal_account_added'] = True
        
        except Exception as e:
            print(f"❌ Row {row_num}: Error processing row: {e}")
            errors += 1
            import traceback
            traceback.print_exc()
    
    # Summary
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Clients processed: {len(imported_clients)}")
    print(f"Service lines linked: {imported_service_lines}")
    print(f"Contacts added: {imported_contacts}")
    print(f"Portal accounts created: {imported_accounts}")
    print(f"Errors: {errors}")
    print("=" * 80)
    
    if dry_run:
        print("🔍 DRY RUN COMPLETE - No changes were made to the database")
    else:
        print("✅ IMPORT COMPLETE")


def main():
    parser = argparse.ArgumentParser(description="Import clients from CSV with pandas")
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--no-portal-accounts', action='store_true', 
                       help='Skip creating portal accounts')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview import without making changes')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"❌ File not found: {args.csv_file}")
        sys.exit(1)
    
    db = DatabaseV2()
    import_clients_from_csv(
        args.csv_file, 
        db, 
        create_portal_accounts=not args.no_portal_accounts,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
