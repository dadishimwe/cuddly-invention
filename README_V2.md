# Zuba Broadband Starlink Manager v2.0

**Enterprise-grade Starlink management platform for ISPs and service providers**

A comprehensive platform for managing Starlink services, client relationships, usage tracking, and reporting. Built specifically for Zuba Broadband with support for both internal team management and client self-service.

---

## 🎯 Key Features

### For Internal Team (Team Portal)
- ✅ **Client Management** - Manage client organizations with multiple contacts
- ✅ **Multi-Kit Support** - Assign multiple Starlink terminals to single clients
- ✅ **Installation Tracking** - Record installation details, Peplink routers, equipment
- ✅ **Usage Monitoring** - Real-time and historical usage data
- ✅ **Email Reports** - Automated usage report generation and delivery
- ✅ **Batch Operations** - Send reports to multiple clients at once
- ✅ **Audit Logging** - Track all system activities
- ✅ **Role-Based Access** - Admin, Member, and Viewer roles

### For Clients (Client Portal)
- ✅ **Self-Service Dashboard** - View all terminals and usage at a glance
- ✅ **Multi-Kit Dashboard** - Manage multiple Starlink terminals in one account
- ✅ **Usage Charts** - Interactive charts for long-term usage analysis
- ✅ **Historical Data** - Access usage data from October 2024 onwards
- ✅ **Report History** - View all past usage reports
- ✅ **Account Management** - Update password and preferences
- ✅ **Installation Details** - View equipment and installation information

### Technical Features
- ✅ **Historical Data Import** - Backfill usage data from October 2024
- ✅ **Responsive Design** - Works on mobile, tablet, and desktop
- ✅ **Anthropic-Inspired UI** - Clean, modern interface
- ✅ **Zuba Broadband Branding** - Custom colors and logo
- ✅ **Edge Case Handling** - Robust error handling and validation
- ✅ **Rate Limiting** - Prevents API throttling during bulk imports
- ✅ **Database Migration** - Safe upgrade from v1 to v2

---

## 🏗️ Architecture

### Two-Portal System

**1. Team Portal** (`web/app.py`)
- Port: 5000 (default)
- For Zuba Broadband staff
- Full administrative access
- Client and terminal management
- Report generation and sending

**2. Client Portal** (`web/client_portal.py`)
- Port: 5001 (default)
- For Zuba Broadband clients
- Self-service usage viewing
- Multi-kit dashboard
- Report history

### Database Schema v2

The enhanced schema supports:
- **Clients** - Organization/company records
- **Client Contacts** - Multiple contacts per client
- **Client Service Lines** - Many-to-many relationship (multi-kit)
- **Client Accounts** - Portal login credentials
- **Installations** - Equipment and installation tracking
- **Daily Usage History** - Historical usage data storage
- **Billing Cycles** - Cycle-based usage summaries
- **Audit Logs** - Activity tracking
- **Support Tickets** - (Ready for future implementation)

---

## 🚀 Quick Start

### 1. Migration from v1

If you have an existing v1 installation:

```bash
cd /path/to/zuba-broadband
python3 database/migrate_to_v2.py
```

This will:
- Backup your existing database
- Create new tables
- Migrate existing client_mappings to clients
- Preserve all historical data

### 2. Fresh Installation

```bash
# Clone repository
git clone https://github.com/dadishimwe/cuddly-invention.git zuba-broadband
cd zuba-broadband

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your credentials
```

### 3. Import Historical Data

```bash
# Import usage data from October 2024 onwards
python3 scripts/import_historical_data.py --start-date 2024-10-01 --cycles 12

# Or import for specific service line
python3 scripts/import_historical_data.py \
    --service-line SL-ABC-123-456-78 \
    --account ACC-12345-67890-12 \
    --cycles 12
```

### 4. Create Client Accounts

```bash
# Using Python shell
python3
>>> from database.db_v2 import DatabaseV2
>>> db = DatabaseV2()
>>> 
>>> # Create client organization
>>> client_id = db.create_client(
...     company_name="Acme Corporation",
...     status="active",
...     billing_address="123 Main St, Kigali"
... )
>>> 
>>> # Assign service line to client
>>> db.assign_service_line_to_client(client_id, "SL-ABC-123-456-78")
>>> 
>>> # Create portal account for client
>>> db.create_client_account(
...     client_id=client_id,
...     email="admin@acme.com",
...     password="secure_password",
...     name="John Doe"
... )
```

