from extensions import db
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type if using PostgreSQL
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta
import datetime as dt
from sqlalchemy import Text, Enum
from sqlalchemy.dialects import postgresql
import uuid

# Import WhatsApp model
from models.whatsapp import WhatsAppIntegration
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Can be null for Firebase users
    email = db.Column(db.String(128), unique=True, nullable=True)  # For Firebase users
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)  # Firebase User ID
    profile_picture = db.Column(db.String(512), nullable=True)  # Profile picture URL
    auth_provider = db.Column(db.String(20), default='local')  # 'local', 'firebase', 'google'
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    chatbots = db.relationship('Chatbot', backref='owner', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    leads = db.relationship('Lead', backref='owner', lazy=True)
    subscription = db.relationship('Subscription', backref='user', uselist=False)


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


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime)


class QuestionAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    question_metadata = db.Column(db.JSON)
    conversation_id = db.Column(db.String(36), nullable=True)  # To track specific conversations


#------------------------------------------------
# START  OF NEW MODELS
#----------------------------------------------
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    priority = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc), onupdate=lambda: datetime.now(dt.timezone.utc))
    account_details = db.Column(db.JSON)

class TicketResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))

#----------------------------------------
# END OF NEW MODELS
#------------------------------------------


# Removed duplicate import

class GmailIntegration(db.Model):
    __tablename__ = 'gmail_integration'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))



class SentimentAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    user_sentiment = db.Column(db.Boolean, nullable=False)  # True for positive, False for negative
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    conversation_id = db.Column(db.String(36), nullable=True)  # To track specific conversations


class ConversationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)  # Group messages by conversation
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)  # User's message
    response = db.Column(db.Text, nullable=False)  # Chatbot's response
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))

    # Define relationship with Chatbot
    chatbot = db.relationship('Chatbot', backref=db.backref('conversation_messages', lazy=True))


# Live chat feature has been removed


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    status = db.Column(db.String(20), default='new')  # new, contacted, qualified, converted, etc.
    notes = db.Column(db.Text, nullable=True)


class ChatbotAvatar(db.Model):
    """Model to store chatbot avatar images in the database"""
    __tablename__ = 'chatbot_avatar'
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)  # Store the actual image data
    content_type = db.Column(db.String(100), nullable=False)  # Store the MIME type
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))

    # Define relationship with Chatbot
    chatbot = db.relationship('Chatbot', backref=db.backref('avatars', lazy=True))


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
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc),
                          onupdate=lambda: datetime.now(dt.timezone.utc))

    # Relationships
    subscriptions = db.relationship('Subscription', backref='plan', lazy=True)


class Subscription(db.Model):
    """Model to store user subscriptions"""
    __tablename__ = 'subscription'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    status = db.Column(Enum('active', 'canceled', 'past_due', 'trialing', 'unpaid', name='subscription_status'),
                      default='trialing', nullable=False)
    start_date = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc), nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)  # Null for ongoing subscriptions
    trial_end = db.Column(db.DateTime, nullable=True)
    billing_cycle = db.Column(Enum('monthly', 'annual', name='billing_cycle'), default='monthly', nullable=False)
    # Payment method type (stripe, paypal, etc.)
    payment_method = db.Column(db.String(20), default='stripe', nullable=True)
    # Stripe specific fields
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    payment_method_id = db.Column(db.String(100), nullable=True)
    # PayPal specific fields
    paypal_subscription_id = db.Column(db.String(100), nullable=True)
    paypal_order_id = db.Column(db.String(100), nullable=True)
    # Common fields
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc),
                          onupdate=lambda: datetime.now(dt.timezone.utc))

    # Helper methods
    def is_active(self):
        """Check if subscription is active"""
        if self.status not in ['active', 'trialing']:
            return False

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(dt.timezone.utc)
        if self.end_date:
            # Ensure end_date has timezone info
            if self.end_date.tzinfo is None:
                # If end_date is naive, assume it's in UTC
                from datetime import timezone
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
        now = datetime.now(dt.timezone.utc)

        # Ensure trial_end has timezone info
        if self.trial_end.tzinfo is None:
            # If trial_end is naive, assume it's in UTC
            from datetime import timezone
            trial_end = self.trial_end.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_end

        return trial_end > now

    def days_left_in_trial(self):
        """Get days left in trial period"""
        if not self.is_in_trial():
            return 0

        # Make sure we're comparing timezone-aware datetimes
        now = datetime.now(dt.timezone.utc)

        # Ensure trial_end has timezone info
        if self.trial_end.tzinfo is None:
            # If trial_end is naive, assume it's in UTC
            from datetime import timezone
            trial_end = self.trial_end.replace(tzinfo=timezone.utc)
        else:
            trial_end = self.trial_end

        delta = trial_end - now
        return max(0, delta.days)


class PaymentHistory(db.Model):
    """Model to store payment history"""
    __tablename__ = 'payment_history'
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    status = db.Column(Enum('succeeded', 'failed', 'pending', name='payment_status'), nullable=False)
    stripe_payment_intent_id = db.Column(db.String(100), nullable=True)
    stripe_invoice_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)  # e.g., 'card', 'paypal'
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))

    # Relationship
    subscription = db.relationship('Subscription', backref=db.backref('payments', lazy=True))


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