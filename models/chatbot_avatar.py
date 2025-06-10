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


class ChatbotAvatar(db.Model):
    """Model to store chatbot avatar images in the database"""
    __tablename__ = 'chatbot_avatar'
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)  # Store the actual image data
    content_type = db.Column(db.String(100), nullable=False)  # Store the MIME type
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Define relationship with Chatbot
    chatbot = db.relationship('Chatbot', backref=db.backref('avatars', lazy=True))


