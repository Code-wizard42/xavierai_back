"""
Auth Routes Module

This module contains route handlers for authentication-related operations.
It uses the service layer for business logic.
"""
from flask import Blueprint, request, jsonify, session, make_response
import logging
from functools import wraps
from flask_cors import cross_origin
from flask import current_app
from werkzeug.security import check_password_hash

from xavier_back.models import User
from xavier_back.extensions import db
from xavier_back.services.auth_service import AuthService
from xavier_back.services.subscription_service import SubscriptionService
from xavier_back.utils.log_utils import log_operation

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)

def handle_errors(f):
    """Decorator to handle errors in route handlers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"error": "An unexpected error occurred"}), 500
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
@handle_errors
def register():
    """Register a new user"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Use the service to register the user
    user, error = AuthService.register_user(username, password, email)

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user and return a JWT token."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        # Use the service to login the user
        user, error = AuthService.login_user(username, password)

        if error:
            return jsonify({"error": error}), 401

        # Set session with permanent flag
        session.permanent = True
        session['user_id'] = user.id
        session.modified = True

        # Get subscription data safely
        try:
            subscription_data = SubscriptionService.get_user_subscription(user.id)
            has_active_subscription = subscription_data is not None and subscription_data.get('is_active', False)
            
            # Get plan information if a subscription exists
            plan_info = None
            if subscription_data and 'plan' in subscription_data:
                plan_info = {
                    'name': subscription_data['plan'].get('name'),
                    'id': subscription_data['plan'].get('id')
                }
        except Exception as e:
            logger.error(f"Error getting subscription data: {str(e)}")
            # Provide default values if subscription check fails
            subscription_data = None
            has_active_subscription = False
            plan_info = None

        # Create a response with proper headers
        response = jsonify({
            "message": "Logged in successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "profile_picture": user.profile_picture
            },
            "subscription": {
                "has_active_subscription": has_active_subscription,
                "status": subscription_data.get('status') if subscription_data else None,
                "plan": plan_info
            }
        })

        return response, 200
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "An error occurred during login. Please try again."}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout a user"""
    if 'user_id' in session:
        session.pop('user_id', None)
        session.clear()

    # Create a response with proper headers
    response = jsonify({"message": "Logged out successfully"})

    return response, 200

@auth_bp.route('/verify-firebase-token', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True, 
              allow_headers=['Content-Type', 'Authorization', 'user-id', 'X-Requested-With'],
              origins=["http://localhost:4200", "https://localhost:4200", "http://localhost:3000", 
                       "http://localhost:5173", "http://localhost:8080", "*"])
@handle_errors
def verify_token():
    """Verify a Firebase token and login or register the user"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, user-id, X-Requested-With')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
         
    data = request.json
    id_token = data.get('idToken')

    if not id_token:
        return jsonify({"error": "No token provided"}), 400

    # Use the service to verify the token
    user, user_info, error = AuthService.verify_firebase_auth(id_token)

    if error:
        return jsonify({"error": error}), 401

    # Check if the user has an active subscription
    subscription_data = SubscriptionService.get_user_subscription(user.id)
    has_active_subscription = subscription_data is not None and subscription_data.get('is_active', False)
    
    # Get plan information if a subscription exists
    plan_info = None
    if subscription_data and 'plan' in subscription_data:
        plan_info = {
            'name': subscription_data['plan'].get('name'),
            'id': subscription_data['plan'].get('id')
        }

    # Clear any existing session
    session.clear()

    # Set new session data
    session.permanent = True
    session['user_id'] = user.id
    session['_fresh'] = True  # Mark session as fresh
    session.modified = True

    # Log minimal authentication info
    log_operation(logger, "firebase_login", "success", {"user_id": user.id})

    # Create a response with proper headers
    response = jsonify({
        "message": "Authentication successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "profile_picture": user.profile_picture
        },
        "subscription": {
            "has_active_subscription": has_active_subscription,
            "status": subscription_data.get('status') if subscription_data else None,
            "plan": plan_info
        }
    })
    
    # Explicitly add CORS headers to ensure they're included
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')

    return response, 200

@auth_bp.route('/current-user', methods=['GET'])
@handle_errors
def get_current_user():
    """Get the current logged in user"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    # Use the service to get the user
    user = AuthService.get_user(session['user_id'])

    if not user:
        session.pop('user_id', None)
        return jsonify({"error": "User not found"}), 404

    # Get subscription data
    subscription_data = SubscriptionService.get_user_subscription(user.id)
    has_active_subscription = subscription_data is not None and subscription_data.get('is_active', False)
    
    # Get plan information if a subscription exists
    plan_info = None
    if subscription_data and 'plan' in subscription_data:
        plan_info = {
            'name': subscription_data['plan'].get('name'),
            'id': subscription_data['plan'].get('id')
        }

    return jsonify({
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "profile_picture": user.profile_picture,
            "auth_provider": user.auth_provider
        },
        "subscription": {
            "has_active_subscription": has_active_subscription,
            "status": subscription_data.get('status') if subscription_data else None,
            "plan": plan_info
        }
    }), 200

@auth_bp.route('/update-profile', methods=['PUT'])
@handle_errors
def update_profile():
    """Update the current user's profile"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json

    # Use the service to update the user's profile
    user, error = AuthService.update_user_profile(session['user_id'], data)

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Profile updated successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "profile_picture": user.profile_picture,
            "auth_provider": user.auth_provider
        }
    }), 200

@auth_bp.route('/change-password', methods=['PUT'])
@handle_errors
def change_password():
    """Change the current user's password"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    # Use the service to change the password
    success, error = AuthService.change_password(session['user_id'], current_password, new_password)

    if not success:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Password changed successfully"}), 200
