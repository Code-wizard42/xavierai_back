from xavier_back.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from xavier_back.models.whatsapp import WhatsAppIntegration


class Chatbot(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data = db.Column(JSON)  # JSON column to store both PDF and database data
    feedbacks = db.relationship(
        'Feedback',
        backref='chatbot',
        lazy=True,
        cascade="all, delete-orphan"
    )
    leads = db.relationship(
        'Lead',
        backref='chatbot',
        lazy=True,
        cascade="all, delete-orphan"
    )


