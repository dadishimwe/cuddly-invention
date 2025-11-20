#!/usr/bin/env python3
"""
Convert existing client_mappings.csv to v2 import format
This helps migrate your existing data to the new structure
"""

import csv
import sys
from pathlib import Path

def convert_mappings_to_v2(input_csv: str, output_csv: str):
    """
    Convert client_mappings.csv to clients_import format
    """
    print(f"📥 Reading from: {input_csv}")
    print(f"📤 Writing to: {output_csv}")
    
    clients_data = {}
    
    # Read existing mappings
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            client_name = row.get('client_name', '').strip()
            service_line_id = row.get('service_line_id', '').strip()
            primary_email = row.get('primary_email', '').strip()
            
            if not client_name or not service_line_id:
                continue
            
            # Group by client name (for multi-kit clients)
            if client_name not in clients_data:
                clients_data[client_name] = {
                    'company_name': client_name,
                    'primary_contact_email': primary_email,
                    'service_lines': []
                }
            
            # Add this service line
            clients_data[client_name]['service_lines'].append({
                'service_line_id': service_line_id,
                'primary_email': primary_email,
                'cc_emails': row.get('cc_emails', '').strip(),
                'active': row.get('active', 'true').strip(),
                'report_frequency': row.get('report_frequency', 'on_demand').strip()
            })
    
    # Write to new format
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
        
        for client_name, client_data in clients_data.items():
            # Create one row per service line
            for i, sl in enumerate(client_data['service_lines']):
                # First service line gets portal account, others don't
                row = {
                    'company_name': client_data['company_name'],
                    'service_line_id': sl['service_line_id'],
                    'primary_contact_email': client_data['primary_contact_email'],
                    'status': 'active' if sl['active'].lower() in ('true', '1', 'yes') else 'suspended',
                    'portal_account_email': client_data['primary_contact_email'] if i == 0 else '',
                    'portal_account_password': 'ChangeMe123!' if i == 0 else '',  # Default password
                    'portal_account_name': client_data['company_name'] if i == 0 else ''
                }
                writer.writerow(row)
    
    print(f"\n✅ Conversion complete!")
    print(f"   Clients: {len(clients_data)}")
    print(f"   Total service lines: {sum(len(c['service_lines']) for c in clients_data.values())}")
    print(f"\n⚠️  IMPORTANT: Review {output_csv} and add:")
    print(f"   - Installation dates and details")
    print(f"   - Peplink router information")
    print(f"   - Contact phone numbers")
    print(f"   - Billing/service addresses")
    print(f"   - Change default passwords!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python convert_mappings_to_v2.py <input_csv> [output_csv]")
        print("Example: python convert_mappings_to_v2.py config/client_mappings.csv config/clients_import.csv")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else 'config/clients_import.csv'
    
    if not Path(input_csv).exists():
        print(f"❌ Error: Input file not found: {input_csv}")
        sys.exit(1)
    
    convert_mappings_to_v2(input_csv, output_csv)

