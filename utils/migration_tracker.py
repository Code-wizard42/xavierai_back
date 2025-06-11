"""
Migration Tracker

This module tracks which migrations have been applied to avoid running them
on every application startup.
"""
import os
import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the path to the migration tracker file
# Use /tmp for production environments, local instance for development
def get_tracker_file_path():
    """Get the appropriate path for the tracker file based on environment"""
    if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('ENVIRONMENT') == 'production':
        # Production: use temp directory
        return os.path.join(tempfile.gettempdir(), 'migrations_applied.json')
    else:
        # Development: use local instance directory
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'migrations_applied.json')

TRACKER_FILE = get_tracker_file_path()

def ensure_tracker_file():
    """Ensure the tracker file exists"""
    try:
        # Make sure the directory exists
        instance_dir = os.path.dirname(TRACKER_FILE)
        if not os.path.exists(instance_dir):
            os.makedirs(instance_dir, exist_ok=True)
        
        # Create the tracker file if it doesn't exist
        if not os.path.exists(TRACKER_FILE):
            with open(TRACKER_FILE, 'w') as f:
                json.dump({}, f)
    except PermissionError:
        logger.warning(f"Cannot create tracker file at {TRACKER_FILE}, using in-memory tracking")
        # Fallback to in-memory tracking if file system is not writable
        return False
    except Exception as e:
        logger.error(f"Error creating tracker file: {str(e)}")
        return False
    return True

# In-memory fallback for read-only file systems
_memory_tracker = {}

def is_migration_applied(migration_name):
    """Check if a migration has been applied"""
    if not ensure_tracker_file():
        # Use in-memory tracking
        return _memory_tracker.get(migration_name, False)
    
    try:
        with open(TRACKER_FILE, 'r') as f:
            applied_migrations = json.load(f)
            return applied_migrations.get(migration_name, False)
    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")
        # Fallback to in-memory
        return _memory_tracker.get(migration_name, False)

def mark_migration_applied(migration_name):
    """Mark a migration as applied"""
    if not ensure_tracker_file():
        # Use in-memory tracking
        _memory_tracker[migration_name] = True
        logger.info(f"Migration {migration_name} marked as applied (in-memory)")
        return True
    
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
        # Fallback to in-memory
        _memory_tracker[migration_name] = True
        logger.info(f"Migration {migration_name} marked as applied (in-memory fallback)")
        return False 