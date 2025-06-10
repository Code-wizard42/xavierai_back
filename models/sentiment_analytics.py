from xavier_back.extensions import db
from datetime import datetime
import datetime as dt
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from xavier_back.models.whatsapp import WhatsAppIntegration


class SentimentAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    user_sentiment = db.Column(db.Boolean, nullable=False)  # True for positive, False for negative
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    conversation_id = db.Column(db.String(36), nullable=True)  # To track specific conversations


