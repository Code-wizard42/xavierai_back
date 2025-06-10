"""
Migration script to add PayPal-related columns to the subscription table.
"""
import logging
from sqlalchemy import Column, String
from sqlalchemy.sql import text
from xavier_back.extensions import db

logger = logging.getLogger(__name__)

def run_migration():
    """
    Add PayPal-related columns to the subscription table if they don't exist.
    """
    logger.info("Running migration to add PayPal columns to subscription table")
    
    # Check if columns already exist to avoid errors
    inspector = db.inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('subscription')]
    
    columns_to_add = {
        'paypal_subscription_id': 'VARCHAR(100)',
        'paypal_order_id': 'VARCHAR(100)'
    }
    
    # Add missing columns
    for column_name, column_type in columns_to_add.items():
        if column_name not in existing_columns:
            logger.info(f"Adding column {column_name} to subscription table")
            
            # Using raw SQL for flexibility
            sql = f"ALTER TABLE subscription ADD COLUMN {column_name} {column_type}"
            try:
                db.session.execute(text(sql))
                logger.info(f"Column {column_name} added successfully")
            except Exception as e:
                logger.error(f"Error adding column {column_name}: {str(e)}")
                db.session.rollback()
                raise
    
    # Commit the transaction
    db.session.commit()
    logger.info("PayPal columns migration completed successfully") 