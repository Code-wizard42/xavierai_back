from extensions import db
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from models.whatsapp import WhatsAppIntegration


class PaymentHistory(db.Model):
    """Model to store payment history"""
    __tablename__ = 'payment_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id', ondelete='CASCADE'), nullable=True)  # Making nullable
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Using string type to match USER-DEFINED in schema
    stripe_payment_intent_id = db.Column(db.String(100), nullable=True)
    stripe_invoice_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)  # e.g., 'card', 'paypal'
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paypal_order_id = db.Column(db.String(100), nullable=True)
    paypal_transaction_id = db.Column(db.String(100), nullable=True)
    lemon_squeezy_order_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    subscription = db.relationship('Subscription', backref=db.backref('payments', lazy=True), foreign_keys=[subscription_id])
    user = db.relationship('User', backref=db.backref('payments', lazy=True), foreign_keys=[user_id])


