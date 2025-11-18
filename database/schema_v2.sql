-- Zuba Broadband Starlink Manager - Enhanced Database Schema v2.0
-- This schema supports multi-kit clients, client portal, historical data, and advanced features

-- ============================================================================
-- CORE TABLES (Enhanced from v1)
-- ============================================================================

-- Service Lines (Starlink Terminals) - Enhanced
CREATE TABLE IF NOT EXISTS service_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number VARCHAR(255) NOT NULL,
    service_line_id VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(255),
    service_line_number VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team Members (Internal Staff) - Existing
CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member', -- admin, member, viewer
    active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CLIENT MANAGEMENT (New)
-- ============================================================================

-- Clients (Organizations/Companies)
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name VARCHAR(255) NOT NULL,
    registration_number VARCHAR(255),
    tax_id VARCHAR(255),
    billing_address TEXT,
    service_address TEXT,
    status VARCHAR(50) DEFAULT 'active', -- active, suspended, cancelled
    service_start_date DATE,
    service_end_date DATE,
    contract_type VARCHAR(50), -- monthly, annual, custom
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Client Contacts (Multiple contacts per client)
CREATE TABLE IF NOT EXISTS client_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    role VARCHAR(100), -- primary, technical, billing, etc.
    is_primary BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

-- Client Service Lines (Many-to-many: clients can have multiple kits)
CREATE TABLE IF NOT EXISTS client_service_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    service_line_id VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE,
    UNIQUE(client_id, service_line_id)
);

-- Client Portal Accounts (For client self-service)
CREATE TABLE IF NOT EXISTS client_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

-- ============================================================================
-- INSTALLATION & EQUIPMENT TRACKING
-- ============================================================================

-- Installation Records
CREATE TABLE IF NOT EXISTS installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_line_id VARCHAR(255) NOT NULL,
    installation_date DATE NOT NULL,
    technician_name VARCHAR(255),
    installation_address TEXT,
    peplink_router_installed BOOLEAN DEFAULT FALSE,
    peplink_model VARCHAR(100),
    peplink_serial_number VARCHAR(255),
    peplink_firmware_version VARCHAR(50),
    starlink_dish_serial VARCHAR(255),
    installation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE
);

-- Equipment History (Track replacements, upgrades, etc.)
CREATE TABLE IF NOT EXISTS equipment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_line_id VARCHAR(255) NOT NULL,
    equipment_type VARCHAR(100) NOT NULL, -- router, dish, cable, etc.
    action VARCHAR(50) NOT NULL, -- installed, replaced, removed, upgraded
    old_serial_number VARCHAR(255),
    new_serial_number VARCHAR(255),
    reason TEXT,
    performed_by INTEGER, -- team_member_id
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES team_members(id)
);

-- ============================================================================
-- USAGE DATA & HISTORY
-- ============================================================================

-- Historical Daily Usage (For storing backfilled and ongoing data)
CREATE TABLE IF NOT EXISTS daily_usage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_line_id VARCHAR(255) NOT NULL,
    usage_date DATE NOT NULL,
    priority_gb DECIMAL(10, 2) DEFAULT 0,
    standard_gb DECIMAL(10, 2) DEFAULT 0,
    total_gb DECIMAL(10, 2) NOT NULL,
    billing_cycle_start DATE,
    billing_cycle_end DATE,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE,
    UNIQUE(service_line_id, usage_date)
);

-- Billing Cycles (Track billing periods for each service line)
CREATE TABLE IF NOT EXISTS billing_cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_line_id VARCHAR(255) NOT NULL,
    cycle_start_date DATE NOT NULL,
    cycle_end_date DATE NOT NULL,
    total_usage_gb DECIMAL(10, 2),
    priority_usage_gb DECIMAL(10, 2),
    standard_usage_gb DECIMAL(10, 2),
    days_in_cycle INTEGER,
    status VARCHAR(50) DEFAULT 'active', -- active, completed, billed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE,
    UNIQUE(service_line_id, cycle_start_date)
);

-- ============================================================================
-- REPORTING & NOTIFICATIONS
-- ============================================================================

-- Report Logs (Enhanced from v1)
CREATE TABLE IF NOT EXISTS report_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mapping_id INTEGER, -- Legacy support
    client_id INTEGER, -- New client reference
    service_line_id VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    cc_emails TEXT,
    report_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_date DATE,
    end_date DATE,
    billing_cycle_start DATE,
    billing_cycle_end DATE,
    total_usage_gb DECIMAL(10, 2),
    days_included INTEGER,
    email_subject TEXT,
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE
);

