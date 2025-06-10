"""
Stripe Service Module

This module contains business logic for Stripe payment processing.
"""
import logging
import os
import random
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone

import stripe
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import User, Subscription, Plan, PaymentHistory

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Stripe with API key from environment variable
stripe_api_key = os.environ.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_API_KEY')
if stripe_api_key:
    stripe.api_key = stripe_api_key
    logger.info("Stripe initialized with API key")
else:
    logger.warning("STRIPE_SECRET_KEY environment variable not set. Stripe functionality will be limited.")

# Store the publishable key for potential use in API responses
stripe_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
if not stripe_publishable_key:
    logger.warning("STRIPE_PUBLISHABLE_KEY environment variable not set.")

class StripeService:
    """Service for handling Stripe payment processing"""

    @staticmethod
    def create_customer(user_id: int, email: str, name: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a Stripe customer for a user

        Args:
            user_id: The user ID
            email: The user's email address
            name: The user's name (optional)

        Returns:
            Tuple of (success, customer_id, error_message)
        """
        if not stripe_api_key:
            return False, None, "Stripe API key not configured"

        try:
            # Create the customer in Stripe
            customer_data = {
                'email': email,
                'metadata': {'user_id': str(user_id)}
            }
            if name:
                customer_data['name'] = name

            customer = stripe.Customer.create(**customer_data)

            # Update the user's subscription with the customer ID
            user = User.query.get(user_id)
            if not user:
                return False, None, "User not found"

            if not user.subscription:
                # Create a free subscription if the user doesn't have one
                free_plan = Plan.query.filter_by(name='Free').first()
                if not free_plan:
                    return False, None, "Free plan not found"

                subscription = Subscription(
                    plan_id=free_plan.id,
                    status='active',
                    billing_cycle='monthly'
                )
                user.subscription = subscription
                db.session.add(subscription)

            user.subscription.stripe_customer_id = customer.id
            db.session.commit()

            return True, customer.id, None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in create_customer: {str(e)}")
            return False, None, f"Stripe error: {str(e)}"
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in create_customer: {str(e)}")
            return False, None, f"Database error: {str(e)}"

    @staticmethod
    def create_subscription(user_id: int, plan_id: int, payment_method_id: str, billing_cycle: str = 'monthly') -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a Stripe subscription for a user

        Args:
            user_id: The user ID
            plan_id: The plan ID
            payment_method_id: The Stripe payment method ID
            billing_cycle: 'monthly' or 'annual'

        Returns:
            Tuple of (success, subscription_data, error_message)
        """
        # Check if this is a simulated payment method (for testing)
        is_simulated = not payment_method_id.startswith('pm_') or '_simulated' in payment_method_id

        # For real Stripe integration, we need the API key
        if not is_simulated and not stripe_api_key:
            return False, None, "Stripe API key not configured"

        try:
            user = User.query.get(user_id)
            if not user:
                return False, None, "User not found"

            plan = Plan.query.get(plan_id)
            if not plan:
                return False, None, "Plan not found"

            # If plan is free, just update the database without creating a Stripe subscription
            if plan.price == 0:
                if not user.subscription:
                    subscription = Subscription(
                        plan_id=plan_id,
                        status='active',
                        billing_cycle=billing_cycle
                    )
                    user.subscription = subscription
                    db.session.add(subscription)
                else:
                    user.subscription.plan_id = plan_id
                    user.subscription.status = 'active'
                    user.subscription.billing_cycle = billing_cycle

                db.session.commit()
                return True, {'id': user.subscription.id, 'status': 'active'}, None

            # For simulated payment methods, create a simulated subscription
            if is_simulated:
                logger.info(f"Creating simulated subscription for user {user_id} with plan {plan_id}")

                # Generate simulated IDs
                simulated_customer_id = f"cus_sim_{random.randint(10000000, 99999999)}"
                simulated_subscription_id = f"sub_sim_{random.randint(10000000, 99999999)}"
                simulated_client_secret = f"pi_sim_{random.randint(10000000, 99999999)}_secret_{random.randint(10000000, 99999999)}"

                # Update or create subscription
                if not user.subscription:
                    subscription = Subscription(
                        plan_id=plan_id,
                        status='active',  # Automatically activate for testing
                        billing_cycle=billing_cycle,
                        stripe_customer_id=simulated_customer_id,
                        stripe_subscription_id=simulated_subscription_id,
                        payment_method_id=payment_method_id,
                        start_date=datetime.now(timezone.utc)
                    )
                    user.subscription = subscription
                    db.session.add(subscription)
                else:
                    user.subscription.plan_id = plan_id
                    user.subscription.status = 'active'  # Automatically activate for testing
                    user.subscription.billing_cycle = billing_cycle
                    user.subscription.stripe_customer_id = simulated_customer_id
                    user.subscription.stripe_subscription_id = simulated_subscription_id
                    user.subscription.payment_method_id = payment_method_id
                    user.subscription.start_date = datetime.now(timezone.utc)

                db.session.commit()

                # Return simulated data
                return True, {
                    'id': user.subscription.id,
                    'stripe_subscription_id': simulated_subscription_id,
                    'status': 'active',
                    'client_secret': simulated_client_secret,
                    'simulated': True
                }, None

            # For real Stripe integration, proceed with normal flow
            # Get or create Stripe customer
            if not user.subscription or not user.subscription.stripe_customer_id:
                success, customer_id, error = StripeService.create_customer(
                    user_id, user.email, user.username
                )
                if not success:
                    return False, None, error
            else:
                customer_id = user.subscription.stripe_customer_id

            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )

            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )

            # Create the subscription in Stripe
            price = plan.annual_price if billing_cycle == 'annual' else plan.price
            stripe_subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[
                    {'price_data': {
                        'unit_amount': int(price * 100),  # Convert to cents
                        'currency': 'usd',
                        'product_data': {
                            'name': f"{plan.name} Plan ({billing_cycle})",
                            'metadata': {'plan_id': str(plan_id)}
                        },
                        'recurring': {
                            'interval': 'year' if billing_cycle == 'annual' else 'month'
                        }
                    }}
                ],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'user_id': str(user_id),
                    'plan_id': str(plan_id),
                    'billing_cycle': billing_cycle
                }
            )

            # Update the user's subscription in the database
            if not user.subscription:
                subscription = Subscription(
                    plan_id=plan_id,
                    status=stripe_subscription.status,
                    billing_cycle=billing_cycle,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=stripe_subscription.id,
                    payment_method_id=payment_method_id,
                    start_date=datetime.now(timezone.utc)
                )
                user.subscription = subscription
                db.session.add(subscription)
            else:
                user.subscription.plan_id = plan_id
                user.subscription.status = stripe_subscription.status
                user.subscription.billing_cycle = billing_cycle
                user.subscription.stripe_customer_id = customer_id
                user.subscription.stripe_subscription_id = stripe_subscription.id
                user.subscription.payment_method_id = payment_method_id
                user.subscription.start_date = datetime.now(timezone.utc)

            db.session.commit()

            # Return the subscription data
            return True, {
                'id': user.subscription.id,
                'stripe_subscription_id': stripe_subscription.id,
                'status': stripe_subscription.status,
                'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret
            }, None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in create_subscription: {str(e)}")
            return False, None, f"Stripe error: {str(e)}"
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in create_subscription: {str(e)}")
            return False, None, f"Database error: {str(e)}"

    @staticmethod
    def cancel_subscription(user_id: int, at_period_end: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Cancel a user's Stripe subscription

        Args:
            user_id: The user ID
            at_period_end: Whether to cancel at the end of the billing period

        Returns:
            Tuple of (success, error_message)
        """
        if not stripe_api_key:
            return False, "Stripe API key not configured"

        try:
            user = User.query.get(user_id)
            if not user or not user.subscription:
                return False, "No active subscription found"

            subscription = user.subscription

            # If there's no Stripe subscription ID, just update the database
            if not subscription.stripe_subscription_id:
                if at_period_end:
                    subscription.cancel_at_period_end = True
                else:
                    subscription.status = 'canceled'

                db.session.commit()
                return True, None

            # Cancel the subscription in Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)

            if at_period_end:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.cancel_at_period_end = True
            else:
                stripe.Subscription.delete(subscription.stripe_subscription_id)
                subscription.status = 'canceled'

            db.session.commit()
            return True, None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in cancel_subscription: {str(e)}")
            return False, f"Stripe error: {str(e)}"
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in cancel_subscription: {str(e)}")
            return False, f"Database error: {str(e)}"
