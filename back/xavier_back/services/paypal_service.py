"""
PayPal Service Module

This module contains business logic for PayPal payment processing.
"""
import logging
import os
import random
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone, timedelta

import requests
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import User, Subscription, Plan, PaymentHistory
from xavier_back.config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Initialize PayPal with API credentials from config
paypal_client_id = Config.PAYPAL_CLIENT_ID
paypal_client_secret = Config.PAYPAL_CLIENT_SECRET
paypal_api_base = Config.PAYPAL_API_BASE
paypal_app_name = Config.PAYPAL_APP_NAME

if paypal_client_id and paypal_client_secret:
    logger.info("PayPal credentials loaded from configuration")
    logger.info(f"Using PayPal API base: {paypal_api_base}")
    logger.info(f"Using PayPal app name: {paypal_app_name}")
else:
    logger.warning("PayPal credentials not properly configured. PayPal functionality will be limited.")


class PayPalService:
    """Service for handling PayPal payment processing"""

    @staticmethod
    def get_access_token() -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get an access token from PayPal API

        Returns:
            Tuple of (success, access_token, error_message)
        """
        if not paypal_client_id or not paypal_client_secret:
            return False, None, "PayPal credentials not configured"

        try:
            url = f"{paypal_api_base}/v1/oauth2/token"
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en_US"
            }
            data = {
                "grant_type": "client_credentials"
            }

            response = requests.post(
                url,
                auth=(paypal_client_id, paypal_client_secret),
                headers=headers,
                data=data
            )

            if response.status_code == 200:
                response_data = response.json()
                return True, response_data.get("access_token"), None
            else:
                logger.error(f"Failed to get PayPal access token: {response.text}")
                return False, None, f"Failed to get PayPal access token: {response.status_code}"

        except Exception as e:
            logger.exception("Error getting PayPal access token")
            return False, None, str(e)

    @staticmethod
    def create_order(plan_id: int, plan_name: str, price: float, billing_cycle: str = 'monthly', 
                   enable_guest_checkout: bool = True, force_guest_checkout: bool = False,
                   return_url: str = None, cancel_url: str = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a PayPal order for checkout with guest checkout enabled

        Args:
            plan_id: The plan ID in our database
            plan_name: The name of the plan
            price: The price of the plan
            billing_cycle: 'monthly' or 'annual'
            enable_guest_checkout: Whether to enable guest checkout (default: True)
            force_guest_checkout: Whether to force the guest checkout flow (default: False)
            return_url: Custom return URL after successful payment
            cancel_url: Custom cancel URL if payment is canceled

        Returns:
            Tuple of (success, order_data, error_message)
        """
        success, access_token, error = PayPalService.get_access_token()
        if not success:
            return False, None, error

        try:
            url = f"{paypal_api_base}/v2/checkout/orders"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            # Format the price to 2 decimal places
            formatted_price = "{:.2f}".format(price)
            
            # Determine if we're in development mode
            is_development = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('ENVIRONMENT') == 'development'
            
            # Set the return URLs based on environment or provided URLs
            if return_url is None:
                if is_development:
                    return_url = "http://localhost:4200/subscription?success=true"
                else:
                    return_url = "https://xavierai.site/subscription?success=true"
            
            if cancel_url is None:
                if is_development:
                    cancel_url = "http://localhost:4200/subscription?cancel=true"
                else:
                    cancel_url = "https://xavierai.site/subscription?cancel=true"
            
            logger.info(f"Using return URL: {return_url}")
            logger.info(f"Using cancel URL: {cancel_url}")

            # Create the order payload
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": "USD",
                            "value": formatted_price
                        },
                        "description": f"{plan_name} Plan ({billing_cycle} billing)",
                        "custom_id": f"{plan_id}:{billing_cycle}"  # Store plan ID and billing cycle
                    }
                ],
                "application_context": {
                    "brand_name": "Xavier AI",
                    "landing_page": "BILLING",  # BILLING enables guest checkout
                    "shipping_preference": "NO_SHIPPING",
                    "user_action": "PAY_NOW",
                    "return_url": return_url,
                    "cancel_url": cancel_url
                }
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code in (200, 201):
                response_data = response.json()

                # Extract the approval URL and order ID
                order_id = response_data.get("id")

                # Find the approve link
                approve_url = None
                for link in response_data.get("links", []):
                    if link.get("rel") == "approve":
                        approve_url = link.get("href")
                        
                        # If force_guest_checkout is True, modify the URL to prioritize credit card payment
                        if force_guest_checkout and approve_url:
                            # Add fundingSource=card to prioritize the card payment method
                            if "?" in approve_url:
                                approve_url += "&fundingSource=card"
                            else:
                                approve_url += "?fundingSource=card"
                        break

                return True, {
                    "id": order_id,
                    "approve_url": approve_url,
                    "plan_id": plan_id,
                    "billing_cycle": billing_cycle
                }, None
            else:
                logger.error(f"Failed to create PayPal order: {response.text}")
                return False, None, f"Failed to create PayPal order: {response.status_code} - {response.text}"

        except Exception as e:
            logger.exception("Error creating PayPal order")
            return False, None, str(e)

    @staticmethod
    def capture_order(order_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Capture a PayPal order after approval

        Args:
            order_id: The PayPal order ID

        Returns:
            Tuple of (success, capture_data, error_message)
        """
        success, access_token, error = PayPalService.get_access_token()
        if not success:
            return False, None, error

        try:
            url = f"{paypal_api_base}/v2/checkout/orders/{order_id}/capture"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            response = requests.post(url, headers=headers)

            if response.status_code in (200, 201):
                response_data = response.json()

                # Extract the transaction ID and status
                status = response_data.get("status")

                # Get the custom_id from the purchase unit to retrieve plan_id and billing_cycle
                purchase_units = response_data.get("purchase_units", [])
                custom_id = purchase_units[0].get("custom_id") if purchase_units else None

                # Parse the custom_id to get plan_id and billing_cycle
                plan_id = None
                billing_cycle = "monthly"
                if custom_id and ":" in custom_id:
                    plan_id_str, billing_cycle = custom_id.split(":")
                    try:
                        plan_id = int(plan_id_str)
                    except ValueError:
                        logger.error(f"Invalid plan_id in custom_id: {custom_id}")

                return True, {
                    "id": order_id,
                    "status": status,
                    "plan_id": plan_id,
                    "billing_cycle": billing_cycle,
                    "transaction_id": response_data.get("id")
                }, None
            else:
                logger.error(f"Failed to capture PayPal order: {response.text}")
                return False, None, f"Failed to capture PayPal order: {response.status_code} - {response.text}"

        except Exception as e:
            logger.exception("Error capturing PayPal order")
            return False, None, str(e)

    @staticmethod
    def create_product(name: str, description: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a product in PayPal

        Args:
            name: Product name
            description: Product description

        Returns:
            Tuple of (success, product_id, error_message)
        """
        success, access_token, error = PayPalService.get_access_token()
        if not success:
            return False, None, error

        try:
            url = f"{paypal_api_base}/v1/catalogs/products"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            payload = {
                "name": name,
                "type": "SERVICE"
            }

            if description:
                payload["description"] = description

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code in (200, 201):
                response_data = response.json()
                return True, response_data.get("id"), None
            else:
                logger.error(f"Failed to create PayPal product: {response.text}")
                return False, None, f"Failed to create PayPal product: {response.status_code}"

        except Exception as e:
            logger.exception("Error creating PayPal product")
            return False, None, str(e)

    @staticmethod
    def create_plan(product_id: str, name: str, price: float, interval: str = "MONTH") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a billing plan in PayPal

        Args:
            product_id: PayPal product ID
            name: Plan name
            price: Plan price
            interval: Billing interval (MONTH or YEAR)

        Returns:
            Tuple of (success, plan_id, error_message)
        """
        success, access_token, error = PayPalService.get_access_token()
        if not success:
            return False, None, error

        try:
            url = f"{paypal_api_base}/v1/billing/plans"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            payload = {
                "product_id": product_id,
                "name": name,
                "billing_cycles": [
                    {
                        "frequency": {
                            "interval_unit": interval,
                            "interval_count": 1
                        },
                        "tenure_type": "REGULAR",
                        "sequence": 1,
                        "total_cycles": 0,  # Infinite cycles
                        "pricing_scheme": {
                            "fixed_price": {
                                "value": str(price),
                                "currency_code": "USD"
                            }
                        }
                    }
                ],
                "payment_preferences": {
                    "auto_bill_outstanding": True,
                    "setup_fee": {
                        "value": "0",
                        "currency_code": "USD"
                    },
                    "setup_fee_failure_action": "CONTINUE",
                    "payment_failure_threshold": 3
                }
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code in (200, 201):
                response_data = response.json()
                return True, response_data.get("id"), None
            else:
                logger.error(f"Failed to create PayPal plan: {response.text}")
                return False, None, f"Failed to create PayPal plan: {response.status_code}"

        except Exception as e:
            logger.exception("Error creating PayPal plan")
            return False, None, str(e)

    @staticmethod
    def create_subscription(user_id: int, plan_id: int, paypal_subscription_id: str = None, billing_cycle: str = 'monthly') -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a subscription for a user using PayPal

        Args:
            user_id: The user ID
            plan_id: The plan ID in our database
            paypal_subscription_id: The PayPal subscription ID (if already created)
            billing_cycle: 'monthly' or 'annual'

        Returns:
            Tuple of (success, subscription_data, error_message)
        """
        # Check if this is a simulated payment
        is_simulated = paypal_subscription_id and '_simulated' in paypal_subscription_id

        try:
            user = User.query.get(user_id)
            if not user:
                return False, None, "User not found"

            plan = Plan.query.get(plan_id)
            if not plan:
                return False, None, "Plan not found"

            # For simulated payments, create a subscription record with simulated data
            if is_simulated:
                # Generate simulated IDs
                simulated_subscription_id = paypal_subscription_id or f"I-PAYPAL_SIMULATED_{random.randint(10000000, 99999999)}"

                # Create or update subscription record
                if not user.subscription:
                    subscription = Subscription(
                        plan_id=plan_id,
                        status='active',
                        billing_cycle=billing_cycle,
                        paypal_subscription_id=simulated_subscription_id,
                        payment_method='paypal',
                        start_date=datetime.now(timezone.utc)
                    )
                    user.subscription = subscription
                    db.session.add(subscription)
                else:
                    user.subscription.plan_id = plan_id
                    user.subscription.status = 'active'
                    user.subscription.billing_cycle = billing_cycle
                    user.subscription.paypal_subscription_id = simulated_subscription_id
                    user.subscription.payment_method = 'paypal'
                    user.subscription.start_date = datetime.now(timezone.utc)

                db.session.commit()

                # Return simulated data
                return True, {
                    'id': user.subscription.id,
                    'paypal_subscription_id': simulated_subscription_id,
                    'status': 'active',
                    'simulated': True
                }, None

            # For real PayPal integration with an existing subscription ID
            if paypal_subscription_id:
                # Create or update subscription record
                if not user.subscription:
                    subscription = Subscription(
                        plan_id=plan_id,
                        status='active',
                        billing_cycle=billing_cycle,
                        paypal_subscription_id=paypal_subscription_id,
                        payment_method='paypal',
                        start_date=datetime.now(timezone.utc)
                    )
                    user.subscription = subscription
                    db.session.add(subscription)
                else:
                    user.subscription.plan_id = plan_id
                    user.subscription.status = 'active'
                    user.subscription.billing_cycle = billing_cycle
                    user.subscription.paypal_subscription_id = paypal_subscription_id
                    user.subscription.payment_method = 'paypal'
                    user.subscription.start_date = datetime.now(timezone.utc)

                db.session.commit()

                # Create payment history record
                payment = PaymentHistory(
                    subscription_id=user.subscription.id,
                    amount=plan.annual_price if billing_cycle == 'annual' else plan.price,
                    currency='USD',
                    status='succeeded',
                    payment_method='paypal'
                )
                db.session.add(payment)
                db.session.commit()

                return True, {
                    'id': user.subscription.id,
                    'paypal_subscription_id': paypal_subscription_id,
                    'status': 'active'
                }, None

            # If no PayPal subscription ID provided, return error
            return False, None, "PayPal subscription ID is required"

        except SQLAlchemyError as e:
            logger.exception("Database error creating subscription")
            db.session.rollback()
            return False, None, f"Database error: {str(e)}"
        except Exception as e:
            logger.exception("Error creating subscription")
            return False, None, str(e)

    @staticmethod
    def cancel_subscription(subscription_id: str) -> Tuple[bool, Optional[str]]:
        """
        Cancel a PayPal subscription

        Args:
            subscription_id: The PayPal subscription ID

        Returns:
            Tuple of (success, error_message)
        """
        # For simulated subscriptions, just return success
        if '_simulated' in subscription_id:
            return True, None

        success, access_token, error = PayPalService.get_access_token()
        if not success:
            return False, error

        try:
            url = f"{paypal_api_base}/v1/billing/subscriptions/{subscription_id}/cancel"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            payload = {
                "reason": "Canceled by user"
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code in (200, 201, 204):
                return True, None
            else:
                logger.error(f"Failed to cancel PayPal subscription: {response.text}")
                return False, f"Failed to cancel subscription: {response.status_code}"

        except Exception as e:
            logger.exception("Error canceling PayPal subscription")
            return False, str(e)

    @staticmethod
    def create_subscription_with_paypal(user_id: int, plan_id: int, payment_id: str, billing_cycle: str = 'monthly') -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a subscription with PayPal payment

        Args:
            user_id: The user ID
            plan_id: The plan ID
            payment_id: The PayPal payment ID (subscription ID or order ID)
            billing_cycle: 'monthly' or 'annual'

        Returns:
            Tuple of (success, subscription_data, error_message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False, None, "User not found"

            plan = Plan.query.get(plan_id)
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return False, None, "Plan not found"

            # Check if payment_id is for a subscription or order
            is_subscription = payment_id.startswith('I-')
            is_order = payment_id.startswith('ORDER-') or not is_subscription
            
            logger.info(f"Creating subscription for user {user_id} with payment_id {payment_id} (type: {'subscription' if is_subscription else 'order'})")

            # Create or update subscription
            if not user.subscription:
                logger.info(f"Creating new subscription for user {user_id}")
                subscription = Subscription(
                    plan_id=plan_id,
                    status='active',  # Set status to active immediately since payment was made
                    billing_cycle=billing_cycle,
                    payment_method='paypal',
                    start_date=datetime.now(timezone.utc)
                )
                if is_subscription:
                    subscription.paypal_subscription_id = payment_id
                else:
                    subscription.paypal_order_id = payment_id
                
                user.subscription = subscription
                db.session.add(subscription)
            else:
                logger.info(f"Updating existing subscription for user {user_id}")
                user.subscription.plan_id = plan_id
                user.subscription.status = 'active'  # Always set to active, not trialing
                user.subscription.billing_cycle = billing_cycle
                user.subscription.payment_method = 'paypal'
                
                if is_subscription:
                    user.subscription.paypal_subscription_id = payment_id
                else:
                    user.subscription.paypal_order_id = payment_id
                    
                subscription = user.subscription

            # Ensure we're using timezone-aware datetime
            now = datetime.now(timezone.utc)
            subscription.updated_at = now
            subscription.start_date = now  # Reset start date with new payment
            
            # Skip trial period since payment was already made
            subscription.status = 'active'
            subscription.trial_end = None

            # Create a payment record
            payment = PaymentHistory(
                subscription_id=subscription.id,
                amount=plan.annual_price if billing_cycle == 'annual' else plan.price,
                currency='USD',
                status='succeeded',
                payment_method='paypal',
                payment_date=now
            )
            db.session.add(payment)
            
            db.session.commit()
            logger.info(f"Successfully created/updated subscription for user {user_id}")

            # Get and return the subscription data
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            if subscription_data:
                subscription_data['payment_successful'] = True
                return True, subscription_data, None
            else:
                logger.error(f"Failed to retrieve subscription data for user {user_id}")
                return False, None, "Failed to retrieve subscription data"

        except SQLAlchemyError as e:
            logger.exception(f"Database error creating subscription: {str(e)}")
            db.session.rollback()
            return False, None, f"Database error: {str(e)}"
        except Exception as e:
            logger.exception(f"Error creating subscription: {str(e)}")
            return False, None, str(e)


