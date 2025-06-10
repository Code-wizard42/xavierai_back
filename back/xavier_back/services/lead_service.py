"""
Lead Service Module

This module contains business logic for lead operations, separating it from the route handlers.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import Lead, Chatbot, ConversationMessage

logger = logging.getLogger(__name__)

class LeadService:
    """Service class for lead-related operations"""

    @staticmethod
    def create_lead(chatbot_id: str, name: str, email: str, phone: Optional[str] = None,
                   message: Optional[str] = None, user_id: Optional[int] = None) -> Tuple[Optional[Lead], Optional[str]]:
        """
        Create a new lead

        Args:
            chatbot_id: The ID of the chatbot
            name: Lead name
            email: Lead email
            phone: Optional phone number
            message: Optional message
            user_id: Optional user ID (defaults to chatbot owner if not provided)

        Returns:
            Tuple containing (lead, error_message)
        """
        try:
            # Validate chatbot exists
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot:
                return None, "Chatbot not found"

            # Use chatbot owner if no user ID provided
            if not user_id:
                user_id = chatbot.user_id

            # Create lead
            new_lead = Lead(
                chatbot_id=chatbot_id,
                name=name,
                email=email,
                phone=phone,
                message=message,
                user_id=user_id,
                status='new'
            )

            db.session.add(new_lead)
            db.session.commit()

            return new_lead, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error creating lead: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def get_lead(lead_id: int) -> Optional[Lead]:
        """
        Get a lead by ID

        Args:
            lead_id: The ID of the lead

        Returns:
            The lead object or None if not found
        """
        try:
            return Lead.query.get(lead_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving lead {lead_id}: {str(e)}")
            return None

    @staticmethod
    def get_leads_for_user(user_id: int, chatbot_id: Optional[str] = None,
                          status: Optional[str] = None) -> List[Lead]:
        """
        Get leads for a user

        Args:
            user_id: The ID of the user
            chatbot_id: Optional chatbot ID filter
            status: Optional status filter

        Returns:
            List of leads
        """
        try:
            query = Lead.query.filter_by(user_id=user_id)

            if chatbot_id:
                query = query.filter_by(chatbot_id=chatbot_id)

            if status:
                query = query.filter_by(status=status)

            return query.order_by(desc(Lead.created_at)).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving leads for user {user_id}: {str(e)}")
            return []

    @staticmethod
    def update_lead_status(lead_id: int, status: str) -> Tuple[bool, Optional[str]]:
        """
        Update a lead's status

        Args:
            lead_id: The ID of the lead
            status: New status (new, contacted, qualified, converted, etc.)

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return False, "Lead not found"

            # Validate status
            valid_statuses = ['new', 'contacted', 'qualified', 'converted', 'closed']
            if status not in valid_statuses:
                return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"

            lead.status = status
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating lead status: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def update_lead_notes(lead_id: int, notes: str) -> Tuple[bool, Optional[str]]:
        """
        Update a lead's notes

        Args:
            lead_id: The ID of the lead
            notes: New notes

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return False, "Lead not found"

            lead.notes = notes
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating lead notes: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def delete_lead(lead_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a lead

        Args:
            lead_id: The ID of the lead

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return False, "Lead not found"

            db.session.delete(lead)
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error deleting lead: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def detect_lead_intent(conversation_id: str, chatbot_id: str) -> Dict[str, Any]:
        """
        Analyze conversation to detect if a lead form should be suggested

        Args:
            conversation_id: The ID of the conversation
            chatbot_id: The ID of the chatbot

        Returns:
            Dictionary with detection results
        """
        try:
            # Get conversation messages
            messages = ConversationMessage.query.filter_by(
                conversation_id=conversation_id,
                chatbot_id=chatbot_id
            ).order_by(ConversationMessage.timestamp).all()

            if not messages or len(messages) < 2:
                return {"should_suggest_lead": False, "confidence": 0.0}

            # Extract user messages and bot responses
            user_messages = []
            bot_responses = []

            for i, msg in enumerate(messages):
                if i % 2 == 0:  # User message
                    user_messages.append(msg.message.lower())
                else:  # Bot response
                    bot_responses.append(msg.response.lower())

            # Simple keyword-based detection
            interest_keywords = [
                'interested', 'buy', 'purchase', 'pricing', 'cost', 'price',
                'demo', 'demonstration', 'trial', 'contact', 'sales', 'more info',
                'more information', 'learn more', 'tell me more', 'features',
                'how much', 'subscription', 'plan', 'package', 'offer'
            ]

            # Count interest keywords in user messages
            keyword_count = 0
            for msg in user_messages:
                for keyword in interest_keywords:
                    if keyword in msg:
                        keyword_count += 1

            # Calculate confidence based on keyword count and message count
            confidence = min(1.0, keyword_count / (len(user_messages) * 0.5))

            # Determine if we should suggest a lead form
            should_suggest = confidence >= 0.4  # Threshold can be adjusted

            return {
                "should_suggest_lead": should_suggest,
                "confidence": round(confidence, 2)
            }
        except Exception as e:
            logger.error(f"Error detecting lead intent: {str(e)}")
            return {"should_suggest_lead": False, "confidence": 0.0, "error": str(e)}
