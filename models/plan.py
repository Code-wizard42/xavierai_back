from extensions import db
from datetime import datetime, timezone as dt
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from models.whatsapp import WhatsAppIntegration


class Plan(db.Model):
    """Model to store subscription plans"""
    __tablename__ = 'plan'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # e.g., 'Free', 'Basic', 'Premium'
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)  # Monthly price
    annual_price = db.Column(db.Float, nullable=True)  # Annual price (optional)
    features = db.Column(db.JSON, nullable=False)  # JSON array of features
    max_chatbots = db.Column(db.Integer, nullable=False, default=999999999)  # Maximum number of chatbots (unlimited)
    max_conversations_per_month = db.Column(db.Integer, nullable=False, default=1000)  # Monthly conversation limit per chatbot
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.utc),
                          onupdate=lambda: datetime.now(dt.utc))

    # Relationships - using a unique backref name to avoid conflicts
    subscriptions = db.relationship('Subscription', backref='plan_details', lazy=True)


