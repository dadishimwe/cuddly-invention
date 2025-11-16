#!/usr/bin/env python3
"""
Direct Starlink API CLI Tool
Query the Starlink API directly from terminal without database storage.
Returns raw JSON responses.
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from starlink.StarlinkClient import StarlinkClient


def print_json(data, pretty=True):
    """Print JSON data in a readable format"""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def list_accounts(client: StarlinkClient):
    """List all accounts"""
    print("📋 Fetching accounts...")
    accounts = client.accounts.list_accounts()
    print_json(accounts)
    return accounts


def list_service_lines(client: StarlinkClient, account_number: str):
    """List all service lines (terminals) for an account"""
    print(f"📡 Fetching service lines for account {account_number}...")
    service_lines = client.service_lines.list_service_lines(account_number)
    print_json(service_lines)
    return service_lines


def get_service_line_details(client: StarlinkClient, account_number: str, service_line_id: str):
    """Get details for a specific service line"""
    print(f"🔍 Fetching details for service line {service_line_id}...")
    details = client.service_lines.get_service_line(account_number, service_line_id)
    print_json(details)
    return details


def get_usage_data(
    client: StarlinkClient,
    account_number: str,
    service_lines: list = None,
    cycles_to_fetch: int = 1,
    target_date: str = None
):
    """Get usage data for service lines"""
    print(f"📊 Fetching usage data...")
    print(f"   Account: {account_number}")
    if service_lines:
        print(f"   Service Lines: {service_lines}")
    print(f"   Cycles to fetch: {cycles_to_fetch}")
    if target_date:
        print(f"   Target billing cycle: {target_date}")
    
    usage_data = client.usage.get_live_usage_data(
        account_number,
        service_lines=service_lines,
        cycles_to_fetch=cycles_to_fetch,
        target_billing_cycle=target_date
    )
    
    print_json(usage_data)
    return usage_data


def get_raw_api_response(client: StarlinkClient, account_number: str, cycles: int = 1):
    """Get raw API response without processing"""
    print(f"🔌 Fetching raw API response...")
    endpoint = f"/enterprise/v1/accounts/{account_number}/billing-cycles/query"
    payload = {
        "previousBillingCycles": cycles - 1,
        "pageLimit": 50,
        "pageIndex": 0
    }
    
    response = client.post(endpoint, data=payload)
    print_json(response)
    return response


def filter_usage_by_date_range(usage_data: dict, start_date: str, end_date: str):
    """Filter usage data by date range"""
    print(f"\n📅 Filtering usage data from {start_date} to {end_date}...")
    
    filtered = {}
    for sl_id, data in usage_data.items():
        daily_usage = data.get('daily_usage', [])
        filtered_daily = [
            day for day in daily_usage
            if start_date <= day.get('date', '') <= end_date
        ]
        
        if filtered_daily:
            filtered[sl_id] = {
                **data,
                'daily_usage': filtered_daily
            }
    
    print_json(filtered)
    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Direct Starlink API CLI - Query API without database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all accounts
  python starlink_api_cli.py accounts

  # List all terminals for an account
  python starlink_api_cli.py terminals --account ACC-12345-67890-12

  # Get usage data for all terminals
  python starlink_api_cli.py usage --account ACC-12345-67890-12

  # Get usage for specific terminals
  python starlink_api_cli.py usage --account ACC-12345-67890-12 \\
      --service-lines SL-123-456-78 SL-987-654-32

  # Get usage for date range
  python starlink_api_cli.py usage --account ACC-12345-67890-12 \\
      --start-date 2025-10-13 --end-date 2025-11-09

  # Get raw API response
  python starlink_api_cli.py raw --account ACC-12345-67890-12
        """
    )
    
    parser.add_argument(
        'command',
        choices=['accounts', 'terminals', 'usage', 'raw', 'details'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--account',
        help='Account number (required for terminals, usage, raw, details)'
    )
    
    parser.add_argument(
        '--service-lines',
        nargs='+',
        help='Service line IDs (for usage or details command)'
    )
    
    parser.add_argument(
        '--service-line',
        help='Single service line ID (for details command)'
    )
    
    parser.add_argument(
        '--cycles',
        type=int,
        default=1,
        help='Number of billing cycles to fetch (default: 1)'
    )
    
    parser.add_argument(
        '--target-date',
        help='Target billing cycle date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for filtering usage (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for filtering usage (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--compact',
        action='store_true',
        help='Output compact JSON (no pretty printing)'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    CLIENT_ID = os.getenv("STARLINK_CLIENT_ID")
    CLIENT_SECRET = os.getenv("STARLINK_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Error: STARLINK_CLIENT_ID and STARLINK_CLIENT_SECRET must be set in .env file")
        sys.exit(1)
    
    # Initialize client
    client = StarlinkClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    
    try:
        if args.command == 'accounts':
            list_accounts(client)
        
        elif args.command == 'terminals':
            if not args.account:
                print("❌ Error: --account is required for terminals command")
                sys.exit(1)
            list_service_lines(client, args.account)
        
        elif args.command == 'details':
            if not args.account or not args.service_line:
                print("❌ Error: --account and --service-line are required for details command")
                sys.exit(1)
            get_service_line_details(client, args.account, args.service_line)
        
        elif args.command == 'usage':
            if not args.account:
                print("❌ Error: --account is required for usage command")
                sys.exit(1)
            
            usage_data = get_usage_data(
                client,
                args.account,
                service_lines=args.service_lines,
                cycles_to_fetch=args.cycles,
                target_date=args.target_date
            )
            
            # Filter by date range if provided
            if args.start_date and args.end_date:
                filter_usage_by_date_range(usage_data, args.start_date, args.end_date)
        
        elif args.command == 'raw':
            if not args.account:
                print("❌ Error: --account is required for raw command")
                sys.exit(1)
            get_raw_api_response(client, args.account, args.cycles)
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

