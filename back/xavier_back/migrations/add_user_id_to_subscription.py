"""
Migration script to add user_id column to subscription table and fix relationships.
"""
import logging
from xavier_back import create_app
from xavier_back.extensions import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

def add_user_id_to_subscription():
    """Add user_id column to subscription table if it doesn't exist"""
    try:
        # Create application context
        app = create_app()
        with app.app_context():
            # Check if column already exists
            result = db.session.execute(text("PRAGMA table_info(subscription)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'user_id' not in columns:
                logger.info("Adding user_id column to subscription table")
                db.session.execute(text("ALTER TABLE subscription ADD COLUMN user_id INTEGER REFERENCES user(id)"))
                db.session.commit()
                logger.info("Added user_id column to subscription table")
            else:
                logger.info("user_id column already exists in subscription table")
                
            # Now, try to fix the relationships by linking subscriptions to users
            logger.info("Fixing user-subscription relationships")
            
            # Get all users with subscriptions
            result = db.session.execute(text("""
                SELECT u.id AS user_id, s.id AS subscription_id 
                FROM user u 
                JOIN subscription s ON s.user_id IS NULL
            """)).fetchall()
            
            for row in result:
                user_id = row[0]
                subscription_id = row[1]
                logger.info(f"Linking subscription {subscription_id} to user {user_id}")
                
                # Update the subscription with the user ID
                db.session.execute(text(f"UPDATE subscription SET user_id = {user_id} WHERE id = {subscription_id}"))
            
            db.session.commit()
            logger.info("Fixed user-subscription relationships")
            
            return True
    except Exception as e:
        logger.error(f"Error adding user_id to subscription: {str(e)}")
        return False

if __name__ == "__main__":
    add_user_id_to_subscription() 