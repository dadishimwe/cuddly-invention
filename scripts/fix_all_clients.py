#!/usr/bin/env python3
"""
Comprehensive fix for all client issues:
1. Merge clients with same portal email
2. Create missing portal accounts
3. Link service lines to correct clients
4. Clean up duplicates
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2
import csv

db = DatabaseV2()

# Load fixed CSV
print("Loading CSV data...")
csv_data = {}
portal_to_sls = {}  # portal_email -> [service_line_ids]
for sl_id, data in csv_data.items():
    portal = data['portal_email']
    if portal not in portal_to_sls:
        portal_to_sls[portal] = []
    portal_to_sls[portal].append(sl_id)

with open('config/clients_import_fixed.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sl_id = row['service_line_id']
        portal_email = row.get('portal_account_email', '').strip()
        company = row['company_name']
        password = row.get('portal_account_password', '').strip() or 'ChangeMe123!'
        
        if portal_email and '@' in portal_email:
            csv_data[sl_id] = {
                'company': company,
                'portal_email': portal_email,
                'password': password
            }
            if portal_email not in portal_to_sls:
                portal_to_sls[portal_email] = []
            portal_to_sls[portal_email].append(sl_id)

print(f"Loaded {len(csv_data)} service lines from CSV")
print(f"Found {len(portal_to_sls)} unique portal emails\n")

print("=" * 70)
print("STEP 1: MERGE CLIENTS BY PORTAL EMAIL")
print("=" * 70)

# For each portal email, ensure one client with all service lines
for portal_email, sl_ids in portal_to_sls.items():
    if len(sl_ids) > 1:
        print(f"\nPortal: {portal_email} ({len(sl_ids)} kits)")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find or create main client
            cursor.execute("""
                SELECT c.id, c.company_name
                FROM clients c
                JOIN client_accounts ca ON c.id = ca.client_id
                WHERE ca.email = ?
                LIMIT 1
            """, (portal_email,))
            existing = cursor.fetchone()
            
            if existing:
                main_client_id = existing['id']
                print(f"  Using existing client: {existing['company_name']} (ID: {main_client_id})")
            else:
                # Find client by first service line
                cursor.execute("""
                    SELECT c.id, c.company_name
                    FROM clients c
                    JOIN client_service_lines csl ON c.id = csl.client_id
                    WHERE csl.service_line_id = ?
                    LIMIT 1
                """, (sl_ids[0],))
                first_client = cursor.fetchone()
                
                if first_client:
                    main_client_id = first_client['id']
                    print(f"  Using client with first service line: {first_client['company_name']} (ID: {main_client_id})")
                else:
                    # Create new client
                    main_company = csv_data[sl_ids[0]]['company']
                    main_client_id = db.create_client(
                        company_name=main_company,
                        status='active',
                        notes=f"Auto-merged client for portal {portal_email}"
                    )
                    print(f"  Created new client: {main_company} (ID: {main_client_id})")
            
            # Link all service lines to main client
            linked = 0
            for sl_id in sl_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO client_service_lines (client_id, service_line_id, assigned_at)
                    VALUES (?, ?, datetime('now'))
                """, (main_client_id, sl_id))
                if cursor.rowcount > 0:
                    linked += 1
            
            # Create portal account if doesn't exist
            cursor.execute("SELECT id FROM client_accounts WHERE client_id = ?", (main_client_id,))
            if not cursor.fetchone():
                password = csv_data[sl_ids[0]]['password']
                db.create_client_account(
                    client_id=main_client_id,
                    email=portal_email,
                    password=password,
                    name=csv_data[sl_ids[0]]['company']
                )
                print(f"  Created portal account: {portal_email}")
            
            conn.commit()
            if linked > 0:
                print(f"  ✅ Linked {linked} service lines")

print("\n" + "=" * 70)
print("STEP 2: CREATE PORTAL ACCOUNTS FOR SINGLE-KIT CLIENTS")
print("=" * 70)

# For single-kit clients, create portal accounts
single_kit_portals = {portal: sls[0] for portal, sls in portal_to_sls.items() if len(sls) == 1}

for portal_email, sl_id in single_kit_portals.items():
    data = csv_data[sl_id]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Find client with this service line
        cursor.execute("""
            SELECT c.id, c.company_name
            FROM clients c
            JOIN client_service_lines csl ON c.id = csl.client_id
            WHERE csl.service_line_id = ?
            LIMIT 1
        """, (sl_id,))
        result = cursor.fetchone()
        
        if result:
            result = dict(result)
            client_id = result['id']
            
            # Check if portal account exists
            cursor.execute("SELECT id FROM client_accounts WHERE client_id = ?", (client_id,))
            if not cursor.fetchone():
                # Check if email already used
                cursor.execute("SELECT client_id FROM client_accounts WHERE email = ?", (portal_email,))
                existing = cursor.fetchone()
                
                if existing:
                    # Link service line to existing client
                    target_client_id = dict(existing)['client_id']
                    if target_client_id != client_id:
                        # Check if already linked to target
                        cursor.execute("""
                            SELECT id FROM client_service_lines 
                            WHERE client_id = ? AND service_line_id = ?
                        """, (target_client_id, sl_id))
                        if not cursor.fetchone():
                            # Remove from old client first
                            cursor.execute("""
                                DELETE FROM client_service_lines 
                                WHERE service_line_id = ? AND client_id = ?
                            """, (sl_id, client_id))
                            # Link to new client
                            cursor.execute("""
                                INSERT INTO client_service_lines (client_id, service_line_id, assigned_at)
                                VALUES (?, ?, datetime('now'))
                            """, (target_client_id, sl_id))
                            conn.commit()
                            print(f"  Linked {sl_id} to existing client with portal {portal_email}")
                        else:
                            # Already linked, just remove from old client
                            cursor.execute("""
                                DELETE FROM client_service_lines 
                                WHERE service_line_id = ? AND client_id = ?
                            """, (sl_id, client_id))
                            conn.commit()
                else:
                    # Create portal account
                    try:
                        db.create_client_account(
                            client_id=client_id,
                            email=portal_email,
                            password=data['password'],
                            name=result['company_name']
                        )
                        print(f"  ✅ Created portal for {result['company_name']}: {portal_email}")
                    except Exception as e:
                        print(f"  ⚠️  Error: {e}")

print("\n" + "=" * 70)
print("STEP 3: CLEAN UP DUPLICATE/EMPTY CLIENTS")
print("=" * 70)

with db.get_connection() as conn:
    cursor = conn.cursor()
    
    # Find clients with no service lines
    cursor.execute("""
        SELECT c.id, c.company_name
        FROM clients c
        LEFT JOIN client_service_lines csl ON c.id = csl.client_id
        WHERE csl.id IS NULL
    """)
    empty_clients = cursor.fetchall()
    
    if empty_clients:
        print(f"Found {len(empty_clients)} empty clients:")
        for client in empty_clients:
            print(f"  Deleting: {client['company_name']} (ID: {client['id']})")
            cursor.execute("DELETE FROM client_contacts WHERE client_id = ?", (client['id'],))
            cursor.execute("DELETE FROM client_accounts WHERE client_id = ?", (client['id'],))
            cursor.execute("DELETE FROM clients WHERE id = ?", (client['id'],))
        conn.commit()
        print(f"  ✅ Deleted {len(empty_clients)} empty clients")
    else:
        print("✅ No empty clients found")

print("\n" + "=" * 70)
print("✅ ALL FIXES COMPLETE!")
print("=" * 70)

