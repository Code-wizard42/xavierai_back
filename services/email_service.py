"""
Email Service Module

This module contains business logic for email operations, separating it from the route handlers.
"""
import logging
import os
from typing import Dict, List, Any, Optional, Tuple

import resend
from flask import current_app

logger = logging.getLogger(__name__)

class EmailService:
    """Service class for email-related operations"""

    @staticmethod
    def initialize_resend():
        """Initialize the Resend API client"""
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            logger.warning("RESEND_API_KEY not found in environment variables")
            return False

        try:
            resend.api_key = api_key
            return True
        except Exception as e:
            logger.error(f"Error initializing Resend: {str(e)}")
            return False

    @staticmethod
    def send_email(to: str, subject: str, html_content: str,
                  from_email: Optional[str] = None, reply_to: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send an email using Resend

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            from_email: Optional sender email (defaults to configured default)
            reply_to: Optional reply-to email

        Returns:
            Tuple containing (success, email_id, error_message)
        """
        try:
            # Initialize Resend if not already initialized
            if not hasattr(resend, 'api_key') or not resend.api_key:
                EmailService.initialize_resend()

            # Set default from_email if not provided
            if not from_email:
                from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'Xavier AI <onboarding@xavierai.site>')

            # Ensure from_email has proper format "Name <email@domain.com>"
            if from_email and '@' in from_email and '<' not in from_email:
                # If it's just an email without a name, add a default name
                from_email = f"Xavier AI <{from_email}>"

            # Log the from_email for debugging
            logger.info(f"Sending email with from_email: {from_email}")

            # Prepare email parameters
            params = {
                'from': from_email,
                'to': to,
                'subject': subject,
                'html': html_content
            }

            # Add reply_to if provided
            if reply_to:
                params['reply_to'] = reply_to

            # Send the email
            response = resend.Emails.send(params)

            if response and 'id' in response:
                return True, response['id'], None
            else:
                return False, None, "No email ID returned from Resend"
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    @staticmethod
    def get_user_notification_email(user_id: int) -> Optional[str]:
        """
        Get the user's preferred notification email address

        Args:
            user_id: The user ID

        Returns:
            The user's preferred notification email or None if not found
        """
        try:
            # First check if the user has notification preferences
            from models import User, NotificationPreference

            # Check if the user has notification preferences
            pref = NotificationPreference.query.filter_by(user_id=user_id).first()
            if pref and pref.notification_email:
                logger.info(f"Using notification email from preferences: {pref.notification_email}")
                return pref.notification_email

            # If no preferences or no notification email set, fall back to user's email
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"User {user_id} not found when getting notification email")
                return None

            # Return the user's email as a fallback
            logger.info(f"Using user's email as fallback: {user.email}")
            return user.email
        except Exception as e:
            logger.error(f"Error getting user notification email: {str(e)}")
            return None

    @staticmethod
    def send_ticket_notification(ticket_data: Dict[str, Any], to_email: str) -> Tuple[bool, Optional[str]]:
        """
        Send a notification email for a new ticket

        Args:
            ticket_data: Dictionary with ticket data
            to_email: Recipient email address

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            # Check if we should use a different notification email
            user_id = ticket_data.get('user_id')
            if user_id:
                notification_email = EmailService.get_user_notification_email(user_id)
                if notification_email:
                    to_email = notification_email
                    logger.info(f"Using user's notification email: {to_email}")

            subject = f"New Support Ticket: {ticket_data.get('subject', 'No Subject')}"

            # Create HTML content
            description = ticket_data.get('description', 'No description provided.').replace('\n', '<br>')
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #0066CC;">New Support Ticket</h2>
                <p>A new support ticket has been created:</p>

                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Subject:</strong> {ticket_data.get('subject', 'N/A')}</p>
                    <p><strong>Priority:</strong> {ticket_data.get('priority', 'medium').capitalize()}</p>
                    <p><strong>Status:</strong> {ticket_data.get('status', 'open').capitalize()}</p>
                    <p><strong>Created:</strong> {ticket_data.get('created_at', 'N/A')}</p>
                </div>

                <div style="margin: 20px 0;">
                    <h3>Description:</h3>
                    <p>{description}</p>
                </div>

                <p>Please log in to the system to respond to this ticket.</p>

                <div style="margin-top: 30px; font-size: 12px; color: #666;">
                    <p>This is an automated message from the Xavier AI support system.</p>
                </div>
            </div>
            """

            # Send the email
            success, email_id, error = EmailService.send_email(
                to=to_email,
                subject=subject,
                html_content=html_content,
                reply_to=ticket_data.get('contact_email')
            )

            if not success:
                return False, error

            return True, None
        except Exception as e:
            error_msg = f"Error sending ticket notification: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def send_lead_notification(lead_data: Dict[str, Any], to_email: str) -> Tuple[bool, Optional[str]]:
        """
        Send a notification email for a new lead

        Args:
            lead_data: Dictionary with lead data
            to_email: Recipient email address

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            # Check if we should use a different notification email
            user_id = lead_data.get('user_id')
            if user_id:
                notification_email = EmailService.get_user_notification_email(user_id)
                if notification_email:
                    to_email = notification_email
                    logger.info(f"Using user's notification email for lead: {to_email}")

            subject = f"New Lead: {lead_data.get('name', 'No Name')}"

            # Create HTML content
            message = lead_data.get('message', 'No message provided.').replace('\n', '<br>')
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #0066CC;">New Lead</h2>
                <p>A new lead has been captured from your chatbot:</p>

                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Name:</strong> {lead_data.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {lead_data.get('email', 'N/A')}</p>
                    <p><strong>Phone:</strong> {lead_data.get('phone', 'N/A')}</p>
                    <p><strong>Created:</strong> {lead_data.get('created_at', 'N/A')}</p>
                </div>

                <div style="margin: 20px 0;">
                    <h3>Message:</h3>
                    <p>{message}</p>
                </div>

                <p>Please log in to the system to follow up with this lead.</p>

                <div style="margin-top: 30px; font-size: 12px; color: #666;">
                    <p>This is an automated message from the Xavier AI lead management system.</p>
                </div>
            </div>
            """

            # Send the email
            success, email_id, error = EmailService.send_email(
                to=to_email,
                subject=subject,
                html_content=html_content,
                reply_to=lead_data.get('email')
            )

            if not success:
                return False, error

            return True, None
        except Exception as e:
            error_msg = f"Error sending lead notification: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
