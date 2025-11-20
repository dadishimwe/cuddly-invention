# Backup and Migration Guide

This guide explains how to backup your data and migrate to a new server (like a VPS).

## 📦 What to Backup

### Essential Files:

1. **Database file**: `data/starlink.db`
   - Contains all your data (clients, service lines, usage history, etc.)

2. **CSV export files** (recommended for easy migration):
   - `config/clients_export.csv` - All client data
   - `config/service_lines.csv` - Service lines
   - Original `config/client_mappings.csv` - Legacy backup

3. **Configuration files**:
   - `.env` - Environment variables (API keys, SMTP settings, etc.)
   - `config/nginx.conf` - Nginx configuration
   - `config/starlink-manager.service` - Systemd service file

4. **Code** (if not using Git):
   - Entire project directory

---

## 🔄 Migration Workflow

### Option 1: Full Database Backup (Fastest)

**On old server:**
```bash
# Backup database
cp data/starlink.db data/starlink.db.backup_$(date +%Y%m%d)

# Copy to new server
scp data/starlink.db.backup_* user@new-server:/path/to/starlink-manager/data/
```

**On new server:**
```bash
# Restore database
cp data/starlink.db.backup_YYYYMMDD data/starlink.db

# Verify
python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2(); print(f'Clients: {len(db.get_all_clients())}')"
```

**Pros:**
- ✅ Fastest method
- ✅ Preserves all data including usage history
- ✅ Preserves all relationships

**Cons:**
- ⚠️ Database file can be large
- ⚠️ Must be same database version

---

### Option 2: CSV Export/Import (Recommended for Fresh Setup)

**On old server:**
```bash
# Export service lines
python3 scripts/import_csv.py service-lines config/service_lines.csv --db data/starlink.db > /dev/null 2>&1 || true

# Export clients (v2 format)
python3 scripts/export_clients_v2.py config/clients_backup.csv

# Copy files to new server
scp config/clients_backup.csv user@new-server:/path/to/starlink-manager/config/
scp config/service_lines.csv user@new-server:/path/to/starlink-manager/config/
```

**On new server:**
```bash
# 1. Initialize database (creates schema)
python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2()"

# 2. Import service lines
python3 scripts/import_csv.py service-lines config/service_lines.csv

# 3. Import clients
python3 scripts/import_clients_v2.py config/clients_backup.csv --no-portal-accounts

# 4. Set new passwords for portal accounts (or use password reset)
```

**Pros:**
- ✅ Human-readable format
- ✅ Easy to review/edit before import
- ✅ Works across database versions
- ✅ Can selectively import

**Cons:**
- ⚠️ Doesn't include usage history (must re-import)
- ⚠️ Passwords not exported (security)

---

### Option 3: Git + CSV (Best for Code + Data)

**Setup:**
```bash
# Add CSV files to Git (but NOT .env or database)
git add config/*.csv
git commit -m "Backup client data"
git push
```

**On new server:**
```bash
# Clone repository
git clone https://github.com/your-repo/starlink-manager.git
cd starlink-manager

# Import data
python3 scripts/import_csv.py service-lines config/service_lines.csv
python3 scripts/import_clients_v2.py config/clients_backup.csv
```

**Pros:**
- ✅ Version control for data
- ✅ Easy to track changes
- ✅ Can rollback if needed

