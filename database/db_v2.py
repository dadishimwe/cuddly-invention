"""
Enhanced Database Operations for Zuba Broadband Starlink Manager v2
Supports clients, multi-kit management, client portal, and advanced features
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import datetime, date
import hashlib
import secrets


class DatabaseV2:
    """Enhanced database handler with v2 schema support"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'starlink.db')
        
        self.db_path = db_path
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.db_path)
        Path(data_dir).mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _dict_from_row(self, row) -> Dict:
        """Convert sqlite3.Row to dictionary"""
        if row is None:
            return None
        return dict(zip(row.keys(), row))
    
    # ========================================================================
    # CLIENT MANAGEMENT
    # ========================================================================
    
    def create_client(self, company_name: str, **kwargs) -> int:
        """Create a new client organization"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clients (
                    company_name, registration_number, tax_id, billing_address,
                    service_address, status, service_start_date, service_end_date,
                    contract_type, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_name,
                kwargs.get('registration_number'),
                kwargs.get('tax_id'),
                kwargs.get('billing_address'),
                kwargs.get('service_address'),
                kwargs.get('status', 'active'),
                kwargs.get('service_start_date'),
                kwargs.get('service_end_date'),
                kwargs.get('contract_type'),
                kwargs.get('notes')
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_client(self, client_id: int) -> Optional[Dict]:
        """Get client by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            return self._dict_from_row(cursor.fetchone())
    
    def get_all_clients(self, status: Optional[str] = None) -> List[Dict]:
        """Get all clients, optionally filtered by status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM clients WHERE status = ? ORDER BY company_name", (status,))
            else:
                cursor.execute("SELECT * FROM clients ORDER BY company_name")
            return [self._dict_from_row(row) for row in cursor.fetchall()]
    
    def update_client(self, client_id: int, **kwargs) -> bool:
        """Update client information"""
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['company_name', 'registration_number', 'tax_id', 'billing_address',
                      'service_address', 'status', 'service_start_date', 'service_end_date',
                      'contract_type', 'notes']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(client_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE clients SET {', '.join(fields)} WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_client(self, client_id: int) -> bool:
        """Delete a client (cascade deletes related records)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # CLIENT CONTACTS
    # ========================================================================
    
    def add_client_contact(self, client_id: int, name: str, email: str, **kwargs) -> int:
        """Add a contact person for a client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO client_contacts (
                    client_id, name, email, phone, role, is_primary, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, name, email,
                kwargs.get('phone'),
                kwargs.get('role', 'contact'),
                kwargs.get('is_primary', False),
                kwargs.get('active', True)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_client_contacts(self, client_id: int, active_only: bool = True) -> List[Dict]:
        """Get all contacts for a client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("""
                    SELECT * FROM client_contacts 
                    WHERE client_id = ? AND active = TRUE 
                    ORDER BY is_primary DESC, name
                """, (client_id,))
            else:
                cursor.execute("""
                    SELECT * FROM client_contacts 
                    WHERE client_id = ? 
                    ORDER BY is_primary DESC, name
                """, (client_id,))
            return [self._dict_from_row(row) for row in cursor.fetchall()]
    
    def update_client_contact(self, contact_id: int, **kwargs) -> bool:
        """Update a client contact"""
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['name', 'email', 'phone', 'role', 'is_primary', 'active']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(contact_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE client_contacts SET {', '.join(fields)} WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # CLIENT SERVICE LINES (Multi-kit support)
    # ========================================================================
    
    def assign_service_line_to_client(self, client_id: int, service_line_id: str) -> bool:
        """Assign a service line (kit) to a client"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO client_service_lines (client_id, service_line_id)
                    VALUES (?, ?)
                """, (client_id, service_line_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Already assigned
    
    def unassign_service_line_from_client(self, client_id: int, service_line_id: str) -> bool:
        """Remove a service line assignment from a client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM client_service_lines 
                WHERE client_id = ? AND service_line_id = ?
            """, (client_id, service_line_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_client_service_lines(self, client_id: int) -> List[Dict]:
        """Get all service lines for a client"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sl.*, csl.assigned_at
                FROM service_lines sl
                JOIN client_service_lines csl ON sl.service_line_id = csl.service_line_id
                WHERE csl.client_id = ?
                ORDER BY csl.assigned_at DESC
            """, (client_id,))
            return [self._dict_from_row(row) for row in cursor.fetchall()]
    
    def get_service_line_client(self, service_line_id: str) -> Optional[Dict]:
        """Get the client for a service line"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.* FROM clients c
                JOIN client_service_lines csl ON c.id = csl.client_id
                WHERE csl.service_line_id = ?
            """, (service_line_id,))
            return self._dict_from_row(cursor.fetchone())
    
    # ========================================================================
    # CLIENT PORTAL ACCOUNTS
    # ========================================================================
    
    def create_client_account(self, client_id: int, email: str, password: str, name: str) -> int:
        """Create a client portal account"""
        password_hash = self._hash_password(password)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO client_accounts (client_id, email, password_hash, name, active)
                VALUES (?, ?, ?, ?, TRUE)
            """, (client_id, email, password_hash, name))
            conn.commit()
            return cursor.lastrowid
    
    def authenticate_client_account(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate a client portal user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM client_accounts WHERE email = ? AND active = TRUE
            """, (email,))
            account = cursor.fetchone()
            
            if account and self._verify_password(password, account['password_hash']):
                # Update last login
                cursor.execute("""
                    UPDATE client_accounts SET last_login = ? WHERE id = ?
                """, (datetime.now().isoformat(), account['id']))
                conn.commit()
                return self._dict_from_row(account)
            
            return None
    
    def get_client_account(self, account_id: int) -> Optional[Dict]:
        """Get client account by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM client_accounts WHERE id = ?", (account_id,))
            return self._dict_from_row(cursor.fetchone())
    
    def get_client_account_by_email(self, email: str) -> Optional[Dict]:
        """Get client account by email"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM client_accounts WHERE email = ?", (email,))
            return self._dict_from_row(cursor.fetchone())
    
    def update_client_account_password(self, account_id: int, new_password: str) -> bool:
        """Update client account password"""
        password_hash = self._hash_password(new_password)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE client_accounts 
                SET password_hash = ?, updated_at = ? 
                WHERE id = ?
            """, (password_hash, datetime.now().isoformat(), account_id))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # INSTALLATION TRACKING
    # ========================================================================
    
    def add_installation(self, service_line_id: str, installation_date: date, **kwargs) -> int:
        """Record an installation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO installations (
                    service_line_id, installation_date, technician_name,
                    installation_address, peplink_router_installed, peplink_model,
                    peplink_serial_number, peplink_firmware_version,
                    starlink_dish_serial, installation_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                service_line_id, installation_date,
                kwargs.get('technician_name'),
                kwargs.get('installation_address'),
                kwargs.get('peplink_router_installed', False),
                kwargs.get('peplink_model'),
                kwargs.get('peplink_serial_number'),
                kwargs.get('peplink_firmware_version'),
                kwargs.get('starlink_dish_serial'),
                kwargs.get('installation_notes')
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_installation(self, service_line_id: str) -> Optional[Dict]:
        """Get installation record for a service line"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM installations 
                WHERE service_line_id = ? 
                ORDER BY installation_date DESC 
                LIMIT 1
            """, (service_line_id,))
            return self._dict_from_row(cursor.fetchone())
    
    def update_installation(self, installation_id: int, **kwargs) -> bool:
        """Update installation record"""
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['technician_name', 'installation_address', 'peplink_router_installed',
                      'peplink_model', 'peplink_serial_number', 'peplink_firmware_version',
                      'starlink_dish_serial', 'installation_notes']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(installation_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE installations SET {', '.join(fields)} WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # HISTORICAL USAGE DATA
    # ========================================================================
    
    def add_daily_usage(self, service_line_id: str, usage_date: date, 
                       total_gb: float, **kwargs) -> bool:
        """Add or update daily usage record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO daily_usage_history (
                        service_line_id, usage_date, priority_gb, standard_gb, total_gb,
                        billing_cycle_start, billing_cycle_end
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(service_line_id, usage_date) DO UPDATE SET
                        priority_gb = excluded.priority_gb,
                        standard_gb = excluded.standard_gb,
                        total_gb = excluded.total_gb,
                        billing_cycle_start = excluded.billing_cycle_start,
                        billing_cycle_end = excluded.billing_cycle_end
                """, (
                    service_line_id, usage_date,
                    kwargs.get('priority_gb', 0),
                    kwargs.get('standard_gb', 0),
                    total_gb,
                    kwargs.get('billing_cycle_start'),
                    kwargs.get('billing_cycle_end')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding daily usage: {e}")
            return False
    
    def get_usage_history(self, service_line_id: str, start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> List[Dict]:
        """Get usage history for a service line"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if start_date and end_date:
                cursor.execute("""
                    SELECT * FROM daily_usage_history
                    WHERE service_line_id = ? AND usage_date BETWEEN ? AND ?
                    ORDER BY usage_date ASC
                """, (service_line_id, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT * FROM daily_usage_history
                    WHERE service_line_id = ?
                    ORDER BY usage_date ASC
                """, (service_line_id,))
            
            return [self._dict_from_row(row) for row in cursor.fetchall()]
    
    def get_usage_summary_by_cycle(self, service_line_id: str) -> List[Dict]:
        """Get usage summary grouped by billing cycle"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    billing_cycle_start,
                    billing_cycle_end,
                    SUM(priority_gb) as total_priority_gb,
                    SUM(standard_gb) as total_standard_gb,
                    SUM(total_gb) as total_usage_gb,
                    COUNT(*) as days_count
                FROM daily_usage_history
                WHERE service_line_id = ? AND billing_cycle_start IS NOT NULL
                GROUP BY billing_cycle_start, billing_cycle_end
                ORDER BY billing_cycle_start DESC
            """, (service_line_id,))
            return [self._dict_from_row(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================
    
    def log_audit(self, user_id: int, user_type: str, action: str, 
                  resource_type: str, resource_id: Optional[int] = None,
                  details: Optional[str] = None, ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None):
        """Log an audit event"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, user_type, action, resource_type, resource_id,
                    details, ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, user_type, action, resource_type, resource_id,
                 details, ip_address, user_agent))
            conn.commit()
    
    def get_audit_logs(self, limit: int = 100, user_id: Optional[int] = None,
                      resource_type: Optional[str] = None) -> List[Dict]:
        """Get audit logs with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if resource_type:
                query += " AND resource_type = ?"
                params.append(resource_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [self._dict_from_row(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            salt, pwd_hash = password_hash.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except:
            return False
    
    def get_statistics(self) -> Dict:
        """Get system-wide statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total clients
            cursor.execute("SELECT COUNT(*) as count FROM clients WHERE status = 'active'")
            stats['active_clients'] = cursor.fetchone()['count']
            
            # Total service lines
            cursor.execute("SELECT COUNT(*) as count FROM service_lines WHERE active = TRUE")
            stats['active_service_lines'] = cursor.fetchone()['count']
            
            # Total reports sent
            cursor.execute("SELECT COUNT(*) as count FROM report_logs WHERE status = 'sent'")
            stats['reports_sent'] = cursor.fetchone()['count']
            
            # Client accounts
            cursor.execute("SELECT COUNT(*) as count FROM client_accounts WHERE active = TRUE")
            stats['client_accounts'] = cursor.fetchone()['count']
            
            return stats
