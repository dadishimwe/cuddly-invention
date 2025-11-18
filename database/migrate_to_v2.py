#!/usr/bin/env python3
"""
Database Migration Script - v1 to v2
Migrates existing data to new schema while preserving all information
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database


class DatabaseMigration:
    """Handle database migration from v1 to v2"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'starlink.db')
        
        self.db_path = db_path
        self.backup_path = db_path + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
    def backup_database(self):
        """Create backup of current database"""
        print(f"📦 Creating backup: {self.backup_path}")
        
        import shutil
        if os.path.exists(self.db_path):
            shutil.copy2(self.db_path, self.backup_path)
            print(f"✅ Backup created successfully")
        else:
            print(f"⚠️  No existing database found, starting fresh")
    
    def run_migration(self):
        """Execute the migration"""
        print("\n" + "="*60)
        print("🚀 Starting Database Migration to v2")
        print("="*60 + "\n")
        
        # Step 1: Backup
        self.backup_database()
        
        # Step 2: Connect to database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Step 3: Check if migration needed
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
            if cursor.fetchone():
                print("ℹ️  Database already migrated to v2")
                response = input("Do you want to re-run migration? (yes/no): ")
                if response.lower() != 'yes':
                    print("Migration cancelled")
                    return
            
            # Step 4: Load new schema
            print("\n📋 Loading new schema...")
            schema_path = os.path.join(os.path.dirname(__file__), 'schema_v2.sql')
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            cursor.executescript(schema_sql)
            conn.commit()
            print("✅ New schema loaded")
            
            # Step 5: Migrate existing data
            print("\n📊 Migrating existing data...")
            
            # Migrate client_mappings to clients and client_service_lines
            cursor.execute("SELECT * FROM client_mappings WHERE active = 1")
            mappings = cursor.fetchall()
            
            migrated_clients = {}
            
            for mapping in mappings:
                client_name = mapping['client_name']
                
                # Check if client already exists
                if client_name not in migrated_clients:
                    # Create new client
                    cursor.execute("""
                        INSERT INTO clients (company_name, status, service_start_date, created_at)
                        VALUES (?, 'active', ?, ?)
                    """, (client_name, datetime.now().date(), mapping['created_at']))
                    
                    client_id = cursor.lastrowid
                    migrated_clients[client_name] = client_id
                    
                    # Create primary contact from mapping email
                    cursor.execute("""
                        INSERT INTO client_contacts (client_id, name, email, role, is_primary, active)
                        VALUES (?, ?, ?, 'primary', TRUE, TRUE)
                    """, (client_id, client_name, mapping['primary_email']))
                    
                    print(f"  ✓ Created client: {client_name}")
                else:
                    client_id = migrated_clients[client_name]
                
                # Link service line to client
                try:
                    cursor.execute("""
                        INSERT INTO client_service_lines (client_id, service_line_id, assigned_at)
                        VALUES (?, ?, ?)
                    """, (client_id, mapping['service_line_id'], mapping['created_at']))
                    print(f"  ✓ Linked service line {mapping['service_line_id']} to {client_name}")
                except sqlite3.IntegrityError:
                    print(f"  ⚠️  Service line {mapping['service_line_id']} already linked to {client_name}")
                
                # Update mapping with client_id
                cursor.execute("""
                    UPDATE client_mappings SET client_id = ? WHERE id = ?
                """, (client_id, mapping['id']))
            
            conn.commit()
            
            # Step 6: Update report_logs with client_id
            print("\n📝 Updating report logs...")
            cursor.execute("""
                UPDATE report_logs 
                SET client_id = (
                    SELECT client_id FROM client_mappings 
                    WHERE client_mappings.id = report_logs.mapping_id
                )
                WHERE mapping_id IS NOT NULL
            """)
            conn.commit()
            print(f"✅ Updated {cursor.rowcount} report logs")
            
            # Step 7: Create version marker
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (2)")
            conn.commit()
            
            print("\n" + "="*60)
            print("✅ Migration completed successfully!")
            print("="*60)
            print(f"\n📊 Summary:")
            print(f"  - Clients created: {len(migrated_clients)}")
            print(f"  - Backup location: {self.backup_path}")
            print(f"  - Database version: 2")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print(f"Rolling back changes...")
            conn.rollback()
            print(f"Database backup available at: {self.backup_path}")
            raise
        finally:
            conn.close()


def main():
    """Main migration function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Zuba Broadband Starlink Manager - Database Migration v2    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Check for custom database path
    db_path = None
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        print(f"Using custom database path: {db_path}\n")
    
    migration = DatabaseMigration(db_path)
    
    try:
        migration.run_migration()
        print("\n✨ You can now use the new features!")
        print("   - Client portal")
        print("   - Multi-kit support")
        print("   - Installation tracking")
        print("   - Historical data import")
        print("   - And more!\n")
    except Exception as e:
        print(f"\n💥 Migration error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
