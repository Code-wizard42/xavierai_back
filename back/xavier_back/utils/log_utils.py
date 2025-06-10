"""
Utility functions for standardized logging across the application.
This module provides simplified logging functions to ensure consistency.
"""
import logging

def get_logger(name):
    """
    Get a logger with standardized format and level.
    
    Args:
        name: Name of the logger (typically __name__)
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    # If handlers are already configured, just return the logger
    if logger.handlers:
        return logger
        
    # Configure a simple console handler if none exists
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)
    
    return logger

def log_operation(logger, operation, status="success", details=None):
    """
    Log an operation with a standardized format.
    
    Args:
        logger: The logger instance
        operation: The operation being performed (e.g., "user_login", "subscription_update")
        status: "success" or "failed"
        details: Optional dictionary of additional details
    """
    msg = f"{operation} {status}"
    if details:
        # Format details as a simple string
        details_str = ", ".join(f"{k}={v}" for k, v in details.items())
        msg += f" - {details_str}"
        
    if status == "success":
        logger.info(msg)
    else:
        logger.error(msg)

def log_api_request(logger, path, status_code, user_id=None, duration=None):
    """
    Log an API request with minimal necessary information.
    
    Args:
        logger: The logger instance
        path: The request path
        status_code: HTTP status code
        user_id: Optional user ID
        duration: Optional request duration in seconds
    """
    msg = f"API {path} {status_code}"
    
    if user_id:
        msg += f" user={user_id}"
        
    if duration:
        msg += f" time={duration:.2f}s"
        
    # Only log as warning if it's an error or slow request
    if status_code >= 400 or (duration and duration > 3):
        logger.warning(msg)
    elif status_code >= 300:
        logger.info(msg) 