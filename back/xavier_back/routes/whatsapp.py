"""
WhatsApp Integration Module

This module handles the integration with WhatsApp via Twilio API.
It provides routes for receiving and sending WhatsApp messages.
"""
from flask import Blueprint, request, jsonify, current_app
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import json
import uuid
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import Chatbot, ConversationMessage
from xavier_back.services.chatbot_service import ChatbotService
from xavier_back.services.subscription_service import SubscriptionService

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
whatsapp_bp = Blueprint('whatsapp', __name__)

def get_twilio_client():
    """
    Initialize and return a Twilio client using credentials from environment variables
    """
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

    if not account_sid or not auth_token:
        logger.error("Twilio credentials not found in environment variables")
        return None

    return Client(account_sid, auth_token)

@whatsapp_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint for receiving WhatsApp messages via Twilio
    """
    try:
        # Get the message content
        incoming_msg = request.values.get('Body', '').strip()
        sender_phone = request.values.get('From', '')

        if not sender_phone:
            logger.error("No sender phone number provided in webhook request")
            resp = MessagingResponse()
            resp.message("Error: Missing sender information")
            return str(resp)

        # Clean up the sender phone number (remove 'whatsapp:' prefix if present)
        if sender_phone.startswith('whatsapp:'):
            clean_phone = sender_phone[9:]  # Remove 'whatsapp:' prefix
        else:
            clean_phone = sender_phone

        # Import WhatsAppIntegration model
        from xavier_back.models.whatsapp import WhatsAppIntegration

        # Look up the chatbot ID based on the WhatsApp number
        whatsapp_integration = WhatsAppIntegration.query.filter_by(
            whatsapp_number=clean_phone,
            is_active=True
        ).first()

        if not whatsapp_integration:
            logger.error(f"No active WhatsApp integration found for number: {clean_phone}")
            resp = MessagingResponse()
            resp.message("Sorry, this WhatsApp number is not linked to a chatbot.")
            return str(resp)

        chatbot_id = whatsapp_integration.chatbot_id

        # Check subscription status for the chatbot owner
        chatbot = ChatbotService.get_chatbot(chatbot_id)
        if chatbot and chatbot.user_id:
            subscription_data = SubscriptionService.get_user_subscription(chatbot.user_id)
            if not subscription_data or not subscription_data.get('is_active'):
                logger.warning(f"WhatsApp message blocked for chatbot {chatbot_id} - subscription expired")
                resp = MessagingResponse()
                resp.message("This service is temporarily unavailable. Please contact the business owner.")
                return str(resp)

            # Check for billing overdue
            from xavier_back.models import User
            user = User.query.get(chatbot.user_id)
            if user and user.subscription and user.subscription.is_billing_overdue():
                logger.warning(f"WhatsApp message blocked for chatbot {chatbot_id} - billing overdue")
                resp = MessagingResponse()
                resp.message("This service is temporarily unavailable due to billing issues. Please contact the business owner.")
                return str(resp)

        # Generate a conversation ID if not present
        conversation_id = request.values.get('conversation_id', str(uuid.uuid4()))

        # Process the message using the existing chatbot service
        result = ChatbotService.get_answer(chatbot_id, incoming_msg, conversation_id)

        # Create a Twilio response
        resp = MessagingResponse()

        if 'error' in result:
            resp.message("Sorry, I encountered an error while processing your request.")
            logger.error(f"Error processing WhatsApp message: {result['error']}")
        else:
            # Add the answer to the response
            resp.message(result['answer'])

        return str(resp)

    except Exception as e:
        logger.error(f"Error in WhatsApp webhook: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an unexpected error.")
        return str(resp)

@whatsapp_bp.route('/send', methods=['POST'])
def send_message():
    """
    Endpoint for sending WhatsApp messages via Twilio API
    """
    try:
        data = request.json

        if not all(k in data for k in ['to', 'message', 'chatbot_id']):
            return jsonify({"error": "Missing required fields"}), 400

        # Get Twilio client
        client = get_twilio_client()
        if not client:
            return jsonify({"error": "Twilio client initialization failed"}), 500

        # Get the WhatsApp number from environment variables
        whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
        if not whatsapp_number:
            return jsonify({"error": "WhatsApp number not configured"}), 500

        # Format the 'to' number for WhatsApp
        to_number = data['to']
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"

        # Format the 'from' number for WhatsApp
        from_number = f"whatsapp:{whatsapp_number}"

        # Send the message
        message = client.messages.create(
            body=data['message'],
            from_=from_number,
            to=to_number
        )

        # Store the message in the conversation history
        try:
            new_message = ConversationMessage(
                conversation_id=data.get('conversation_id', str(uuid.uuid4())),
                chatbot_id=data['chatbot_id'],
                message='',  # This is a bot-initiated message
                response=data['message'],
                timestamp=datetime.utcnow()
            )
            db.session.add(new_message)
            db.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error storing WhatsApp message: {str(e)}")
            db.session.rollback()
            # Continue even if storing fails

        return jsonify({
            "success": True,
            "message_sid": message.sid,
            "status": message.status
        })

    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}")
        return jsonify({"error": str(e)}), 500

@whatsapp_bp.route('/status', methods=['GET'])
def check_status():
    """
    Check the status of the WhatsApp integration
    """
    try:
        # Check if Twilio credentials are configured
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')

        if not account_sid or not auth_token or not whatsapp_number:
            return jsonify({
                "status": "not_configured",
                "message": "WhatsApp integration is not fully configured"
            })

        # Try to initialize the Twilio client
        client = get_twilio_client()
        if not client:
            return jsonify({
                "status": "error",
                "message": "Failed to initialize Twilio client"
            })

        # Check if the WhatsApp number is valid
        try:
            # Just fetch the account info to verify credentials
            account = client.api.accounts(account_sid).fetch()
            return jsonify({
                "status": "active",
                "message": "WhatsApp integration is active",
                "whatsapp_number": whatsapp_number,
                "account_status": account.status
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error verifying Twilio account: {str(e)}"
            })

    except Exception as e:
        logger.error(f"Error checking WhatsApp status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        })
