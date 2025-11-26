#!/usr/bin/env python3
"""
Management CLI
Manage service lines, client mappings, and view reports
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database
from database.db_v2 import DatabaseV2


def list_service_lines(db: Database, active_only: bool = True):
    """List all service lines"""
    service_lines = db.get_service_lines(active_only=active_only)
    
    if not service_lines:
        print("No service lines found.")
        return
    
    table_data = []
    for sl in service_lines:
        table_data.append([
            sl['id'],
            sl['account_number'],
            sl['service_line_id'],
            sl['nickname'] or 'N/A',
            '✓' if sl['active'] else '✗'
        ])
    
    headers = ['ID', 'Account', 'Service Line ID', 'Nickname', 'Active']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    print(f"\nTotal: {len(service_lines)} service line(s)")


def list_client_mappings(db: Database, active_only: bool = True):
    """List all client mappings"""
    mappings = db.get_client_mappings(active_only=active_only)
    
    if not mappings:
        print("No client mappings found.")
        return
    
    table_data = []
    for m in mappings:
        last_sent = m['last_sent_at']
        if last_sent:
            try:
                last_sent = datetime.fromisoformat(last_sent).strftime('%Y-%m-%d %H:%M')
            except:
                pass
        else:
            last_sent = 'Never'
        
        table_data.append([
            m['id'],
            m['client_name'],
            m['service_line_id'],
            m['nickname'] or 'N/A',
            m['primary_email'],
            m['report_frequency'],
            last_sent,
            '✓' if m['active'] else '✗'
        ])
    
    headers = ['ID', 'Client', 'Service Line', 'Nickname', 'Email', 'Frequency', 'Last Sent', 'Active']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    print(f"\nTotal: {len(mappings)} mapping(s)")


def view_mapping_details(db: Database, mapping_id: int):
    """View detailed information about a client mapping"""
    mapping = db.get_client_mapping(mapping_id)
    
    if not mapping:
        print(f"❌ Mapping ID {mapping_id} not found")
        return
    
    print("\n" + "="*60)
    print(f"CLIENT MAPPING DETAILS (ID: {mapping_id})")
    print("="*60)
    print(f"Client Name:       {mapping['client_name']}")
    print(f"Service Line ID:   {mapping['service_line_id']}")
    print(f"Terminal Nickname: {mapping['nickname'] or 'N/A'}")
    print(f"Account Number:    {mapping['account_number']}")
    print(f"Primary Email:     {mapping['primary_email']}")
    print(f"CC Emails:         {mapping['cc_emails'] or 'None'}")
    print(f"Report Frequency:  {mapping['report_frequency']}")
    print(f"Active:            {'Yes' if mapping['active'] else 'No'}")
    print(f"Last Sent:         {mapping['last_sent_at'] or 'Never'}")
    print(f"Created:           {mapping['created_at']}")
    print("="*60)
    
    # Show recent report logs
    logs = db.get_report_logs(limit=10, mapping_id=mapping_id)
    if logs:
        print(f"\nRECENT REPORTS ({len(logs)} most recent):")
        print("-"*60)
        
        log_data = []
        for log in logs:
            log_data.append([
                log['sent_at'][:16] if log['sent_at'] else 'N/A',
                log['report_type'],
                log['status'],
                f"{log['total_usage_gb']:.2f} GB" if log['total_usage_gb'] else 'N/A',
                log['days_included'] or 'N/A'
            ])
        
        headers = ['Sent At', 'Type', 'Status', 'Usage', 'Days']
        print(tabulate(log_data, headers=headers, tablefmt='simple'))


def view_report_logs(db: Database, limit: int = 50):
    """View recent report logs"""
    logs = db.get_report_logs(limit=limit)
    
    if not logs:
        print("No report logs found.")
        return
    
    table_data = []
    for log in logs:
        table_data.append([
            log['id'],
            log['sent_at'][:16] if log['sent_at'] else 'N/A',
            log['service_line_id'][:20] + '...' if len(log['service_line_id']) > 20 else log['service_line_id'],
            log['recipient_email'],
            log['status'],
            f"{log['total_usage_gb']:.2f} GB" if log['total_usage_gb'] else 'N/A'
        ])
    
    headers = ['ID', 'Sent At', 'Service Line', 'Recipient', 'Status', 'Usage']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    print(f"\nShowing {len(logs)} most recent log(s)")


def init_database(v2: bool = False):
    """Initialize database with schema"""
    print("\n" + "="*60)
    print("DATABASE INITIALIZATION")
    print("="*60)
    
    if v2:
        print("Initializing with v2 schema...")
        db = DatabaseV2()
        # The DatabaseV2 constructor automatically creates tables
        print("✅ Database initialized with v2 schema")
    else:
        print("Initializing with v1 schema...")
        db = Database()
        # The Database constructor automatically creates tables
        print("✅ Database initialized with v1 schema")
    
    print("Database ready at:", db.db_path)
    print("="*60)


def add_service_line_interactive(db: Database):
    """Interactively add a service line"""
    print("\n" + "="*60)
    print("ADD NEW SERVICE LINE")
    print("="*60)
    
    account_number = input("Account Number: ").strip()
    service_line_id = input("Service Line ID: ").strip()
    nickname = input("Nickname (optional): ").strip() or None
    service_line_number = input("Service Line Number (optional): ").strip() or None
    active = input("Active? (y/n) [y]: ").strip().lower() != 'n'
    
    if not account_number or not service_line_id:
        print("❌ Account number and service line ID are required")
        return
    
    try:
        db.add_service_line(account_number, service_line_id, nickname, 
                           service_line_number, active)
        print(f"✅ Service line {service_line_id} added successfully")
    except Exception as e:
        print(f"❌ Error: {e}")


def add_client_mapping_interactive(db: Database):
    """Interactively add a client mapping"""
    print("\n" + "="*60)
    print("ADD NEW CLIENT MAPPING")
    print("="*60)
    
    # Show available service lines
    print("\nAvailable Service Lines:")
    service_lines = db.get_service_lines(active_only=True)
    for sl in service_lines:
        print(f"  - {sl['service_line_id']} ({sl['nickname'] or 'No nickname'})")
    print()
    
    client_name = input("Client Name: ").strip()
    service_line_id = input("Service Line ID: ").strip()
    primary_email = input("Primary Email: ").strip()
    cc_emails = input("CC Emails (comma-separated, optional): ").strip() or None
    report_frequency = input("Report Frequency (daily/weekly/on_demand) [on_demand]: ").strip() or 'on_demand'
    active = input("Active? (y/n) [y]: ").strip().lower() != 'n'
    
    if not client_name or not service_line_id or not primary_email:
        print("❌ Client name, service line ID, and primary email are required")
        return
    
    # Verify service line exists
    if not db.get_service_line(service_line_id):
        print(f"❌ Service line {service_line_id} not found")
        return
    
    try:
        db.add_client_mapping(client_name, service_line_id, primary_email,
                             cc_emails, active, report_frequency)
        print(f"✅ Client mapping for {client_name} added successfully")
    except Exception as e:
        print(f"❌ Error: {e}")


def update_mapping_status(db: Database, mapping_id: int, active: bool):
    """Update mapping active status"""
    try:
        db.update_client_mapping(mapping_id, active=active)
        status = "activated" if active else "deactivated"
        print(f"✅ Mapping {mapping_id} {status} successfully")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage service lines, client mappings, and reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all service lines
  python manage.py list-service-lines

  # List all client mappings
  python manage.py list-mappings

  # View mapping details
  python manage.py view-mapping --id 1

  # Add service line interactively
  python manage.py add-service-line

  # Add client mapping interactively
  python manage.py add-mapping

  # View recent report logs
  python manage.py logs

  # Deactivate a mapping
  python manage.py deactivate-mapping --id 1
        """
    )
    
    parser.add_argument(
        'command',
        choices=[
            'init', 'list-service-lines', 'list-mappings', 'view-mapping',
            'add-service-line', 'add-mapping', 'logs',
            'activate-mapping', 'deactivate-mapping'
        ],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--v2',
        action='store_true',
        help='Use v2 schema (for init command)'
    )
    
    parser.add_argument(
        '--id',
        type=int,
        help='Mapping ID (for view-mapping, activate-mapping, deactivate-mapping)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Include inactive items'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Limit for logs (default: 50)'
    )
    
    parser.add_argument(
        '--db',
        default='../data/starlink.db',
        help='Path to database file'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'init':
            init_database(v2=args.v2)
            return
        
        # Initialize database for other commands
        db = Database(args.db)
        
        if args.command == 'list-service-lines':
            list_service_lines(db, active_only=not args.all)
        
        elif args.command == 'list-mappings':
            list_client_mappings(db, active_only=not args.all)
        
        elif args.command == 'view-mapping':
            if not args.id:
                print("❌ Error: --id is required")
                sys.exit(1)
            view_mapping_details(db, args.id)
        
        elif args.command == 'add-service-line':
            add_service_line_interactive(db)
        
        elif args.command == 'add-mapping':
            add_client_mapping_interactive(db)
        
        elif args.command == 'logs':
            view_report_logs(db, limit=args.limit)
        
        elif args.command == 'activate-mapping':
            if not args.id:
                print("❌ Error: --id is required")
                sys.exit(1)
            update_mapping_status(db, args.id, True)
        
        elif args.command == 'deactivate-mapping':
            if not args.id:
                print("❌ Error: --id is required")
                sys.exit(1)
            update_mapping_status(db, args.id, False)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
