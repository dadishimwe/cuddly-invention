# Starlink Manager

A comprehensive management system for Starlink Enterprise API with automated usage reporting, client management, and a secure web interface for team collaboration.

## Features

### 🛰️ Starlink API Integration
- Direct integration with Starlink Enterprise API
- Fetch account, service line, and usage data
- Support for multiple billing cycles and date ranges
- Automatic token management and refresh

### 📊 Usage Reporting
- Generate detailed usage reports for clients
- Daily usage breakdown (Priority and Standard data)
- Email delivery with professional HTML templates
- Support for custom date ranges
- Automated report scheduling

### 👥 Client Management
- Map client emails to Starlink terminals
- Support for multiple recipients (CC emails)
- Configurable report frequencies (daily, weekly, on-demand)
- Track report history and delivery status

### 🌐 Web Interface
- Secure, responsive web dashboard
- Role-based access control (Admin, Member, Viewer)
- Real-time usage data visualization
- Generate and send reports with a few clicks
- No exposure of API credentials to team members

### 💾 Database Management
- SQLite database (no external database required)
- CSV import for bulk data loading
- Command-line management tools
- Automatic schema initialization

### 🔒 Security
- Environment-based credential management
- Password hashing for user accounts
- Session-based authentication
- HTTPS support with SSL/TLS
- Restricted file permissions

## Project Structure

```
starlink-manager/
├── starlink/               # Starlink API client modules
│   ├── StarlinkClient.py   # Main API client
│   ├── AuthManager.py      # Authentication handler
│   ├── AccountManager.py   # Account operations
│   ├── ServiceLineManager.py # Service line operations
│   ├── UsageManager.py     # Usage data operations
│   └── starlink_api_cli.py # CLI for direct API queries
├── database/               # Database layer
│   ├── db.py              # Database operations
│   └── schema.sql         # Database schema
├── scripts/               # Management scripts
│   ├── import_csv.py      # CSV import utility
│   ├── send_report.py     # Report generation and sending
│   └── manage.py          # CLI management tool
├── web/                   # Web interface
│   ├── app.py            # Flask application
│   ├── templates/        # HTML templates
│   └── static/           # CSS and JavaScript
├── config/               # Configuration files
│   ├── service_lines_template.csv
│   ├── client_mappings_template.csv
│   ├── starlink-manager.service  # Systemd service
│   └── nginx.conf        # Nginx configuration
├── docs/                 # Documentation
│   └── DEPLOYMENT.md     # VPS deployment guide
├── data/                 # Database storage (created on first run)
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Starlink Enterprise API credentials
- SMTP email account (for sending reports)

### Installation

1. **Extract the archive**

```bash
unzip starlink-manager.zip
cd starlink-manager
```

2. **Create virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

Required configuration:
- `STARLINK_CLIENT_ID` - Your Starlink API client ID
- `STARLINK_CLIENT_SECRET` - Your Starlink API client secret
- `SMTP_USER` - Email address for sending reports
- `SMTP_PASSWORD` - Email password or app password
- `FLASK_SECRET_KEY` - Random secret key for web sessions

5. **Import your data**

```bash
# Import service lines
python3 scripts/import_csv.py service-lines config/service_lines.csv

# Import client mappings
python3 scripts/import_csv.py client-mappings config/client_mappings.csv
```

6. **Start the web interface**

```bash
cd web
python3 app.py
```

Access the web interface at `http://localhost:5000`

**Default admin credentials** will be printed on first run. **Save these immediately!**

## Usage

### Web Interface

The web interface provides a user-friendly way to:
- View all service lines and client mappings
- Generate and send usage reports
- View real-time usage data
- Track report history
- Manage team member access (admin only)

**Access levels:**
- **Admin**: Full access including user management
- **Member**: Can generate reports and view all data
- **Viewer**: Read-only access to data and reports

### Command Line Tools

#### 1. Direct API Queries

Query the Starlink API directly without database storage:

```bash
# List all accounts
python3 starlink/starlink_api_cli.py accounts

# List terminals for an account
python3 starlink/starlink_api_cli.py terminals --account ACC-12345-67890-12

# Get usage data
python3 starlink/starlink_api_cli.py usage --account ACC-12345-67890-12

# Get usage for specific terminals
python3 starlink/starlink_api_cli.py usage --account ACC-12345-67890-12 \
    --service-lines SL-123-456-78 SL-987-654-32

# Get usage for date range
python3 starlink/starlink_api_cli.py usage --account ACC-12345-67890-12 \
    --start-date 2025-10-13 --end-date 2025-11-09
```

#### 2. Database Management

Manage service lines and client mappings:

```bash
# List all service lines
python3 scripts/manage.py list-service-lines

# List all client mappings
python3 scripts/manage.py list-mappings

# View mapping details
python3 scripts/manage.py view-mapping --id 1

# Add service line interactively
python3 scripts/manage.py add-service-line

# Add client mapping interactively
python3 scripts/manage.py add-mapping

# View report logs
python3 scripts/manage.py logs

# Deactivate a mapping
python3 scripts/manage.py deactivate-mapping --id 1
```

#### 3. Report Generation

Generate and send usage reports:

```bash
# Send report for a specific mapping
python3 scripts/send_report.py --mapping-id 1

# Send report for custom date range
python3 scripts/send_report.py --mapping-id 1 \
    --start-date 2025-10-13 --end-date 2025-11-09

# Preview report without sending (dry run)
python3 scripts/send_report.py --mapping-id 1 --dry-run

# Send reports to all active mappings
python3 scripts/send_report.py --all
```

