#!/bin/bash
set -e

echo "=========================================="
echo "Starlink Manager - Docker Entrypoint"
echo "=========================================="

# Wait a moment for any dependencies
sleep 2

# Initialize database if it doesn't exist
if [ ! -f /app/data/starlink_manager.db ]; then
    echo "📦 Database not found. Initializing v2 schema..."
    python3 /app/scripts/manage.py init --v2
    echo "✅ Database initialized with v2 schema"
else
    echo "✅ Database found at /app/data/starlink_manager.db"
    
    # Check if migration to v2 is needed
    echo "🔍 Checking database schema version..."
    python3 -c "
import sys
sys.path.insert(0, '/app')
from database.db_v2 import DatabaseV2
db = DatabaseV2()
try:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='clients'\")
        if not cursor.fetchone():
            print('⚠️  V2 tables not found. Migration needed.')
            sys.exit(1)
        else:
            print('✅ V2 schema detected')
except Exception as e:
    print(f'⚠️  Error checking schema: {e}')
    sys.exit(1)
" || {
    echo "🔄 Migrating database to v2 schema..."
    python3 /app/database/migrate_to_v2.py
    echo "✅ Migration completed"
}
fi

# Create default admin user if none exists
echo "👤 Checking for admin users..."
python3 -c "
import sys
sys.path.insert(0, '/app')
from database.db import Database
from werkzeug.security import generate_password_hash
import secrets
import os

db = Database()
users = db.get_all_team_members(active_only=False)

if not users:
    print('📝 No users found. Creating default admin user...')
    default_password = os.getenv('DEFAULT_ADMIN_PASSWORD', secrets.token_urlsafe(16))
    password_hash = generate_password_hash(default_password)
    db.add_team_member('admin', password_hash, 'Administrator', 
                      os.getenv('ADMIN_EMAIL', 'admin@example.com'), 'admin')
    print('✅ Default admin user created:')
    print(f'   Username: admin')
    print(f'   Password: {default_password}')
    print('   ⚠️  PLEASE CHANGE THIS PASSWORD AFTER FIRST LOGIN!')
else:
    print(f'✅ Found {len(users)} existing user(s)')
"

echo "=========================================="
echo "🚀 Starting application..."
echo "=========================================="

# Execute the main command
exec "$@"
