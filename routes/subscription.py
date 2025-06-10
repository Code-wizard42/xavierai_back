"""
Subscription Routes Module

This module contains API routes for subscription management.
"""
import logging
import os
import json
from functools import wraps
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import User, Subscription, Plan, PaymentHistory
from xavier_back.services.subscription_service import SubscriptionService
from xavier_back.utils.auth_utils import login_required

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
subscription_bp = Blueprint('subscription', __name__)

# Helper function to get user ID from session
def get_user_id_from_session() -> Optional[int]:
    """Get user ID from session"""
    return session.get('user_id')

@subscription_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get all available subscription plans"""
    plans = SubscriptionService.get_available_plans()
    return jsonify(plans), 200

@subscription_bp.route('/config', methods=['GET'])
def get_config():
    """Get payment configuration"""
    import os

    # Get the payment configuration from environment variables
    paypal_client_id = os.environ.get('PAYPAL_CLIENT_ID')

    # Determine if PayPal is available
    payment_methods = []
    if paypal_client_id:
        payment_methods.append('paypal')

    # If no payment methods are available, default to simulated payments
    if not payment_methods:
        payment_methods.append('simulated')

    return jsonify({
        'paypalClientId': paypal_client_id,
        'availablePaymentMethods': payment_methods,
        'enableGuestCheckout': True  # Enable guest checkout by default
    }), 200

@subscription_bp.route('/create-paypal-order', methods=['POST'])
def create_paypal_order():
    """Create a PayPal order for checkout"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        plan_id = data.get('plan_id')
        if not plan_id:
            return jsonify({"error": "Plan ID is required"}), 400

        billing_cycle = data.get('billing_cycle', 'monthly')
        if billing_cycle not in ['monthly', 'annual']:
            return jsonify({"error": "Invalid billing cycle"}), 400

        # Get the enable_guest_checkout flag (default to True)
        enable_guest_checkout = data.get('enable_guest_checkout', True)
        
        # Get the force_guest_checkout flag (default to False)
        force_guest_checkout = data.get('force_guest_checkout', False)
        
        # If force_guest_checkout is True, ensure enable_guest_checkout is also True
        if force_guest_checkout:
            enable_guest_checkout = True

        # Get the return URL from the request or fallback to defaults
        # This allows the frontend to specify the return URL explicitly, including localhost URLs
        origin = request.headers.get('Origin')
        
        # Determine if we're in development mode
        is_development = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('ENVIRONMENT') == 'development'
        
        # Use the origin if provided, otherwise fall back to default URLs
        base_url = None
        if origin:
            base_url = origin
        elif is_development:
            base_url = "http://localhost:4200"
        else:
            base_url = "https://xavierai.site"
        
        # Set return URLs
        return_url = f"{base_url}/subscription?success=true"
        cancel_url = f"{base_url}/subscription?cancel=true"

        # Check if the plan exists
        plan = Plan.query.get(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404

        # Get the price based on the billing cycle
        price = plan.annual_price if billing_cycle == 'annual' else plan.price

        # Create a PayPal order
        from xavier_back.services.paypal_service import PayPalService

        success, order_data, error = PayPalService.create_order(
            plan_id=plan_id,
            plan_name=plan.name,
            price=price,
            billing_cycle=billing_cycle,
            enable_guest_checkout=enable_guest_checkout,
            force_guest_checkout=force_guest_checkout,
            return_url=return_url,
            cancel_url=cancel_url
        )

        if not success:
            return jsonify({"error": error}), 400

        return jsonify(order_data), 201
    except Exception as e:
        logger.error(f"Error creating PayPal order: {str(e)}")
        return jsonify({"error": str(e)}), 500

@subscription_bp.route('/init-plans', methods=['GET'])
def init_plans():
    """Initialize subscription plans"""
    try:
        # Check if plans already exist
        existing_plans = Plan.query.all()
        if existing_plans:
            return jsonify({
                'message': f'Found {len(existing_plans)} existing plans',
                'plans': [
                    {
                        'id': plan.id,
                        'name': plan.name,
                        'price': plan.price,
                        'annual_price': plan.annual_price
                    }
                    for plan in existing_plans
                ]
            }), 200

        # Create a single plan with all features for $10
        plans = [
            {
                'name': 'Premium',
                'description': 'All features included',
                'price': 10.0,
                'annual_price': 100.0,
                'features': [
                    'Unlimited chatbots',
                    'Unlimited conversations',
                    'Advanced lead generation',
                    'Premium analytics',
                    'Priority support',
                    'Custom branding',
                    'API access',
                    'Team collaboration',
                    'Custom integrations',
                    'Advanced analytics & reporting'
                ],
                'max_chatbots': 999999  # Effectively unlimited
            }
        ]

        # Add the plans to the database
        created_plans = []
        for plan_data in plans:
            # Ensure we're using timezone-aware datetime
            now = datetime.now(timezone.utc)
            plan = Plan(
                name=plan_data['name'],
                description=plan_data['description'],
                price=plan_data['price'],
                annual_price=plan_data['annual_price'],
                features=plan_data['features'],
                max_chatbots=plan_data['max_chatbots'],
                is_active=True,
                created_at=now,
                updated_at=now
            )
            db.session.add(plan)
            created_plans.append(plan_data)

        # Commit the changes
        db.session.commit()

        return jsonify({
            'message': 'Plans created successfully!',
            'plans': created_plans
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing plans: {str(e)}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/subscription', methods=['GET'])
@login_required
def get_subscription():
    """Get the current user's subscription"""
    user_id = get_user_id_from_session()
    subscription = SubscriptionService.get_user_subscription(user_id)

    if not subscription:
        return jsonify({"error": "No subscription found"}), 404

    return jsonify(subscription), 200

@subscription_bp.route('/capture-paypal-order', methods=['POST'])
def capture_paypal_order():
    """Capture a PayPal order after approval"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        order_id = data.get('order_id')
        if not order_id:
            return jsonify({"error": "Order ID is required"}), 400

        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required. Please log in and try again."}), 401
        
        logger.info(f"Capturing PayPal order {order_id} for user {user_id}")

        # Capture the PayPal order
        from xavier_back.services.paypal_service import PayPalService

        success, capture_data, error = PayPalService.capture_order(order_id)

        if not success:
            logger.error(f"Failed to capture PayPal order: {error}")
            return jsonify({"error": error}), 400

        # Extract plan_id and billing_cycle from the capture data
        plan_id = capture_data.get('plan_id')
        billing_cycle = capture_data.get('billing_cycle', 'monthly')

        if not plan_id:
            logger.error("Plan ID not found in order data")
            return jsonify({"error": "Plan ID not found in order data"}), 400

        # Create a subscription using the PayPal order ID
        success, subscription_data, error = PayPalService.create_subscription_with_paypal(
            user_id, plan_id, order_id, billing_cycle
        )

        if not success:
            logger.error(f"Failed to create subscription: {error}")
            return jsonify({"error": error}), 400

        # Get the updated subscription data
        subscription = SubscriptionService.get_user_subscription(user_id)
        
        if not subscription:
            logger.error("Failed to retrieve subscription details after creation")
            return jsonify({"error": "Failed to retrieve subscription details after creation"}), 500

        # Ensure subscription is active (not in trial)
        if subscription.get('status') == 'trialing':
            # Update subscription to active since payment was made
            try:
                user = User.query.get(user_id)
                if user and user.subscription:
                    user.subscription.status = 'active'
                    db.session.commit()
                    logger.info(f"Updated subscription status to active for user {user_id}")
                    
                    # Refresh subscription data
                    subscription = SubscriptionService.get_user_subscription(user_id)
            except Exception as e:
                logger.error(f"Error updating subscription status: {e}")
        
        # Add PayPal-specific data
        subscription['payment_method'] = 'paypal'
        subscription['paypal_order_id'] = order_id
        subscription['is_active'] = True
        
        logger.info(f"Subscription created/updated successfully for user {user_id} with PayPal order {order_id}")
        
        # Return the complete subscription object
        return jsonify(subscription), 200

    except Exception as e:
        logger.error(f"Error capturing PayPal order: {str(e)}")
        return jsonify({"error": str(e)}), 500

def create_subscription():
    """Create or update a subscription for the current user"""
    try:
        # Get user ID from session or use a test user ID
        user_id = session.get('user_id')
        if not user_id:
            # For testing purposes, use a fixed user ID
            # In production, this would come from the session
            user_id = 1  # Use a test user ID
            logger.info(f"Using test user ID: {user_id}")

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Log the request data for debugging
        logger.info(f"Subscription creation request: {data}")

        plan_id = data.get('plan_id')
        if not plan_id:
            return jsonify({"error": "Plan ID is required"}), 400

        billing_cycle = data.get('billing_cycle', 'monthly')
        if billing_cycle not in ['monthly', 'annual']:
            return jsonify({"error": "Invalid billing cycle"}), 400

        payment_method = data.get('payment_method', 'paypal')
        paypal_subscription_id = data.get('paypal_subscription_id')
        paypal_order_id = data.get('paypal_order_id')  # New field for order-based payments

        # Check if the plan exists
        plan = Plan.query.get(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404

        # For paid plans with PayPal, we need either a subscription ID or an order ID
        if payment_method == 'paypal' and not (paypal_subscription_id or paypal_order_id):
            return jsonify({"error": "PayPal subscription ID or order ID is required for PayPal payments"}), 400

        # Check if this is a simulated payment method (for testing)
        is_simulated = (paypal_subscription_id and '_simulated' in paypal_subscription_id) or \
                       (paypal_order_id and '_simulated' in paypal_order_id)

        if is_simulated:
            # For simulated payments, create a subscription directly
            logger.info(f"Creating simulated subscription for user {user_id} with plan {plan_id}")
            success, subscription, error = SubscriptionService.create_subscription(
                user_id, plan_id, billing_cycle
            )

            if not success:
                return jsonify({"error": error}), 400

            # Add simulated data for frontend
            import random
            subscription_data = {
                'simulated': True
            }

            # Get the updated subscription data
            subscription_info = SubscriptionService.get_user_subscription(user_id)

            # Add the simulated flag to the response
            if subscription_info:
                subscription_info['simulated'] = True
                return jsonify(subscription_info), 201
            else:
                return jsonify({"error": "Failed to create subscription"}), 500
        else:
            # Use the PayPal service to create a subscription
            from xavier_back.services.paypal_service import PayPalService

            # If we have an order ID, use that instead of a subscription ID
            if paypal_order_id:
                paypal_subscription_id = f"ORDER-{paypal_order_id}"

            success, subscription_data, error = PayPalService.create_subscription(
                user_id, plan_id, paypal_subscription_id, billing_cycle
            )

            if not success:
                return jsonify({"error": error}), 400

            # Get the updated subscription data
            subscription = SubscriptionService.get_user_subscription(user_id)

            if subscription:
                # Add PayPal-specific data if available
                if subscription_data and 'paypal_subscription_id' in subscription_data:
                    subscription['paypal_subscription_id'] = subscription_data['paypal_subscription_id']
                return jsonify(subscription), 201
            else:
                return jsonify({"error": "Failed to create subscription"}), 500
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        return jsonify({"error": str(e)}), 500

subscription_bp.add_url_rule(
    '/subscription', methods=['POST'], view_func=create_subscription
)

@subscription_bp.route('/subscription/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel the current user's subscription"""
    user_id = get_user_id_from_session()
    data = request.json

    at_period_end = data.get('at_period_end', True)

    # Get the user's subscription
    subscription_data = SubscriptionService.get_user_subscription(user_id)
    if not subscription_data:
        return jsonify({"error": "No active subscription found"}), 404

    # Get the payment method from the subscription data
    payment_method = subscription_data.get('payment_method', 'stripe')

    # Check if this is a paid plan with a subscription
    if subscription_data.get('plan', {}).get('price', 0) > 0:
        if payment_method == 'paypal' and subscription_data.get('paypal_subscription_id'):
            # Use the PayPal service to cancel the subscription
            from xavier_back.services.paypal_service import PayPalService
            success, error = PayPalService.cancel_subscription(subscription_data.get('paypal_subscription_id'))

            # If successful, update the subscription status in the database
            if success:
                # Update the subscription status in the database
                subscription = Subscription.query.filter_by(id=subscription_data.get('id')).first()
                if subscription:
                    if at_period_end:
                        subscription.cancel_at_period_end = True
                    else:
                        subscription.status = 'canceled'
                    db.session.commit()
                    logger.info(f"Updated PayPal subscription {subscription_data.get('paypal_subscription_id')} status")
        else:
            # Use the regular service for free plans or plans without payment integration
            success, error = SubscriptionService.cancel_subscription(user_id, at_period_end)
    else:
        # Use the regular service for free plans
        success, error = SubscriptionService.cancel_subscription(user_id, at_period_end)

    if not success:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Subscription canceled successfully"}), 200

@subscription_bp.route('/subscription/check-feature', methods=['GET'])
@login_required
def check_feature_access():
    """Check if the current user has access to a specific feature"""
    user_id = get_user_id_from_session()
    feature = request.args.get('feature')

    if not feature:
        return jsonify({"error": "Feature parameter is required"}), 400

    has_access = SubscriptionService.check_feature_access(user_id, feature)

    return jsonify({"has_access": has_access}), 200

@subscription_bp.route('/subscription/check-chatbot-limit', methods=['GET'])
@login_required
def check_chatbot_limit():
    """Check if the current user has reached their chatbot limit"""
    user_id = get_user_id_from_session()

    has_reached_limit, current_count, max_allowed = SubscriptionService.check_chatbot_limit(user_id)

    return jsonify({
        "has_reached_limit": has_reached_limit,
        "current_count": current_count,
        "max_allowed": max_allowed
    }), 200

# Payment webhook endpoint
@subscription_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    """Handle payment webhook events"""
    # Redirect to PayPal webhook handler
    return paypal_webhook()

# PayPal webhook endpoint for handling subscription events
@subscription_bp.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    """Handle PayPal webhook events"""
    import os
    import hmac
    import hashlib
    import base64

    # Get the webhook ID and secret from environment variables
    webhook_id = os.environ.get('PAYPAL_WEBHOOK_ID')
    webhook_secret = os.environ.get('PAYPAL_WEBHOOK_SECRET')

    if not webhook_id or not webhook_secret:
        logger.warning("PAYPAL_WEBHOOK_ID or PAYPAL_WEBHOOK_SECRET not set. Webhook verification disabled.")

    payload = request.data
    paypal_transmission_id = request.headers.get('PAYPAL-TRANSMISSION-ID')
    paypal_transmission_time = request.headers.get('PAYPAL-TRANSMISSION-TIME')
    paypal_transmission_sig = request.headers.get('PAYPAL-TRANSMISSION-SIG')
    paypal_cert_url = request.headers.get('PAYPAL-CERT-URL')
    paypal_auth_algo = request.headers.get('PAYPAL-AUTH-ALGO')

    try:
        # Parse the payload
        event = json.loads(payload)

        # Verify the webhook signature (in production, you should implement this)
        # For now, we'll skip verification for simplicity

        # Handle the event based on its type
        event_type = event.get('event_type')
        logger.info(f"Received PayPal webhook event: {event_type}")

        # Get the resource data
        resource = event.get('resource', {})

        if event_type == 'BILLING.SUBSCRIPTION.CREATED':
            # Subscription was created
            subscription_id = resource.get('id')
            status = resource.get('status')

            # Find the subscription with this PayPal subscription ID
            subscription = Subscription.query.filter_by(paypal_subscription_id=subscription_id).first()
            if subscription:
                subscription.status = 'active' if status == 'ACTIVE' else 'trialing'
                db.session.commit()
                logger.info(f"Updated PayPal subscription {subscription_id} status to {subscription.status}")

        elif event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
            # Subscription was activated
            subscription_id = resource.get('id')

            # Find the subscription with this PayPal subscription ID
            subscription = Subscription.query.filter_by(paypal_subscription_id=subscription_id).first()
            if subscription:
                subscription.status = 'active'
                db.session.commit()
                logger.info(f"Activated PayPal subscription {subscription_id}")

        elif event_type == 'PAYMENT.SALE.COMPLETED' or event_type == 'CHECKOUT.ORDER.COMPLETED':
            # Payment was completed - handle both subscription payments and order payments
            subscription_id = resource.get('billing_agreement_id')
            transaction_id = resource.get('id')
            order_id = resource.get('id')  # For checkout orders
            amount = resource.get('amount', {}).get('total') or resource.get('purchase_units', [{}])[0].get('amount', {}).get('value')
            currency = resource.get('amount', {}).get('currency') or resource.get('purchase_units', [{}])[0].get('amount', {}).get('currency_code', 'USD')

            # Try to find subscription by PayPal subscription ID first
            subscription = None
            if subscription_id:
                subscription = Subscription.query.filter_by(paypal_subscription_id=subscription_id).first()
            
            # If not found, try to find by order ID
            if not subscription and order_id:
                subscription = Subscription.query.filter_by(paypal_order_id=order_id).first()
            
            # If subscription found, update it
            if subscription:
                # Ensure subscription is active
                subscription.status = 'active'
                
                # Create payment history record
                payment = PaymentHistory(
                    subscription_id=subscription.id,
                    amount=float(amount) if amount else 0,
                    currency=currency or 'USD',
                    status='succeeded',
                    payment_method='paypal'
                )
                db.session.add(payment)
                db.session.commit()
                logger.info(f"Recorded PayPal payment for subscription {subscription_id or order_id}")
            else:
                logger.warning(f"Could not find subscription for PayPal payment {subscription_id or order_id}")

        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            # Subscription was cancelled
            subscription_id = resource.get('id')

            # Find the subscription with this PayPal subscription ID
            subscription = Subscription.query.filter_by(paypal_subscription_id=subscription_id).first()
            if subscription:
                subscription.status = 'canceled'
                db.session.commit()
                logger.info(f"Cancelled PayPal subscription {subscription_id}")

        elif event_type == 'BILLING.SUBSCRIPTION.SUSPENDED':
            # Subscription was suspended (payment failed)
            subscription_id = resource.get('id')

            # Find the subscription with this PayPal subscription ID
            subscription = Subscription.query.filter_by(paypal_subscription_id=subscription_id).first()
            if subscription:
                subscription.status = 'past_due'
                db.session.commit()
                logger.info(f"Suspended PayPal subscription {subscription_id}")

        return jsonify({"status": "success"}), 200
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in PayPal webhook: {str(e)}")
        return jsonify({"error": "Invalid payload"}), 400
    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        return jsonify({"error": str(e)}), 400

@subscription_bp.route('/subscription/process-lemonsqueezy', methods=['POST'])
@login_required
def process_lemonsqueezy_order():
    """Process a Lemon Squeezy order and create a subscription"""
    user_id = get_user_id_from_session()
    data = request.json
    
    order_id = data.get('order_id')
    plan_id = data.get('plan_id')
    customer_id = data.get('customer_id', '')
    subscription_id = data.get('subscription_id', '')
    billing_cycle = data.get('billing_cycle', 'monthly')
    
    if not order_id or not plan_id:
        return jsonify({"error": "Order ID and plan_id are required"}), 400
    
    logger.info(f"Processing Lemon Squeezy order {order_id} for user {user_id}, plan {plan_id}")
    
    try:
        # Create subscription using PayPal service's create_subscription_with_paypal method
        # This ensures proper handling of the subscription status and payment records
        from xavier_back.services.paypal_service import PayPalService
        
        # Format the order ID to indicate it's from Lemon Squeezy
        ls_order_id = f"LS-{order_id}"
        
        # Use the PayPal service's create_subscription_with_paypal method
        # This ensures subscription is set to active and payment records are created
        success, subscription_data, error = PayPalService.create_subscription_with_paypal(
            user_id=user_id,
            plan_id=plan_id,
            payment_id=ls_order_id,
            billing_cycle=billing_cycle
        )
        
        if not success:
            logger.error(f"Failed to create subscription for Lemon Squeezy order: {error}")
            return jsonify({"error": error}), 400
        
        # Explicitly update the subscription with Lemon Squeezy specific data
        user = User.query.get(user_id)
        if user and user.subscription:
            # Set Lemon Squeezy specific fields
            user.subscription.payment_method = 'lemon_squeezy'
            user.subscription.lemon_squeezy_order_id = order_id
            user.subscription.lemon_squeezy_customer_id = customer_id
            user.subscription.lemon_squeezy_subscription_id = subscription_id
            user.subscription.status = 'active'  # Make sure it's active
            
            # Save changes
            db.session.commit()
            logger.info(f"Updated Lemon Squeezy specific fields for user {user_id}")
        else:
            logger.error(f"User {user_id} or subscription not found after creation")
        
        # Get the updated subscription
        subscription = SubscriptionService.get_user_subscription(user_id)
        if not subscription:
            logger.error("Failed to retrieve subscription details after creation")
            return jsonify({"error": "Failed to retrieve subscription details after creation"}), 500
        
        # Add Lemon Squeezy-specific data to response for frontend
        subscription['payment_method'] = 'lemon_squeezy'
        subscription['lemon_squeezy_order_id'] = order_id
        subscription['is_active'] = True
        
        logger.info(f"Subscription created/updated successfully for user {user_id} with Lemon Squeezy order {order_id}")
        
        return jsonify(subscription), 201
        
    except Exception as e:
        logger.error(f"Error processing Lemon Squeezy order: {str(e)}")
        return jsonify({"error": str(e)}), 500

@subscription_bp.route('/lemonsqueezy-webhook', methods=['POST'])
def lemonsqueezy_webhook():
    """Handle Lemon Squeezy webhook events"""
    try:
        # Get the webhook payload
        payload = request.json
        logger.info(f"Received Lemon Squeezy webhook: {payload.get('meta', {}).get('event_name')}")
        
        # Extract event type and data
        event_type = payload.get('meta', {}).get('event_name')
        data = payload.get('data', {})
        attributes = data.get('attributes', {})
        
        # Process different event types
        if event_type == 'order_created' or event_type == 'subscription_created':
            # Get order/customer information
            order_id = data.get('id')
            customer_id = attributes.get('customer_id')
            user_email = attributes.get('user_email')
            
            # Get product information from attributes or first-level items if available
            product_id = attributes.get('product_id')
            variant_id = attributes.get('variant_id')
            
            logger.info(f"Processing Lemon Squeezy {event_type} webhook for order {order_id}, email {user_email}")
            
            # Try to map the Lemon Squeezy product to our plan
            # Note: You need to set up this mapping based on your product IDs
            # For now, use the first plan for simplicity
            plan = Plan.query.filter_by(is_active=True).first()
            if not plan:
                logger.error(f"No active plan found for Lemon Squeezy order {order_id}")
                return jsonify({"error": "No active plan found"}), 400
                
            plan_id = plan.id
            
            # Find user by email
            user = User.query.filter_by(email=user_email).first()
            if not user:
                logger.warning(f"User with email {user_email} not found for Lemon Squeezy order {order_id}")
                return jsonify({"status": "success", "message": "User not found"}), 200
            
            # Update subscription
            if user:
                # If user has a subscription, update it
                if user.subscription:
                    user.subscription.plan_id = plan_id
                    user.subscription.status = 'active'  # Important: set to active, not trialing
                    user.subscription.payment_method = 'lemon_squeezy'
                    user.subscription.lemon_squeezy_order_id = order_id
                    user.subscription.lemon_squeezy_customer_id = customer_id
                    
                    # If it's a subscription event, update subscription ID
                    if event_type == 'subscription_created' and attributes.get('subscription_id'):
                        user.subscription.lemon_squeezy_subscription_id = attributes.get('subscription_id')
                    
                    user.subscription.billing_cycle = 'monthly'  # Default to monthly
                    user.subscription.start_date = datetime.now(timezone.utc)
                    user.subscription.updated_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Updated subscription for user {user.id} via Lemon Squeezy webhook")
                else:
                    # Create new subscription
                    subscription = Subscription(
                        plan_id=plan_id,
                        status='active',  # Important: set to active, not trialing
                        billing_cycle='monthly',  # Default to monthly
                        payment_method='lemon_squeezy',
                        lemon_squeezy_order_id=order_id,
                        lemon_squeezy_customer_id=customer_id,
                        start_date=datetime.now(timezone.utc)
                    )
                    
                    # If it's a subscription event, set subscription ID
                    if event_type == 'subscription_created' and attributes.get('subscription_id'):
                        subscription.lemon_squeezy_subscription_id = attributes.get('subscription_id')
                    
                    user.subscription = subscription
                    db.session.add(subscription)
                    logger.info(f"Created new subscription for user {user.id} via Lemon Squeezy webhook")
                
                # Create payment record
                total = attributes.get('total', 0) / 100  # Convert cents to dollars
                currency = attributes.get('currency', 'USD')
                
                payment = PaymentHistory(
                    subscription_id=user.subscription.id,
                    amount=float(total),
                    currency=currency,
                    status='succeeded',
                    payment_method='lemon_squeezy',
                    payment_date=datetime.now(timezone.utc)
                )
                db.session.add(payment)
                db.session.commit()
                logger.info(f"Created payment record for user {user.id}")
        
        elif event_type == 'subscription_cancelled' or event_type == 'subscription_expired':
            # Handle subscription cancellation
            user_email = attributes.get('user_email')
            
            # Find user by email
            user = User.query.filter_by(email=user_email).first()
            if user and user.subscription:
                user.subscription.status = 'canceled'
                user.subscription.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.info(f"Cancelled subscription for user {user.id} via Lemon Squeezy webhook")
        
        elif event_type == 'subscription_payment_success':
            # Handle successful subscription payment
            user_email = attributes.get('user_email')
            
            # Find user by email
            user = User.query.filter_by(email=user_email).first()
            if user and user.subscription:
                # Ensure subscription is active
                user.subscription.status = 'active'
                user.subscription.updated_at = datetime.now(timezone.utc)
                
                # Create payment record
                total = attributes.get('total', 0) / 100  # Convert cents to dollars
                currency = attributes.get('currency', 'USD')
                
                payment = PaymentHistory(
                    subscription_id=user.subscription.id,
                    amount=float(total),
                    currency=currency,
                    status='succeeded',
                    payment_method='lemon_squeezy',
                    payment_date=datetime.now(timezone.utc)
                )
                db.session.add(payment)
                db.session.commit()
                logger.info(f"Recorded successful payment for user {user.id} via Lemon Squeezy webhook")
        
        elif event_type == 'subscription_payment_failed':
            # Handle failed subscription payment
            user_email = attributes.get('user_email')
            
            # Find user by email
            user = User.query.filter_by(email=user_email).first()
            if user and user.subscription:
                # Update subscription status
                user.subscription.status = 'past_due'
                user.subscription.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.info(f"Marked subscription as past_due for user {user.id} due to payment failure")
        
        # Add more event handlers as needed
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Error processing Lemon Squeezy webhook: {str(e)}")
        return jsonify({"error": str(e)}), 400

@subscription_bp.route('/subscription/process-flutterwave', methods=['POST'])
@login_required
def process_flutterwave_order():
    """Process a Flutterwave transaction and create a subscription"""
    user_id = get_user_id_from_session()
    data = request.json
    
    transaction_id = data.get('transaction_id')
    plan_id = data.get('plan_id')
    customer_id = data.get('customer_id', '')
    billing_cycle = data.get('billing_cycle', 'monthly')
    
    if not transaction_id or not plan_id:
        return jsonify({"error": "Transaction ID and plan_id are required"}), 400
    
    logger.info(f"Processing Flutterwave transaction {transaction_id} for user {user_id}, plan {plan_id}")
    
    try:
        # Create subscription using PayPal service's create_subscription_with_paypal method
        # This ensures proper handling of the subscription status and payment records
        from xavier_back.services.paypal_service import PayPalService
        
        # Format the transaction ID to indicate it's from Flutterwave
        fw_transaction_id = f"FW-{transaction_id}"
        
        # Use the PayPal service's create_subscription_with_paypal method
        # This ensures subscription is set to active and payment records are created
        success, subscription_data, error = PayPalService.create_subscription_with_paypal(
            user_id=user_id,
            plan_id=plan_id,
            payment_id=fw_transaction_id,
            billing_cycle=billing_cycle
        )
        
        if not success:
            logger.error(f"Failed to create subscription for Flutterwave transaction: {error}")
            return jsonify({"error": error}), 400
        
        # Explicitly update the subscription with Flutterwave specific data
        user = User.query.get(user_id)
        if user and user.subscription:
            # Set Flutterwave specific fields
            user.subscription.payment_method = 'flutterwave'
            user.subscription.flutterwave_transaction_id = transaction_id
            user.subscription.flutterwave_customer_id = customer_id
            user.subscription.status = 'active'  # Make sure it's active
            
            # Save changes
            db.session.commit()
            logger.info(f"Updated Flutterwave specific fields for user {user_id}")
        else:
            logger.error(f"User {user_id} or subscription not found after creation")
        
        # Get the updated subscription
        subscription = SubscriptionService.get_user_subscription(user_id)
        if not subscription:
            logger.error("Failed to retrieve subscription details after creation")
            return jsonify({"error": "Failed to retrieve subscription details after creation"}), 500
        
        # Add Flutterwave-specific data to response for frontend
        subscription['payment_method'] = 'flutterwave'
        subscription['flutterwave_transaction_id'] = transaction_id
        subscription['is_active'] = True
        
        logger.info(f"Subscription created/updated successfully for user {user_id} with Flutterwave transaction {transaction_id}")
        
        return jsonify(subscription), 201
        
    except Exception as e:
        logger.error(f"Error processing Flutterwave transaction: {str(e)}")
        return jsonify({"error": str(e)}), 500
