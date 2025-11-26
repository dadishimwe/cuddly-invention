# Starlink Manager - VPS Deployment Guide

This guide provides step-by-step instructions for deploying Starlink Manager on a VPS (Virtual Private Server) using Docker and Docker Compose.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [VPS Requirements](#vps-requirements)
3. [Initial VPS Setup](#initial-vps-setup)
4. [Install Docker and Docker Compose](#install-docker-and-docker-compose)
5. [Clone and Configure the Application](#clone-and-configure-the-application)
6. [Build and Run with Docker](#build-and-run-with-docker)
7. [Configure Nginx Reverse Proxy](#configure-nginx-reverse-proxy)
8. [Setup SSL with Let's Encrypt](#setup-ssl-with-lets-encrypt)
9. [Configure Firewall](#configure-firewall)
10. [Database Backups](#database-backups)
11. [Monitoring and Logs](#monitoring-and-logs)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- A VPS with Ubuntu 22.04 LTS (recommended)
- Root or sudo access to the VPS
- Domain names pointing to your VPS IP:
  - `zubadash.dadishimwe.com` (Admin Dashboard)
  - `zubaclient.dadishimwe.com` (Client Portal)
- Starlink API credentials (Client ID and Secret)
- SMTP credentials for email reports

---

## VPS Requirements

**Minimum Specifications:**
- **RAM:** 1-2 GB
- **CPU:** 1-2 vCPUs
- **Storage:** 20 GB SSD
- **OS:** Ubuntu 22.04 LTS

**Recommended Providers:**
- DigitalOcean (Droplet)
- Linode
- Vultr
- Hetzner

---

## Initial VPS Setup

### 1. SSH into Your VPS

```bash
ssh root@your_vps_ip
```

### 2. Update System Packages

```bash
apt update && apt upgrade -y
```

### 3. Create a Non-Root User (Optional but Recommended)

```bash
adduser starlink
usermod -aG sudo starlink
su - starlink
```

### 4. Set Timezone

```bash
sudo timedatectl set-timezone Africa/Kigali
```

---

## Install Docker and Docker Compose

### 1. Install Docker

```bash
# Install prerequisites
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add your user to the docker group
sudo usermod -aG docker $USER

# Apply group changes (or logout and login again)
newgrp docker

# Verify installation
docker --version
```

### 2. Install Docker Compose

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

---

## Clone and Configure the Application

### 1. Clone the Repository

```bash
cd /home/starlink  # or your preferred directory
git clone https://github.com/dadishimwe/cuddly-invention.git starlink-manager
cd starlink-manager
```

### 2. Create Environment File

```bash
cp .env.example .env
nano .env
```

**Configure the following variables in `.env`:**

```env
# Starlink API Credentials
STARLINK_CLIENT_ID=your_actual_client_id
STARLINK_CLIENT_SECRET=your_actual_client_secret

# Database Configuration
STARLINK_DB_PATH=/app/data/starlink_manager.db

# Flask Configuration
FLASK_SECRET_KEY=generate_a_secure_random_key_here
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5000

# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com

# Default Admin User
DEFAULT_ADMIN_PASSWORD=YourSecurePassword123!
ADMIN_EMAIL=admin@yourdomain.com

# Chatwoot Configuration (optional)
CHATWOOT_WEBSITE_TOKEN=your_chatwoot_token
CHATWOOT_BASE_URL=https://app.chatwoot.com

# Application Settings
COMPANY_NAME=Zuba Broadband
ADMIN_SUBDOMAIN=zubadash.dadishimwe.com
CLIENT_SUBDOMAIN=zubaclient.dadishimwe.com

# Logging
LOG_LEVEL=INFO
```

**Generate a secure Flask secret key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Create Data Directories

```bash
mkdir -p data logs config
```

---

## Build and Run with Docker

### 1. Build the Docker Image

```bash
docker-compose build
```

### 2. Start the Application

```bash
docker-compose up -d
```

### 3. Check Container Status

```bash
docker-compose ps
docker-compose logs -f
```

### 4. Verify Application is Running

```bash
curl http://localhost:5000/health
```

You should see: `{"status":"healthy","timestamp":"..."}`

---

## Configure Nginx Reverse Proxy

### 1. Install Nginx

```bash
sudo apt install -y nginx
```

### 2. Copy Nginx Configuration

```bash
sudo cp config/nginx-vps.conf /etc/nginx/sites-available/starlink-manager
```

### 3. Create Symbolic Link

```bash
sudo ln -s /etc/nginx/sites-available/starlink-manager /etc/nginx/sites-enabled/
```

### 4. Test Nginx Configuration

```bash
sudo nginx -t
```

### 5. Restart Nginx

```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## Setup SSL with Let's Encrypt

### 1. Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificates

**For Admin Dashboard:**

```bash
sudo certbot --nginx -d zubadash.dadishimwe.com
```

**For Client Portal:**

```bash
sudo certbot --nginx -d zubaclient.dadishimwe.com
```

Follow the prompts:
- Enter your email address
- Agree to terms of service
- Choose whether to redirect HTTP to HTTPS (recommended: Yes)

### 3. Verify Auto-Renewal

```bash
sudo certbot renew --dry-run
```

### 4. Update Nginx Configuration

After SSL setup, uncomment the HTTPS server blocks in `/etc/nginx/sites-available/starlink-manager`:

```bash
sudo nano /etc/nginx/sites-available/starlink-manager
```

Uncomment the HTTPS sections and the HTTP to HTTPS redirect lines.

### 5. Reload Nginx

```bash
sudo systemctl reload nginx
```

---

## Configure Firewall

### 1. Install UFW (if not already installed)

```bash
sudo apt install -y ufw
```

### 2. Configure Firewall Rules

```bash
# Allow SSH (important - don't lock yourself out!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

**Expected output:**

```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

---

## Database Backups

### 1. Create Backup Script

```bash
nano ~/backup-starlink-db.sh
```

**Add the following content:**

```bash
#!/bin/bash
# Starlink Manager Database Backup Script

BACKUP_DIR="/home/starlink/backups"
DB_PATH="/home/starlink/starlink-manager/data/starlink_manager.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/starlink_db_$DATE.db"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Copy database
cp $DB_PATH $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "starlink_db_*.db.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### 2. Make Script Executable

```bash
chmod +x ~/backup-starlink-db.sh
```

### 3. Schedule Daily Backups with Cron

```bash
crontab -e
```

**Add the following line (runs daily at 2 AM):**

```
0 2 * * * /home/starlink/backup-starlink-db.sh >> /home/starlink/backup.log 2>&1
```

### 4. Test Backup

```bash
~/backup-starlink-db.sh
ls -lh ~/backups/
```

---

## Monitoring and Logs

### 1. View Application Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service logs
docker-compose logs starlink-manager
```

### 2. Check Container Health

```bash
docker-compose ps
docker inspect starlink-manager | grep -A 10 Health
```

### 3. Monitor Resource Usage

```bash
# Container stats
docker stats

# System resources
htop  # install with: sudo apt install htop
```

### 4. Check Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Check if port is already in use
sudo netstat -tulpn | grep 5000

# Restart container
docker-compose restart
```

### Database Issues

```bash
# Access container shell
docker-compose exec starlink-manager bash

# Check database
python3 -c "from database.db_v2 import DatabaseV2; db = DatabaseV2(); print('DB OK')"

# Reinitialize database (WARNING: This will delete all data)
docker-compose exec starlink-manager python3 /app/scripts/manage.py init --v2
```

### Permission Issues

```bash
# Fix data directory permissions
sudo chown -R 1000:1000 data/ logs/
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificates manually
sudo certbot renew

# Test SSL configuration
sudo nginx -t
```

### Application Not Accessible

```bash
# Check if container is running
docker-compose ps

# Check if Nginx is running
sudo systemctl status nginx

# Check firewall
sudo ufw status

# Test local connection
curl http://localhost:5000/health

# Test through Nginx
curl http://zubadash.dadishimwe.com/health
```

### High Memory Usage

```bash
# Reduce Gunicorn workers in docker-compose.yml
# Change from --workers 3 to --workers 2

# Restart container
docker-compose restart
```

---

## Updating the Application

### 1. Pull Latest Changes

```bash
cd /home/starlink/starlink-manager
git pull origin main
```

### 2. Rebuild and Restart

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### 3. Verify Update

```bash
docker-compose logs -f
curl http://localhost:5000/health
```

---

## Maintenance Tasks

### Weekly

- Check application logs for errors
- Verify backups are running
- Monitor disk space: `df -h`

### Monthly

- Update system packages: `sudo apt update && sudo apt upgrade -y`
- Review and clean old Docker images: `docker system prune -a`
- Test backup restoration

### Quarterly

- Review and update SSL certificates (auto-renewed, but verify)
- Review user access and permissions
- Update application to latest version

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/dadishimwe/cuddly-invention/issues
- Email: admin@yourdomain.com

---

**Deployment completed! Your Starlink Manager should now be accessible at:**
- Admin Dashboard: https://zubadash.dadishimwe.com
- Client Portal: https://zubaclient.dadishimwe.com
