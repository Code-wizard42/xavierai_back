"""
Email Service Routes Module

This module contains route handlers for email-related operations.
It uses the service layer for business logic.
"""
from flask import Blueprint, request, jsonify, session, current_app
import logging
import os
from functools import wraps

from models import Ticket
from extensions import db
from services.email_service import EmailService
from utils.auth_utils import login_required

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Create blueprint
email_bp = Blueprint('email', __name__)

def handle_errors(f):
    """Decorator to handle errors in route handlers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error: {str(e)}")
            return jsonify({"error": str(e)}), 500
    return decorated_function

@email_bp.route('/send-email', methods=['POST'])
@login_required
@handle_errors
def send_email():
    """
    Send an email using Resend API
    Required fields in request body:
    - to_email: Recipient email address
    - subject: Email subject
    - html_content: Email body in HTML format
    - from_email (optional): Sender email address
    - reply_to (optional): Reply-to email address
    """
    data = request.json

    # Validate required fields
    if not all(k in data for k in ['to_email', 'subject', 'html_content']):
        return jsonify({"error": "Missing required fields: to_email, subject, html_content"}), 400

    # Initialize Resend if not already initialized
    EmailService.initialize_resend()

    # Send the email using the service
    success, email_id, error = EmailService.send_email(
        to=data['to_email'],
        subject=data['subject'],
        html_content=data['html_content'],
        from_email=data.get('from_email'),
        reply_to=data.get('reply_to')
    )

    if not success:
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Email sent successfully",
        "email_id": email_id
    }), 200

@email_bp.route('/send-ticket-email/<ticket_id>', methods=['POST'])
@login_required
@handle_errors
def send_ticket_email(ticket_id):
    """
    Send an email about a specific ticket
    Required fields in request body:
    - to_email: Recipient email address
    - from_email (optional): Sender email address
    - reply_to (optional): Reply-to email address
    - subject (optional): Custom email subject
    - html_content (optional): Custom email content
    """
    data = request.json

    # Validate required fields
    if 'to_email' not in data:
        return jsonify({"error": "Missing required field: to_email"}), 400

    # Get ticket details
    ticket = Ticket.query.get_or_404(ticket_id)

    # Check if custom content is provided
    if 'html_content' in data and data['html_content'].strip():
        # Send custom email
        success, email_id, error = EmailService.send_email(
            to=data['to_email'],
            subject=data.get('subject', f"Re: Ticket #{ticket.id} - {ticket.subject}"),
            html_content=data['html_content'],
            from_email=data.get('from_email'),
            reply_to=data.get('reply_to')
        )
    else:
        # Format ticket data for the default template
        ticket_data = {
            'id': ticket.id,
            'subject': ticket.subject,
            'description': ticket.description,
            'priority': ticket.priority,
            'status': ticket.status,
            'created_at': ticket.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'contact_email': data.get('reply_to')
        }

        # Send the ticket notification using the service
        success, error = EmailService.send_ticket_notification(
            ticket_data=ticket_data,
            to_email=data['to_email']
        )
        email_id = None

    if not success:
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Ticket email sent successfully",
        "email_id": email_id
    }), 200

@email_bp.route('/send-lead-email', methods=['POST'])
@login_required
@handle_errors
def send_lead_email():
    """
    Send an email about a lead
    Required fields in request body:
    - to_email: Recipient email address
    - lead_data: Lead data (name, email, phone, message, created_at)
    """
    data = request.json

    # Validate required fields
    if not all(k in data for k in ['to_email', 'lead_data']):
        return jsonify({"error": "Missing required fields: to_email, lead_data"}), 400

    lead_data = data['lead_data']
    if not all(k in lead_data for k in ['name', 'email']):
        return jsonify({"error": "Missing required lead data: name, email"}), 400

    # Send the lead notification using the service
    success, error = EmailService.send_lead_notification(
        lead_data=lead_data,
        to_email=data['to_email']
    )

    if not success:
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Lead email sent successfully"
    }), 200

def generate_ticket_email_content(ticket):
    """Generate HTML content for ticket email"""
    status_color = {
        'open': '#3b82f6',  # blue
        'in_progress': '#8b5cf6',  # purple
        'resolved': '#10b981',  # green
        'closed': '#6b7280'  # gray
    }

    priority_color = {
        'high': '#ef4444',  # red
        'medium': '#f59e0b',  # yellow
        'low': '#10b981'  # green
    }

    ticket_status = ticket.status.lower()
    ticket_priority = ticket.priority.lower()

    status_bg_color = status_color.get(ticket_status, '#6b7280')
    priority_bg_color = priority_color.get(ticket_priority, '#6b7280')

    # Format created_at date
    created_at = ticket.created_at.strftime('%B %d, %Y at %I:%M %p')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ margin-bottom: 20px; }}
            .ticket-info {{ margin-bottom: 30px; }}
            .badge {{ display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; margin-right: 10px; }}
            .status {{ background-color: {status_bg_color}; }}
            .priority {{ background-color: {priority_bg_color}; }}
            .details {{ background-color: #f9fafb; padding: 15px; border-radius: 5px; margin-top: 20px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #6b7280; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Ticket #{ticket.id}: {ticket.subject}</h2>
            </div>

            <div class="ticket-info">
                <p>
                    <span class="badge status">{ticket.status.title()}</span>
                    <span class="badge priority">{ticket.priority.title()}</span>
                </p>
                <p><strong>Created:</strong> {created_at}</p>

                <div class="details">
                    <h3>Description</h3>
                    <p>{ticket.description}</p>

                    <h3>Account Details</h3>
                    <p>{ticket.account_details if hasattr(ticket, 'account_details') else 'No account details provided'}</p>
                </div>
            </div>

            <div class="footer">
                <p>This is an automated message regarding your support ticket. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html
