"""
Migration to fix the subscription foreign key constraint.
This adds ON DELETE CASCADE to the subscription_user_id_fkey constraint.
"""
import logging
from sqlalchemy import create_engine, text, inspect
from xavier_back.config import Config

logger = logging.getLogger(__name__)

def run():
    """Run the migration to fix subscription foreign key constraint"""
    logger.info("Starting migration to fix subscription foreign key constraint")
    
    try:
        # Create database engine
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        # Check if we're using SQLite
        is_sqlite = 'sqlite' in Config.SQLALCHEMY_DATABASE_URI.lower()
        
        with engine.connect() as connection:
            if is_sqlite:
                # SQLite approach: recreate the table with the new constraint
                # First, get current data
                result = connection.execute(text("SELECT * FROM subscription"))
                subscriptions = [dict(row) for row in result.mappings()]
                
                # Create a temporary table with the correct constraint
                connection.execute(text("""
                    CREATE TABLE subscription_new (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
                        plan_id INTEGER NOT NULL REFERENCES plan(id),
                        status TEXT NOT NULL,
                        start_date TIMESTAMP NOT NULL,
                        end_date TIMESTAMP,
                        trial_end TIMESTAMP,
                        billing_cycle TEXT NOT NULL,
                        payment_method TEXT,
                        stripe_customer_id TEXT,
                        stripe_subscription_id TEXT,
                        payment_method_id TEXT,
                        paypal_subscription_id TEXT,
                        paypal_order_id TEXT,
                        paystack_reference TEXT,
                        lemon_squeezy_order_id TEXT,
                        lemon_squeezy_customer_id TEXT,
                        lemon_squeezy_subscription_id TEXT,
                        cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))
                
                # Copy data from old table to new table
                for sub in subscriptions:
                    # Build the insert statement dynamically
                    columns = ', '.join(sub.keys())
                    placeholders = ', '.join([':' + k for k in sub.keys()])
                    insert_sql = f"INSERT INTO subscription_new ({columns}) VALUES ({placeholders})"
                    connection.execute(text(insert_sql), sub)
                
                # Drop old table and rename new table
                connection.execute(text("DROP TABLE subscription"))
                connection.execute(text("ALTER TABLE subscription_new RENAME TO subscription"))
                
                logger.info("Successfully recreated subscription table with ON DELETE CASCADE in SQLite")
            else:
                # PostgreSQL approach: modify the constraint directly
                connection.execute(text("""
                    ALTER TABLE subscription 
                    DROP CONSTRAINT IF EXISTS subscription_user_id_fkey;
                """))
                
                connection.execute(text("""
                    ALTER TABLE subscription 
                    ADD CONSTRAINT subscription_user_id_fkey 
                    FOREIGN KEY (user_id) 
                    REFERENCES "user" (id) 
                    ON DELETE CASCADE;
                """))
                
                logger.info("Successfully modified foreign key constraint in PostgreSQL")
            
            # Commit the transaction
            connection.commit()
        
        logger.info("Successfully fixed subscription foreign key constraint")
        return True
    except Exception as e:
        logger.error(f"Error fixing subscription foreign key constraint: {str(e)}")
        return False

if __name__ == "__main__":
    run() 