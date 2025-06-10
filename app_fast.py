"""
Fast Development Application Module.
This is a streamlined version of the main app for faster development startup.
"""

import os
import logging
import time
from flask import Flask, request, jsonify, make_response, session
from flask_cors import CORS
from xavier_back.config import Config
from xavier_back.extensions import db, migrate
from xavier_back.routes.auth import auth_bp
from xavier_back.routes.chatbot import chatbot_bp
from xavier_back.models import User
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_session import Session

# Set environment variable for development mode
os.environ['FLASK_ENV'] = 'development'
os.environ['FAST_MODE'] = 'true'

# Set up minimal logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def create_fast_app():
    """Create a fast-loading Flask application for development."""
    
    # Create app with minimal configuration
    app = Flask(__name__)
    
    # Essential configuration only
    app.config.from_object(Config)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/xavier.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Session configuration (filesystem only for speed)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = './flask_session'
    app.config['SESSION_PERMANENT'] = False
    
    # Initialize only essential extensions
    db.init_app(app)
    Session(app)
    
    # Minimal CORS setup
    CORS(app, supports_credentials=True, origins="*")
    
    # Use ProxyFix for development
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    
    # Essential request handlers
    @app.before_request
    def before_request():
        request.environ['REQUEST_START_TIME'] = time.time()
        
        # Handle OPTIONS requests
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, user-id')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 200

    @app.after_request
    def after_request(response):
        # Minimal CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Performance tracking (optional)
        request_time = time.time() - request.environ.get('REQUEST_START_TIME', time.time())
        if request_time > 2:  # Only log slow requests
            logger.warning(f"Slow request: {request.path} took {request_time:.2f}s")
            
        return response

    # Register only essential blueprints
    app.register_blueprint(chatbot_bp)  # Main chatbot functionality
    app.register_blueprint(auth_bp)     # Authentication if needed
    
    # Essential routes
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "mode": "fast"})
    
    # Minimal database setup
    with app.app_context():
        try:
            # Create tables only if they don't exist
            db.create_all()
            
            # Create default user if needed
            if not db.session.get(User, 4269):
                default_user = User(
                    id=4269,
                    username='default_ticket_user',
                    password_hash='default_not_used'
                )
                db.session.add(default_user)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Database setup error: {e}")
            db.session.rollback()

    return app

# Create the fast app
app = create_fast_app()

if __name__ == '__main__':
    print("🚀 Starting Xavier AI in FAST MODE")
    print("⚡ Skipping: Firebase, NLTK, Vector DB, Scheduler, Analytics")
    print("✅ Available: Chatbot API, Authentication, Health Check")
    print("🌐 Server starting at http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 