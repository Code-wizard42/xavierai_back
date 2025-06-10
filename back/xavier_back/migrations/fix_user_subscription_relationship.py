"""
Migration script to fix broken user-subscription relationships.
"""
import logging
from sqlalchemy.sql import text
from xavier_back.extensions import db
from xavier_back.models import User, Subscription, PaymentHistory

logger = logging.getLogger(__name__)

def run_migration():
    """
    Fix broken user-subscription relationships in the database.
    This migration ensures that users with subscriptions have proper bidirectional relationships.
    """
    logger.info("Running migration to fix user-subscription relationships")
    
    try:
        # First fix payment_history records with null subscription_id (which violates the constraint)
        logger.info("Checking for payment_history records with null subscription_id")
        payment_records = PaymentHistory.query.filter_by(subscription_id=None).all()
        
        if payment_records:
            logger.info(f"Found {len(payment_records)} payment history records with null subscription_id")
            
            # Handle these records - either delete them or create default subscriptions
            for payment in payment_records:
                # Option 1: Delete invalid payment records (if they're not needed)
                logger.info(f"Deleting payment history record {payment.id} with null subscription_id")
                db.session.delete(payment)
            
            # Commit these changes before proceeding
            db.session.commit()
            logger.info("Fixed payment history records with null subscription_id")
        else:
            logger.info("No payment history records with null subscription_id found")
        
        # Now proceed with fixing user-subscription relationships
        subscriptions = Subscription.query.all()
        logger.info(f"Found {len(subscriptions)} subscriptions to check")
        
        fixed_count = 0
        for subscription in subscriptions:
            user_id = subscription.user_id
            user = User.query.get(user_id)
            
            if not user:
                logger.warning(f"Subscription {subscription.id} has no matching user with ID {user_id}")
                continue
                
            # Check if the user's subscription relationship is broken
            if not user.subscription or user.subscription.id != subscription.id:
                logger.info(f"Fixing user {user_id} relationship with subscription {subscription.id}")
                user.subscription = subscription
                fixed_count += 1
        
        if fixed_count > 0:
            logger.info(f"Fixed {fixed_count} broken user-subscription relationships")
            db.session.commit()
        else:
            logger.info("No broken user-subscription relationships found")
            
        # Now check for any users with active subscriptions in the backend that might not be reflected in database
        for user in User.query.all():
            # Skip users that already have a subscription
            if user.subscription:
                continue
                
            # Check if there are any subscriptions for this user
            subscription = Subscription.query.filter_by(user_id=user.id).first()
            if subscription:
                logger.info(f"Found subscription {subscription.id} for user {user.id} - linking them")
                user.subscription = subscription
                db.session.commit()
                fixed_count += 1
        
        if fixed_count > 0:
            logger.info(f"Fixed {fixed_count} total broken relationships")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing user-subscription relationships: {str(e)}")
        db.session.rollback()
        return False 