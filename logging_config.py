import os
import logging
from logging.handlers import RotatingFileHandler

def configure_logging(app):
    """Configure logging for the application"""

    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Set up file handler for error logs
    error_file_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s [%(pathname)s:%(lineno)d]'
    ))

    # Set up file handler for info logs
    info_file_handler = RotatingFileHandler(
        'logs/info.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(info_file_handler)
    root_logger.addHandler(console_handler)

    # Configure app logger
    app.logger.setLevel(logging.INFO)

    # Set Werkzeug logger to ERROR level to suppress request logs
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.ERROR)
    
    # Suppress excessive SQL Alchemy logs
    sql_logger = logging.getLogger('sqlalchemy.engine')
    sql_logger.setLevel(logging.WARNING)
    
    # Reduce logging from other libraries
    for logger_name in ['urllib3', 'requests', 'chardet', 'werkzeug', 'flask']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Log application startup with minimal info
    app.logger.info('Xavier AI started')
