from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from flask_apscheduler import APScheduler
import logging

# Configure logging
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
scheduler = APScheduler()
# mongo_client = MongoClient('mongodb://localhost:27017/')
# mongo_db = mongo_client['your_database_name']
# inventory_collection = mongo_db['inventory']

def init_db(app):
    # Configure SQLAlchemy pool settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,  # Increased for handling multiple streams
        'pool_timeout': 30,
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
        'max_overflow': 40,
        'pool_pre_ping': True
    }
    
    db.init_app(app)
    migrate.init_app(app, db)
    
def init_scheduler(app):
    """Initialize the APScheduler with the Flask app and configure jobs"""
    # Basic scheduler configuration
    app.config['SCHEDULER_API_ENABLED'] = False
    app.config['SCHEDULER_TIMEZONE'] = 'UTC'
    
    # Initialize scheduler with app
    scheduler.init_app(app)
    
    # Add scheduled tasks
    from xavier_back.utils.scheduled_tasks import run_daily_tasks
    
    # Wrap the daily tasks with app context
    def run_daily_tasks_with_context():
        """Wrapper function to ensure task runs within app context"""
        logger.info("Running scheduled daily tasks with app context")
        with app.app_context():
            try:
                run_daily_tasks()
            except Exception as e:
                logger.error(f"Error in scheduled task: {str(e)}")
    
    # Add a daily job to run at 1:00 AM UTC
    scheduler.add_job(
        id='daily_tasks',
        func=run_daily_tasks_with_context,  # Use the wrapped function
        trigger='cron', 
        hour=1,  # 1 AM
        minute=0,  # 00 minutes
        misfire_grace_time=3600  # Allow tasks to run up to an hour late
    )
    
    # Start the scheduler
    scheduler.start()
