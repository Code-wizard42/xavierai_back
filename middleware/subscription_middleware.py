"""
Subscription Middleware Module

This module provides middleware for verifying subscription status on protected routes.
"""
from functools import wraps
from flask import request, jsonify, session, current_app
from services.subscription_service import SubscriptionService

def subscription_required(feature=None):
    """
    Middleware to check if a user has a valid subscription.
    Optionally checks for access to a specific feature.
    
    Args:
        feature: Optional feature to check access for
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user ID from session
            user_id = session.get('user_id')
            if not user_id:
                current_app.logger.warning("Unauthorized access attempt to subscription-protected route")
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            
            # Get the user's subscription
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            
            # Check if user has an active subscription
            if not subscription_data or not subscription_data.get('is_active'):
                current_app.logger.warning(f"User {user_id} attempted to access protected route without active subscription")
                return jsonify({
                    "error": "This feature requires an active subscription",
                    "redirect": "/subscription",
                    "subscription_required": True
                }), 403
            
            # If a specific feature is required, check for it
            if feature and not SubscriptionService.check_feature_access(user_id, feature):
                current_app.logger.warning(f"User {user_id} attempted to access feature {feature} without access")
                return jsonify({
                    "error": f"Your current plan doesn't include access to {feature}",
                    "redirect": "/subscription",
                    "subscription_upgrade_required": True
                }), 403
            
            # If all checks pass, proceed with the request
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator 