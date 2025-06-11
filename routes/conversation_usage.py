"""
Conversation Usage Routes

This module contains routes for managing conversation usage and limits.
"""

from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from middleware.subscription_middleware import subscription_required
from services.conversation_limit_service import ConversationLimitService
from utils.response_utils import optimize_json_response
import logging

logger = logging.getLogger(__name__)

conversation_usage_bp = Blueprint('conversation_usage', __name__)


@conversation_usage_bp.route('/conversation-usage/summary', methods=['GET'])
@login_required
@subscription_required()
def get_usage_summary():
    """Get conversation usage summary for the authenticated user"""
    try:
        user_id = session.get('user_id')
        
        # Get optional year and month parameters
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        summary = ConversationLimitService.get_usage_summary(user_id, year, month)
        
        if 'error' in summary:
            return jsonify(summary), 500
        
        return optimize_json_response(summary)
        
    except Exception as e:
        logger.error(f"Error getting usage summary: {str(e)}")
        return jsonify({"error": "Failed to get usage summary"}), 500


@conversation_usage_bp.route('/conversation-usage/chatbot/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
def get_chatbot_usage(chatbot_id):
    """Get detailed usage information for a specific chatbot"""
    try:
        user_id = session.get('user_id')
        
        # First check if the user owns this chatbot
        from services.chatbot_service import ChatbotService
        chatbot = ChatbotService.get_chatbot(chatbot_id)
        
        if not chatbot or chatbot.user_id != user_id:
            return jsonify({"error": "Chatbot not found or unauthorized"}), 404
        
        usage_info = ConversationLimitService.get_chatbot_usage_info(chatbot_id)
        
        if 'error' in usage_info:
            return jsonify(usage_info), 500
        
        return optimize_json_response(usage_info)
        
    except Exception as e:
        logger.error(f"Error getting chatbot usage for {chatbot_id}: {str(e)}")
        return jsonify({"error": "Failed to get chatbot usage"}), 500


@conversation_usage_bp.route('/conversation-usage/check-limit/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
def check_conversation_limit(chatbot_id):
    """Check conversation limit for a specific chatbot"""
    try:
        user_id = session.get('user_id')
        
        # First check if the user owns this chatbot
        from services.chatbot_service import ChatbotService
        chatbot = ChatbotService.get_chatbot(chatbot_id)
        
        if not chatbot or chatbot.user_id != user_id:
            return jsonify({"error": "Chatbot not found or unauthorized"}), 404
        
        can_proceed, limit_info = ConversationLimitService.check_conversation_limit(chatbot_id)
        
        response_data = {
            "can_proceed": can_proceed,
            "limit_info": limit_info
        }
        
        return optimize_json_response(response_data)
        
    except Exception as e:
        logger.error(f"Error checking conversation limit for {chatbot_id}: {str(e)}")
        return jsonify({"error": "Failed to check conversation limit"}), 500


@conversation_usage_bp.route('/conversation-usage/dashboard', methods=['GET'])
@login_required
@subscription_required()
def get_usage_dashboard():
    """Get comprehensive usage dashboard data"""
    try:
        user_id = session.get('user_id')
        
        # Get current month summary
        current_summary = ConversationLimitService.get_usage_summary(user_id)
        
        if 'error' in current_summary:
            return jsonify(current_summary), 500
        
        # Get subscription info for plan details
        from services.subscription_service import SubscriptionService
        subscription_data = SubscriptionService.get_user_subscription(user_id)
        
        dashboard_data = {
            "usage_summary": current_summary,
            "subscription_info": {
                "plan_name": subscription_data.get('plan', {}).get('name', 'Unknown') if subscription_data else 'Unknown',
                "conversation_limit": subscription_data.get('plan', {}).get('max_conversations_per_month', 1000) if subscription_data else 1000,
                "is_active": subscription_data.get('is_active', False) if subscription_data else False
            },
            "recommendations": []
        }
        
        # Add recommendations based on usage
        total_usage = current_summary.get('total_conversations_used', 0)
        limit_per_chatbot = current_summary.get('conversation_limit_per_chatbot', 1000)
        chatbot_count = current_summary.get('chatbot_count', 0)
        
        if current_summary.get('has_exceeded_limits', False):
            dashboard_data["recommendations"].append({
                "type": "upgrade",
                "message": "Some of your chatbots have exceeded their monthly conversation limits. Consider upgrading your plan for higher limits.",
                "priority": "high"
            })
        elif total_usage > (limit_per_chatbot * chatbot_count * 0.8):  # 80% usage threshold
            dashboard_data["recommendations"].append({
                "type": "warning",
                "message": "You're approaching your conversation limits. Monitor your usage to avoid interruptions.",
                "priority": "medium"
            })
        elif total_usage < (limit_per_chatbot * chatbot_count * 0.2):  # Low usage
            dashboard_data["recommendations"].append({
                "type": "optimization",
                "message": "You have plenty of conversation capacity remaining. Consider promoting your chatbots to increase engagement.",
                "priority": "low"
            })
        
        return optimize_json_response(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error getting usage dashboard: {str(e)}")
        return jsonify({"error": "Failed to get usage dashboard"}), 500 