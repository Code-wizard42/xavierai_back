"""
Main application module.
This is the entry point for the Flask application.
"""

import os
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, make_response, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from config import Config
from extensions import db, migrate
from .routes.auth import auth_bp
from .routes.chatbot import chatbot_bp
from .routes.analytics import analytics_bp
from .routes.leads import leads_bp
from .routes.email_service import email_bp
from .routes.user import user_bp
from .routes.conversation_usage import conversation_usage_bp
from .routes.admin import admin_bp
import time
from logging_config import configure_logging
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql
from models import User  # Add this import
from werkzeug.middleware.proxy_fix import ProxyFix
from firebase_config import initialize_firebase
from flask_session import Session
from flask_compress import Compress
import functools
import ensure_env as ensure_env
from .utils.log_utils import log_api_request

# Set environment variable for development mode
if not os.environ.get('FLASK_ENV') and not os.environ.get('ENVIRONMENT'):
    os.environ['FLASK_ENV'] = 'development'

# Run environment checks to ensure proper setup
ensure_env.run_all_checks()

# Set up basic logging until the app is created
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logger.info("Starting Xavier AI")

def create_app(test_config=None):
    """Create and configure the Flask application."""

    # Create and configure the app
    app = Flask(__name__, 
                instance_relative_config=True,
                static_folder='static',
                static_url_path='/static')

    # Load configuration
    app.config.from_object('xavier_back.config.Config')

    # Configure logging with the app
    configure_logging(app)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Configure CORS
    CORS(app, supports_credentials=True, 
         origins=["http://localhost:4200", "https://localhost:4200", "http://localhost:3000", 
                  "http://localhost:5173", "http://localhost:8080", "*"], 
         allow_headers=["Content-Type", "Authorization", "user-id", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         expose_headers=["Content-Type", "Authorization"])

    # Configure database
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure session storage
    try:
        # Import redis for session storage
        import redis
        from redis.exceptions import RedisError
        
        session_redis = None
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            # Try Redis URL first
            if redis_url.startswith('rediss://'):
                # For SSL connections, try multiple SSL configurations for compatibility
                try:
                    # Try basic SSL config first
                    session_redis = redis.from_url(
                        redis_url,
                        ssl_cert_reqs=None,
                        ssl_check_hostname=False,
                        ssl_ca_certs=None,
                        decode_responses=False,  # Critical: Use False to avoid Unicode issues with session data
                        socket_timeout=10,
                        socket_connect_timeout=10,
                        retry_on_timeout=True
                    )
                    session_redis.ping()
                    logger.info("Redis SSL connection successful with basic SSL config")
                except Exception as ssl_error:
                    logger.warning(f"Basic SSL config failed: {str(ssl_error)}. Trying alternative SSL config.")
                    try:
                        # Try with specific TLS version and connection pool
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                        
                        pool = redis.ConnectionPool.from_url(
                            redis_url,
                            ssl_context=ssl_context,
                            decode_responses=False,  # Critical: Use False to avoid Unicode issues
                            socket_timeout=10,
                            socket_connect_timeout=10,
                            retry_on_timeout=True
                        )
                        session_redis = redis.Redis(connection_pool=pool)
                        session_redis.ping()
                        logger.info("Redis SSL connection successful with TLS context")
                    except Exception as alt_error:
                        logger.warning(f"TLS context config also failed: {str(alt_error)}. Trying non-SSL approach.")
                        try:
                            # Last resort: try converting rediss:// to redis:// (non-SSL)
                            non_ssl_url = redis_url.replace('rediss://', 'redis://')
                            session_redis = redis.from_url(
                                non_ssl_url,
                                decode_responses=False,  # Critical: Use False to avoid Unicode issues
                                socket_timeout=10,
                                socket_connect_timeout=10,
                                retry_on_timeout=True
                            )
                            session_redis.ping()
                            logger.info("Redis connection successful without SSL")
                        except Exception as final_error:
                            logger.warning(f"All Redis URL connection attempts failed: {str(final_error)}")
                            session_redis = None
            else:
                # For non-SSL connections
                try:
                    session_redis = redis.from_url(
                        redis_url, 
                        decode_responses=False,  # Critical: Use False to avoid Unicode issues
                        socket_timeout=10,
                        socket_connect_timeout=10,
                        retry_on_timeout=True
                    )
                    session_redis.ping()
                    logger.info("Redis connection successful")
                except Exception as e:
                    logger.warning(f"Redis URL connection failed: {str(e)}")
                    session_redis = None
        
        # If Redis URL failed, try individual environment variables
        if not session_redis:
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_db = int(os.environ.get('REDIS_DB', 0))
            redis_password = os.environ.get('REDIS_PASSWORD')
            
            if redis_host != 'localhost' or redis_password:
                # Cloud Redis configuration
                try:
                    # Try SSL connection first
                    try:
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                        
                        session_redis = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            db=redis_db,
                            password=redis_password,
                            ssl=True,
                            ssl_context=ssl_context,
                            socket_timeout=10,
                            socket_connect_timeout=10,
                            retry_on_timeout=True,
                            decode_responses=False  # Critical: Use False to avoid Unicode issues
                        )
                        session_redis.ping()
                        logger.info(f"Connected to Redis Cloud at {redis_host}:{redis_port} with SSL")
                    except Exception as ssl_error:
                        logger.warning(f"SSL connection failed: {str(ssl_error)}. Trying non-SSL.")
                        # Try without SSL
                        session_redis = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            db=redis_db,
                            password=redis_password,
                            ssl=False,
                            socket_timeout=10,
                            socket_connect_timeout=10,
                            retry_on_timeout=True,
                            decode_responses=False  # Critical: Use False to avoid Unicode issues
                        )
                        session_redis.ping()
                        logger.info(f"Connected to Redis at {redis_host}:{redis_port} without SSL")
                except Exception as e:
                    logger.warning(f"Failed to connect to Redis cloud: {str(e)}")
                    session_redis = None
            else:
                # Local Redis configuration
                try:
                    session_redis = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password,
                        socket_timeout=10,
                        socket_connect_timeout=10,
                        retry_on_timeout=True,
                        decode_responses=False  # Critical: Use False to avoid Unicode issues
                    )
                    session_redis.ping()
                    logger.info(f"Connected to local Redis at {redis_host}:{redis_port}/{redis_db}")
                except Exception as e:
                    logger.warning(f"Failed to connect to local Redis: {str(e)}")
                    session_redis = None
        
        # Configure Flask-Session based on Redis availability
        if session_redis:
            app.config['SESSION_TYPE'] = 'redis'
            app.config['SESSION_REDIS'] = session_redis
            app.config['SESSION_PERMANENT'] = False
            app.config['SESSION_USE_SIGNER'] = True
            app.config['SESSION_KEY_PREFIX'] = 'xavier_session:'
            app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
            logger.info("Configured Flask-Session to use Redis")
        else:
            raise Exception("No Redis connection available")
        
    except Exception as e:
        # Fallback to filesystem sessions if Redis is not available
        logger.warning(f"Failed to configure Redis for sessions: {str(e)}. Using filesystem sessions.")
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = './flask_session'
        app.config['SESSION_FILE_THRESHOLD'] = 500
        app.config['SESSION_PERMANENT'] = False
        app.config['SESSION_USE_SIGNER'] = True
    
    # Ensure secure session cookie settings
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENVIRONMENT') != 'development'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Stricter setting for better security
    
    Session(app)

    # Initialize Flask-Compress for response compression
    compress = Compress()
    compress.init_app(app)

    # Use ProxyFix to handle X-Forwarded headers correctly
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.after_request
    def add_response_headers(response):
        # Add CORS headers
        origin = request.headers.get('Origin')
        if origin:
            # Allow the specific origin that made the request
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, user-id, X-Requested-With'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            # Vary the response based on Origin to support multiple origins
            response.headers['Vary'] = 'Origin'
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Add performance headers
        response.headers['Server-Timing'] = f'total;dur={request.environ.get("RESPONSE_TIME", 0)}'

        # Add caching headers based on request type and path
        if request.method == 'GET':
            if any(request.path.startswith(prefix) for prefix in ['/static/', '/assets/']):
                # Static assets can be cached for longer periods
                response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
                response.headers['Expires'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 31536000))
            elif any(request.path.startswith(prefix) for prefix in ['/analytics/', '/chatbots/']):
                # API GET requests that change frequently but can still benefit from caching
                response.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=60'  # 5 minutes + 1 minute stale
            else:
                # Other GET requests get a shorter cache time
                response.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=30'  # 1 minute + 30s stale
                
            # Add ETag support for better caching
            if response.status_code == 200 and hasattr(response, 'get_data'):
                try:
                    if hasattr(response, 'direct_passthrough') and not response.direct_passthrough and response.data:
                        response.add_etag()
                except (RuntimeError, AttributeError):
                    # Skip ETag for responses that don't support it
                    pass
        else:
            # For POST/PUT/DELETE requests, prevent caching
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        return response

    @app.before_request
    def before_request():
        # Store request start time for performance tracking
        request.environ['REQUEST_START_TIME'] = time.time()
        
        # Only log important debugging information for specific paths
        if request.path.startswith('/subscription') or request.path.startswith('/auth'):
            if 'user_id' in session:
                logger.debug(f"User {session['user_id']} accessed {request.method} {request.path}")
        
        # Always allow preflight requests for all routes
        if request.method == 'OPTIONS':
            response = make_response()
            origin = request.headers.get('Origin', '*')
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, user-id, X-Requested-With')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '3600')  # Cache preflight for 1 hour
            return response, 200

    @app.after_request
    def after_request(response):
        # Calculate response time
        request_time = time.time() - request.environ.get('REQUEST_START_TIME', time.time())
        request.environ['RESPONSE_TIME'] = int(request_time * 1000)  # Convert to milliseconds
        
        # Only log non-static, non-health check requests with issues or significant response times
        if (response.status_code >= 400 or request_time > 3) and \
           not request.path.startswith('/static') and \
           request.path != '/health':
            user_id = session.get('user_id') if 'user_id' in session else None
            log_api_request(logger, request.path, response.status_code, user_id, request_time)
            
        return response

    # Initialize Firebase
    try:
        initialize_firebase()
    except Exception as e:
        logger.error(f"Firebase init error: {str(e)}")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(email_bp, url_prefix='/email')
    app.register_blueprint(user_bp, url_prefix='/user')

    # Register subscription blueprint
    from .routes.subscription import subscription_bp
    app.register_blueprint(subscription_bp, url_prefix='/subscription')

    # Register conversation usage blueprint
    app.register_blueprint(conversation_usage_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')

    # Register WhatsApp integration blueprints
    from .routes.whatsapp import whatsapp_bp
    from .routes.whatsapp_config import whatsapp_config_bp
    app.register_blueprint(whatsapp_bp, url_prefix='/whatsapp')
    app.register_blueprint(whatsapp_config_bp, url_prefix='/whatsapp')

    # Create database tables and default user
    with app.app_context():
        try:
            # Import the migration tracker
            from .utils.migration_tracker import is_migration_applied, mark_migration_applied
            
            # Only create tables if not already done
            if not is_migration_applied('create_all_tables'):
                logger.info("Creating database tables")
                db.create_all()
                mark_migration_applied('create_all_tables')
            
            # Check if default user exists
            default_user = db.session.get(User, 4269)
            if not default_user:
                default_user = User(
                    id=4269,
                    username='default_ticket_user',
                    password_hash='default_not_used'
                )
                db.session.add(default_user)
                db.session.commit()
                logger.info("Default user created successfully")
            else:
                logger.info("Default user already exists")

            # Run the PayPal columns migration
            if not is_migration_applied('paypal_columns'):
                try:
                    logger.info("Running PayPal columns migration")
                    from .migrations.add_paypal_columns import run_migration as add_paypal_columns_migration
                    add_paypal_columns_migration()
                    mark_migration_applied('paypal_columns')
                except Exception as e:
                    logger.error(f"Error running PayPal columns migration: {e}")

            # Run the Lemon Squeezy columns migration
            if not is_migration_applied('lemonsqueezy_columns'):
                try:
                    logger.info("Running Lemon Squeezy columns migration")
                    from .migrations.add_lemonsqueezy_columns import run_migration as add_lemonsqueezy_columns_migration
                    add_lemonsqueezy_columns_migration()
                    mark_migration_applied('lemonsqueezy_columns')
                except Exception as e:
                    logger.error(f"Error running Lemon Squeezy columns migration: {e}")
                
            # Run the Flutterwave columns migration
            if not is_migration_applied('flutterwave_columns'):
                try:
                    logger.info("Running Flutterwave columns migration")
                    from .migrations.add_flutterwave_columns import run_migration as add_flutterwave_columns_migration
                    add_flutterwave_columns_migration()
                    mark_migration_applied('flutterwave_columns')
                except Exception as e:
                    logger.error(f"Error running Flutterwave columns migration: {e}")

            # Automatically initialize subscription plans if none exist
            try:
                from .routes.subscription import init_plans
                init_plans()
                logger.info("Subscription plans initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing subscription plans: {e}")
                
            # Initialize and start the scheduler
            try:
                from extensions import init_scheduler
                init_scheduler(app)
                logger.info("Scheduler initialized and started successfully")
            except Exception as e:
                logger.error(f"Error initializing scheduler: {e}")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            db.session.rollback()

    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        })

    @app.route('/subscription-status')
    def subscription_status():
        """Check current user's subscription status."""
        from .services.subscription_service import SubscriptionService
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated", "has_active_subscription": False}), 401
            
        subscription_data = SubscriptionService.get_user_subscription(user_id)
        is_active = subscription_data is not None and subscription_data.get('is_active', False)
        
        return jsonify({
            "has_active_subscription": is_active,
            "subscription": subscription_data
        })

    # Run database migrations if needed
    from migrations import run_migrations

    # Add our custom migration for fixing user-subscription relationships
    from .migrations.fix_user_subscription_relationship import run_migration as fix_subscriptions

    # Run migrations on startup instead of using before_first_request which is deprecated
    def run_startup_tasks():
        """
        Run tasks during application startup.
        This includes running database migrations.
        """
        # Import the migration tracker
        from .utils.migration_tracker import is_migration_applied, mark_migration_applied
        
        # Run database migrations if not already applied
        if not is_migration_applied('alembic_migrations'):
            logger.info("Running alembic database migrations")
            run_migrations()
            mark_migration_applied('alembic_migrations')
        
        # Run specific migration to fix user-subscription relationships if not already applied
        if not is_migration_applied('fix_user_subscription_relationships'):
            try:
                logger.info("Running migration to fix user-subscription relationships")
                fix_subscriptions()
                mark_migration_applied('fix_user_subscription_relationships')
            except Exception as e:
                logger.error(f"Error running subscription relationship fix: {str(e)}")
    
    # Register a function to run after the application is fully set up
    @app.after_request
    def after_setup(response):
        # Run startup tasks once, only on the first request
        if not hasattr(app, '_startup_tasks_complete'):
            with app.app_context():
                run_startup_tasks()
            app._startup_tasks_complete = True
        return response

    return app

# Create the application
app = create_app()

# Run the application if executed directly
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

