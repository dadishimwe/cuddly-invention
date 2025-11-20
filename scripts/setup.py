#!/usr/bin/env python3
"""
Universal Setup Script - Handles all scenarios (fresh install, v1, v2, migration)
Detects current state and guides you through setup
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database
from database.db_v2 import DatabaseV2
import sqlite3


def detect_database_state(db_path):
    """Detect what state the database is in"""
    if not os.path.exists(db_path):
        return 'none'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for v2 tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
    has_clients = cursor.fetchone() is not None
    
    # Check for v1 tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_mappings'")
    has_mappings = cursor.fetchone() is not None
    
    # Check for schema version
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
    has_version = cursor.fetchone() is not None
    
    conn.close()
    
    if has_clients:
        return 'v2'
    elif has_mappings and not has_clients:
        return 'v1'
    else:
        return 'unknown'


def check_service_lines_exist(db_path):
    """Check if service lines are imported"""
    try:
        db = Database(db_path)
        service_lines = db.get_service_lines(active_only=False)
        return len(service_lines) > 0
    except:
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Zuba Broadband Starlink Manager - Setup Wizard          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Detect database path
    db_path = os.getenv('STARLINK_DB_PATH')
    if not db_path:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'starlink.db')
    
    db_path = os.path.abspath(db_path)
    
    print(f"📁 Database: {db_path}")
    
    # Detect state
    state = detect_database_state(db_path)
    
    print(f"\n🔍 Detected state: {state.upper()}")
    print("=" * 60)
    
    if state == 'none':
        print("\n✨ Fresh Installation Detected")
        print("\nYou have two options:")
        print("\n1. Start with v2 (Recommended - Full Features)")
        print("   - Multi-kit client support")
        print("   - Client portal")
        print("   - Installation tracking")
        print("   - Historical data import")
        print("\n2. Start with v1 (Legacy - Simple)")
        print("   - Basic client mappings")
        print("   - Report generation")
        print("   - Can migrate to v2 later")
        
        choice = input("\nChoose option (1 or 2) [1]: ").strip() or '1'
        
        if choice == '1':
            print("\n📋 Setting up v2...")
            # Initialize v2 database
            db = DatabaseV2(db_path)
            print("✅ v2 database initialized")
            print("\n📝 Next steps:")
            print("   1. Import service lines:")
            print("      python3 scripts/import_csv.py service-lines config/service_lines.csv")
            print("\n   2. Import clients (v2 format):")
            print("      python3 scripts/import_clients_v2.py config/clients_import.csv")
            print("\n   OR use legacy format (will work but limited features):")
            print("      python3 scripts/import_csv.py client-mappings config/client_mappings.csv")
        else:
            print("\n📋 Setting up v1...")
            # Initialize v1 database
            db = Database(db_path)
            print("✅ v1 database initialized")
            print("\n📝 Next steps:")
            print("   1. Import service lines:")
            print("      python3 scripts/import_csv.py service-lines config/service_lines.csv")
            print("\n   2. Import client mappings:")
            print("      python3 scripts/import_csv.py client-mappings config/client_mappings.csv")
    
    elif state == 'v1':
        print("\n📦 v1 Database Detected")
        print("\nYou can:")
        print("1. Migrate to v2 (Recommended)")
        print("2. Continue using v1")
        
        choice = input("\nMigrate to v2? (y/n) [y]: ").strip().lower() or 'y'
        
        if choice == 'y':
            print("\n🚀 Running migration...")
            from database.migrate_to_v2 import DatabaseMigration
            migration = DatabaseMigration(db_path)
            try:
                migration.run_migration()
                print("\n✅ Migration complete!")
                print("\n📝 Next steps:")
                print("   - Your old client_mappings still work")
                print("   - You can now use v2 features")
                print("   - Import additional data:")
                print("     python3 scripts/import_clients_v2.py config/clients_import.csv")
            except Exception as e:
                print(f"\n❌ Migration failed: {e}")
                print("You can continue using v1 - all features still work")
        else:
            print("\n✅ Continuing with v1")
            print("All existing features will continue to work")
    
    elif state == 'v2':
        print("\n✅ v2 Database Detected")
        
        # Check what data exists
        db_v2 = DatabaseV2(db_path)
        clients = db_v2.get_all_clients()
        
        db = Database(db_path)
        service_lines = db.get_service_lines(active_only=False)
        mappings = db.get_client_mappings(active_only=False)
        
        print(f"\n📊 Current data:")
        print(f"   Service lines: {len(service_lines)}")
        print(f"   Client mappings (legacy): {len(mappings)}")
        print(f"   Clients (v2): {len(clients)}")
        
        if len(service_lines) == 0:
            print("\n⚠️  No service lines found")
            print("   Import service lines first:")
            print("   python3 scripts/import_csv.py service-lines config/service_lines.csv")
        elif len(clients) == 0 and len(mappings) > 0:
            print("\n💡 You have legacy client_mappings but no v2 clients")
            print("   You can:")
            print("   1. Continue using legacy mappings (they still work)")
            print("   2. Convert to v2 clients:")
            print("      python3 scripts/convert_mappings_to_v2.py config/client_mappings.csv config/clients_import.csv")
            print("      python3 scripts/import_clients_v2.py config/clients_import.csv")
        else:
            print("\n✅ Setup looks good!")
            print("   You can:")
            print("   - Use admin portal: python3 web/app.py")
            print("   - Use client portal: python3 web/client_portal.py")
            print("   - Import more data: python3 scripts/import_clients_v2.py config/clients_import.csv")
    
    else:
        print("\n⚠️  Unknown database state")
        print("   Database file exists but structure is unclear")
        print("   You may need to restore from backup")
    
    print("\n" + "=" * 60)
    print("📚 For detailed instructions, see:")
    print("   - README.md (basic setup)")
    print("   - docs/BULK_IMPORT_GUIDE.md (data import)")
    print("   - docs/BACKUP_AND_MIGRATION.md (migration)")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

