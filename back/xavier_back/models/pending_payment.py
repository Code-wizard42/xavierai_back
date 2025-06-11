from extensions import db
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSON
import uuid

class PendingPayment(db.Model):
    """Model to store pending payments before they are processed"""
    __tablename__ = 'pending_payment'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_provider = db.Column(db.String(50), nullable=False)  # e.g., 'stripe', 'paypal', 'paystack'
    payment_id = db.Column(db.String(100), nullable=False)  # Provider's payment ID
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(Enum('pending', 'completed', 'failed', name='pending_payment_status'), nullable=False)
    email = db.Column(db.String(128), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=True)
    payment_data = db.Column(db.Text, nullable=True)  # Additional payment details as JSON
    is_processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Define relationships
    user = db.relationship('User', backref=db.backref('pending_payments', lazy=True))
    plan = db.relationship('Plan', backref=db.backref('pending_payments', lazy=True)) 