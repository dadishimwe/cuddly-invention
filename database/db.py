"""Database connection and operations module"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    """Database handler supporting SQLite"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/starlink.db
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'starlink.db')
        
        self.db_path = db_path
        self._ensure_data_directory()
        self._initialize_schema()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.db_path)
        Path(data_dir).mkdir(parents=True, exist_ok=True)
    
    def _initialize_schema(self):
        """Initialize database schema if not exists"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results as list of dicts
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute INSERT/UPDATE/DELETE query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows or last inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute query with multiple parameter sets
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    # Service Lines operations
    def add_service_line(self, account_number: str, service_line_id: str, 
                        nickname: str = None, service_line_number: str = None,
                        active: bool = True) -> int:
        """Add a new service line"""
        query = """
            INSERT INTO service_lines (account_number, service_line_id, nickname, 
                                      service_line_number, active)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (account_number, service_line_id, 
                                           nickname, service_line_number, active))
    
    def get_service_lines(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all service lines"""
        query = "SELECT * FROM service_lines"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY nickname, service_line_id"
        return self.execute_query(query)
    
    def get_service_line(self, service_line_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific service line"""
        query = "SELECT * FROM service_lines WHERE service_line_id = ?"
        results = self.execute_query(query, (service_line_id,))
        return results[0] if results else None
    
    # Client Mappings operations
    def add_client_mapping(self, client_name: str, service_line_id: str,
                          primary_email: str, cc_emails: str = None,
                          active: bool = True, report_frequency: str = 'on_demand') -> int:
        """Add a new client mapping"""
        query = """
            INSERT INTO client_mappings (client_name, service_line_id, primary_email,
                                        cc_emails, active, report_frequency)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (client_name, service_line_id, primary_email,
                                           cc_emails, active, report_frequency))
    
    def get_client_mappings(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all client mappings"""
        query = """
            SELECT cm.*, sl.nickname, sl.account_number
            FROM client_mappings cm
            LEFT JOIN service_lines sl ON cm.service_line_id = sl.service_line_id
        """
        if active_only:
            query += " WHERE cm.active = 1"
        query += " ORDER BY cm.client_name"
        return self.execute_query(query)
    
    def get_client_mapping(self, mapping_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific client mapping"""
        query = """
            SELECT cm.*, sl.nickname, sl.account_number
            FROM client_mappings cm
            LEFT JOIN service_lines sl ON cm.service_line_id = sl.service_line_id
            WHERE cm.id = ?
        """
        results = self.execute_query(query, (mapping_id,))
        return results[0] if results else None
    
    def update_client_mapping(self, mapping_id: int, **kwargs) -> int:
        """Update a client mapping"""
        allowed_fields = ['client_name', 'primary_email', 'cc_emails', 
                         'active', 'report_frequency', 'last_sent_at']
        
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return 0
        
        values.append(mapping_id)
        query = f"UPDATE client_mappings SET {', '.join(updates)} WHERE id = ?"
        return self.execute_update(query, tuple(values))
    
    # Report Logs operations
    def add_report_log(self, mapping_id: int, service_line_id: str,
                      recipient_email: str, report_type: str, status: str,
                      **kwargs) -> int:
        """Add a report log entry"""
        query = """
            INSERT INTO report_logs (mapping_id, service_line_id, recipient_email,
                                    report_type, status, cc_emails, start_date, end_date,
                                    billing_cycle_start, billing_cycle_end, total_usage_gb,
                                    days_included, error_message, email_subject)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (
            mapping_id, service_line_id, recipient_email, report_type, status,
            kwargs.get('cc_emails'), kwargs.get('start_date'), kwargs.get('end_date'),
            kwargs.get('billing_cycle_start'), kwargs.get('billing_cycle_end'),
            kwargs.get('total_usage_gb'), kwargs.get('days_included'),
            kwargs.get('error_message'), kwargs.get('email_subject')
        ))
    
    def get_report_logs(self, limit: int = 100, mapping_id: int = None) -> List[Dict[str, Any]]:
        """Get report logs"""
        query = "SELECT * FROM report_logs"
        params = ()
        
        if mapping_id:
            query += " WHERE mapping_id = ?"
            params = (mapping_id,)
        
        query += " ORDER BY sent_at DESC LIMIT ?"
        params = params + (limit,)
        
        return self.execute_query(query, params)
    
    # Team Members operations
    def add_team_member(self, username: str, password_hash: str, name: str,
                       email: str, role: str = 'member') -> int:
        """Add a new team member"""
        query = """
            INSERT INTO team_members (username, password_hash, name, email, role)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_update(query, (username, password_hash, name, email, role))
    
    def get_team_member(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a team member by username"""
        query = "SELECT * FROM team_members WHERE username = ? AND active = 1"
        results = self.execute_query(query, (username,))
        return results[0] if results else None
    
    def get_all_team_members(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all team members"""
        query = "SELECT id, username, name, email, role, active, created_at FROM team_members"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY name"
        return self.execute_query(query)
