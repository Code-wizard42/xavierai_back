"""
Subscription Service Module

This module contains business logic for subscription operations.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import User, Subscription, Plan, PaymentHistory

# Configure logging
logger = logging.getLogger(__name__)

class SubscriptionService:
    """Service for handling subscription operations"""

    @staticmethod
    def get_user_subscription(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user's subscription details

        Args:
            user_id: The user ID

        Returns:
            Dictionary with subscription details or None if not found
        """
        try:
            user = User.query.get(user_id)
            if not user or not user.subscription:
                return None

            # Get the subscription and associated plan
            subscription = user.subscription
            plan = Plan.query.get(subscription.plan_id)

            # Check if the subscription is active
            is_active = subscription.is_active()

            # Get billing cycle info
            billing_cycle = subscription.billing_cycle or 'monthly'

            # Format the response
            subscription_data = {
                'id': subscription.id,
                'status': subscription.status,
                'is_active': is_active,
                'plan': {
                    'id': plan.id,
                    'name': plan.name,
                    'description': plan.description,
                    'price': plan.price if billing_cycle == 'monthly' else plan.annual_price,
                    'features': plan.features,
                    'max_chatbots': plan.max_chatbots,
                    'max_conversations_per_month': plan.max_conversations_per_month
                },
                'billing_cycle': billing_cycle,
                'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
                'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
                'next_billing_date': subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
                'is_billing_overdue': subscription.is_billing_overdue(),
                'days_until_billing': subscription.days_until_billing(),
                'payment_method': subscription.payment_method
            }

            # Add trial-specific info if in trial
            if subscription.is_in_trial():
                subscription_data['trial_end'] = subscription.trial_end.isoformat()
                subscription_data['days_left_in_trial'] = subscription.days_left_in_trial()
                subscription_data['in_trial'] = True
            else:
                subscription_data['in_trial'] = False

            # Add PayPal-specific fields if using PayPal
            if subscription.payment_method == 'paypal':
                subscription_data['paypal_subscription_id'] = subscription.paypal_subscription_id
                subscription_data['paypal_order_id'] = subscription.paypal_order_id
            
            # Add Paystack-specific fields if using Paystack
            elif subscription.payment_method == 'paystack':
                subscription_data['paystack_reference'] = subscription.paystack_reference
            
            # Add Lemon Squeezy-specific fields if using Lemon Squeezy
            elif subscription.payment_method == 'lemon_squeezy':
                subscription_data['lemon_squeezy_order_id'] = subscription.lemon_squeezy_order_id
                subscription_data['lemon_squeezy_customer_id'] = subscription.lemon_squeezy_customer_id
                subscription_data['lemon_squeezy_subscription_id'] = subscription.lemon_squeezy_subscription_id

            return subscription_data
        except Exception as e:
            logger.exception(f"Error getting user subscription: {str(e)}")
            return None

    @staticmethod
    def get_available_plans() -> List[Dict[str, Any]]:
        """
        Get all available subscription plans

        Returns:
            List of plan dictionaries
        """
        try:
            plans = Plan.query.filter_by(is_active=True).all()
            return [
                {
                    'id': plan.id,
                    'name': plan.name,
                    'description': plan.description,
                    'price': plan.price,
                    'annual_price': plan.annual_price,
                    'features': plan.features,
                    'max_chatbots': plan.max_chatbots
                }
                for plan in plans
            ]
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_available_plans: {str(e)}")
            return []

    @staticmethod
    def create_subscription(user_id: int, plan_id: int, billing_cycle: str = 'monthly', payment_provider: str = None, payment_id: str = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a new subscription for a user

        Args:
            user_id: The user ID
            plan_id: The plan ID
            billing_cycle: 'monthly' or 'annual'
            payment_provider: The payment provider (paypal, paystack, lemon_squeezy, etc.)
            payment_id: The payment ID from the provider

        Returns:
            Tuple of (success, subscription_data, error_message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, None, "User not found"

            plan = Plan.query.get(plan_id)
            if not plan:
                return False, None, "Plan not found"

            # Check if user already has a subscription
            if user.subscription:
                # Update existing subscription
                user.subscription.plan_id = plan_id
                user.subscription.billing_cycle = billing_cycle
                user.subscription.status = 'active'
                # Ensure we're using timezone-aware datetime
                now = datetime.now(timezone.utc)
                user.subscription.start_date = now
                user.subscription.end_date = None
                user.subscription.updated_at = now
                
                # Update payment information if provided
                if payment_provider:
                    user.subscription.payment_method = payment_provider
                
                # Set provider-specific payment IDs
                if payment_id:
                    if payment_provider == 'paypal':
                        user.subscription.paypal_subscription_id = payment_id
                    elif payment_provider == 'paystack':
                        user.subscription.paystack_reference = payment_id
                    elif payment_provider == 'lemon_squeezy':
                        user.subscription.lemon_squeezy_order_id = payment_id
                
                subscription = user.subscription
            else:
                # Create new subscription
                # Ensure we're using timezone-aware datetime
                now = datetime.now(timezone.utc)
                subscription = Subscription(
                    plan_id=plan_id,
                    status='active',
                    start_date=now,
                    billing_cycle=billing_cycle,
                    payment_method=payment_provider
                )
                
                # Set provider-specific payment IDs
                if payment_id:
                    if payment_provider == 'paypal':
                        subscription.paypal_subscription_id = payment_id
                    elif payment_provider == 'paystack':
                        subscription.paystack_reference = payment_id
                    elif payment_provider == 'lemon_squeezy':
                        subscription.lemon_squeezy_order_id = payment_id
                
                user.subscription = subscription
                db.session.add(subscription)

            # Set trial period for paid plans if no payment information provided
            if plan.price > 0 and not payment_id and not payment_provider:
                subscription.status = 'trialing'
                # Ensure we're using timezone-aware datetime
                now = datetime.now(timezone.utc)
                subscription.trial_end = now + timedelta(days=14)  # 14-day trial
                # Set billing date to trial end date
                subscription.next_billing_date = subscription.trial_end
            else:
                # If payment was made, ensure status is active, not trialing
                subscription.status = 'active'
                # Set next billing date for active subscriptions
                subscription.set_next_billing_date()

            # Create payment history record if payment information is provided
            if payment_id and payment_provider:
                payment_history = PaymentHistory(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    plan_id=plan_id,
                    amount=plan.price if billing_cycle == 'monthly' else plan.annual_price,
                    payment_method=payment_provider,
                    payment_id=payment_id,
                    status='completed',
                    created_at=now
                )
                db.session.add(payment_history)

            db.session.commit()

            return True, SubscriptionService.get_user_subscription(user_id), None
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in create_subscription: {str(e)}")
            return False, None, f"Database error: {str(e)}"

    @staticmethod
    def cancel_subscription(user_id: int, at_period_end: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Cancel a user's subscription

        Args:
            user_id: The user ID
            at_period_end: Whether to cancel at the end of the billing period

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = User.query.get(user_id)
            if not user or not user.subscription:
                return False, "No active subscription found"

            subscription = user.subscription

            if at_period_end:
                subscription.cancel_at_period_end = True
            else:
                subscription.status = 'canceled'
                # Ensure we're using timezone-aware datetime
                now = datetime.now(timezone.utc)
                subscription.end_date = now

            # Ensure we're using timezone-aware datetime
            now = datetime.now(timezone.utc)
            subscription.updated_at = now
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in cancel_subscription: {str(e)}")
            return False, f"Database error: {str(e)}"

    @staticmethod
    def check_feature_access(user_id: int, feature: str) -> bool:
        """
        Check if a user has access to a specific feature

        Args:
            user_id: The user ID
            feature: The feature to check

        Returns:
            True if the user has access, False otherwise
        """
        try:
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            if not subscription_data or not subscription_data['is_active']:
                return False

            # Check if the feature is in the plan's features
            return feature in subscription_data['plan']['features']
        except Exception as e:
            logger.error(f"Error in check_feature_access: {str(e)}")
            return False

    @staticmethod
    def check_chatbot_limit(user_id: int) -> Tuple[bool, int, int]:
        """
        Check if a user has reached their chatbot limit

        Args:
            user_id: The user ID

        Returns:
            Tuple of (has_reached_limit, current_count, max_allowed)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return True, 0, 4

            current_count = len(user.chatbots)
            max_allowed = 4

            return current_count >= max_allowed, current_count, max_allowed
        except Exception as e:
            logger.error(f"Error in check_chatbot_limit: {str(e)}")
            return True, 0, 4
