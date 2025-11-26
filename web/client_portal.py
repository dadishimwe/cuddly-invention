"""
Client Portal - Self-service portal for Zuba Broadband clients
Allows clients to view their usage, download reports, and manage their account
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from functools import wraps
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_v2 import DatabaseV2
from starlink.StarlinkClient import StarlinkClient

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-in-production')

# Chatwoot configuration
app.config['CHATWOOT_WEBSITE_TOKEN'] = os.getenv('CHATWOOT_WEBSITE_TOKEN')
app.config['CHATWOOT_BASE_URL'] = os.getenv('CHATWOOT_BASE_URL', 'https://app.chatwoot.com')

# Initialize database
db = DatabaseV2()

# Initialize Starlink client
starlink_client = StarlinkClient(
    client_id=os.getenv('STARLINK_CLIENT_ID'),
    client_secret=os.getenv('STARLINK_CLIENT_SECRET')
)


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def login_required(f):
    """Decorator to require client login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'client_account_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health')
def health():
    """Health check endpoint for Docker"""
    from flask import jsonify
    return jsonify({'status': 'healthy', 'service': 'client_portal'}), 200


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Client portal login"""
    if 'client_account_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        account = db.authenticate_client_account(email, password)
        
        if account:
            session['client_account_id'] = account['id']
            session['client_id'] = account['client_id']
            session['client_name'] = account['name']
            session['client_email'] = account['email']
            
            # Log audit
            db.log_audit(
                user_id=account['id'],
                user_type='client_account',
                action='login',
                resource_type='session',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash(f'Welcome back, {account["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('client_portal/login.html')


@app.route('/logout')
@login_required
def logout():
    """Client portal logout"""
    # Log audit
    if 'client_account_id' in session:
        db.log_audit(
            user_id=session['client_account_id'],
            user_type='client_account',
            action='logout',
            resource_type='session',
            ip_address=request.remote_addr
        )
    
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# ============================================================================
# DASHBOARD
# ============================================================================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Client dashboard showing all kits and usage overview"""
    client_id = session['client_id']
    
    # Get client info
    client = db.get_client(client_id)
    
    # Get all service lines for this client
    service_lines = db.get_client_service_lines(client_id)
    
    # Get usage summary for each service line
    usage_summaries = []
    total_usage_all_kits = 0
    
    for sl in service_lines:
        try:
            # Try to get usage from historical data first
            cycles = db.get_usage_summary_by_cycle(sl['service_line_id'])
            
            # If no historical data, fetch from API (like admin does)
            if not cycles:
                try:
                    usage_data = starlink_client.usage.get_live_usage_data(
                        sl['account_number'],
                        service_lines=[sl['service_line_id']],
                        cycles_to_fetch=1
                    )
                    
                    sl_data = usage_data.get(sl['service_line_id'], {})
                    daily_usage = sl_data.get('daily_usage', [])
                    
                    if daily_usage:
                        # Calculate totals from API data
                        total_usage = sum(day.get('total_gb', day.get('usage_gb', 0)) for day in daily_usage)
                        cycle_start = sl_data.get('billing_cycle_start_date')
                        cycle_end = sl_data.get('billing_cycle_end_date')
                        
                        usage_summaries.append({
                            'service_line_id': sl['service_line_id'],
                            'nickname': sl['nickname'] or 'Unnamed Terminal',
                            'account_number': sl['account_number'],
                            'total_usage_gb': total_usage,
                            'cycle_start': cycle_start,
                            'cycle_end': cycle_end,
                            'days_count': len(daily_usage),
                            'source': 'api'
                        })
                        total_usage_all_kits += total_usage
                    else:
                        usage_summaries.append({
                            'service_line_id': sl['service_line_id'],
                            'nickname': sl['nickname'] or 'Unnamed Terminal',
                            'account_number': sl['account_number'],
                            'total_usage_gb': 0,
                            'cycle_start': None,
                            'cycle_end': None,
                            'days_count': 0,
                            'source': 'none'
                        })
                except Exception as api_error:
                    print(f"Error fetching from API for {sl['service_line_id']}: {api_error}")
                    usage_summaries.append({
                        'service_line_id': sl['service_line_id'],
                        'nickname': sl['nickname'] or 'Unnamed Terminal',
                        'account_number': sl['account_number'],
                        'total_usage_gb': 0,
                        'cycle_start': None,
                        'cycle_end': None,
                        'days_count': 0,
                        'source': 'error',
                        'error': str(api_error)
                    })
            else:
                # Use historical data
                latest_cycle = cycles[0]
                usage_summaries.append({
                    'service_line_id': sl['service_line_id'],
                    'nickname': sl['nickname'] or 'Unnamed Terminal',
                    'account_number': sl['account_number'],
                    'total_usage_gb': latest_cycle['total_usage_gb'],
                    'cycle_start': latest_cycle['billing_cycle_start'],
                    'cycle_end': latest_cycle['billing_cycle_end'],
                    'days_count': latest_cycle['days_count'],
                    'source': 'historical'
                })
                total_usage_all_kits += latest_cycle['total_usage_gb']
        except Exception as e:
            print(f"Error fetching usage for {sl['service_line_id']}: {e}")
            usage_summaries.append({
                'service_line_id': sl['service_line_id'],
                'nickname': sl['nickname'] or 'Unnamed Terminal',
                'account_number': sl['account_number'],
                'total_usage_gb': 0,
                'cycle_start': None,
                'cycle_end': None,
                'days_count': 0,
                'source': 'error',
                'error': str(e)
            })
    
    # Log audit
    db.log_audit(
        user_id=session['client_account_id'],
        user_type='client_account',
        action='view',
        resource_type='dashboard',
        ip_address=request.remote_addr
    )
    
    return render_template('client_portal/dashboard.html',
                         client=client,
                         service_lines=service_lines,
                         usage_summaries=usage_summaries,
                         total_usage_all_kits=total_usage_all_kits)


