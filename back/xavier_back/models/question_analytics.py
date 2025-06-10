from xavier_back.extensions import db
from datetime import datetime, timezone
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from xavier_back.models.whatsapp import WhatsAppIntegration


class QuestionAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    question_metadata = db.Column(db.JSON)
    conversation_id = db.Column(db.String(36), nullable=True)  # To track specific conversations


#------------------------------------------------
# START  OF NEW MODELS
#----------------------------------------------
