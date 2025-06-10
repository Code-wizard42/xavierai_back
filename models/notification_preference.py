from extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from models.whatsapp import WhatsAppIntegration


class NotificationPreference(db.Model):
    """Model to store user notification preferences"""
    __tablename__ = 'notification_preference'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Store notification preferences as JSON
    # Format: {
    #   "preferences": [
    #     {
    #       "eventType": "new_ticket",
    #       "channels": {"email": true, "platform": true, "none": false}
    #     },
    #     ...
    #   ],
    #   "emailFrequency": "immediate",
    #   "notificationEmail": "user@example.com"
    # }
    preferences = db.Column(db.JSON, nullable=False)

    # Specific fields for quick access
    notification_email = db.Column(db.String(128), nullable=True)
    email_frequency = db.Column(db.String(20), default='immediate')  # immediate, hourly, daily, weekly

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc),
                          onupdate=lambda: datetime.now(dt.timezone.utc))

    # Define relationship with User
    user = db.relationship('User', backref=db.backref('notification_preferences', lazy=True))