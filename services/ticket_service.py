"""
Ticket Service Module

This module contains business logic for ticket operations, separating it from the route handlers.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import Ticket, TicketResponse, User, Chatbot

logger = logging.getLogger(__name__)

class TicketService:
    """Service class for ticket-related operations"""

    @staticmethod
    def create_ticket(chatbot_id: str, subject: str, description: str, priority: str = 'medium',
                     user_id: Optional[int] = None, account_details: Optional[str] = None) -> Tuple[Optional[Ticket], Optional[str]]:
        """
        Create a new support ticket

        Args:
            chatbot_id: The ID of the chatbot
            subject: Ticket subject
            description: Ticket description
            priority: Ticket priority (low, medium, high)
            user_id: Optional user ID (defaults to default user if not provided)
            account_details: Optional account details in JSON format

        Returns:
            Tuple containing (ticket, error_message)
        """
        try:
            # Validate chatbot exists
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot:
                return None, "Chatbot not found"

            # Use default user if no user ID provided
            if not user_id:
                default_user = User.query.get(4269)  # Default ticket user
                if not default_user:
                    return None, "Default user not found"
                user_id = default_user.id

            # Create ticket
            new_ticket = Ticket(
                user_id=user_id,
                chatbot_id=chatbot_id,
                subject=subject,
                description=description,
                status='open',
                priority=priority,
                account_details=account_details
            )
            print(f"new_ticket{new_ticket}")

            db.session.add(new_ticket)
            db.session.commit()

            return new_ticket, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error creating ticket: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def get_ticket(ticket_id: int) -> Optional[Ticket]:
        """
        Get a ticket by ID

        Args:
            ticket_id: The ID of the ticket

        Returns:
            The ticket object or None if not found
        """
        try:
            return Ticket.query.get(ticket_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving ticket {ticket_id}: {str(e)}")
            return None

    @staticmethod
    def get_tickets_for_chatbot(chatbot_id: str, status: Optional[str] = None) -> List[Ticket]:
        """
        Get tickets for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            status: Optional status filter

        Returns:
            List of tickets
        """
        try:
            query = Ticket.query.filter_by(chatbot_id=chatbot_id)

            if status:
                query = query.filter_by(status=status)

            return query.order_by(desc(Ticket.created_at)).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving tickets for chatbot {chatbot_id}: {str(e)}")
            return []

    @staticmethod
    def update_ticket_status(ticket_id: int, status: str) -> Tuple[bool, Optional[str]]:
        """
        Update a ticket's status

        Args:
            ticket_id: The ID of the ticket
            status: New status (open, in_progress, resolved, closed)

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return False, "Ticket not found"

            # Validate status
            valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
            if status not in valid_statuses:
                return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"

            ticket.status = status
            ticket.updated_at = datetime.now()
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating ticket status: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def update_ticket_priority(ticket_id: int, priority: str) -> Tuple[bool, Optional[str]]:
        """
        Update a ticket's priority

        Args:
            ticket_id: The ID of the ticket
            priority: New priority (low, medium, high)

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return False, "Ticket not found"

            # Validate priority
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                return False, f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"

            ticket.priority = priority
            ticket.updated_at = datetime.now()
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating ticket priority: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def add_response(ticket_id: int, user_id: int, response: str) -> Tuple[Optional[TicketResponse], Optional[str]]:
        """
        Add a response to a ticket

        Args:
            ticket_id: The ID of the ticket
            user_id: The ID of the user adding the response
            response: The response text

        Returns:
            Tuple containing (ticket_response, error_message)
        """
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return None, "Ticket not found"

            # Create response
            new_response = TicketResponse(
                ticket_id=ticket_id,
                user_id=user_id,
                response=response
            )

            db.session.add(new_response)

            # Update ticket timestamp
            ticket.updated_at = datetime.now()

            db.session.commit()

            return new_response, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error adding ticket response: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def get_ticket_responses(ticket_id: int) -> List[TicketResponse]:
        """
        Get responses for a ticket

        Args:
            ticket_id: The ID of the ticket

        Returns:
            List of ticket responses
        """
        try:
            return TicketResponse.query.filter_by(ticket_id=ticket_id).order_by(TicketResponse.created_at).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving responses for ticket {ticket_id}: {str(e)}")
            return []

    @staticmethod
    def delete_ticket(ticket_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a ticket

        Args:
            ticket_id: The ID of the ticket

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return False, "Ticket not found"

            # First delete all related ticket responses
            # This is necessary because the ticket_id column in TicketResponse has a NOT NULL constraint
            TicketResponse.query.filter_by(ticket_id=ticket_id).delete()

            # Then delete the ticket
            db.session.delete(ticket)
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error deleting ticket: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
