"""
Migration script to add Flutterwave columns to the Subscription model
"""

import logging
from sqlalchemy import Column, String
from sqlalchemy.sql import text
from extensions import db

logger = logging.getLogger(__name__)

def run_migration():
    """
    Add Flutterwave columns to the subscription table
    """
    try:
        # Check if the columns already exist
        columns_exist = False
        with db.engine.connect() as connection:
            # Check if flutterwave_transaction_id column exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='subscription' AND column_name='flutterwave_transaction_id'
            """))
            columns_exist = result.rowcount > 0

        if columns_exist:
            logger.info("Flutterwave columns already exist in subscription table")
            return True

        # Add the columns using SQLAlchemy's alter_column
        with db.engine.connect() as connection:
            connection.execute(text("""
                ALTER TABLE subscription
                ADD COLUMN flutterwave_transaction_id VARCHAR(100),
                ADD COLUMN flutterwave_customer_id VARCHAR(100),
                ADD COLUMN flutterwave_payment_id VARCHAR(100)
            """))
            logger.info("Added Flutterwave columns to subscription table")
        
        return True
    except Exception as e:
        logger.error(f"Error adding Flutterwave columns: {e}")
        return False 