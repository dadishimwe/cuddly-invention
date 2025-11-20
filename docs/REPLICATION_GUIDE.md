# Replication Guide - Setting Up on a New Server

This guide covers **all scenarios** for setting up the project on a new VPS or server, handling edge cases and ensuring everything works.

## 🎯 Quick Answer

**Yes, your old `client_mappings.csv` import script still works!**

The `client_mappings` table is kept for backward compatibility in v2, so:
- ✅ Old import script works on both v1 and v2 databases
- ✅ Old CSV format still works
- ✅ You can use either old or new import methods
- ✅ Everything is backward compatible

---

## 📋 Setup Scenarios

### Scenario 1: Fresh Install (No Data)

**On new VPS:**

```bash
# 1. Clone/copy codebase
git clone <your-repo> /opt/starlink-manager
cd /opt/starlink-manager

# 2. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env  # Add your credentials

# 4. Run setup wizard (detects state automatically)
python3 scripts/setup.py
```

The wizard will:
- Detect no database exists
- Ask if you want v1 or v2
- Guide you through next steps

**Then import data:**
```bash
# Import service lines (works for both v1 and v2)
python3 scripts/import_csv.py service-lines config/service_lines.csv

# Option A: Use legacy format (still works!)
python3 scripts/import_csv.py client-mappings config/client_mappings.csv

# Option B: Use v2 format (more features)
python3 scripts/import_clients_v2.py config/clients_import.csv
```

---

### Scenario 2: Fresh Install with CSV Files

**You have CSV files ready:**

```bash
# 1-3. Same as Scenario 1

# 4. Import service lines
python3 scripts/import_csv.py service-lines config/service_lines.csv

# 5. Import clients (choose one):
# Legacy format (simple, works everywhere)
python3 scripts/import_csv.py client-mappings config/client_mappings.csv

# OR v2 format (full features)
python3 scripts/import_clients_v2.py config/clients_import.csv
```

**Both methods work!** Use whichever CSV format you have.

---

### Scenario 3: Restore from Backup (Database File)

**You have a database backup:**

```bash
# 1-3. Same as Scenario 1

# 4. Restore database
cp /path/to/backup/starlink.db.backup_YYYYMMDD data/starlink.db

# 5. Verify
python3 scripts/setup.py  # Will detect v1 or v2 and show status
```

**That's it!** Everything should work.

---

### Scenario 4: Restore from CSV Export

**You have CSV exports:**

```bash
# 1-3. Same as Scenario 1

# 4. Initialize database (creates schema)
python3 scripts/setup.py  # Choose v2

# 5. Import service lines
python3 scripts/import_csv.py service-lines config/service_lines.csv

# 6. Import clients
python3 scripts/import_clients_v2.py config/clients_backup.csv

# 7. Set portal account passwords (they weren't exported for security)
# Use admin interface or database directly
```

---

### Scenario 5: Migrate Existing v1 to v2

**You have an existing v1 database:**

```bash
# 1. Backup first!
cp data/starlink.db data/starlink.db.backup_$(date +%Y%m%d)

# 2. Run migration
python3 database/migrate_to_v2.py

# 3. Verify
python3 scripts/setup.py  # Should show v2 status

# 4. Your old client_mappings still work!
# But you can now also use v2 features
```

---

## 🔄 Edge Cases Handled

### Edge Case 1: Mixed v1 and v2 Data

**Situation:** You have both `client_mappings` (v1) and `clients` (v2) tables.

**Solution:** Both work simultaneously!
- Old import script → writes to `client_mappings`
- New import script → writes to `clients`
- Admin portal shows both
- Reports work with both

**No action needed** - the system handles this automatically.

---

### Edge Case 2: Fresh Install but Want v1

**Situation:** New server, want simple v1 setup.

**Solution:**
```bash
# Use old Database class (v1)
python3 -c "from database.db import Database; db = Database()"

# Import with old script
python3 scripts/import_csv.py service-lines config/service_lines.csv
python3 scripts/import_csv.py client-mappings config/client_mappings.csv
```

**Everything works** - v1 is still fully supported.

---

### Edge Case 3: v2 Database but Only Have Legacy CSV

**Situation:** Database is v2, but you only have `client_mappings.csv` (old format).

