"""
Chatbot Access Middleware Module

This module provides middleware for verifying subscription status before allowing chatbot interactions.
It specifically checks if the user's subscription is active and billing is up to date.
"""
from functools import wraps
from flask import request, jsonify, session, current_app
from services.subscription_service import SubscriptionService
from services.conversation_limit_service import ConversationLimitService


def chatbot_subscription_required(f):
    """
    Middleware to check if a user has a valid subscription specifically for chatbot interactions.
    This decorator checks:
    1. User authentication
    2. Chatbot ownership 
    3. Active subscription
    4. Billing date not passed
    
    Returns:
        Decorated function that blocks access if subscription is expired or billing is overdue
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract chatbot_id from route parameters
        chatbot_id = kwargs.get('chatbot_id')
        if not chatbot_id:
            current_app.logger.error("Chatbot ID not found in route parameters")
            return jsonify({"error": "Invalid chatbot request"}), 400

        # Check if chatbot exists and get owner information
        # Use direct query to avoid cached detached instances
        from models import Chatbot
        chatbot = Chatbot.query.get(chatbot_id)
        if not chatbot:
            current_app.logger.warning(f"Chatbot not found: {chatbot_id}")
            return jsonify({"error": "Chatbot not found"}), 404

        # Get chatbot owner's user ID
        user_id = chatbot.user_id
        if not user_id:
            current_app.logger.error(f"Chatbot {chatbot_id} has no associated user")
            return jsonify({"error": "Chatbot configuration error"}), 500

        # Get the user's subscription
        subscription_data = SubscriptionService.get_user_subscription(user_id)
        
        # Check if user has an active subscription
        if not subscription_data or not subscription_data.get('is_active'):
            current_app.logger.warning(f"User {user_id} attempted to use chatbot {chatbot_id} without active subscription")
            return jsonify({
                "error": "This chatbot's subscription has expired. Please renew your subscription to continue using this service.",
                "subscription_required": True,
                "chatbot_disabled": True
            }), 402  # Payment Required status code
        
        # Check if subscription billing is overdue
        from models import User
        user = User.query.get(user_id)
        if user and user.subscription and user.subscription.is_billing_overdue():
            current_app.logger.warning(f"User {user_id} chatbot {chatbot_id} blocked due to overdue billing")
            return jsonify({
                "error": "This chatbot's subscription payment is overdue. Please update your payment to continue using this service.",
                "billing_overdue": True,
                "chatbot_disabled": True,
                "next_billing_date": user.subscription.next_billing_date.isoformat() if user.subscription.next_billing_date else None
            }), 402  # Payment Required status code
        
        # If all checks pass, proceed with the request
        return f(*args, **kwargs)
    
    return decorated_function


def public_chatbot_subscription_required(f):
    """
    Middleware for public chatbot endpoints (like the ask endpoint) that don't require user login
    but still need to check the chatbot owner's subscription status.
    
    Returns:
        Decorated function that blocks chatbot usage if owner's subscription is expired
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract chatbot_id from route parameters
        chatbot_id = kwargs.get('chatbot_id')
        if not chatbot_id:
            current_app.logger.error("Chatbot ID not found in route parameters")
            return jsonify({"error": "Invalid chatbot request"}), 400

        # Check if chatbot exists and get owner information
        # Use direct query to avoid cached detached instances
        from models import Chatbot
        chatbot = Chatbot.query.get(chatbot_id)
        if not chatbot:
            current_app.logger.warning(f"Chatbot not found: {chatbot_id}")
            return jsonify({"error": "Chatbot not found"}), 404

        # Get chatbot owner's user ID
        user_id = chatbot.user_id
        if not user_id:
            current_app.logger.error(f"Chatbot {chatbot_id} has no associated user")
            return jsonify({"error": "Chatbot configuration error"}), 500

        # Get the user's subscription
        subscription_data = SubscriptionService.get_user_subscription(user_id)
        
        # Check if user has an active subscription
        if not subscription_data or not subscription_data.get('is_active'):
            current_app.logger.warning(f"Public access to chatbot {chatbot_id} blocked - owner subscription expired")
            return jsonify({
                "error": "This chatbot is currently unavailable. The subscription has expired.",
                "chatbot_unavailable": True
            }), 503  # Service Unavailable status code
        
        # Check if subscription billing is overdue
        from models import User
        user = User.query.get(user_id)
        if user and user.subscription and user.subscription.is_billing_overdue():
            current_app.logger.warning(f"Public access to chatbot {chatbot_id} blocked - owner billing overdue")
            return jsonify({
                "error": "This chatbot is temporarily unavailable due to billing issues.",
                "chatbot_unavailable": True
            }), 503  # Service Unavailable status code
        
        # Check conversation limits
        can_proceed, limit_info = ConversationLimitService.check_conversation_limit(chatbot_id)
        if not can_proceed:
            current_app.logger.warning(f"Public access to chatbot {chatbot_id} blocked - conversation limit exceeded")
            error_message = "This chatbot has reached its monthly conversation limit."
            if limit_info.get('conversation_limit'):
                error_message += f" Limit: {limit_info['conversation_limit']} conversations per month."
            
            return jsonify({
                "error": error_message,
                "conversation_limit_exceeded": True,
                "usage_info": {
                    "current_usage": limit_info.get('current_usage', 0),
                    "conversation_limit": limit_info.get('conversation_limit', 0),
                    "plan_name": limit_info.get('plan_name', 'Unknown')
                }
            }), 429  # Too Many Requests status code
        
        # If all checks pass, proceed with the request
        return f(*args, **kwargs)
    
    return decorated_function 