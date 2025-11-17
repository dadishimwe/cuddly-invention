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


@app.route('/preview-report/<int:mapping_id>', methods=['GET', 'POST'])
@login_required
def preview_report(mapping_id):
    """Preview email report before sending"""
    mapping = db.get_client_mapping(mapping_id)
    if not mapping:
        flash('Mapping not found', 'error')
        return redirect(url_for('mappings'))
    
    start_date = request.args.get('start_date') or request.form.get('start_date')
    end_date = request.args.get('end_date') or request.form.get('end_date')
    
    try:
        client = get_starlink_client()
        from scripts.send_report import EmailReportGenerator
        generator = EmailReportGenerator(db, client, dry_run=True)
        
        # Get usage data
        usage_data = client.usage.get_live_usage_data(
            mapping['account_number'],
            service_lines=[mapping['service_line_id']],
            cycles_to_fetch=1
        )
        
        sl_data = usage_data.get(mapping['service_line_id'], {})
        daily_usage = sl_data.get('daily_usage', [])
        
        if start_date and end_date:
            daily_usage = [
                day for day in daily_usage
                if start_date <= day.get('date', '') <= end_date
            ]
        else:
            if daily_usage:
                start_date = daily_usage[0].get('date')
                end_date = daily_usage[-1].get('date')
        
        total_usage_gb = sum(day.get('total_gb', 0) for day in daily_usage)
        
        # Generate HTML preview
        html_content = generator._format_html_email(
            mapping['client_name'],
            mapping['service_line_id'],
            mapping['nickname'],
            daily_usage,
            start_date,
            end_date,
            total_usage_gb
        )
        
        return render_template('preview_report.html', 
                             mapping=mapping,
                             html_content=html_content,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        flash(f'Error generating preview: {str(e)}', 'error')
        return redirect(url_for('mapping_detail', mapping_id=mapping_id))


@app.route('/batch-send', methods=['GET', 'POST'])
@login_required
def batch_send():
    """Send reports to multiple clients"""
    if request.method == 'POST':
        mapping_ids = request.form.getlist('mapping_ids')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not mapping_ids:
            flash('Please select at least one client', 'error')
            return redirect(url_for('batch_send'))
        
        try:
            client = get_starlink_client()
            generator = EmailReportGenerator(db, client, dry_run=False)
            
            success_count = 0
            error_count = 0
            
            for mapping_id in mapping_ids:
                try:
                    generator.generate_report(int(mapping_id), start_date, end_date)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Error sending to mapping {mapping_id}: {e}")
            
            flash(f'Batch send complete: {success_count} sent, {error_count} failed', 'success' if error_count == 0 else 'warning')
        except Exception as e:
            flash(f'Error in batch send: {str(e)}', 'error')
        
        return redirect(url_for('reports'))
    
    # GET request - show form
    mappings = db.get_client_mappings(active_only=True)
    return render_template('batch_send.html', mappings=mappings)


@app.route('/edit-mapping/<int:mapping_id>', methods=['GET', 'POST'])
@login_required
def edit_mapping(mapping_id):
    """Edit client mapping"""
    mapping = db.get_client_mapping(mapping_id)
    if not mapping:
        flash('Mapping not found', 'error')
        return redirect(url_for('mappings'))
    
    if request.method == 'POST':
        try:
            db.update_client_mapping(
                mapping_id,
                client_name=request.form.get('client_name'),
                primary_email=request.form.get('primary_email'),
                cc_emails=request.form.get('cc_emails'),
                report_frequency=request.form.get('report_frequency'),
                active=request.form.get('active') == 'on'
            )
            flash('Client mapping updated successfully', 'success')
            return redirect(url_for('mapping_detail', mapping_id=mapping_id))
        except Exception as e:
            flash(f'Error updating mapping: {str(e)}', 'error')
    
    return render_template('edit_mapping.html', mapping=mapping)


@app.route('/add-mapping', methods=['GET', 'POST'])
@login_required
def add_mapping():
    """Add new client mapping"""
    if request.method == 'POST':
        try:
            db.add_client_mapping(
                client_name=request.form.get('client_name'),
                service_line_id=request.form.get('service_line_id'),
                primary_email=request.form.get('primary_email'),
                cc_emails=request.form.get('cc_emails'),
                active=request.form.get('active', 'on') == 'on',
                report_frequency=request.form.get('report_frequency', 'on_demand')
            )
            flash('Client mapping added successfully', 'success')
            return redirect(url_for('mappings'))
        except Exception as e:
            flash(f'Error adding mapping: {str(e)}', 'error')
    
    service_lines = db.get_service_lines(active_only=True)
    return render_template('add_mapping.html', service_lines=service_lines)


@app.route('/add-terminal', methods=['GET', 'POST'])
@login_required
def add_terminal():
    """Add new service line/terminal"""
    if request.method == 'POST':
        try:
            db.add_service_line(
                account_number=request.form.get('account_number'),
                service_line_id=request.form.get('service_line_id'),
                nickname=request.form.get('nickname'),
                service_line_number=request.form.get('service_line_number'),
                active=request.form.get('active', 'on') == 'on'
            )
            flash('Terminal added successfully', 'success')
            return redirect(url_for('service_lines'))
        except Exception as e:
            flash(f'Error adding terminal: {str(e)}', 'error')
    
    return render_template('add_terminal.html')


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
