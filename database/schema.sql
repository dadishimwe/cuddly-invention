-- Starlink Manager Database Schema
-- Supports both PostgreSQL and SQLite

-- Service Lines (Terminals)
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

-- Client Email Mappings
CREATE TABLE IF NOT EXISTS client_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name VARCHAR(255) NOT NULL,
    service_line_id VARCHAR(255) NOT NULL,
    primary_email VARCHAR(255) NOT NULL,
    cc_emails TEXT,  -- Comma-separated list
    active BOOLEAN DEFAULT TRUE,
    report_frequency VARCHAR(20) DEFAULT 'on_demand',  -- 'daily', 'weekly', 'on_demand'
    last_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service_line_id, primary_email)
);

-- Email Report Logs
CREATE TABLE IF NOT EXISTS report_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mapping_id INTEGER,
    service_line_id VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    cc_emails TEXT,
    report_type VARCHAR(50) NOT NULL,  -- 'current_cycle', 'custom_range'
    start_date DATE,
    end_date DATE,
    billing_cycle_start DATE,
    billing_cycle_end DATE,
    total_usage_gb DECIMAL(10, 2),
    days_included INTEGER,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- 'sent', 'failed', 'pending'
    error_message TEXT,
    email_subject VARCHAR(255),
    FOREIGN KEY (mapping_id) REFERENCES client_mappings(id)
);

-- Team Members (for web interface access)
CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) DEFAULT 'member',  -- 'admin', 'member', 'viewer'
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Usage Logs (for tracking API calls)
CREATE TABLE IF NOT EXISTS api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_service_lines_account ON service_lines(account_number);
CREATE INDEX IF NOT EXISTS idx_client_mappings_service_line ON client_mappings(service_line_id);
CREATE INDEX IF NOT EXISTS idx_client_mappings_active ON client_mappings(active);
CREATE INDEX IF NOT EXISTS idx_report_logs_sent_at ON report_logs(sent_at);
CREATE INDEX IF NOT EXISTS idx_report_logs_status ON report_logs(status);
CREATE INDEX IF NOT EXISTS idx_team_members_username ON team_members(username);
