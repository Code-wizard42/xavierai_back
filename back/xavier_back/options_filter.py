import logging

# Configure logging to filter out OPTIONS requests
log = logging.getLogger('werkzeug')

# Define a filter to ignore OPTIONS requests
class OptionsRequestFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        # Filter out OPTIONS requests
        if 'OPTIONS' in message and '200' in message:
            return False
        return True

# Apply the filter
log.addFilter(OptionsRequestFilter())
