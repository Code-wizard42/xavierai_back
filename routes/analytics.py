"""
Analytics Routes Module

This module contains route handlers for analytics-related operations.
It uses the service layer for business logic.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
import logging
from functools import wraps

from xavier_back.models import QuestionAnalytics, SentimentAnalytics
from xavier_back.extensions import db
from xavier_back.services.analytics_service import AnalyticsService
from xavier_back.utils.auth_utils import login_required
from xavier_back.middleware.subscription_middleware import subscription_required

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Create blueprint
analytics_bp = Blueprint('analytics', __name__)

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

# Helper function for backward compatibility
def track_question_helper(chatbot_id, question_data):
    """Helper function to track question analytics"""
    return AnalyticsService.track_question(chatbot_id, question_data)

@analytics_bp.route('/analytics/questions/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_chatbot_analytics(chatbot_id):
    """Get analytics for a specific chatbot"""
    try:
        # Get optional date range filters from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        days = request.args.get('days', 30, type=int)

        # Use direct database query for this specific endpoint
        query = QuestionAnalytics.query.filter_by(chatbot_id=chatbot_id)

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(QuestionAnalytics.timestamp >= start_date)

        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(QuestionAnalytics.timestamp <= end_date)

        analytics = query.order_by(QuestionAnalytics.timestamp.desc()).all()

        return jsonify({
            "total_questions": len(analytics),
            "analytics": [{
                "question": record.question,
                "answer": record.answer,
                "timestamp": record.timestamp.isoformat(),
                "metadata": record.question_metadata
            } for record in analytics]
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving analytics: {str(e)}")
        return jsonify({"error": "Failed to retrieve analytics"}), 500

@analytics_bp.route('/analytics/common_questions/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_common_questions(chatbot_id):
    """Get most commonly asked questions"""
    try:
        days = request.args.get('days', 30, type=int)

        # Use the service to get common questions
        common_questions = AnalyticsService.get_common_questions(chatbot_id, limit=10, days=days)

        return jsonify({
            "top_questions": common_questions,
            "total_questions": len(common_questions),
            "timeframe_days": days
        }), 200

    except Exception as e:
        logger.error(f"Error getting common questions: {str(e)}")
        return jsonify({"error": "Failed to get common questions"}), 500

@analytics_bp.route('/analytics/question_clusters/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_question_clusters(chatbot_id):
    """Get question clusters by topic"""
    try:
        days = request.args.get('days', 30, type=int)
        num_clusters = request.args.get('num_clusters', 5, type=int)

        # Use the service to get question clusters
        clusters = AnalyticsService.get_question_clusters(chatbot_id, num_clusters=num_clusters, days=days)

        return jsonify({
            "clusters": clusters,
            "timeframe_days": days
        }), 200

    except Exception as e:
        logger.error(f"Error clustering questions: {str(e)}")
        return jsonify({"error": "Failed to cluster questions"}), 500

@analytics_bp.route('/analytics/usage_patterns/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_usage_patterns(chatbot_id):
    """Get usage patterns and trends"""
    try:
        days = request.args.get('days', 30, type=int)

        # Use the service to get usage patterns
        usage_patterns = AnalyticsService.get_usage_patterns(chatbot_id, days=days)

        return jsonify({
            "daily_trends": usage_patterns.get("daily", []),
            "hourly_distribution": usage_patterns.get("hourly", []),
            "total_questions": usage_patterns.get("total_questions", 0),
            "unique_conversations": usage_patterns.get("unique_conversations", 0),
            "timeframe_days": days
        }), 200

    except Exception as e:
        logger.error(f"Error getting usage patterns: {str(e)}")
        return jsonify({"error": "Failed to get usage patterns"}), 500

@analytics_bp.route('/analytics/sentiment/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_sentiment_analytics(chatbot_id):
    """Get sentiment analytics for a specific chatbot"""
    try:
        days = request.args.get('days', 30, type=int)

        # Use the service to get sentiment analytics
        sentiment_data = AnalyticsService.get_sentiment_analytics(chatbot_id, days=days)

        return jsonify({
            "total_ratings": sentiment_data.get("total_ratings", 0),
            "positive_ratings": sentiment_data.get("positive_ratings", 0),
            "negative_ratings": sentiment_data.get("negative_ratings", 0),
            "satisfaction_rate": sentiment_data.get("satisfaction_rate", 0),
            "daily_sentiment": sentiment_data.get("daily_sentiment", []),
            "timeframe_days": days
        }), 200

    except Exception as e:
        logger.error(f"Error getting sentiment analytics: {str(e)}")
        return jsonify({"error": "Failed to get sentiment analytics"}), 500

@analytics_bp.route('/analytics/sentiment/<chatbot_id>', methods=['POST'])
@handle_errors
def submit_sentiment(chatbot_id):
    """Submit user sentiment for a chat interaction"""
    try:
        data = request.json
        sentiment = data.get('sentiment')
        conversation_id = data.get('conversation_id')

        if sentiment is None:
            return jsonify({"error": "Sentiment value is required"}), 400

        # Use the service to track sentiment
        success, error = AnalyticsService.track_sentiment(chatbot_id, sentiment, conversation_id)

        if not success:
            return jsonify({"error": error}), 500

        return jsonify({"message": "Sentiment recorded successfully"}), 201

    except Exception as e:
        logger.error(f"Error submitting sentiment: {str(e)}")
        return jsonify({"error": "Failed to submit sentiment"}), 500

@analytics_bp.route('/analytics/dashboard/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_analytics_dashboard(chatbot_id):
    """Get comprehensive analytics dashboard"""
    try:
        days = request.args.get('days', 30, type=int)

        # Use the service to get dashboard analytics
        dashboard = AnalyticsService.get_dashboard_analytics(chatbot_id, days=days)

        if "error" in dashboard:
            return jsonify({"error": dashboard["error"]}), 500

        # Ensure we have the correct structure for the dashboard
        response_data = {
            "common_questions": dashboard.get("common_questions", {
                "top_questions": [],
                "total_questions": 0
            }),
            "topic_clusters": dashboard.get("question_clusters", []),
            "usage_patterns": dashboard.get("usage_patterns", {
                "daily": [],
                "hourly": [],
                "total_questions": 0,
                "unique_conversations": 0
            }),
            "sentiment_analytics": dashboard.get("sentiment", {
                "total_ratings": 0,
                "positive_ratings": 0,
                "negative_ratings": 0,
                "satisfaction_rate": 0,
                "daily_sentiment": []
            }),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "timeframe_days": days
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        return jsonify({"error": "Failed to get dashboard data"}), 500
