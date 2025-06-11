# import os
# from dotenv import load_dotenv
# from datetime import timedelta

# # Load environment variables from .env file
# load_dotenv()

# # Determine if we're in development or production
# ENVIRONMENT = os.getenv('FLASK_ENV', 'development')
# IS_DEVELOPMENT = ENVIRONMENT == 'development'

# class Config:
#     # Database configuration
#     SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///crm.db')  # Use SQLite for local dev
#     # Fix PostgreSQL URI if needed (for Heroku compatibility)
#     if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
#         SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
#     SQLALCHEMY_TRACK_MODIFICATIONS = False

#     # Connection pooling settings
#     SQLALCHEMY_ENGINE_OPTIONS = {
#         'pool_size': 10,  # Maximum number of connections
#         'pool_recycle': 3600,  # Recycle connections after 1 hour
#         'pool_pre_ping': True  # Check connection validity before using it
#     }

#     # Session configuration
#     SESSION_TYPE = 'filesystem'
#     SESSION_FILE_DIR = './flask_session'  # Ensure this directory exists
#     SESSION_FILE_THRESHOLD = 500
#     SESSION_FILE_MODE = 384  # 0o600 in decimal
#     SESSION_PERMANENT = True
#     PERMANENT_SESSION_LIFETIME = timedelta(days=1)  # 24 hours
#     SESSION_COOKIE_NAME = 'session'
#     SESSION_COOKIE_SECURE = False  # For development, set to True in production
#     SESSION_COOKIE_HTTPONLY = True
#     SESSION_COOKIE_SAMESITE = 'None'  # This allows cross-site requests
#     SESSION_COOKIE_PATH = '/'
#     SESSION_COOKIE_DOMAIN = None  # Will use the current domain
#     SESSION_USE_SIGNER = True
#     SESSION_REFRESH_EACH_REQUEST = True
#     SESSION_KEY_PREFIX = 'xavier_'

#     # Application secret key
#     SECRET_KEY = os.getenv('SECRET_KEY', 'a8e7d4f2c1b9e6a3d8c5b2e9f7a4d1c8e5b2a9f7d4e1c8b5a2f7e4d1c8b5a3f6')

#     # Firebase configuration
#     FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS', 'firebase-credentials.json')

#     # Upload configuration
#     UPLOAD_FOLDER = 'uploads'
#     MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size

#     # Development-specific settings
#     if IS_DEVELOPMENT:
#         # For development, set more permissive cookie settings
#         SESSION_COOKIE_SECURE = False  # Using HTTP in development
#         SESSION_COOKIE_SAMESITE = 'None'  # Allow cross-site cookies in dev
#     else:
#         # For production, ensure more secure settings
#         SESSION_COOKIE_SECURE = True  # Require HTTPS
#         SESSION_COOKIE_SAMESITE = 'Lax'  # More restrictive in production

#     # Google OAuth settings
#     GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
#     GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
#     GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth2callback')



import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///crm.db')  # Use SQLite for local dev
    # Fix PostgreSQL URI if needed (for Heroku compatibility)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'spacex42695')
    SESSION_TYPE = 'filesystem'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_HTTPONLY = True

    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload size for optimal performance

    # Google OAuth settings
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth2callback')

    # PayPal settings
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_API_BASE = os.getenv('PAYPAL_API_BASE', '')  # Use sandbox by default
    PAYPAL_APP_NAME = os.getenv('PAYPAL_APP_NAME', '')

    # Paystack settings
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY','')
    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY','')
    PAYSTACK_API_BASE = os.getenv('PAYSTACK_API_BASE', '')
    
    # Subscription settings
    RENEWAL_REMINDER_DAYS = [7, 3, 1]  # Send reminders 7, 3, and 1 day before renewal