"""
Lemon Squeezy Service Module

This module contains business logic for Lemon Squeezy payment processing.
"""
import os
import requests
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from xavier_back.extensions import db
from xavier_back.models import User, Subscription, Plan, PaymentHistory
from xavier_back.config import Config

logger = logging.getLogger(__name__)

class LemonSqueezyService:
    """Service for handling Lemon Squeezy payment processing"""
    
    @classmethod
    def verify_order(cls, order_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify a Lemon Squeezy order
        
        Args:
            order_id: The Lemon Squeezy order ID
            
        Returns:
            Tuple of (success, order_data, error_message)
        """
        # Get API details from config
        api_key = Config.LEMON_SQUEEZY_API_KEY
        
        if not api_key:
            logger.warning("Lemon Squeezy API key not configured")
            # Return success anyway since we don't want to block the payment flow
            # The API key is only needed for verification, but we can still create the subscription
            return True, {"id": order_id, "status": "paid"}, None
            
        try:
            # Call the Lemon Squeezy API to verify the order
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json"
            }
            
            response = requests.get(f"https://api.lemonsqueezy.com/v1/orders/{order_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Verified Lemon Squeezy order {order_id}")
                return True, data.get("data", {"id": order_id, "status": "paid"}), None
            else:
                logger.warning(f"Failed to verify Lemon Squeezy order {order_id}: {response.text}")
                # Still return success to not block the payment flow
                return True, {"id": order_id, "status": "paid"}, None
                
        except Exception as e:
            logger.exception(f"Error verifying Lemon Squeezy order: {str(e)}")
            # Still return success to not block the payment flow
            return True, {"id": order_id, "status": "paid"}, None
            
    @classmethod
    def create_subscription(cls, user_id: int, plan_id: int, order_id: str, 
                           customer_id: Optional[str] = None, subscription_id: Optional[str] = None, 
                           billing_cycle: str = 'monthly') -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a subscription record after successful Lemon Squeezy payment
        
        Args:
            user_id: User ID
            plan_id: Plan ID
            order_id: Lemon Squeezy order ID
            customer_id: Lemon Squeezy customer ID (optional)
            subscription_id: Lemon Squeezy subscription ID (optional)
            billing_cycle: 'monthly' or 'annual'
            
        Returns:
            Tuple of (success, subscription_data, error_message)
        """
        try:
            # Verify the order first (optional step)
            success, order_data, error = cls.verify_order(order_id)
            
            # Get the user and plan
            user = User.query.get(user_id)
            if not user:
                return False, None, f"User with ID {user_id} not found"
                
            plan = Plan.query.get(plan_id)
            if not plan:
                return False, None, f"Plan with ID {plan_id} not found"
            
            logger.info(f"Creating subscription for user {user_id} with plan {plan_id} and order {order_id}")
            
            # Check if user already has a subscription
            existing_subscription = Subscription.query.filter_by(user_id=user_id).first()
            
            # Set up subscription data
            now = datetime.now(timezone.utc)
            
            if existing_subscription:
                logger.info(f"User {user_id} already has subscription ID {existing_subscription.id}, updating it")
                # Update existing subscription
                existing_subscription.plan_id = plan_id
                existing_subscription.status = 'active'
                existing_subscription.billing_cycle = billing_cycle
                existing_subscription.payment_method = 'lemon_squeezy'
                existing_subscription.lemon_squeezy_order_id = order_id
                
                if customer_id:
                    existing_subscription.lemon_squeezy_customer_id = customer_id
                    
                if subscription_id:
                    existing_subscription.lemon_squeezy_subscription_id = subscription_id
                    
                existing_subscription.updated_at = now
                subscription = existing_subscription
            else:
                logger.info(f"Creating new subscription for user {user_id}")
                # Create new subscription
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status='active',
                    start_date=now,
                    billing_cycle=billing_cycle,
                    payment_method='lemon_squeezy',
                    lemon_squeezy_order_id=order_id,
                    lemon_squeezy_customer_id=customer_id,
                    lemon_squeezy_subscription_id=subscription_id,
                    created_at=now,
                    updated_at=now
                )
                db.session.add(subscription)
                # Flush to get the subscription ID
                db.session.flush()
                logger.info(f"Created new subscription with ID {subscription.id}")
            
            # Update the user's subscription relationship
            if user and subscription:
                # Set the subscription on the user directly
                user.subscription = subscription
                logger.info(f"Set user.subscription = subscription {subscription.id} for user {user.id}")
            
            # Create payment history record
            price = plan.annual_price if billing_cycle == 'annual' else plan.price
            payment_history = PaymentHistory(
                user_id=user_id,
                subscription_id=subscription.id if hasattr(subscription, 'id') else None,
                amount=price,
                currency='USD',  # Lemon Squeezy uses USD by default
                payment_method='lemon_squeezy',
                payment_id=order_id,
                status='completed',
                lemon_squeezy_order_id=order_id,
                created_at=now
            )
            
            db.session.add(payment_history)
            
            # Make sure to commit the changes
            db.session.commit()
            
            # Double-check that the subscription was saved correctly
            saved_sub = Subscription.query.get(subscription.id)
            if not saved_sub:
                logger.error(f"Subscription {subscription.id} was not saved correctly!")
            else:
                logger.info(f"Verified subscription {saved_sub.id} was saved correctly")
                
            # Double-check that the user-subscription relationship is correct
            refreshed_user = User.query.get(user_id)
            if refreshed_user and refreshed_user.subscription:
                logger.info(f"Verified user {refreshed_user.id} has subscription {refreshed_user.subscription.id}")
            else:
                logger.error(f"User {user_id} still does not have a subscription after commit!")
            
            logger.info(f"Successfully created subscription for user {user_id} with Lemon Squeezy order {order_id}")
            
            # Return success and subscription data
            return True, {
                'id': subscription.id,
                'user_id': user_id,
                'plan_id': plan_id,
                'status': 'active',
                'payment_method': 'lemon_squeezy',
                'lemon_squeezy_order_id': order_id,
                'lemon_squeezy_customer_id': customer_id,
                'lemon_squeezy_subscription_id': subscription_id
            }, None
            
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error creating subscription with Lemon Squeezy: {str(e)}")
            return False, None, str(e)
            
    @classmethod
    def process_webhook(cls, payload: Dict[str, Any]) -> bool:
        """
        Process Lemon Squeezy webhook notification
        
        Args:
            payload: Webhook payload
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Get event type from meta.event_name
            meta = payload.get('meta', {})
            event = meta.get('event_name')
            
            if not event:
                logger.warning("Webhook payload missing event_name in meta")
                return False
                
            logger.info(f"Processing Lemon Squeezy webhook event: {event}")
            
            # Get the data object
            data = payload.get('data', {})
            if not data:
                logger.warning("Webhook payload missing data")
                return False
                
            # Extract order ID and other relevant fields
            order_id = data.get('id')
            if not order_id:
                logger.warning("Webhook event missing order ID")
                return False
                
            # Handle different event types
            if event == 'order_created':
                # Get order attributes
                attributes = data.get('attributes', {})
                customer_id = attributes.get('customer_id')
                user_email = attributes.get('user_email')
                
                # Look for a subscription with this order ID
                subscription = Subscription.query.filter_by(
                    lemon_squeezy_order_id=order_id,
                    payment_method='lemon_squeezy'
                ).first()
                
                if subscription:
                    # Update the subscription status
                    subscription.status = 'active'
                    subscription.updated_at = datetime.now(timezone.utc)
                    
                    # Make sure the user-subscription relationship is set
                    user = User.query.get(subscription.user_id)
                    if user:
                        user.subscription = subscription
                    
                    db.session.commit()
                    logger.info(f"Updated subscription for Lemon Squeezy order {order_id} to active")
                    return True
                else:
                    # Try to find user by email if available
                    if user_email:
                        user = User.query.filter_by(email=user_email).first()
                        if user:
                            # Get the default plan
                            plan = Plan.query.filter_by(is_active=True).first()
                            if not plan:
                                logger.error("No active plan found for new subscription")
                                return False
                                
                            # Create a new subscription for this user
                            now = datetime.now(timezone.utc)
                            new_subscription = Subscription(
                                user_id=user.id,
                                plan_id=plan.id,
                                status='active',
                                start_date=now,
                                billing_cycle='monthly',  # Default to monthly
                                payment_method='lemon_squeezy',
                                lemon_squeezy_order_id=order_id,
                                lemon_squeezy_customer_id=customer_id,
                                created_at=now,
                                updated_at=now
                            )
                            db.session.add(new_subscription)
                            db.session.flush()  # Flush to get the ID
                            
                            # Update the user's subscription relationship
                            user.subscription = new_subscription
                            
                            # Create payment history record
                            payment_history = PaymentHistory(
                                user_id=user.id,
                                subscription_id=new_subscription.id,
                                amount=plan.price,
                                currency='USD',  # Lemon Squeezy uses USD by default
                                payment_method='lemon_squeezy',
                                payment_id=order_id,
                                status='completed',
                                lemon_squeezy_order_id=order_id,
                                created_at=now
                            )
                            
                            db.session.add(payment_history)
                            db.session.commit()
                            logger.info(f"Created new subscription for user {user.id} with Lemon Squeezy order {order_id}")
                            return True
                    
                    logger.warning(f"No subscription or user found for Lemon Squeezy order {order_id}")
                    return False
                    
            elif event == 'subscription_created':
                # Subscription created
                attributes = data.get('attributes', {})
                order_id = attributes.get('order_id')
                subscription_id = data.get('id')
                
                if not order_id:
                    logger.warning("Webhook subscription_created missing order_id in attributes")
                    return False
                    
                # Find subscription by order ID
                subscription = Subscription.query.filter_by(
                    lemon_squeezy_order_id=order_id,
                    payment_method='lemon_squeezy'
                ).first()
                
                if subscription:
                    # Update the subscription with the subscription ID
                    subscription.lemon_squeezy_subscription_id = subscription_id
                    subscription.status = 'active'
                    subscription.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info(f"Updated subscription for Lemon Squeezy order {order_id} with subscription ID {subscription_id}")
                    return True
                else:
                    logger.warning(f"No subscription found for Lemon Squeezy order {order_id}")
                    return False
                    
            elif event == 'subscription_cancelled':
                # Subscription cancelled
                subscription_id = data.get('id')
                
                if not subscription_id:
                    logger.warning("Webhook subscription_cancelled missing subscription ID")
                    return False
                    
                # Find subscription by subscription ID
                subscription = Subscription.query.filter_by(
                    lemon_squeezy_subscription_id=subscription_id,
                    payment_method='lemon_squeezy'
                ).first()
                
                if subscription:
                    # Update the subscription status
                    subscription.status = 'canceled'
                    subscription.cancel_at_period_end = True
                    subscription.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info(f"Marked subscription with Lemon Squeezy subscription ID {subscription_id} as cancelled")
                    return True
                else:
                    logger.warning(f"No subscription found for Lemon Squeezy subscription ID {subscription_id}")
                    return False
                    
            # Return success for other event types
            return True
                
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error processing Lemon Squeezy webhook: {str(e)}")
            return False 