# ============================================================================
# USAGE DETAILS
# ============================================================================

@app.route('/usage/<service_line_id>')
@login_required
def usage_details(service_line_id):
    """Detailed usage view for a specific service line"""
    client_id = session['client_id']
    
    # Verify this service line belongs to this client
    service_lines = db.get_client_service_lines(client_id)
    service_line = next((sl for sl in service_lines if sl['service_line_id'] == service_line_id), None)
    
    if not service_line:
        flash('Service line not found or access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get billing cycles
    cycles = db.get_usage_summary_by_cycle(service_line_id)
    
    # Get selected cycle or default to latest
    selected_cycle_start = request.args.get('cycle')
    
    if selected_cycle_start and cycles:
        cycle = next((c for c in cycles if c['billing_cycle_start'] == selected_cycle_start), cycles[0])
    elif cycles:
        cycle = cycles[0]
    else:
        cycle = None
    
    # Get daily usage for selected cycle
    daily_usage = []
    if cycle:
        daily_usage = db.get_usage_history(
            service_line_id,
            start_date=cycle['billing_cycle_start'],
            end_date=cycle['billing_cycle_end']
        )
    
    # If no historical data, fetch from API
    if not daily_usage:
        try:
            usage_data = starlink_client.usage.get_live_usage_data(
                service_line['account_number'],
                service_lines=[service_line_id],
                cycles_to_fetch=1
            )
            sl_data = usage_data.get(service_line_id, {})
            daily_usage = sl_data.get('daily_usage', [])
        except Exception as e:
            print(f"Error fetching from API: {e}")
            daily_usage = []
    
    # Get installation info
    installation = db.get_installation(service_line_id)
    
    # Log audit
    db.log_audit(
        user_id=session['client_account_id'],
        user_type='client_account',
        action='view',
        resource_type='usage',
        resource_id=service_line_id,
        ip_address=request.remote_addr
    )
    
    return render_template('client_portal/usage_details.html',
                         service_line=service_line,
                         cycles=cycles,
                         selected_cycle=cycle,
                         daily_usage=daily_usage,
                         installation=installation)


# ============================================================================
# REPORTS
# ============================================================================

@app.route('/reports')
@login_required
def reports():
    """View report history"""
    client_id = session['client_id']
    
    # Get all reports for this client
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM report_logs
            WHERE client_id = ?
            ORDER BY sent_at DESC
            LIMIT 50
        """, (client_id,))
        report_logs = [dict(row) for row in cursor.fetchall()]
    
    # Log audit
    db.log_audit(
        user_id=session['client_account_id'],
        user_type='client_account',
        action='view',
        resource_type='reports',
        ip_address=request.remote_addr
    )
    
    return render_template('client_portal/reports.html', reports=report_logs)


# ============================================================================
# ACCOUNT SETTINGS
# ============================================================================

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account_settings():
    """Account settings and password change"""
    account_id = session['client_account_id']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate
            account = db.get_client_account(account_id)
            if not db._verify_password(current_password, account['password_hash']):
                flash('Current password is incorrect', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'error')
            elif len(new_password) < 8:
                flash('Password must be at least 8 characters', 'error')
            else:
                # Update password
                db.update_client_account_password(account_id, new_password)
                
                # Log audit
                db.log_audit(
                    user_id=account_id,
                    user_type='client_account',
                    action='update',
                    resource_type='password',
                    ip_address=request.remote_addr
                )
                
                flash('Password updated successfully', 'success')
                return redirect(url_for('account_settings'))
    
    account = db.get_client_account(account_id)
    client = db.get_client(session['client_id'])
    
    return render_template('client_portal/account.html', account=account, client=client)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/usage-chart/<service_line_id>')
@login_required
def api_usage_chart(service_line_id):
    """API endpoint for usage chart data"""
    client_id = session['client_id']
    
    # Verify access
    service_lines = db.get_client_service_lines(client_id)
    if not any(sl['service_line_id'] == service_line_id for sl in service_lines):
        return jsonify({'error': 'Access denied'}), 403
    
    # Get cycle parameter
    cycle_start = request.args.get('cycle')
    
    if cycle_start:
        # Get specific cycle
        cycles = db.get_usage_summary_by_cycle(service_line_id)
        cycle = next((c for c in cycles if c['billing_cycle_start'] == cycle_start), None)
        
        if cycle:
            daily_usage = db.get_usage_history(
                service_line_id,
                start_date=cycle['billing_cycle_start'],
                end_date=cycle['billing_cycle_end']
            )
        else:
            daily_usage = []
    else:
        # Get last 30 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        daily_usage = db.get_usage_history(service_line_id, start_date, end_date)
    
    # Format for chart
    chart_data = {
        'labels': [d['usage_date'] for d in daily_usage],
        'datasets': [
            {
                'label': 'Priority Data (GB)',
                'data': [float(d['priority_gb']) for d in daily_usage],
                'borderColor': '#eb6e34',
                'backgroundColor': 'rgba(235, 110, 52, 0.1)'
            },
            {
                'label': 'Standard Data (GB)',
                'data': [float(d['standard_gb']) for d in daily_usage],
                'borderColor': '#060352',
                'backgroundColor': 'rgba(6, 3, 82, 0.1)'
            }
        ]
    }
    
    return jsonify(chart_data)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('client_portal/error.html', 
                         error_code=404, 
                         error_message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('client_portal/error.html',
                         error_code=500,
                         error_message='Internal server error'), 500


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('CLIENT_PORTAL_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     Zuba Broadband Client Portal                            ║
║     Running on http://localhost:{port}                       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
