# Starlink Manager - VPS Deployment Guide

This guide will walk you through deploying the Starlink Manager system on a VPS (Virtual Private Server) with secure access for your team.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial VPS Setup](#initial-vps-setup)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Web Interface Setup](#web-interface-setup)
7. [Domain and SSL Configuration](#domain-and-ssl-configuration)
8. [Team Access Management](#team-access-management)
9. [Maintenance and Monitoring](#maintenance-and-monitoring)

---

## Prerequisites

### VPS Requirements

- **OS**: Ubuntu 22.04 LTS or newer
- **RAM**: Minimum 1GB (2GB recommended)
- **Storage**: Minimum 10GB
- **Network**: Public IP address

### What You'll Need

- Starlink API credentials (Client ID and Secret)
- SMTP email credentials (for sending reports)
- Domain name (optional, but recommended for SSL)
- SSH access to your VPS

---

## Initial VPS Setup

### 1. Connect to Your VPS

```bash
ssh root@your-vps-ip
```

### 2. Update System

```bash
apt update && apt upgrade -y
```

### 3. Create Application User

```bash
# Create user for running the application
useradd -m -s /bin/bash starlink
usermod -aG sudo starlink

# Set password
passwd starlink
```

### 4. Install Required Software

```bash
# Install Python and dependencies
apt install -y python3 python3-pip python3-venv

# Install Nginx (web server)
apt install -y nginx

# Install Git (optional, for updates)
apt install -y git

# Install UFW (firewall)
apt install -y ufw
```

### 5. Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable
```

---

## Installation

### 1. Upload and Extract the Application

```bash
# Switch to application user
su - starlink

# Create application directory
sudo mkdir -p /opt/starlink-manager
sudo chown starlink:starlink /opt/starlink-manager

# Upload the zip file to your VPS (from your local machine)
# scp starlink-manager.zip starlink@your-vps-ip:/opt/

# Extract
cd /opt
unzip starlink-manager.zip -d starlink-manager
cd starlink-manager
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

### 1. Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required Configuration:**

```env
# Starlink API Credentials
STARLINK_CLIENT_ID=your_actual_client_id
STARLINK_CLIENT_SECRET=your_actual_client_secret

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com

# Flask Web Application
FLASK_SECRET_KEY=generate_random_32_char_string_here
FLASK_DEBUG=False
PORT=5000
```

**Generate a secure Flask secret key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Secure the Environment File

```bash
# Restrict access to .env file
chmod 600 .env
```

---

## Database Setup

### 1. Initialize Database

The database will be automatically created when you first run the application. The schema is applied automatically.

```bash
# Create data directory
mkdir -p data
chmod 755 data
```

### 2. Import Service Lines from CSV

**Prepare your CSV file** (`service_lines.csv`):

```csv
account_number,service_line_id,nickname,service_line_number,active
ACC-12345-67890-12,SL-ABC-123-456-78,Office Terminal 1,1234567890,true
ACC-12345-67890-12,SL-ABC-987-654-32,Office Terminal 2,0987654321,true
```

**Import:**

```bash
cd /opt/starlink-manager
source venv/bin/activate
python3 scripts/import_csv.py service-lines config/service_lines.csv
```

### 3. Import Client Mappings from CSV

**Prepare your CSV file** (`client_mappings.csv`):

```csv
client_name,service_line_id,primary_email,cc_emails,active,report_frequency
Acme Corp,SL-ABC-123-456-78,client@acme.com,"manager@acme.com,billing@acme.com",true,on_demand
Tech Solutions,SL-ABC-987-654-32,contact@techsolutions.com,admin@techsolutions.com,true,daily
```

**Import:**

```bash
python3 scripts/import_csv.py client-mappings config/client_mappings.csv
```

### 4. Verify Data

```bash
# List service lines
python3 scripts/manage.py list-service-lines

# List client mappings
python3 scripts/manage.py list-mappings
```

---

## Web Interface Setup

### 1. Test the Application

```bash
# Test run (development mode)
cd /opt/starlink-manager/web
source ../venv/bin/activate
python3 app.py
```

**Note the default admin credentials** that are printed on first run. Save these!

Press `Ctrl+C` to stop the test server.

### 2. Set Up Systemd Service

```bash
# Copy service file
sudo cp /opt/starlink-manager/config/starlink-manager.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable starlink-manager

# Start service
sudo systemctl start starlink-manager

# Check status
sudo systemctl status starlink-manager
```

### 3. Configure Nginx

```bash
# Copy nginx configuration
sudo cp /opt/starlink-manager/config/nginx.conf /etc/nginx/sites-available/starlink-manager

# Edit with your domain
sudo nano /etc/nginx/sites-available/starlink-manager
# Change "your-domain.com" to your actual domain or server IP

# Enable site
sudo ln -s /etc/nginx/sites-available/starlink-manager /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 4. Access the Web Interface

Open your browser and navigate to:
- `http://your-domain.com` (if using domain)
- `http://your-vps-ip` (if using IP address)

**Login with the default admin credentials** printed during first run.

---

## Domain and SSL Configuration

### 1. Point Your Domain to VPS

In your domain registrar's DNS settings, create an A record:

```
Type: A
Name: @ (or subdomain like "starlink")
Value: your-vps-ip
TTL: 3600
```

Wait for DNS propagation (5-30 minutes).

### 2. Install Certbot (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Follow the prompts
# Certbot will automatically configure nginx for HTTPS
```

### 3. Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up a cron job for renewal
```

---

## Team Access Management

### 1. Create Team Member Accounts

**Option A: Via Web Interface (Admin Only)**

1. Login as admin
2. Navigate to **Users** menu
3. Click **Add New User**
4. Fill in details and assign role:
   - **Admin**: Full access including user management
   - **Member**: Can generate reports and view data
   - **Viewer**: Read-only access

**Option B: Via Command Line**

```bash
cd /opt/starlink-manager
source venv/bin/activate

# Interactive mode
python3 -c "
from database.db import Database
from werkzeug.security import generate_password_hash

db = Database()
username = input('Username: ')
password = input('Password: ')
name = input('Full Name: ')
email = input('Email: ')
role = input('Role (admin/member/viewer): ')

password_hash = generate_password_hash(password)
db.add_team_member(username, password_hash, name, email, role)
print(f'User {username} created successfully!')
"
```

### 2. Security Best Practices

- **Change default admin password immediately**
- Use strong passwords (minimum 12 characters)
- Assign appropriate roles (principle of least privilege)
- Regularly review user access
- Enable HTTPS before allowing team access
- Consider implementing 2FA (requires additional setup)

### 3. Restricting Access to Environment Variables

The `.env` file contains sensitive credentials. Only admins should have access:

```bash
# Set proper ownership
sudo chown starlink:starlink /opt/starlink-manager/.env
sudo chmod 600 /opt/starlink-manager/.env

# Team members cannot view or modify this file
# They access the system only through the web interface
```

---

## Maintenance and Monitoring

### 1. View Application Logs

```bash
# View web service logs
sudo journalctl -u starlink-manager -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Restart Services

```bash
# Restart web application
sudo systemctl restart starlink-manager

# Restart nginx
sudo systemctl restart nginx
```

### 3. Database Backup

```bash
# Create backup directory
mkdir -p /opt/starlink-manager/backups

# Backup database
cp /opt/starlink-manager/data/starlink.db \
   /opt/starlink-manager/backups/starlink-$(date +%Y%m%d-%H%M%S).db

# Automated daily backup (add to crontab)
crontab -e
# Add line:
# 0 2 * * * cp /opt/starlink-manager/data/starlink.db /opt/starlink-manager/backups/starlink-$(date +\%Y\%m\%d).db
```

### 4. Update Application

```bash
# Stop service
sudo systemctl stop starlink-manager

# Backup current version
cd /opt
sudo tar -czf starlink-manager-backup-$(date +%Y%m%d).tar.gz starlink-manager/

# Upload and extract new version
# ... (same as installation)

# Restart service
sudo systemctl start starlink-manager
```

### 5. Monitor Disk Space

```bash
# Check disk usage
df -h

# Check database size
du -h /opt/starlink-manager/data/starlink.db
```

---

## Common Tasks

### Generate a Report Manually

**Via Web Interface:**
1. Login
2. Navigate to **Generate Report**
3. Select client and date range
4. Click **Generate Report**

**Via Command Line:**

```bash
cd /opt/starlink-manager
source venv/bin/activate

# Send report for mapping ID 1
python3 scripts/send_report.py --mapping-id 1

# Send to all active mappings
python3 scripts/send_report.py --all

# Dry run (preview without sending)
python3 scripts/send_report.py --mapping-id 1 --dry-run
```

### Query Starlink API Directly

```bash
cd /opt/starlink-manager
source venv/bin/activate

# List accounts
python3 starlink/starlink_api_cli.py accounts

# List terminals
python3 starlink/starlink_api_cli.py terminals --account ACC-12345-67890-12

# Get usage data
python3 starlink/starlink_api_cli.py usage --account ACC-12345-67890-12
```

### Add New Clients

```bash
cd /opt/starlink-manager
source venv/bin/activate

# Interactive mode
python3 scripts/manage.py add-mapping
```

---

## Troubleshooting

### Web Interface Not Loading

```bash
# Check if service is running
sudo systemctl status starlink-manager

# Check nginx status
sudo systemctl status nginx

# Check logs
sudo journalctl -u starlink-manager -n 50
```

### Email Reports Not Sending

1. Verify SMTP credentials in `.env`
2. Check if Gmail App Password is used (not regular password)
3. Test with dry-run mode first
4. Check report logs in web interface

### Database Errors

```bash
# Check database file permissions
ls -la /opt/starlink-manager/data/

# Reinitialize database (WARNING: deletes all data)
rm /opt/starlink-manager/data/starlink.db
cd /opt/starlink-manager/web
source ../venv/bin/activate
python3 app.py  # Will recreate database
```

### Cannot Login

```bash
# Reset admin password
cd /opt/starlink-manager
source venv/bin/activate

python3 -c "
from database.db import Database
from werkzeug.security import generate_password_hash

db = Database()
new_password = 'your_new_password'
password_hash = generate_password_hash(new_password)

with db.get_connection() as conn:
    conn.execute('UPDATE team_members SET password_hash = ? WHERE username = ?', 
                 (password_hash, 'admin'))
    conn.commit()

print('Admin password reset successfully!')
"
```

---

## Security Checklist

- [ ] Changed default admin password
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Firewall configured (UFW)
- [ ] `.env` file permissions set to 600
- [ ] Regular backups configured
- [ ] Only necessary ports open (22, 80, 443)
- [ ] Team members have appropriate role assignments
- [ ] SSH key authentication enabled (password auth disabled)
- [ ] System updates automated or scheduled

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Consult the README.md file
4. Contact your system administrator

---

**Last Updated**: November 2025
