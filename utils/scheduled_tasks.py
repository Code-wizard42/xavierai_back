"""
Scheduled Tasks Module

This module contains scheduled tasks that run on a regular basis.
"""
import logging
from datetime import datetime, timezone
from flask import current_app

# Configure logging
logger = logging.getLogger(__name__)

def run_daily_tasks():
    """Run daily scheduled tasks"""
    logger.info("Running daily scheduled tasks")
    
    # Check for subscription renewals
    check_subscription_renewals()
    
    # Add other daily tasks here
    
    logger.info("Completed daily scheduled tasks")

def check_subscription_renewals():
    """Check for subscription renewals and send reminders"""
    try:
        logger.info("Checking for subscription renewals")
        
        # Import here to avoid circular imports
        from services.subscription_service import SubscriptionService
        
        # We need to ensure we're in an application context
        try:
            # Get the default days before renewal for reminders
            # Default to 7, 3, and 1 days before renewal
            days_before = current_app.config.get('RENEWAL_REMINDER_DAYS', [7, 3, 1])
            
            # Schedule renewal reminders
            reminders_sent, errors = SubscriptionService.schedule_renewal_reminders(days_before_renewal=days_before)
            
            logger.info(f"Sent {reminders_sent} renewal reminders with {len(errors)} errors")
            
            # Log errors if any
            for error in errors:
                logger.error(f"Error sending renewal reminder: {error}")
                
            return True
        except RuntimeError as e:
            # This error occurs when working outside app context
            if "Working outside of application context" in str(e):
                logger.error("Attempted to run scheduled task outside application context. This should be fixed by wrapping tasks in app_context().")
                return False
            raise
    except Exception as e:
        logger.error(f"Error checking subscription renewals: {str(e)}")
        return False 