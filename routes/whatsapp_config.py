"""
WhatsApp Configuration Module

This module handles the configuration of WhatsApp integration via Twilio API.
It provides routes for saving and retrieving WhatsApp configuration.
"""
from flask import Blueprint, request, jsonify, current_app
import os
import json
import logging
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import Chatbot
from xavier_back.models.whatsapp import WhatsAppIntegration
from xavier_back.utils.auth_utils import login_required

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
whatsapp_config_bp = Blueprint('whatsapp_config', __name__)

@whatsapp_config_bp.route('/config', methods=['POST'])
@login_required
def save_config():
    """
    Save WhatsApp configuration

    This endpoint only requires the customer's WhatsApp number and the chatbot ID.
    The Twilio account credentials are stored in environment variables.
    """
    try:
        data = request.json

        if not all(k in data for k in ['whatsappNumber', 'chatbotId']):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate chatbot exists and belongs to the user
        chatbot = Chatbot.query.get(data['chatbotId'])
        if not chatbot:
            return jsonify({"error": "Chatbot not found"}), 404

        # Check if WhatsApp integration already exists for this chatbot
        whatsapp_integration = WhatsAppIntegration.query.filter_by(chatbot_id=data['chatbotId']).first()

        if whatsapp_integration:
            # Update existing integration
            whatsapp_integration.whatsapp_number = data['whatsappNumber']
            whatsapp_integration.is_active = True
        else:
            # Create new integration
            whatsapp_integration = WhatsAppIntegration(
                chatbot_id=data['chatbotId'],
                whatsapp_number=data['whatsappNumber'],
                is_active=True
            )
            db.session.add(whatsapp_integration)

        # Commit changes to database
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "WhatsApp integration saved successfully"
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error saving WhatsApp configuration: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        logger.error(f"Error saving WhatsApp configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

@whatsapp_config_bp.route('/status', methods=['GET'])
@login_required
def check_status():
    """
    Check the status of the WhatsApp integration
    """
    try:
        # Get chatbot ID from query parameters
        chatbot_id = request.args.get('chatbotId')
        if not chatbot_id:
            return jsonify({
                "status": "error",
                "message": "Missing chatbot ID parameter"
            }), 400

        # Check if Twilio credentials are configured in environment variables
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')

        if not account_sid or not auth_token or not twilio_whatsapp_number:
            return jsonify({
                "status": "not_configured",
                "message": "Twilio credentials are not configured on the server"
            })

        # Check if WhatsApp integration exists for this chatbot
        whatsapp_integration = WhatsAppIntegration.query.filter_by(chatbot_id=chatbot_id).first()

        if not whatsapp_integration:
            return jsonify({
                "status": "not_configured",
                "message": "WhatsApp integration is not configured for this chatbot"
            })

        # Check if the chatbot exists
        chatbot = Chatbot.query.get(chatbot_id)
        if not chatbot:
            return jsonify({
                "status": "error",
                "message": "The configured chatbot no longer exists"
            })

        # All checks passed, integration is active
        return jsonify({
            "status": "active",
            "message": "WhatsApp integration is active",
            "whatsapp_number": whatsapp_integration.whatsapp_number,
            "chatbot_id": chatbot_id,
            "chatbot_name": chatbot.name
        })

    except Exception as e:
        logger.error(f"Error checking WhatsApp status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error checking WhatsApp status: {str(e)}"
        })
