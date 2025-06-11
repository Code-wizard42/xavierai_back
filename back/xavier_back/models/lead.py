from extensions import db
from datetime import datetime, timezone
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from models.whatsapp import WhatsAppIntegration


class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    # Make user_id nullable to match existing schema
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='new')  # new, contacted, qualified, converted, etc.
    notes = db.Column(db.Text, nullable=True)


