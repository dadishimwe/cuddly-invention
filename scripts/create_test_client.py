#!/usr/bin/env python3
"""
Create a test client for portal testing
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2

# Initialize database
db = DatabaseV2()

# REPLACE THESE WITH YOUR ACTUAL VALUES:
SERVICE_LINE_ID = "SL-4639906-21306-74"  # ← Change this
CLIENT_NAME = "Tropical Plaza"  # ← Change this
CLIENT_EMAIL = "alice@tropicalplaza.rw"  # ← Change this
CLIENT_PASSWORD = "TestPassword"  # ← Change this

print("=" * 60)
print("Creating Test Client for Portal Testing")
print("=" * 60)

# Step 1: Create client organization
print(f"\n1. Creating client: {CLIENT_NAME}...")
client_id = db.create_client(
    company_name=CLIENT_NAME,
    status="active",
    billing_address="Test Address, Kigali"
)
print(f"   ✅ Client created with ID: {client_id}")

# Step 2: Assign service line
print(f"\n2. Assigning service line {SERVICE_LINE_ID}...")
try:
    db.assign_service_line_to_client(client_id, SERVICE_LINE_ID)
    print(f"   ✅ Service line assigned")
except Exception as e:
    print(f"   ⚠️  Error: {e}")
    print(f"   (This might be okay if already assigned)")

# Step 3: Create portal account
print(f"\n3. Creating portal account for {CLIENT_EMAIL}...")
try:
    account_id = db.create_client_account(
        client_id=client_id,
        email=CLIENT_EMAIL,
        password=CLIENT_PASSWORD,
        name="Test User"
    )
    print(f"   ✅ Portal account created with ID: {account_id}")
except Exception as e:
    print(f"   ⚠️  Error: {e}")
    if "UNIQUE constraint" in str(e):
        print(f"   (Account already exists - that's okay)")

# Step 4: Add primary contact
print(f"\n4. Adding primary contact...")
try:
    db.add_client_contact(
        client_id=client_id,
        name="Test Contact",
        email=CLIENT_EMAIL,
        role="primary",
        is_primary=True
    )
    print(f"   ✅ Contact added")
except Exception as e:
    print(f"   ⚠️  Error: {e}")

print("\n" + "=" * 60)
print("✅ Test Client Setup Complete!")
print("=" * 60)
print(f"\n📋 Login Credentials:")
print(f"   Email: {CLIENT_EMAIL}")
print(f"   Password: {CLIENT_PASSWORD}")
print(f"\n🌐 Client Portal URL: http://localhost:5001")
print(f"\n💡 Next: Start the client portal and test login")

