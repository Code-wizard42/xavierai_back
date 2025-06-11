#!/usr/bin/env python3
"""
Run script for Xavier AI Backend

This script properly sets up the environment and runs the Flask application.
Use this instead of running app.py directly.
"""

import os
import sys

# Add current directory to Python path so imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set environment variables for development
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

# Import and run the app
from app import app

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    print(f"Starting Xavier AI Backend on port {port}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True if os.environ.get('FLASK_ENV') == 'development' else False
    ) 