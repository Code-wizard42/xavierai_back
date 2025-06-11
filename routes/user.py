"""
User Routes Module

This module contains routes for user-related operations.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from extensions import db
from models import User, NotificationPreference
from schemas import NotificationPreferenceSchema

logger = logging.getLogger(__name__)

# Create Blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/notification-preferences', methods=['GET'])
@jwt_required()
def get_notification_preferences():
    """Get the current user's notification preferences"""
    try:
        # Get the current user
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if the user has notification preferences
        notification_pref = NotificationPreference.query.filter_by(user_id=current_user_id).first()

        if notification_pref:
            # Format the response to match the expected structure
            preferences = {
                'userId': current_user_id,
                'preferences': notification_pref.preferences.get('preferences', []),
                'emailFrequency': notification_pref.email_frequency,
                'notificationEmail': notification_pref.notification_email or user.email
            }
        else:
            # Return default preferences
            preferences = {
                'userId': current_user_id,
                'preferences': [
                    {
                        'eventType': 'new_ticket',
                        'channels': {'email': True, 'platform': True, 'none': False}
                    },
                    {
                        'eventType': 'new_lead',
                        'channels': {'email': True, 'platform': True, 'none': False}
                    },
                    {
                        'eventType': 'ticket_update',
                        'channels': {'email': True, 'platform': True, 'none': False}
                    },
                    {
                        'eventType': 'lead_update',
                        'channels': {'email': False, 'platform': True, 'none': False}
                    }
                ],
                'emailFrequency': 'immediate',
                'notificationEmail': user.email
            }

        return jsonify(preferences), 200
    except Exception as e:
        logger.error(f"Error getting notification preferences: {str(e)}")
        return jsonify({'error': 'An error occurred while getting notification preferences'}), 500

@user_bp.route('/notification-preferences', methods=['POST'])
@jwt_required()
def save_notification_preferences():
    """Save the current user's notification preferences"""
    try:
        # Get the current user
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get the request data
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate the data
        if 'preferences' not in data:
            return jsonify({'error': 'Preferences not provided'}), 400

        # Get notification email and frequency
        notification_email = data.get('notificationEmail')
        email_frequency = data.get('emailFrequency', 'immediate')

        try:
            # Validate email frequency using schema
            schema = NotificationPreferenceSchema(only=['email_frequency'])
            schema.load({'email_frequency': email_frequency})
        except ValidationError as err:
            return jsonify({'error': 'Invalid email frequency', 'details': err.messages}), 400

        # Check if the user already has notification preferences
        notification_pref = NotificationPreference.query.filter_by(user_id=current_user_id).first()

        if notification_pref:
            # Update existing preferences
            notification_pref.preferences = data
            notification_pref.notification_email = notification_email
            notification_pref.email_frequency = email_frequency
        else:
            # Create new preferences
            notification_pref = NotificationPreference(
                user_id=current_user_id,
                preferences=data,
                notification_email=notification_email,
                email_frequency=email_frequency
            )
            db.session.add(notification_pref)

        # Save to database
        db.session.commit()

        # Return the updated preferences using schema
        schema = NotificationPreferenceSchema()
        result = schema.dump(notification_pref)

        logger.info(f"Saved notification preferences for user {current_user_id}")

        return jsonify({
            'message': 'Notification preferences saved successfully',
            'preferences': result
        }), 200
    except ValidationError as err:
        logger.error(f"Validation error: {err.messages}")
        db.session.rollback()
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    except Exception as e:
        logger.error(f"Error saving notification preferences: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'An error occurred while saving notification preferences'}), 500
