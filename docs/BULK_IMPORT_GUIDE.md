# Bulk Import Guide - Loading All Client Data

This guide shows you how to import all your client data, installations, contacts, and portal accounts into the v2 database.

## 📋 Step-by-Step Process

### Step 1: Prepare Your Data

You have two options:

#### Option A: Single Comprehensive CSV (Recommended)
Create one CSV file with all data. Each row represents one service line/kit. If a client has multiple kits, create multiple rows with the same `company_name`.

#### Option B: Separate CSVs
- One CSV for clients and service line links
- One CSV for installations
- One CSV for contacts
- One CSV for portal accounts

**We'll use Option A (single CSV) for simplicity.**

---

### Step 2: Create Your Import CSV

Use the template: `config/clients_import_template.csv`

**Required columns:**
- `company_name` - Client organization name
- `service_line_id` - The Starlink service line ID (must exist in database)

**Optional columns (but recommended):**
- `primary_contact_name` - Contact person name
- `primary_contact_email` - Contact email
- `primary_contact_phone` - Contact phone
- `status` - active/suspended/cancelled (default: active)
- `service_start_date` - YYYY-MM-DD format
- `billing_address` - Billing address
- `service_address` - Service location address
- `installation_date` - YYYY-MM-DD format
- `technician_name` - Who installed it
- `installation_address` - Where it was installed
- `peplink_router_installed` - true/false
- `peplink_model` - e.g., "Balance 20X"
- `peplink_serial_number` - Router serial number
- `starlink_dish_serial` - Dish serial number
- `installation_notes` - Any notes
- `portal_account_email` - Email for client portal login
- `portal_account_password` - Password (will be hashed)
- `portal_account_name` - Display name for portal account

---

### Step 3: Example CSV Structure

```csv
company_name,service_line_id,primary_contact_name,primary_contact_email,primary_contact_phone,status,service_start_date,billing_address,service_address,installation_date,technician_name,installation_address,peplink_router_installed,peplink_model,peplink_serial_number,starlink_dish_serial,installation_notes,portal_account_email,portal_account_password,portal_account_name
Akagera Aviation,SL-3263656-24358-78,IT Manager,it@akageraaviation.com,+250788123456,active,2024-10-15,123 Main St Kigali,123 Main St Kigali,2024-10-15,John Doe,123 Main St Kigali,true,Balance 20X,PEP-12345,DISH-67890,Initial installation,admin@akageraaviation.com,SecurePass123!,Admin User
Akagera Aviation,SL-3263650-27699-83,IT Manager,it@akageraaviation.com,+250788123456,active,2024-10-15,123 Main St Kigali,456 Branch St Kigali,2024-10-20,John Doe,456 Branch St Kigali,true,Balance 20X,PEP-12346,DISH-67891,Second terminal,admin@akageraaviation.com,SecurePass123!,Admin User
Bank of Kigali,SL-2568419-22145-74,Network Team,pbana@bk.rw,+250788234567,active,2024-10-10,KN 3 Ave Kigali,KN 3 Ave Kigali,2024-10-10,Jane Smith,KN 3 Ave Kigali,true,Balance 580X,PEP-23456,DISH-78901,Main office installation,network@bk.rw,BKPass2024!,Network Team
```

**Key points:**
- Same `company_name` = same client (multiple kits)
- Portal account created once per client (first row wins)
- Primary contact created once per client (first row wins)
- Each service line gets its own installation record

---

### Step 4: Run the Import

```bash
cd /Users/HP/Downloads/starlink-manager

# Basic import (creates portal accounts)
python3 scripts/import_clients_v2.py config/your_clients.csv

# Import without creating portal accounts (if you want to do that separately)
python3 scripts/import_clients_v2.py config/your_clients.csv --no-portal-accounts

# Use custom database path
python3 scripts/import_clients_v2.py config/your_clients.csv --db /path/to/starlink.db
```

---

### Step 5: Verify the Import

```python
# Quick verification script
from database.db_v2 import DatabaseV2

db = DatabaseV2()

# Check clients
clients = db.get_all_clients()
print(f"Total clients: {len(clients)}")

for client in clients:
    print(f"\n{client['company_name']}:")
    service_lines = db.get_client_service_lines(client['id'])
    print(f"  Service lines: {len(service_lines)}")
    for sl in service_lines:
        print(f"    - {sl['service_line_id']} ({sl['nickname'] or 'No nickname'})")
```

