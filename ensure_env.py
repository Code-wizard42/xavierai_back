"""
Ensure environment script for Xavier AI.
This script checks and sets up the necessary environment for the application to run.
"""

import os
import logging
import sys
import json
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist."""
    dirs_to_create = [
        'uploads',
        'logs',
        'flask_session',
        'instance'
    ]
    
    for dir_path in dirs_to_create:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"Created directory: {dir_path}")

def ensure_fallback_env_vars():
    """Ensure fallback environment variables are set."""
    env_vars = {
        'USE_FALLBACK_EMBEDDINGS': 'true',
        'USE_LOCAL_LLM': 'true',
        'UPLOAD_FOLDER': 'uploads',
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': 'flask_session'
    }
    
    for key, value in env_vars.items():
        if not os.environ.get(key):
            os.environ[key] = value
            logger.info(f"Set environment variable: {key}={value}")

def ensure_vector_db_directories():
    """Create vector database directories."""
    vector_db_dir = 'vector_db'
    if not os.path.exists(vector_db_dir):
        os.makedirs(vector_db_dir)
        logger.info(f"Created vector database directory: {vector_db_dir}")
        
    # Create an empty collection info file if it doesn't exist
    collection_info_path = os.path.join(vector_db_dir, 'collections.json')
    if not os.path.exists(collection_info_path):
        with open(collection_info_path, 'w') as f:
            json.dump({}, f)
        logger.info(f"Created empty collections info file: {collection_info_path}")

def check_database():
    """Check if database file exists in instance directory."""
    instance_dir = 'instance'
    db_file = os.path.join(instance_dir, 'xavier.db')
    
    if not os.path.exists(db_file):
        logger.warning(f"Database file not found: {db_file}")
        logger.info("A new database will be created on application startup")
    else:
        logger.info(f"Database file found: {db_file}")

def run_all_checks():
    """Run all environment checks."""
    logger.info("Running environment checks...")
    
    # Check and create directories
    ensure_directories()
    
    # Ensure fallback environment variables
    ensure_fallback_env_vars()
    
    # Ensure vector database setup
    ensure_vector_db_directories()
    
    # Check database
    check_database()
    
    logger.info("Environment checks completed successfully")

if __name__ == "__main__":
    run_all_checks() 