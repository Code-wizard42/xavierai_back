"""
Migration script to update payment_history table by making subscription_id nullable and adding user_id.
"""
import logging
from sqlalchemy.sql import text
from xavier_back.extensions import db
from xavier_back.models import User, Subscription, PaymentHistory

logger = logging.getLogger(__name__)

def run_migration():
    """
    Update payment_history table to make subscription_id nullable and add user_id column.
    """
    logger.info("Running migration to update payment_history table")
    
    try:
        # Check if columns already exist to avoid errors
        inspector = db.inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('payment_history')]
        
        # Step 1: Make subscription_id nullable
        logger.info("Making subscription_id column nullable in payment_history table")
        try:
            db.session.execute(text("ALTER TABLE payment_history ALTER COLUMN subscription_id DROP NOT NULL"))
            db.session.commit()
            logger.info("Successfully made subscription_id nullable")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error making subscription_id nullable: {str(e)}")
            
        # Step 2: Add user_id column if it doesn't exist
        if 'user_id' not in existing_columns:
            logger.info("Adding user_id column to payment_history table")
            try:
                db.session.execute(text("ALTER TABLE payment_history ADD COLUMN user_id INTEGER REFERENCES \"user\"(id)"))
                db.session.commit()
                logger.info("Successfully added user_id column")
                
                # Step 3: Populate user_id based on subscription's user_id for existing records
                logger.info("Populating user_id values for existing records")
                payment_records = PaymentHistory.query.filter(PaymentHistory.subscription_id.isnot(None)).all()
                
                update_count = 0
                for payment in payment_records:
                    if payment.subscription:
                        # Get the user_id from the subscription
                        user_id = payment.subscription.user_id
                        if user_id:
                            payment.user_id = user_id
                            update_count += 1
                
                if update_count > 0:
                    db.session.commit()
                    logger.info(f"Updated user_id for {update_count} payment records")
                
                # Step 4: Make user_id NOT NULL for future records
                logger.info("Making user_id column NOT NULL")
                db.session.execute(text("ALTER TABLE payment_history ALTER COLUMN user_id SET NOT NULL"))
                db.session.commit()
                logger.info("Successfully made user_id NOT NULL")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding/updating user_id column: {str(e)}")
        else:
            logger.info("user_id column already exists in payment_history table")
            
        # Step 5: Add other new columns
        columns_to_add = {
            'paypal_order_id': 'VARCHAR(100)',
            'paypal_transaction_id': 'VARCHAR(100)',
            'lemon_squeezy_order_id': 'VARCHAR(100)',
            'created_at': 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()',
            'updated_at': 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                logger.info(f"Adding {column_name} column to payment_history table")
                try:
                    db.session.execute(text(f"ALTER TABLE payment_history ADD COLUMN {column_name} {column_type}"))
                    db.session.commit()
                    logger.info(f"Successfully added {column_name} column")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error adding {column_name} column: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error updating payment_history table: {str(e)}")
        db.session.rollback()
        return False 