Or check in the admin portal:
1. Go to `/admin/clients`
2. You should see all imported clients with their service lines and accounts

---

## 🔄 Workflow for Your Existing Data

Since you already have `client_mappings.csv`, here's the best approach:

### Option 1: Convert Existing CSV

1. **Export your current client_mappings.csv**
2. **Add the new columns** (installation data, portal accounts, etc.)
3. **Run the import**

### Option 2: Two-Step Process

1. **First, import basic client structure:**
   ```bash
   # This will create clients and link service lines from your existing CSV
   # You'll need to modify the import script or create a simple converter
   ```

2. **Then, add installation data separately:**
   - Use the admin interface (when we build it)
   - Or create a separate CSV with just installation data

---

## 📝 CSV Template with All Fields Explained

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `company_name` | ✅ Yes | Client organization name | "Akagera Aviation" |
| `service_line_id` | ✅ Yes | Starlink service line ID | "SL-3263656-24358-78" |
| `primary_contact_name` | No | Contact person name | "IT Manager" |
| `primary_contact_email` | No | Contact email | "it@akageraaviation.com" |
| `primary_contact_phone` | No | Contact phone | "+250788123456" |
| `status` | No | Client status | "active" |
| `service_start_date` | No | Service start date | "2024-10-15" |
| `billing_address` | No | Billing address | "123 Main St, Kigali" |
| `service_address` | No | Service location | "123 Main St, Kigali" |
| `installation_date` | No | Installation date | "2024-10-15" |
| `technician_name` | No | Installer name | "John Doe" |
| `installation_address` | No | Installation location | "123 Main St, Kigali" |
| `peplink_router_installed` | No | true/false | "true" |
| `peplink_model` | No | Router model | "Balance 20X" |
| `peplink_serial_number` | No | Router serial | "PEP-12345" |
| `starlink_dish_serial` | No | Dish serial | "DISH-67890" |
| `installation_notes` | No | Installation notes | "Initial installation" |
| `portal_account_email` | No | Portal login email | "admin@client.com" |
| `portal_account_password` | No | Portal password | "SecurePass123!" |
| `portal_account_name` | No | Portal display name | "Admin User" |

---

## 🎯 Quick Start Example

1. **Create your CSV file** (`config/my_clients.csv`):
   ```csv
   company_name,service_line_id,primary_contact_email,installation_date,peplink_router_installed,portal_account_email,portal_account_password
   Test Client,SL-3263656-24358-78,admin@test.com,2024-10-15,true,admin@test.com,TestPass123!
   ```

2. **Run import:**
   ```bash
   python3 scripts/import_clients_v2.py config/my_clients.csv
   ```

3. **Check results:**
   - Visit admin portal → Clients page
   - Or check client portal with the credentials you created

---

## ⚠️ Important Notes

1. **Service lines must exist first** - Run service line import before client import
2. **Duplicate handling:**
   - Same `company_name` = same client (multiple kits)
   - Portal account created once per client (first row)
   - Installation records: one per service line
3. **Passwords** - Will be securely hashed automatically
4. **Dates** - Must be in YYYY-MM-DD format
5. **Booleans** - Use "true"/"false" or "1"/"0"

---

## 🔧 Troubleshooting

**Error: "Service line not found"**
- Make sure you've imported service lines first
- Check the service_line_id is correct

**Error: "Portal account already exists"**
- The script will skip creating duplicate accounts
- This is normal if re-running import

**Missing data after import**
- Check the import summary output
- Verify your CSV has the correct column names
- Check for typos in dates (must be YYYY-MM-DD)

---

## 📊 After Import Checklist

- [ ] All clients appear in `/admin/clients`
- [ ] Service lines are linked correctly
- [ ] Installation records show in client portal
- [ ] Portal accounts can log in
- [ ] Primary contacts are listed
- [ ] Multi-kit clients show all their terminals

---

## Next Steps

After importing:
1. Test client portal logins
2. Verify installation data displays correctly
3. Add any missing installation details via admin interface
4. Create additional contacts if needed
5. Set up portal accounts for additional users

