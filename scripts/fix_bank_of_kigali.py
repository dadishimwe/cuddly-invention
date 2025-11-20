#!/usr/bin/env python3
"""
Fix Bank of Kigali client - remove incorrectly linked service lines
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2
import csv

db = DatabaseV2()

# Expected service lines for Bank of Kigali from CSV
expected_sls = {'SL-2568419-22145-74', 'SL-3603429-94334-75'}  # Bank of Kigali and BK HP II

# Load CSV to get correct mappings
csv_mappings = {}
with open('config/clients_import.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_mappings[row['service_line_id']] = row['company_name']

print("Fixing incorrectly linked service lines...")

# Find client 41
with db.get_connection() as conn:
    cursor = conn.cursor()
    
    # Get all service lines linked to client 41
    cursor.execute("SELECT service_line_id FROM client_service_lines WHERE client_id = ?", (41,))
    all_sls = [row['service_line_id'] for row in cursor.fetchall()]
    
    print(f"Client 41 currently has {len(all_sls)} service lines")
    
    # Find service lines that shouldn't be linked
    wrong_sls = [sl for sl in all_sls if sl not in expected_sls]
    
    print(f"Found {len(wrong_sls)} incorrectly linked service lines")
    
    # Unlink the wrong service lines
    for sl_id in wrong_sls:
        expected_client = csv_mappings.get(sl_id, 'Unknown')
        cursor.execute("DELETE FROM client_service_lines WHERE client_id = ? AND service_line_id = ?", (41, sl_id))
        print(f"  Unlinked: {sl_id} (should belong to: {expected_client})")
    
    conn.commit()
    
    # Fix the portal account email
    cursor.execute("SELECT id, email FROM client_accounts WHERE client_id = ?", (41,))
    account = cursor.fetchone()
    if account and account['email'] == 'ChangeMe123!':
        # Delete the wrong account
        cursor.execute("DELETE FROM client_accounts WHERE id = ?", (account['id'],))
        conn.commit()
        print(f"\n✅ Deleted incorrect portal account (had password '{account['email']}' as email)")
    
    # Check remaining service lines
    cursor.execute("SELECT service_line_id FROM client_service_lines WHERE client_id = ?", (41,))
    remaining = [row['service_line_id'] for row in cursor.fetchall()]
    print(f"\n✅ Client 41 now has {len(remaining)} service lines: {remaining}")

print("\n✅ Cleanup complete!")

