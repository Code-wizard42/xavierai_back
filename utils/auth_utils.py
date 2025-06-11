from flask import session, jsonify, request, current_app
from functools import wraps
import logging
import base64
import json
from utils.log_utils import log_operation

def login_required(f):
    """
    Decorator to check if user is logged in.
    Works with both traditional session-based auth and Firebase auth.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        
        if not user_id:
            # Try to get user_id from Firebase token if available
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    from firebase_config import verify_firebase_token
                    from models import User
                    
                    user_info = verify_firebase_token(token)
                    if user_info.get('verified'):
                        firebase_uid = user_info.get('uid')
                        user = User.query.filter_by(firebase_uid=firebase_uid).first()
                        if user:
                            session.permanent = True
                            session['user_id'] = user.id
                            session.modified = True
                            log_operation(current_app.logger, "auth_token", "success", 
                                         {"user_id": user.id, "path": request.path})
                            return f(*args, **kwargs)
                        else:
                            log_operation(current_app.logger, "auth_token", "failed", 
                                         {"error": f"No user found for firebase_uid: {firebase_uid}", "path": request.path})
                    else:
                        error_msg = user_info.get('error', 'Token verification failed')
                        log_operation(current_app.logger, "auth_token", "failed", 
                                     {"error": f"Token verification failed: {error_msg}", "path": request.path})
                except Exception as e:
                    log_operation(current_app.logger, "auth_token", "failed", 
                                 {"error": str(e), "path": request.path})
            
            log_operation(current_app.logger, "auth_check", "failed", {"path": request.path})
            return jsonify({"error": "Unauthorized - session expired or invalid"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to check if user is an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if user is logged in
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401

        # Then check if user is an admin
        # This would require adding an 'is_admin' field to the User model
        # For now, we'll just return unauthorized
        return jsonify({"error": "Admin access required"}), 403

        # Uncomment when admin field is added to User model
        # from models import User
        # user = User.query.get(session['user_id'])
        # if not user or not user.is_admin:
        #     return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)
    return decorated_function