**Cons:**
- ⚠️ CSV files in Git (but that's okay for this use case)

---

## 📋 Complete Migration Checklist

### Before Migration:

- [ ] Export current data:
  ```bash
  python3 scripts/export_clients_v2.py config/clients_backup_$(date +%Y%m%d).csv
  ```
- [ ] Backup database:
  ```bash
  cp data/starlink.db data/starlink.db.backup_$(date +%Y%m%d)
  ```
- [ ] Backup `.env` file (securely):
  ```bash
  # Copy to secure location, don't commit to Git
  ```
- [ ] Document any custom configurations

### On New Server:

- [ ] Clone/copy codebase
- [ ] Set up virtual environment
- [ ] Install dependencies
- [ ] Copy `.env` file (with updated paths if needed)
- [ ] Initialize database:
  ```bash
  python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2()"
  ```
- [ ] Import service lines:
  ```bash
  python3 scripts/import_csv.py service-lines config/service_lines.csv
  ```
- [ ] Import clients:
  ```bash
  python3 scripts/import_clients_v2.py config/clients_backup.csv
  ```
- [ ] Import historical usage (if needed):
  ```bash
  python3 scripts/import_historical_data.py --start-date 2024-10-01 --cycles 12
  ```
- [ ] Test client portal logins
- [ ] Test admin portal
- [ ] Set up systemd services
- [ ] Configure Nginx
- [ ] Set up SSL certificates

---

## 🔐 Security Notes

### What NOT to commit to Git:

- ❌ `.env` file (contains secrets)
- ❌ `data/starlink.db` (database file)
- ❌ `*.backup` files
- ❌ Any files with passwords

### What's safe to commit:

- ✅ CSV files (no passwords in export)
- ✅ Configuration templates
- ✅ Code files
- ✅ Documentation

### Password Handling:

When exporting, passwords are **never** included in CSV files. After migration:

1. **Option A: Set new passwords**
   ```python
   from database.db_v2 import DatabaseV2
   db = DatabaseV2()
   db.update_client_account_password(account_id, "NewSecurePassword123!")
   ```

2. **Option B: Use password reset** (if you implement that feature)

3. **Option C: Manual setup** - Create portal accounts manually after import

---

## 🔄 Regular Backup Strategy

### Automated Daily Backup:

Create a cron job:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * cd /opt/starlink-manager && python3 scripts/export_clients_v2.py config/backups/clients_$(date +\%Y\%m\%d).csv && cp data/starlink.db data/backups/starlink_$(date +\%Y\%m\%d).db
```

### Weekly Full Backup:

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/opt/starlink-manager/backups"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Export CSV
python3 scripts/export_clients_v2.py $BACKUP_DIR/clients_$DATE.csv

# Backup database
cp data/starlink.db $BACKUP_DIR/starlink_$DATE.db

# Keep only last 4 weeks
find $BACKUP_DIR -name "*.db" -mtime +28 -delete
find $BACKUP_DIR -name "*.csv" -mtime +28 -delete

echo "Backup complete: $DATE"
```

---

## 📊 Data Export Commands

### Export Everything:

```bash
# Export clients (v2 format)
python3 scripts/export_clients_v2.py config/clients_export.csv

# Export service lines (if you have a script for this)
# Or just keep your original config/service_lines.csv
```

### Export Specific Data:

```python
# Custom export script
from database.db_v2 import DatabaseV2
import csv

db = DatabaseV2()

# Export only active clients
clients = db.get_all_clients(status='active')
# ... write to CSV
```

---

## 🚀 Quick Migration Script

Save this as `scripts/migrate_to_new_server.sh`:

```bash
#!/bin/bash
# Quick migration helper

echo "📦 Creating backup package..."

BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Export data
python3 scripts/export_clients_v2.py $BACKUP_DIR/clients.csv
cp config/service_lines.csv $BACKUP_DIR/ 2>/dev/null || true
cp config/client_mappings.csv $BACKUP_DIR/ 2>/dev/null || true

# Backup database
cp data/starlink.db $BACKUP_DIR/starlink.db

# Create info file
cat > $BACKUP_DIR/README.txt <<EOF
Migration Backup - $(date)
==========================

Files included:
- clients.csv: All client data (v2 format)
- service_lines.csv: Service lines
- client_mappings.csv: Legacy mappings (backup)
- starlink.db: Full database backup

To restore:
1. Copy files to new server
2. Initialize database: python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2()"
3. Import service lines: python3 scripts/import_csv.py service-lines service_lines.csv
4. Import clients: python3 scripts/import_clients_v2.py clients.csv
EOF

echo "✅ Backup created in: $BACKUP_DIR"
echo "📤 Copy this directory to your new server"
```

---

## ✅ Verification After Migration

```bash
# Check clients
python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2(); clients = db.get_all_clients(); print(f'Clients: {len(clients)}')"

# Check service lines
python3 scripts/manage.py list-service-lines --db data/starlink.db

# Check portal accounts
python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2(); [print(f\"{a['email']}\") for a in db.get_connection().execute('SELECT email FROM client_accounts').fetchall()]"
```

---

## 💡 Best Practice

**Keep both:**
1. **CSV exports** - Easy to read, edit, version control
2. **Database backups** - Complete data, faster restore

**Regular schedule:**
- Daily: CSV export (lightweight)
- Weekly: Full database backup
- Before major changes: Both

This way you always have a way to restore, whether you need a quick CSV import or a full database restore.

