#!/usr/bin/env python3
"""
Starlink Manager Web Interface
Secure web interface for team members to view and generate reports
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database
from starlink.StarlinkClient import StarlinkClient
from scripts.send_report import EmailReportGenerator

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Initialize database
db_path = os.getenv('STARLINK_DB_PATH') or None
db = Database(db_path)

# Initialize Starlink client (lazy load)
_starlink_client = None

def get_starlink_client():
    """Get or create Starlink client"""
    global _starlink_client
    if _starlink_client is None:
        client_id = os.getenv('STARLINK_CLIENT_ID')
        client_secret = os.getenv('STARLINK_CLIENT_SECRET')
        if not client_id or not client_secret:
            raise ValueError("Starlink credentials not configured")
        _starlink_client = StarlinkClient(client_id, client_secret)
    return _starlink_client


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.get_team_member(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user['role']
            session.permanent = True
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Get statistics
    mappings = db.get_client_mappings(active_only=True)
    service_lines = db.get_service_lines(active_only=True)
    recent_logs = db.get_report_logs(limit=10)
    
    stats = {
        'total_clients': len(mappings),
        'total_service_lines': len(service_lines),
        'reports_sent_today': len([log for log in recent_logs 
                                   if log['sent_at'] and log['sent_at'][:10] == datetime.now().strftime('%Y-%m-%d')]),
        'pending_reports': len([log for log in recent_logs if log['status'] == 'pending'])
    }
    
    return render_template('dashboard.html', stats=stats, recent_logs=recent_logs)


@app.route('/mappings')
@login_required
def mappings():
    """View all client mappings"""
    all_mappings = db.get_client_mappings(active_only=False)
    return render_template('mappings.html', mappings=all_mappings)


@app.route('/mapping/<int:mapping_id>')
@login_required
def mapping_detail(mapping_id):
    """View mapping details"""
    mapping = db.get_client_mapping(mapping_id)
    if not mapping:
        flash('Mapping not found', 'error')
        return redirect(url_for('mappings'))
    
    logs = db.get_report_logs(limit=20, mapping_id=mapping_id)
    return render_template('mapping_detail.html', mapping=mapping, logs=logs)


@app.route('/service-lines')
@login_required
def service_lines():
    """View all service lines"""
    all_service_lines = db.get_service_lines(active_only=False)
    return render_template('service_lines.html', service_lines=all_service_lines)


@app.route('/reports')
@login_required
def reports():
    """View report logs"""
    limit = request.args.get('limit', 100, type=int)
    logs = db.get_report_logs(limit=limit)
    return render_template('reports.html', logs=logs)


@app.route('/generate-report', methods=['GET', 'POST'])
@login_required
def generate_report():
    """Generate and send a report"""
    if request.method == 'POST':
        mapping_id = request.form.get('mapping_id', type=int)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        dry_run = request.form.get('dry_run') == 'on'
        
        if not mapping_id:
            flash('Please select a client mapping', 'error')
            return redirect(url_for('generate_report'))
        
        try:
            client = get_starlink_client()
            generator = EmailReportGenerator(db, client, dry_run=dry_run)
            generator.generate_report(mapping_id, start_date, end_date)
            
            if dry_run:
                flash('Report preview generated (not sent)', 'info')
            else:
                flash('Report sent successfully!', 'success')
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'error')
        
        return redirect(url_for('mapping_detail', mapping_id=mapping_id))
    
    # GET request - show form
    mappings = db.get_client_mappings(active_only=True)
    return render_template('generate_report.html', mappings=mappings)


@app.route('/usage/<service_line_id>')
@login_required
def view_usage(service_line_id):
    """View usage data for a service line"""
    try:
        # Get service line details
        service_line = db.get_service_line(service_line_id)
        if not service_line:
            flash('Service line not found', 'error')
            return redirect(url_for('service_lines'))
        
        # Fetch usage data from API
        client = get_starlink_client()
        usage_data = client.usage.get_live_usage_data(
            service_line['account_number'],
            service_lines=[service_line_id],
            cycles_to_fetch=1
        )
        
        sl_data = usage_data.get(service_line_id, {})
        
        return render_template('usage.html', 
                             service_line=service_line,
                             usage_data=sl_data)
    except Exception as e:
        flash(f'Error fetching usage data: {str(e)}', 'error')
        return redirect(url_for('service_lines'))


# Admin routes
@app.route('/admin/users')
@admin_required
def admin_users():
    """Manage team members (admin only)"""
    users = db.get_all_team_members(active_only=False)
    return render_template('admin_users.html', users=users)


@app.route('/admin/add-user', methods=['POST'])
@admin_required
def admin_add_user():
    """Add a new team member (admin only)"""
    username = request.form.get('username')
    password = request.form.get('password')
    name = request.form.get('name')
    email = request.form.get('email')
    role = request.form.get('role', 'member')
    
    if not all([username, password, name, email]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        password_hash = generate_password_hash(password)
        db.add_team_member(username, password_hash, name, email, role)
        flash(f'User {username} added successfully', 'success')
    except Exception as e:
        flash(f'Error adding user: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))


# API endpoints
@app.route('/api/mappings')
@login_required
def api_mappings():
    """API endpoint to get all mappings"""
    mappings = db.get_client_mappings(active_only=True)
    return jsonify(mappings)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint to get dashboard stats"""
    mappings = db.get_client_mappings(active_only=True)
    service_lines = db.get_service_lines(active_only=True)
    recent_logs = db.get_report_logs(limit=100)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    stats = {
        'total_clients': len(mappings),
        'total_service_lines': len(service_lines),
        'reports_sent_today': len([log for log in recent_logs 
                                   if log['sent_at'] and log['sent_at'][:10] == today]),
        'total_reports': len(recent_logs),
        'failed_reports': len([log for log in recent_logs if log['status'] == 'failed'])
    }
    
    return jsonify(stats)


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found', code=404), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error', code=500), 500


if __name__ == '__main__':
    # Create default admin user if no users exist
    users = db.get_all_team_members(active_only=False)
    if not users:
        print("Creating default admin user...")
        default_password = secrets.token_urlsafe(16)
        password_hash = generate_password_hash(default_password)
        db.add_team_member('admin', password_hash, 'Administrator', 
                          'admin@example.com', 'admin')
        print(f"Default admin user created:")
        print(f"  Username: admin")
        print(f"  Password: {default_password}")
        print(f"  Please change this password after first login!")
    
    # Run development server
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
