"""
Migration Tracker

This module tracks which migrations have been applied to avoid running them
on every application startup.
"""
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the path to the migration tracker file
TRACKER_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'migrations_applied.json')

def ensure_tracker_file():
    """Ensure the tracker file exists"""
    # Make sure the instance directory exists
    instance_dir = os.path.dirname(TRACKER_FILE)
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    # Create the tracker file if it doesn't exist
    if not os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'w') as f:
            json.dump({}, f)

def is_migration_applied(migration_name):
    """Check if a migration has been applied"""
    ensure_tracker_file()
    
    try:
        with open(TRACKER_FILE, 'r') as f:
            applied_migrations = json.load(f)
            return applied_migrations.get(migration_name, False)
    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")
        return False

def mark_migration_applied(migration_name):
    """Mark a migration as applied"""
    ensure_tracker_file()
    
    try:
        # Read current migrations
        with open(TRACKER_FILE, 'r') as f:
            applied_migrations = json.load(f)
        
        # Update with new migration
        applied_migrations[migration_name] = True
        
        # Write back to file
        with open(TRACKER_FILE, 'w') as f:
            json.dump(applied_migrations, f)
            
        logger.info(f"Migration {migration_name} marked as applied")
        return True
    except Exception as e:
        logger.error(f"Error marking migration as applied: {str(e)}")
        return False 