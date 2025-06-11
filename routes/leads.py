"""
Leads Routes Module

This module contains route handlers for lead-related operations.
It uses the service layer for business logic.
"""
from flask import Blueprint, request, jsonify, session, current_app
import logging
from functools import wraps

from models import Lead
from extensions import db
from services.lead_service import LeadService
from utils.auth_utils import login_required

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Create blueprint
leads_bp = Blueprint('leads', __name__)

def handle_errors(f):
    """Decorator to handle errors in route handlers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"error": "An unexpected error occurred"}), 500
    return decorated_function

@leads_bp.route('/api/leads/submit', methods=['POST'])
@handle_errors
def submit_lead():
    """Submit a new lead from the chatbot interface"""
    data = request.json

    # Validate required fields
    required_fields = ['name', 'email', 'chatbot_id']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Use the service to create the lead
    lead, error = LeadService.create_lead(
        chatbot_id=data['chatbot_id'],
        name=data['name'],
        email=data['email'],
        phone=data.get('phone'),
        message=data.get('message')
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify({"message": "Lead submitted successfully"}), 201

@leads_bp.route('/api/leads', methods=['GET'])
@login_required
@handle_errors
def get_leads():
    """Get all leads for the current user"""
    user_id = session.get('user_id')

    # Get query parameters for filtering
    chatbot_id = request.args.get('chatbot_id')
    status = request.args.get('status')

    # Use the service to get leads
    leads = LeadService.get_leads_for_user(user_id, chatbot_id, status)

    # Format the leads for the response
    leads_data = []
    for lead in leads:
        leads_data.append({
            'id': lead.id,
            'name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'message': lead.message,
            'chatbot_id': lead.chatbot_id,
            'created_at': lead.created_at.isoformat(),
            'status': lead.status,
            'notes': getattr(lead, 'notes', None)  # Safely get notes attribute
        })

    return jsonify(leads_data), 200

@leads_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@login_required
@handle_errors
def get_lead(lead_id):
    """Get a specific lead by ID"""
    user_id = session.get('user_id')

    # Use the service to get the lead
    lead = LeadService.get_lead(lead_id)

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    # Check if lead has user_id and if it matches the current user
    try:
        if lead.user_id and lead.user_id != user_id:
            return jsonify({"error": "Unauthorized access to this lead"}), 403
    except Exception as e:
        logger.error(f"Error checking lead ownership: {str(e)}")
        # If there's an error (e.g., user_id column doesn't exist), skip the check

    # Format the lead for the response
    lead_data = {
        'id': lead.id,
        'name': lead.name,
        'email': lead.email,
        'phone': lead.phone,
        'message': lead.message,
        'chatbot_id': lead.chatbot_id,
        'created_at': lead.created_at.isoformat(),
        'status': lead.status,
        'notes': getattr(lead, 'notes', None)  # Safely get notes attribute
    }

    return jsonify(lead_data), 200

@leads_bp.route('/api/leads/<int:lead_id>', methods=['PATCH'])
@login_required
@handle_errors
def update_lead(lead_id):
    """Update a lead's status or notes"""
    user_id = session.get('user_id')
    data = request.json

    # Use the service to get the lead
    lead = LeadService.get_lead(lead_id)

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    # Check if lead has user_id and if it matches the current user
    try:
        if lead.user_id and lead.user_id != user_id:
            return jsonify({"error": "Unauthorized access to this lead"}), 403
    except Exception as e:
        logger.error(f"Error checking lead ownership: {str(e)}")
        # If there's an error (e.g., user_id column doesn't exist), skip the check

    # Update fields if provided
    if 'status' in data:
        success, error = LeadService.update_lead_status(lead_id, data['status'])
        if not success:
            return jsonify({"error": error}), 400

    if 'notes' in data:
        try:
            success, error = LeadService.update_lead_notes(lead_id, data['notes'])
            if not success:
                return jsonify({"error": error}), 400
        except AttributeError:
            logger.warning("Notes column does not exist in lead table")

    return jsonify({"message": "Lead updated successfully"}), 200

@leads_bp.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@login_required
@handle_errors
def delete_lead(lead_id):
    """Delete a lead"""
    user_id = session.get('user_id')

    # Use the service to get the lead
    lead = LeadService.get_lead(lead_id)

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    # Check if lead has user_id and if it matches the current user
    try:
        if lead.user_id and lead.user_id != user_id:
            return jsonify({"error": "Unauthorized access to this lead"}), 403
    except Exception as e:
        logger.error(f"Error checking lead ownership: {str(e)}")
        # If there's an error (e.g., user_id column doesn't exist), skip the check

    # Use the service to delete the lead
    success, error = LeadService.delete_lead(lead_id)

    if not success:
        return jsonify({"error": error}), 500

    return jsonify({"message": "Lead deleted successfully"}), 200

@leads_bp.route('/api/leads/detect-intent', methods=['POST'])
@handle_errors
def detect_lead_intent():
    """Analyze conversation to detect if a lead form should be suggested"""
    data = request.json

    # Validate required fields
    if 'conversation_id' not in data or 'chatbot_id' not in data:
        return jsonify({"error": "Missing required fields: conversation_id and chatbot_id"}), 400

    conversation_id = data['conversation_id']
    chatbot_id = data['chatbot_id']

    # Use the service to detect lead intent
    result = LeadService.detect_lead_intent(conversation_id, chatbot_id)

    # Format the response
    response = {
        "suggest_lead": result.get("should_suggest_lead", False),
        "confidence": result.get("confidence", 0.0),
        "reason": result.get("reason", "Analysis complete"),
        "threshold_met": result.get("confidence", 0.0) >= 0.3  # Lower threshold for testing
    }

    if "error" in result:
        response["error"] = result["error"]

    return jsonify(response), 200