#### 4. CSV Import

Import data from CSV files:

```bash
# Import service lines
python3 scripts/import_csv.py service-lines path/to/service_lines.csv

# Import client mappings
python3 scripts/import_csv.py client-mappings path/to/client_mappings.csv
```

### CSV File Formats

#### Service Lines CSV

```csv
account_number,service_line_id,nickname,service_line_number,active
ACC-12345-67890-12,SL-ABC-123-456-78,Office Terminal 1,1234567890,true
ACC-12345-67890-12,SL-ABC-987-654-32,Office Terminal 2,0987654321,true
```

**Fields:**
- `account_number` (required): Starlink account number
- `service_line_id` (required): Service line identifier
- `nickname` (optional): Friendly name for the terminal
- `service_line_number` (optional): Service line number
- `active` (optional): true/false, defaults to true

#### Client Mappings CSV

```csv
client_name,service_line_id,primary_email,cc_emails,active,report_frequency
Acme Corporation,SL-ABC-123-456-78,client@acme.com,"manager@acme.com,billing@acme.com",true,on_demand
Tech Solutions,SL-ABC-987-654-32,contact@tech.com,admin@tech.com,true,daily
```

**Fields:**
- `client_name` (required): Client company name
- `service_line_id` (required): Service line to map to (must exist in service_lines)
- `primary_email` (required): Primary recipient email
- `cc_emails` (optional): Comma-separated CC emails
- `active` (optional): true/false, defaults to true
- `report_frequency` (optional): daily/weekly/on_demand, defaults to on_demand

## VPS Deployment

For production deployment on a VPS with domain and SSL, see the comprehensive deployment guide:

**[📖 VPS Deployment Guide](docs/DEPLOYMENT.md)**

The deployment guide covers:
- VPS setup and security
- Installation and configuration
- Database initialization
- Web interface with Nginx and SSL
- Team access management
- Monitoring and maintenance
- Troubleshooting

## Email Configuration

### Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Select "Mail" and "Other (Custom name)"
   - Copy the generated 16-character password
3. Use this app password in `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=your-email@gmail.com
```

### Other Email Providers

**Outlook/Office 365:**
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
```

**Custom SMTP:**
```env
SMTP_HOST=mail.yourdomain.com
SMTP_PORT=587
```

## Security Best Practices

1. **Environment Variables**
   - Never commit `.env` to version control
   - Set file permissions: `chmod 600 .env`
   - Use strong, random secret keys

2. **User Management**
   - Change default admin password immediately
   - Use strong passwords (minimum 12 characters)
   - Assign appropriate roles to team members
   - Regularly review user access

3. **Production Deployment**
   - Always use HTTPS with valid SSL certificate
   - Configure firewall (UFW or similar)
   - Keep system and dependencies updated
   - Set up automated backups

4. **Database**
   - Regular backups (automated recommended)
   - Restrict file permissions
   - Monitor database size

## Troubleshooting

### Web Interface Issues

**Cannot access web interface:**
- Check if the service is running: `sudo systemctl status starlink-manager`
- Check logs: `sudo journalctl -u starlink-manager -n 50`
- Verify port 5000 is not blocked by firewall

**Login issues:**
- Verify user exists in database
- Reset password using command line (see DEPLOYMENT.md)
- Check session configuration

### Email Sending Issues

**Reports not sending:**
- Verify SMTP credentials in `.env`
- Test with `--dry-run` flag first
- Check if Gmail App Password is used (not regular password)
- Review error messages in report logs

### API Connection Issues

**Cannot fetch data from Starlink API:**
- Verify API credentials are correct
- Check internet connectivity
- Ensure API credentials have proper permissions
- Check API rate limits

### Database Issues

**Database locked errors:**
- Ensure only one process is writing at a time
- Check file permissions on database file
- Verify sufficient disk space

## Development

### Running Tests

```bash
# Test API connection
python3 starlink/starlink_api_cli.py accounts

# Test report generation (dry run)
python3 scripts/send_report.py --mapping-id 1 --dry-run

# Test web interface
cd web
python3 app.py
```

### Adding New Features

The codebase is modular and extensible:
- **API operations**: Add methods to manager classes in `starlink/`
- **Database operations**: Add methods to `database/db.py`
- **Web routes**: Add routes to `web/app.py`
- **CLI commands**: Add commands to scripts in `scripts/`

## System Requirements

### Minimum Requirements
- Python 3.8+
- 512MB RAM
- 1GB disk space
- Internet connection

### Recommended for Production
- Python 3.10+
- 2GB RAM
- 10GB disk space
- Ubuntu 22.04 LTS
- Domain name with SSL

## Dependencies

Core dependencies:
- `requests` - HTTP client for API calls
- `python-dotenv` - Environment variable management
- `Flask` - Web framework
- `tabulate` - CLI table formatting
- `gunicorn` - Production WSGI server (optional)

All dependencies are specified in `requirements.txt`.

## License

This project is proprietary software. All rights reserved.

## Support

For deployment assistance or issues:
1. Consult this README
2. Review the [Deployment Guide](docs/DEPLOYMENT.md)
3. Check logs for error messages
4. Contact your system administrator

## Changelog

### Version 1.0.0 (November 2025)
- Initial release
- Starlink API integration
- Database management with SQLite
- CSV import functionality
- Email report generation
- Web interface with authentication
- Role-based access control
- VPS deployment support

---

**Built with ❤️ for efficient Starlink management**
