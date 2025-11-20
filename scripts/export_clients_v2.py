#!/usr/bin/env python3
"""
Export Clients v2 - Export all client data to CSV for backup/migration
This creates a CSV file that can be imported on another server
"""

import argparse
import csv
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2


def export_clients_to_csv(output_csv: str, db: DatabaseV2):
    """
    Export all client data to CSV format compatible with import_clients_v2.py
    """
    print(f"📤 Exporting clients to {output_csv}...")
    print("=" * 60)
    
    # Get all clients
    clients = db.get_all_clients()
    
    if not clients:
        print("⚠️  No clients found in database")
        return
    
    exported_rows = 0
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = [
            'company_name', 'service_line_id', 'primary_contact_name', 'primary_contact_email',
            'primary_contact_phone', 'status', 'service_start_date', 'billing_address',
            'service_address', 'installation_date', 'technician_name', 'installation_address',
            'peplink_router_installed', 'peplink_model', 'peplink_serial_number',
            'starlink_dish_serial', 'installation_notes', 'portal_account_email',
            'portal_account_password', 'portal_account_name'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for client in clients:
            client_id = client['id']
            
            # Get service lines for this client
            service_lines = db.get_client_service_lines(client_id)
            
            if not service_lines:
                # Client with no service lines - still export basic info
                row = {
                    'company_name': client.get('company_name', ''),
                    'service_line_id': '',  # No service line
                    'status': client.get('status', 'active'),
                    'service_start_date': client.get('service_start_date', ''),
                    'billing_address': client.get('billing_address', ''),
                    'service_address': client.get('service_address', ''),
                }
                writer.writerow(row)
                exported_rows += 1
                continue
            
            # Get primary contact
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, email, phone, role
                    FROM client_contacts
                    WHERE client_id = ? AND is_primary = 1 AND active = 1
                    LIMIT 1
                """, (client_id,))
                contact = cursor.fetchone()
                primary_contact = dict(contact) if contact else None
            
            # Get portal account (first one)
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT email, name
                    FROM client_accounts
                    WHERE client_id = ? AND active = 1
                    LIMIT 1
                """, (client_id,))
                account = cursor.fetchone()
                portal_account = dict(account) if account else None
            
            # Create one row per service line
            for i, sl in enumerate(service_lines):
                service_line_id = sl['service_line_id']
                
                # Get installation record
                installation = db.get_installation(service_line_id)
                
                # Build row
                row = {
                    'company_name': client.get('company_name', ''),
                    'service_line_id': service_line_id,
                    'primary_contact_name': primary_contact.get('name', '') if primary_contact else '',
                    'primary_contact_email': primary_contact.get('email', '') if primary_contact else '',
                    'primary_contact_phone': primary_contact.get('phone', '') if primary_contact else '',
                    'status': client.get('status', 'active'),
                    'service_start_date': client.get('service_start_date', '') or '',
                    'billing_address': client.get('billing_address', '') or '',
                    'service_address': client.get('service_address', '') or '',
                }
                
                # Add installation data
                if installation:
                    row['installation_date'] = installation.get('installation_date', '') or ''
                    row['technician_name'] = installation.get('technician_name', '') or ''
                    row['installation_address'] = installation.get('installation_address', '') or ''
                    row['peplink_router_installed'] = 'true' if installation.get('peplink_router_installed') else 'false'
                    row['peplink_model'] = installation.get('peplink_model', '') or ''
                    row['peplink_serial_number'] = installation.get('peplink_serial_number', '') or ''
                    row['starlink_dish_serial'] = installation.get('starlink_dish_serial', '') or ''
                    row['installation_notes'] = installation.get('installation_notes', '') or ''
                else:
                    # Empty installation fields
                    row['installation_date'] = ''
                    row['technician_name'] = ''
                    row['installation_address'] = ''
                    row['peplink_router_installed'] = ''
                    row['peplink_model'] = ''
                    row['peplink_serial_number'] = ''
                    row['starlink_dish_serial'] = ''
                    row['installation_notes'] = ''
                
                # Add portal account (only for first service line to avoid duplicates)
                if i == 0 and portal_account:
                    row['portal_account_email'] = portal_account.get('email', '')
                    row['portal_account_password'] = ''  # Never export passwords
                    row['portal_account_name'] = portal_account.get('name', '')
                else:
                    row['portal_account_email'] = ''
                    row['portal_account_password'] = ''
                    row['portal_account_name'] = ''
                
                writer.writerow(row)
                exported_rows += 1
                print(f"  ✓ Exported: {client['company_name']} - {service_line_id}")
    
    print("\n" + "=" * 60)
    print(f"✅ Export complete!")
    print(f"   Clients: {len(clients)}")
    print(f"   Rows exported: {exported_rows}")
    print(f"   File: {output_csv}")
    print("\n⚠️  Note: Passwords are NOT exported for security.")
    print("   You'll need to set new passwords or use password reset after import.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Export all client data to CSV for backup/migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This exports all client data to a CSV file that can be imported on another server.

Example:
  python export_clients_v2.py config/clients_backup.csv
  
  # Export with timestamp
  python export_clients_v2.py config/clients_backup_$(date +%Y%m%d).csv
        """
    )
    
    parser.add_argument(
        'output_csv',
        help='Path to output CSV file'
    )
    
    parser.add_argument(
        '--db',
        default=None,
        help='Path to database file (default: data/starlink.db)'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    db = DatabaseV2(args.db)
    
    try:
        export_clients_to_csv(args.output_csv, db)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

