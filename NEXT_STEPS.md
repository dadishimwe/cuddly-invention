# Next Steps - Action Plan

## ✅ Phase 1: Foundation (Do This First)

### 1. Complete Database Migration
```bash
cd /Users/HP/Downloads/starlink-manager
python3 database/migrate_to_v2.py
```

**Verify success:**
```bash
python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2(); print('✅ Migration successful')"
```

### 2. Test Existing Functionality
- [ ] Start team portal: `python3 web/app.py`
- [ ] Log in and verify you can see:
  - Service lines
  - Client mappings
  - Generate reports
- [ ] Test report generation works

### 3. Create First Test Client
```python
# Run this in Python shell
from database.db_v2 import DatabaseV2
db = DatabaseV2()

# Get an existing service line ID from your mappings
# Then create client:
client_id = db.create_client(
    company_name="Test Company",
    status="active"
)

# Assign service line
db.assign_service_line_to_client(client_id, "SL-3263656-24358-78")

# Create portal account
db.create_client_account(
    client_id=client_id,
    email="test@example.com",
    password="Test123!",
    name="Test User"
)
```

### 4. Test Client Portal
```bash
# Terminal 1: Team portal
python3 web/app.py

# Terminal 2: Client portal  
python3 web/client_portal.py
```

Visit `http://localhost:5001` and log in with test credentials.

---

## 📊 Phase 2: Data Migration (This Week)

### 5. Verify Migration Data
Check that your existing `client_mappings` were converted to `clients`:
```python
from database.db_v2 import DatabaseV2
db = DatabaseV2()

clients = db.get_all_clients()
print(f"Found {len(clients)} clients")
for client in clients:
    print(f"  - {client['company_name']}")
```

### 6. Add Installation Records
For each service line, add installation details:
```python
from database.db_v2 import DatabaseV2
db = DatabaseV2()

# Example - update with your actual data
installations = [
    {
        "service_line_id": "SL-3263656-24358-78",
        "installation_date": "2024-10-15",
        "technician_name": "Your Tech Name",
        "peplink_router_installed": True,
        "peplink_model": "Balance 20X",
        "installation_address": "Client Address"
    },
    # Add more...
]

for inst in installations:
    db.add_installation(**inst)
```

### 7. Import Historical Data (Optional - Can Wait)
```bash
# Test with recent data first
python3 scripts/import_historical_data.py \
    --start-date 2024-11-01 \
    --cycles 1 \
    --delay 2

# If successful, import full history
python3 scripts/import_historical_data.py \
    --start-date 2024-10-01 \
    --cycles 12 \
    --delay 2
```

---

## 🚀 Phase 3: Production Deployment (Next Week)

### 8. Update Team Portal for v2
- Update `web/app.py` to use `DatabaseV2` instead of `Database`
- Test all routes work with new schema

### 9. Deploy Both Portals
- Team Portal: `admin.zuba.dadishimwe.com`
- Client Portal: `zuba.dadishimwe.com`
- Set up systemd services
- Configure Nginx reverse proxy
- Set up SSL certificates

### 10. Create Client Portal Accounts
For each client organization:
1. Create client in database
2. Assign their service lines
3. Create portal account
4. Send login credentials

---

## 🎨 Phase 4: Enhancements (Future)

### 11. Build Missing UI Components
- Installation management forms
- Contact management interface  
- Audit log viewer
- PDF report generation

### 12. Add Advanced Features
- Support ticket system
- Notification alerts
- Advanced analytics
- Mobile app (optional)

---

## 🔍 Quick Verification Checklist

After migration, verify:

- [ ] Database migration completed without errors
- [ ] Backup file created in `data/` directory
- [ ] Team portal still works (`python3 web/app.py`)
- [ ] Can see service lines and mappings
- [ ] Client portal starts (`python3 web/client_portal.py`)
- [ ] Can create test client and log in
- [ ] Historical data import script exists and runs
- [ ] All new tables exist in database

---

## 🆘 If Something Breaks

1. **Restore from backup:**
   ```bash
   cp data/starlink.db.backup_YYYYMMDD_HHMMSS data/starlink.db
   ```

2. **Check migration status:**
   ```python
   from database.db_v2 import DatabaseV2
   db = DatabaseV2()
   # Check if clients table exists
   ```

3. **Rollback:** Use the backup file created during migration

---

## 📞 Next Actions

**Right now:**
1. Run the migration: `python3 database/migrate_to_v2.py`
2. Verify it worked
3. Test team portal still works
4. Create one test client
5. Test client portal

**This week:**
- Migrate all existing clients
- Add installation records
- Test historical data import

**Next week:**
- Deploy to production
- Create client accounts
- Go live!

