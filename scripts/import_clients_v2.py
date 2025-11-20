#!/usr/bin/env python3
"""
Bulk Import Clients v2 - Comprehensive Import Tool
Imports clients, service lines, installations, contacts, and portal accounts from CSV
"""

import argparse
import csv
import sys
import os
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2


def normalize_field(value):
    """Normalize CSV field values"""
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def parse_date(date_str):
    """Parse date string to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except:
        return None


def parse_boolean(value):
    """Parse boolean from string"""
    if not value:
        return False
    return str(value).lower() in ('true', '1', 'yes', 'y')


def import_clients_from_csv(csv_path: str, db: DatabaseV2, create_portal_accounts: bool = True):
    """
    Import clients with all related data from CSV
    
    CSV Format (all fields optional except company_name and service_line_id):
    company_name,service_line_id,primary_contact_name,primary_contact_email,primary_contact_phone,
    status,service_start_date,billing_address,service_address,
    installation_date,technician_name,installation_address,
    peplink_router_installed,peplink_model,peplink_serial_number,starlink_dish_serial,installation_notes,
    portal_account_email,portal_account_password,portal_account_name
    """
    print(f"📥 Importing clients from {csv_path}...")
    print("=" * 60)
    
    imported_clients = {}  # Key: portal_email (for grouping multi-kit clients)
    portal_to_client = {}  # Map portal_email to client_id
    imported_service_lines = 0
    imported_installations = 0
    imported_contacts = 0
    imported_accounts = 0
    errors = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Normalize all fields and handle "None" values
                for key in row:
                    value = normalize_field(row[key])
                    # Convert "None" string to empty
                    if value and value.lower() == 'none':
                        row[key] = None
                    else:
                        row[key] = value
                
                # Required fields
                company_name = row.get('company_name')
                service_line_id = row.get('service_line_id')
                portal_email = row.get('portal_account_email')
                portal_password = row.get('portal_account_password')
                
                # Validate portal_email is actually an email (not password)
                if portal_email and '@' not in portal_email:
                    print(f"⚠️  Row {row_num}: Invalid portal_email '{portal_email}' (doesn't look like an email). Skipping portal account creation for this row.")
                    portal_email = None  # Don't use invalid email
                
                if not company_name:
                    print(f"⚠️  Row {row_num}: Missing company_name, skipping")
                    errors += 1
                    continue
                
                if not service_line_id:
                    print(f"⚠️  Row {row_num}: Missing service_line_id, skipping")
                    errors += 1
                    continue
                
                # Check if service line exists
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM service_lines WHERE service_line_id = ?", (service_line_id,))
                    service_line = cursor.fetchone()
                    
                    if not service_line:
                        print(f"⚠️  Row {row_num}: Service line {service_line_id} not found in database. Skipping.")
                        errors += 1
                        continue
                    
                    service_line = dict(service_line)
                
                # Group by portal_email (same email = one client with multiple kits)
                # If no portal_email, use company_name as fallback
                client_key = portal_email if portal_email else company_name
                
                # Create or get client
                if client_key not in imported_clients:
                    # Check if client already exists by portal email
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
                                client_id = db.create_client(
                                    company_name=company_name,
                                    status=row.get('status', 'active'),
                                    service_start_date=parse_date(row.get('service_start_date')),
                                    billing_address=row.get('billing_address'),
                                    service_address=row.get('service_address'),
                                    notes=f"Imported from CSV on {datetime.now().strftime('%Y-%m-%d')}"
                                )
                                print(f"  ✅ Created client: {company_name} (ID: {client_id})")
                    else:
                        # No portal email - check by company name
                        existing_clients = db.get_all_clients()
                        existing_client = next((c for c in existing_clients if c['company_name'].lower() == company_name.lower()), None)
                        
                        if existing_client:
                            client_id = existing_client['id']
                            print(f"  ℹ️  Using existing client: {company_name} (ID: {client_id})")
                        else:
                            # Create new client
                            client_id = db.create_client(
                                company_name=company_name,
                                status=row.get('status', 'active'),
                                service_start_date=parse_date(row.get('service_start_date')),
                                billing_address=row.get('billing_address'),
                                service_address=row.get('service_address'),
                                notes=f"Imported from CSV on {datetime.now().strftime('%Y-%m-%d')}"
                            )
                            print(f"  ✅ Created client: {company_name} (ID: {client_id})")
                    
                    imported_clients[client_key] = {
                        'id': client_id,
                        'company_name': company_name,
                        'primary_contact_added': False,
                        'portal_account_added': False,
                        'cc_emails_added': set()  # Track CC emails added
                    }
                    portal_to_client[portal_email] = client_id if portal_email else None
                else:
                    client_id = imported_clients[client_key]['id']
                    # Update company name if this is a different name for same portal
                    if company_name != imported_clients[client_key]['company_name']:
                        print(f"  ℹ️  Linking {company_name} to existing client {imported_clients[client_key]['company_name']} (same portal email)")
                
                # Link service line to client
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
                
                # Add primary contact (only once per client)
                # Use portal_account_email as primary contact email
                if not imported_clients[client_key]['primary_contact_added']:
                    contact_name = row.get('primary_contact_name')
                    # Primary contact email = portal account email (single email)
                    primary_contact_email = portal_email or row.get('primary_contact_email', '').split(',')[0].strip()
                    
                    if contact_name or primary_contact_email:
                        try:
                            db.add_client_contact(
                                client_id=client_id,
                                name=contact_name or imported_clients[client_key]['company_name'],
                                email=primary_contact_email,
                                phone=row.get('primary_contact_phone'),
                                role='primary',
                                is_primary=True
                            )
                            print(f"  ✅ Added primary contact: {contact_name or 'N/A'} ({primary_contact_email})")
                            imported_contacts += 1
                            imported_clients[client_key]['primary_contact_added'] = True
                        except Exception as e:
                            print(f"  ⚠️  Error adding contact: {e}")
                
                # Add CC emails (from comma-separated primary_contact_email field)
                cc_emails_str = row.get('primary_contact_email', '')
                contact_name = row.get('primary_contact_name')
                if cc_emails_str and ',' in cc_emails_str:
                    # Parse comma-separated emails
                    cc_emails = [e.strip() for e in cc_emails_str.split(',') if e.strip()]
                    # Remove the portal email if it's in the list (already primary)
                    if portal_email and portal_email in cc_emails:
                        cc_emails.remove(portal_email)
                    
                    # Add each CC email as additional contact
                    for cc_email in cc_emails:
                        if cc_email not in imported_clients[client_key]['cc_emails_added']:
                            try:
                                db.add_client_contact(
                                    client_id=client_id,
                                    name=contact_name or 'Contact',
                                    email=cc_email,
                                    phone=row.get('primary_contact_phone'),
                                    role='contact',
                                    is_primary=False
                                )
                                imported_clients[client_key]['cc_emails_added'].add(cc_email)
                                imported_contacts += 1
                            except Exception as e:
                                # Skip if duplicate
                                pass
                
                # Add installation record
                installation_date = parse_date(row.get('installation_date'))
                if installation_date:
                    try:
                        # Check if installation already exists
                        existing_installation = db.get_installation(service_line_id)
                        
                        if not existing_installation:
                            db.add_installation(
                                service_line_id=service_line_id,
                                installation_date=installation_date,
                                technician_name=row.get('technician_name'),
                                installation_address=row.get('installation_address') or row.get('service_address'),
                                peplink_router_installed=parse_boolean(row.get('peplink_router_installed')),
                                peplink_model=row.get('peplink_model') if row.get('peplink_model') and row.get('peplink_model').lower() != 'none' else None,
                                peplink_serial_number=row.get('peplink_serial_number') if row.get('peplink_serial_number') and row.get('peplink_serial_number').lower() != 'none' else None,
                                starlink_dish_serial=row.get('starlink_dish_serial'),
                                installation_notes=row.get('installation_notes')
                            )
                            print(f"  ✅ Added installation record for {service_line_id}")
                            imported_installations += 1
                        else:
                            print(f"  ℹ️  Installation record already exists for {service_line_id}")
                    except Exception as e:
                        print(f"  ⚠️  Error adding installation: {e}")
                
                # Create portal account (only once per portal_email - handles multi-kit clients)
                if create_portal_accounts and portal_email and not imported_clients[client_key]['portal_account_added']:
                    portal_password = row.get('portal_account_password')
                    portal_name = row.get('portal_account_name')
                    
                    if portal_password:
                        try:
                            # Check if account already exists (by email, not client)
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT id, client_id FROM client_accounts WHERE email = ?", (portal_email,))
                                existing_account = cursor.fetchone()
                                
                                if existing_account:
                                    existing_client_id = existing_account['client_id']
                                    # If account exists for different client, link this client's service lines to that account's client
                                    if existing_client_id != client_id:
                                        print(f"  ⚠️  Portal account {portal_email} exists for different client. Linking service lines to existing client.")
                                        # Update client_id to the existing one
                                        client_id = existing_client_id
                                        imported_clients[client_key]['id'] = client_id
                                    else:
                                        print(f"  ℹ️  Portal account {portal_email} already exists for this client")
                                else:
                                    db.create_client_account(
                                        client_id=client_id,
                                        email=portal_email,
                                        password=portal_password,
                                        name=portal_name or contact_name or imported_clients[client_key]['company_name']
                                    )
                                    print(f"  ✅ Created portal account: {portal_email}")
                                    imported_accounts += 1
                                
                                imported_clients[client_key]['portal_account_added'] = True
                        except Exception as e:
                            print(f"  ⚠️  Error creating portal account: {e}")
                
            except Exception as e:
                print(f"❌ Row {row_num}: Error processing row: {e}")
                import traceback
                traceback.print_exc()
                errors += 1
    
    print("\n" + "=" * 60)
    print("📊 Import Summary")
    print("=" * 60)
    print(f"  Clients processed: {len(imported_clients)}")
    print(f"  Service lines linked: {imported_service_lines}")
    print(f"  Installations added: {imported_installations}")
    print(f"  Contacts added: {imported_contacts}")
    print(f"  Portal accounts created: {imported_accounts}")
    print(f"  Errors: {errors}")
    print("=" * 60)
    
    return {
        'clients': len(imported_clients),
        'service_lines': imported_service_lines,
        'installations': imported_installations,
        'contacts': imported_contacts,
        'accounts': imported_accounts,
        'errors': errors
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import clients with all related data from CSV (v2 schema)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format:
  Required: company_name, service_line_id
  Optional: All other fields (see template)
  
  Multiple rows with same company_name = multiple kits per client
  
Example:
  python import_clients_v2.py config/clients_import.csv
  
  # Skip portal account creation
  python import_clients_v2.py config/clients_import.csv --no-portal-accounts
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to CSV file'
    )
    
    parser.add_argument(
        '--db',
        default=None,
        help='Path to database file (default: data/starlink.db)'
    )
    
    parser.add_argument(
        '--no-portal-accounts',
        action='store_true',
        help='Skip creating portal accounts'
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"❌ Error: CSV file not found: {args.csv_file}")
        sys.exit(1)
    
    # Initialize database
    db = DatabaseV2(args.db)
    
    try:
        import_clients_from_csv(
            args.csv_file,
            db,
            create_portal_accounts=not args.no_portal_accounts
        )
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

