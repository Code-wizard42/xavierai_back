from xavier_back.extensions import db
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from xavier_back.models.whatsapp import WhatsAppIntegration


class ConversationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)  # Group messages by conversation
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)  # User's message
    response = db.Column(db.Text, nullable=False)  # Chatbot's response
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Define relationship with Chatbot
    chatbot = db.relationship('Chatbot', backref=db.backref('conversation_messages', lazy=True))


# Live chat feature has been removed