**Solution:**
```bash
# Option A: Import directly (works!)
python3 scripts/import_csv.py client-mappings config/client_mappings.csv

# Option B: Convert first, then import
python3 scripts/convert_mappings_to_v2.py config/client_mappings.csv config/clients_import.csv
python3 scripts/import_clients_v2.py config/clients_import.csv
```

**Both work!** Option A is faster, Option B gives you v2 features.

---

### Edge Case 4: No CSV Files, Only Database

**Situation:** You only have the database file, no CSV exports.

**Solution:**
```bash
# Just copy the database
cp backup/starlink.db data/starlink.db

# Verify it works
python3 scripts/setup.py
```

**That's it!** Database contains everything.

---

### Edge Case 5: Partial Data (Some Clients, Some Mappings)

**Situation:** Database has some v2 clients and some legacy mappings.

**Solution:** This is normal and handled automatically:
- Admin portal shows both
- Reports work with both
- You can gradually migrate mappings to clients
- Or leave as-is (both work fine)

**No action needed.**

---

## 📊 Import Script Compatibility Matrix

| Script | v1 Database | v2 Database | Notes |
|--------|-------------|-------------|-------|
| `import_csv.py service-lines` | ✅ Works | ✅ Works | Same for both |
| `import_csv.py client-mappings` | ✅ Works | ✅ Works | Legacy format, backward compatible |
| `import_clients_v2.py` | ❌ No | ✅ Works | Requires v2 database |
| `convert_mappings_to_v2.py` | N/A | N/A | Just converts CSV format |

---

## 🚀 Recommended Setup Flow for New VPS

### Step 1: Initial Setup
```bash
# Clone/copy code
cd /opt/starlink-manager

# Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env
```

### Step 2: Choose Your Path

**Path A: Quick Setup (Legacy)**
```bash
python3 scripts/setup.py  # Choose v1
python3 scripts/import_csv.py service-lines config/service_lines.csv
python3 scripts/import_csv.py client-mappings config/client_mappings.csv
```

**Path B: Full v2 Setup**
```bash
python3 scripts/setup.py  # Choose v2
python3 scripts/import_csv.py service-lines config/service_lines.csv
python3 scripts/import_clients_v2.py config/clients_import.csv
```

**Path C: Restore from Backup**
```bash
cp backup/starlink.db data/starlink.db
python3 scripts/setup.py  # Will detect and verify
```

### Step 3: Verify
```bash
# Check status
python3 scripts/setup.py

# Test admin portal
python3 web/app.py
# Visit http://localhost:5000

# Test client portal (if v2)
python3 web/client_portal.py
# Visit http://localhost:5001
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Service lines imported: `python3 scripts/manage.py list-service-lines`
- [ ] Client mappings/clients imported: Check admin portal
- [ ] Admin portal works: `python3 web/app.py`
- [ ] Can generate reports: Test in admin portal
- [ ] Client portal works (if v2): `python3 web/client_portal.py`
- [ ] Database file exists: `ls -lh data/starlink.db`

---

## 🔧 Troubleshooting

**"No such table: client_mappings"**
- Database not initialized
- Run: `python3 scripts/setup.py`

**"Service line not found"**
- Import service lines first
- Run: `python3 scripts/import_csv.py service-lines config/service_lines.csv`

**"Database already migrated to v2"**
- Normal if re-running migration
- Your data is safe
- Continue with v2 features

**"Import works but nothing shows in portal"**
- Check database path in `.env`: `STARLINK_DB_PATH`
- Verify data: `python3 scripts/manage.py list-mappings`

---

## 💡 Best Practices for Replication

1. **Always backup before migration**
   ```bash
   cp data/starlink.db data/starlink.db.backup_$(date +%Y%m%d)
   ```

2. **Keep CSV exports** (human-readable, easy to edit)

3. **Use setup wizard** - it handles edge cases automatically

4. **Test on staging first** if possible

5. **Document your setup** - note which method you used

---

## 📝 Summary

**Key Points:**
- ✅ Old `client_mappings.csv` import **still works** on v2
- ✅ Both v1 and v2 are supported
- ✅ Setup wizard handles all scenarios
- ✅ Backward compatibility maintained
- ✅ Multiple import methods available

**For new VPS:**
1. Run `python3 scripts/setup.py` (detects everything)
2. Import service lines (same for both)
3. Import clients (use whichever CSV format you have)
4. Done!

The system is designed to be **foolproof** - it works whether you use old or new methods, v1 or v2, CSV or database backup.

