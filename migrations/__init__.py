"""
Migrations package initialization.
"""
import logging
from . import fix_subscription_foreign_key

logger = logging.getLogger(__name__)

def run_migrations():
    """Run all migrations"""
    # Run the subscription foreign key fix
    fix_subscription_foreign_key.run()
    
    logger.info("Database migrations completed") 