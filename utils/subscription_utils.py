"""
Subscription Utilities Module

This module contains utility functions for subscription-related operations.
"""
import logging
import functools
from typing import Callable, Any, Dict, List, Optional

from flask import request, jsonify, session, current_app
from services.subscription_service import SubscriptionService

# Configure logging
logger = logging.getLogger(__name__)

def subscription_required(feature: str = None) -> Callable:
    """
    Decorator to check if a user has access to a specific feature based on their subscription.
    
    Args:
        feature: The feature to check access for. If None, just checks for an active subscription.
        
    Returns:
        Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Get user ID from session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
            
            # Check subscription status
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            if not subscription_data or not subscription_data.get('is_active'):
                return jsonify({
                    "error": "Active subscription required",
                    "subscription_required": True
                }), 403
            
            # If a specific feature is required, check for it
            if feature and not SubscriptionService.check_feature_access(user_id, feature):
                return jsonify({
                    "error": f"Your current plan does not include access to {feature}",
                    "subscription_upgrade_required": True
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_chatbot_limit(f: Callable) -> Callable:
    """
    Decorator to check if a user has reached their chatbot limit (4 chatbots max).
    """
    @functools.wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        has_reached_limit, current_count, max_allowed = SubscriptionService.check_chatbot_limit(user_id)
        if has_reached_limit:
            return jsonify({
                "error": f"You have reached your chatbot limit ({current_count}/{max_allowed})",
                "subscription_upgrade_required": True,
                "current_count": current_count,
                "max_allowed": max_allowed
            }), 403

        return f(*args, **kwargs)
    return decorated_function

def get_subscription_features(plan_name: str) -> List[str]:
    """
    Get the features included in a subscription plan.
    
    Args:
        plan_name: The name of the plan
        
    Returns:
        List of features
    """
    # Define features for each plan
    plan_features = {
        'Free': [
            'Create 1 chatbot',
            'Basic analytics',
            'Standard support'
        ],
        'Basic': [
            'Create up to 3 chatbots',
            'Advanced analytics',
            'Priority support',
            'Custom branding',
            'Lead generation'
        ],
        'Premium': [
            'Create unlimited chatbots',
            'Premium analytics',
            'Priority support',
            'Custom branding',
            'Lead generation',
            'API access',
            'Team collaboration'
        ]
    }
    
    return plan_features.get(plan_name, [])