### 5. Run Applications

```bash
# Terminal 1: Team Portal
source venv/bin/activate
python3 web/app.py

# Terminal 2: Client Portal
source venv/bin/activate
python3 web/client_portal.py
```

Access:
- Team Portal: http://localhost:5000
- Client Portal: http://localhost:5001

---

## 📊 Usage Data Management

### Understanding Billing Cycles

Starlink usage is organized by billing cycles (typically 30 days). The system:
- Automatically detects billing cycle dates from API data
- Groups daily usage by cycle
- Displays cycle-based summaries
- Allows filtering by specific cycles

### Chart Display Strategy

For long-term data (12+ billing cycles):
- **Dashboard**: Shows current cycle only
- **Usage Details**: Dropdown to select specific cycle
- **Charts**: Display one cycle at a time for clarity
- **Tables**: Show daily breakdown for selected cycle

This prevents overwhelming users with too much data while maintaining full access to historical information.

### Edge Cases Handled

1. **Missing Data Days** - Gracefully handled, shown as gaps
2. **Partial Cycles** - Correctly calculated and displayed
3. **Multiple Kits** - Each kit tracked independently
4. **Rate Limiting** - Automatic delays between API requests
5. **Duplicate Prevention** - Database constraints prevent duplicate entries
6. **API Errors** - Logged and reported without crashing

---

## 🎨 Design System

### Color Palette

- **Primary Orange**: `#eb6e34` - Zuba Broadband primary color
- **Deep Blue**: `#060352` - Accent color for headers
- **Success Green**: `#10b981` - Positive states
- **Error Red**: `#ef4444` - Warnings and errors
- **Neutral Gray**: `#6b7280` - Secondary text

### Responsive Breakpoints

- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

All interfaces are fully responsive and mobile-optimized.

---

## 🔐 Security Features

### Authentication
- Separate authentication for team and clients
- Password hashing with SHA-256 + salt
- Session management
- Automatic session expiry

### Authorization
- Role-based access control (RBAC)
- Clients can only view their own data
- Team members have role-specific permissions
- API endpoints validate access

### Audit Logging
- All important actions logged
- User ID, type, action, resource tracked
- IP address and user agent recorded
- Queryable audit trail

### Data Protection
- Environment variables for sensitive data
- No pricing information exposed
- Client data isolation
- Secure password storage

---

## 📁 Project Structure

```
zuba-broadband/
├── database/
│   ├── db.py                    # Legacy database operations
│   ├── db_v2.py                 # Enhanced database operations
│   ├── schema.sql               # Legacy schema
│   ├── schema_v2.sql            # Enhanced schema
│   └── migrate_to_v2.py         # Migration script
├── scripts/
│   ├── import_csv.py            # CSV import utility
│   ├── import_historical_data.py # Historical data import
│   ├── send_report.py           # Email report generator
│   └── manage.py                # Management CLI
├── starlink/
│   ├── StarlinkClient.py        # Main API client
│   ├── AuthManager.py           # Authentication
│   ├── AccountManager.py        # Account operations
│   ├── ServiceLineManager.py    # Service line operations
│   └── UsageManager.py          # Usage data operations
├── web/
│   ├── app.py                   # Team portal application
│   ├── client_portal.py         # Client portal application
│   ├── static/
│   │   ├── css/style.css        # Styles
│   │   ├── js/main.js           # JavaScript
│   │   └── images/zuba-logo.png # Logo
│   └── templates/
│       ├── *.html               # Team portal templates
│       └── client_portal/       # Client portal templates
├── config/
│   ├── *.csv                    # CSV templates
│   ├── nginx.conf               # Nginx configuration
│   └── starlink-manager.service # Systemd service
├── docs/
│   └── DEPLOYMENT.md            # Deployment guide
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
└── README_V2.md                 # This file
```

---

## 🔧 Configuration

### Environment Variables

Required in `.env`:

```env
# Starlink API
STARLINK_CLIENT_ID=your_client_id
STARLINK_CLIENT_SECRET=your_client_secret

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# Flask
FLASK_SECRET_KEY=generate-random-key
FLASK_DEBUG=False

# Ports
PORT=5000
CLIENT_PORTAL_PORT=5001
```

### Generate Secret Key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📖 Common Tasks

### Add a New Client

```python
from database.db_v2 import DatabaseV2
db = DatabaseV2()

# Create client
client_id = db.create_client(
    company_name="New Client Ltd",
    status="active",
    service_start_date="2025-01-01"
)

# Add contact
db.add_client_contact(
    client_id=client_id,
    name="Jane Smith",
    email="jane@newclient.com",
    role="primary",
    is_primary=True
)

# Assign service line
db.assign_service_line_to_client(client_id, "SL-XYZ-789")

# Create portal account
db.create_client_account(
    client_id=client_id,
    email="portal@newclient.com",
    password="SecurePass123!",
    name="Jane Smith"
)
```

### Record an Installation

```python
from datetime import date

db.add_installation(
    service_line_id="SL-XYZ-789",
    installation_date=date(2025, 1, 15),
    technician_name="John Tech",
    installation_address="456 Street, Kigali",
    peplink_router_installed=True,
    peplink_model="Peplink MAX BR1 Pro 5G",
    peplink_serial_number="PL123456",
    installation_notes="Installation completed successfully"
)
```

### Import Historical Data

```bash
# All service lines
python3 scripts/import_historical_data.py \
    --start-date 2024-10-01 \
    --cycles 12 \
    --delay 2

# Specific service line
python3 scripts/import_historical_data.py \
    --service-line SL-ABC-123 \
    --account ACC-12345 \
    --cycles 12
```

---

## 🚢 Deployment

### Production Deployment

See `docs/DEPLOYMENT.md` for complete deployment guide.

Quick overview:

1. **VPS Setup** - Ubuntu 22.04 LTS recommended
2. **Domain Configuration** - Point DNS to your VPS
3. **SSL Certificate** - Use Let's Encrypt (Certbot)
4. **Systemd Services** - Run both portals as services
5. **Nginx Reverse Proxy** - Route domains to correct ports
6. **Firewall** - Configure UFW

### Recommended Setup

- **Team Portal**: `admin.zuba.dadishimwe.com` → Port 5000
- **Client Portal**: `zuba.dadishimwe.com` → Port 5001

Both behind Nginx with SSL.

---

## 🐛 Troubleshooting

### Database Migration Issues

```bash
# Check current schema version
sqlite3 data/starlink.db "SELECT * FROM schema_version"

# Restore from backup if needed
cp data/starlink.db.backup_YYYYMMDD_HHMMSS data/starlink.db
```

### Historical Import Fails

- Check API credentials in `.env`
- Verify service line IDs are correct
- Increase `--delay` to avoid rate limiting
- Check logs for specific error messages

### Client Portal Login Issues

- Verify client account exists in database
- Check password was set correctly
- Ensure `active = TRUE` for account
- Check audit logs for login attempts

---

## 📈 Future Enhancements

Ready for implementation:

- [ ] PDF report generation
- [ ] Support ticket system
- [ ] Automated billing integration
- [ ] SMS notifications
- [ ] Mobile app
- [ ] Advanced analytics dashboard
- [ ] Custom report builder
- [ ] API endpoints for integrations

---

## 🤝 Support

For issues or questions:
1. Check this README
2. Review `docs/DEPLOYMENT.md`
3. Check audit logs and application logs
4. Contact Zuba Broadband technical team

---

## 📝 License

Proprietary - Zuba Broadband

---

## 🎉 Changelog

### Version 2.0 (2025-01-19)

**Major Features:**
- Multi-kit client support
- Separate client portal
- Historical data import (from Oct 2024)
- Installation tracking
- Enhanced database schema
- Audit logging
- Responsive design improvements
- User-friendly charts for long-term data

**Database Changes:**
- New tables: clients, client_contacts, client_service_lines, client_accounts
- New tables: installations, daily_usage_history, billing_cycles
- New tables: audit_logs, user_sessions
- Migration script from v1 to v2

**UI/UX Improvements:**
- Anthropic-inspired design
- Zuba Broadband branding
- Mobile-optimized layouts
- Interactive usage charts
- Improved navigation

**Technical Improvements:**
- Rate limiting for API requests
- Edge case handling
- Database indexing
- Session management
- Password security enhancements

---

**Built with ❤️ for Zuba Broadband**