-- Client Mappings (Legacy - kept for backward compatibility)
CREATE TABLE IF NOT EXISTS client_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER, -- Link to new clients table
    client_name VARCHAR(255) NOT NULL,
    service_line_id VARCHAR(255) NOT NULL,
    primary_email VARCHAR(255) NOT NULL,
    cc_emails TEXT,
    active BOOLEAN DEFAULT TRUE,
    report_frequency VARCHAR(50) DEFAULT 'on_demand',
    last_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE CASCADE
);

-- ============================================================================
-- SUPPORT & COMMUNICATION
-- ============================================================================

-- Support Tickets
CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    client_id INTEGER NOT NULL,
    service_line_id VARCHAR(255),
    subject VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open', -- open, in_progress, resolved, closed
    priority VARCHAR(50) DEFAULT 'medium', -- low, medium, high, urgent
    assigned_to INTEGER, -- team_member_id
    created_by INTEGER, -- client_account_id
    created_by_type VARCHAR(50), -- 'client' or 'team'
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (service_line_id) REFERENCES service_lines(service_line_id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES team_members(id)
);

-- Ticket Comments
CREATE TABLE IF NOT EXISTS ticket_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    user_type VARCHAR(50) NOT NULL, -- 'client' or 'team'
    comment TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE, -- Internal notes not visible to clients
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE
);

-- ============================================================================
-- AUDIT & SECURITY
-- ============================================================================

-- Audit Logs (Track all important actions)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_type VARCHAR(50), -- 'team_member' or 'client_account'
    action VARCHAR(100) NOT NULL, -- 'create', 'update', 'delete', 'view', 'login', 'logout'
    resource_type VARCHAR(100), -- 'client', 'service_line', 'report', 'ticket', etc.
    resource_id INTEGER,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session Management
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    user_type VARCHAR(50) NOT NULL, -- 'team_member' or 'client_account'
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- NOTIFICATIONS & ALERTS
-- ============================================================================

-- Notification Preferences
CREATE TABLE IF NOT EXISTS notification_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_type VARCHAR(50) NOT NULL, -- 'team_member' or 'client_account'
    notification_type VARCHAR(100) NOT NULL, -- 'usage_alert', 'ticket_update', 'report_ready', etc.
    enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, user_type, notification_type)
);

-- Notification Queue
CREATE TABLE IF NOT EXISTS notification_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_type VARCHAR(50) NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    sent_via_email BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_service_lines_account ON service_lines(account_number);
CREATE INDEX IF NOT EXISTS idx_service_lines_active ON service_lines(active);

CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_clients_company ON clients(company_name);

CREATE INDEX IF NOT EXISTS idx_client_contacts_client ON client_contacts(client_id);
CREATE INDEX IF NOT EXISTS idx_client_contacts_email ON client_contacts(email);

CREATE INDEX IF NOT EXISTS idx_client_service_lines_client ON client_service_lines(client_id);
CREATE INDEX IF NOT EXISTS idx_client_service_lines_service ON client_service_lines(service_line_id);

CREATE INDEX IF NOT EXISTS idx_client_accounts_email ON client_accounts(email);
CREATE INDEX IF NOT EXISTS idx_client_accounts_client ON client_accounts(client_id);

CREATE INDEX IF NOT EXISTS idx_daily_usage_service_line ON daily_usage_history(service_line_id);
CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON daily_usage_history(usage_date);
CREATE INDEX IF NOT EXISTS idx_daily_usage_service_date ON daily_usage_history(service_line_id, usage_date);

CREATE INDEX IF NOT EXISTS idx_billing_cycles_service_line ON billing_cycles(service_line_id);
CREATE INDEX IF NOT EXISTS idx_billing_cycles_dates ON billing_cycles(cycle_start_date, cycle_end_date);

CREATE INDEX IF NOT EXISTS idx_report_logs_client ON report_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_report_logs_service_line ON report_logs(service_line_id);
CREATE INDEX IF NOT EXISTS idx_report_logs_sent_at ON report_logs(sent_at);

CREATE INDEX IF NOT EXISTS idx_support_tickets_client ON support_tickets(client_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_number ON support_tickets(ticket_number);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_installations_service_line ON installations(service_line_id);
