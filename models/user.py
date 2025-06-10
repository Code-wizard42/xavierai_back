from extensions import db
from sqlalchemy.orm import relationship
from datetime import datetime
import datetime as dt

class User(db.Model):
    """
    User model representing the application users.
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Can be null for Firebase users
    email = db.Column(db.String(128), unique=True, nullable=True)  # For Firebase users
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)  # Firebase User ID
    profile_picture = db.Column(db.String(512), nullable=True)  # Profile picture URL
    auth_provider = db.Column(db.String(20), default='local')  # 'local', 'firebase', 'google'
    
    # Remove the circular dependency by not directly referencing subscription_id
    # The subscription will still be accessible through the relationship
    
    # Define relationships
    chatbots = relationship('Chatbot', backref='owner', lazy=True)
    feedbacks = relationship('Feedback', backref='user', lazy=True)
    leads = relationship('Lead', backref='owner', lazy=True)
    
    # Explicitly define the subscription relationship
    # Using uselist=False to make it a one-to-one relationship
    subscription = relationship('Subscription', 
                               back_populates='user',
                               uselist=False, 
                               cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user object to a dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'profile_picture': self.profile_picture,
            'auth_provider': self.auth_provider,
            'has_subscription': self.subscription is not None
        }
