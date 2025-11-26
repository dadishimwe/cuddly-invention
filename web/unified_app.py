#!/usr/bin/env python3
"""
Unified Application with Subdomain Routing
Routes requests to admin dashboard or client portal based on subdomain
"""

from flask import Flask, request, redirect
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import both applications
from web.app import app as admin_app
from web.client_portal import app as client_app


def create_unified_app():
    """Create unified application with subdomain-based routing"""
    
    # Get subdomain configuration from environment
    admin_subdomain = os.getenv('ADMIN_SUBDOMAIN', 'zubadash.dadishimwe.com')
    client_subdomain = os.getenv('CLIENT_SUBDOMAIN', 'zubaclient.dadishimwe.com')
    
    # Create a simple dispatcher app
    main_app = Flask('unified')
    
    @main_app.before_request
    def route_by_subdomain():
        """Route requests based on subdomain"""
        host = request.host.lower()
        
        # Remove port if present
        if ':' in host:
            host = host.split(':')[0]
        
        # Check which subdomain is being accessed
        if admin_subdomain in host or host.startswith('admin.') or host.startswith('zubadash.'):
            # Route to admin app
            return admin_app.wsgi_app(request.environ, lambda *args: None)
        elif client_subdomain in host or host.startswith('client.') or host.startswith('zubaclient.'):
            # Route to client app
            return client_app.wsgi_app(request.environ, lambda *args: None)
        else:
            # Default to admin for localhost/IP access
            if 'localhost' in host or host.replace('.', '').isdigit():
                return admin_app.wsgi_app(request.environ, lambda *args: None)
            
            # Unknown subdomain
            return f"Unknown subdomain. Please use {admin_subdomain} or {client_subdomain}", 404
    
    @main_app.route('/health')
    def health():
        """Health check for the unified app"""
        from flask import jsonify
        return jsonify({'status': 'healthy', 'service': 'unified'}), 200
    
    return main_app


# Create the unified app
app = create_unified_app()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("=" * 80)
    print("Starlink Manager - Unified Application")
    print("=" * 80)
    print(f"Admin Dashboard: {os.getenv('ADMIN_SUBDOMAIN', 'zubadash.dadishimwe.com')}")
    print(f"Client Portal:   {os.getenv('CLIENT_SUBDOMAIN', 'zubaclient.dadishimwe.com')}")
    print(f"Port:            {port}")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
