from extensions import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid
from models.whatsapp import WhatsAppIntegration


class Subscription(db.Model):
    """Model to store user subscriptions"""
    __tablename__ = 'subscription'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    status = db.Column(db.String(20), default='trialing', nullable=False)  # Using string type to match USER-DEFINED
    start_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)  # Null for ongoing subscriptions
    trial_end = db.Column(db.DateTime, nullable=True)
    next_billing_date = db.Column(db.DateTime, nullable=True)  # Date when next payment is due
    billing_cycle = db.Column(db.String(20), default='monthly', nullable=False)  # Using string type to match USER-DEFINED
    # Payment method type (stripe, paypal, lemon_squeezy, etc.)
    payment_method = db.Column(db.String(20), default='stripe', nullable=True)
    # Stripe specific fields
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    payment_method_id = db.Column(db.String(100), nullable=True)
    # PayPal specific fields
    paypal_subscription_id = db.Column(db.String(100), nullable=True)
    paypal_order_id = db.Column(db.String(100), nullable=True)
    # Paystack specific fields
    paystack_reference = db.Column(db.String(100), nullable=True)
    # Lemon Squeezy specific fields
    lemon_squeezy_order_id = db.Column(db.String(100), nullable=True)
    lemon_squeezy_customer_id = db.Column(db.String(100), nullable=True)
    lemon_squeezy_subscription_id = db.Column(db.String(100), nullable=True)
    # Common fields
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Define the relationship with User (bi-directional)
    user = db.relationship('User', back_populates='subscription', foreign_keys=[user_id])

    # Helper methods
    def is_active(self):
        """Check if subscription is active"""
        if self.status not in ['active', 'trialing']:
            return False

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)
        
        # Check if billing date has passed (subscription expired)
        if self.next_billing_date:
            # Ensure next_billing_date has timezone info
            if self.next_billing_date.tzinfo is None:
                # If next_billing_date is naive, assume it's in UTC
                next_billing = self.next_billing_date.replace(tzinfo=timezone.utc)
            else:
                next_billing = self.next_billing_date

            if next_billing < now and self.status == 'active':
                return False
        
        if self.end_date:
            # Ensure end_date has timezone info
            if self.end_date.tzinfo is None:
                # If end_date is naive, assume it's in UTC
                end_date = self.end_date.replace(tzinfo=timezone.utc)
            else:
                end_date = self.end_date

            if end_date < now:
                return False

        return True

    def is_in_trial(self):
        """Check if subscription is in trial period"""
        if self.status != 'trialing':
            return False
        if not self.trial_end:
            return False

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)

        # Ensure trial_end has timezone info
        if self.trial_end.tzinfo is None:
            # If trial_end is naive, assume it's in UTC
            trial_end = self.trial_end.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_end

        return trial_end > now

    def days_left_in_trial(self):
        """Get days left in trial period"""
        if not self.is_in_trial():
            return 0

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)

        # Ensure trial_end has timezone info
        if self.trial_end.tzinfo is None:
            # If trial_end is naive, assume it's in UTC
            trial_end = self.trial_end.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_end

        delta = trial_end - now
        return max(0, delta.days)

    def is_billing_overdue(self):
        """Check if billing payment is overdue"""
        if not self.next_billing_date or self.status != 'active':
            return False

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)

        # Ensure next_billing_date has timezone info
        if self.next_billing_date.tzinfo is None:
            # If next_billing_date is naive, assume it's in UTC
            next_billing = self.next_billing_date.replace(tzinfo=timezone.utc)
        else:
            next_billing = self.next_billing_date

        return next_billing < now

    def days_until_billing(self):
        """Get days until next billing date"""
        if not self.next_billing_date:
            return None

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)

        # Ensure next_billing_date has timezone info
        if self.next_billing_date.tzinfo is None:
            # If next_billing_date is naive, assume it's in UTC
            next_billing = self.next_billing_date.replace(tzinfo=timezone.utc)
        else:
            next_billing = self.next_billing_date

        delta = next_billing - now
        return delta.days

    def calculate_next_billing_date(self):
        """Calculate the next billing date based on current date and billing cycle"""
        now = datetime.now(timezone.utc)
        
        if self.billing_cycle == 'annual':
            # Add one year
            next_billing = now.replace(year=now.year + 1)
        else:
            # Default to monthly
            # Handle month overflow
            if now.month == 12:
                next_billing = now.replace(year=now.year + 1, month=1)
            else:
                next_billing = now.replace(month=now.month + 1)
        
        return next_billing

    def set_next_billing_date(self):
        """Set the next billing date automatically"""
        self.next_billing_date = self.calculate_next_billing_date()


