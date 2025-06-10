"""
WhatsApp Integration Model

This module defines the database model for WhatsApp integration.
"""
from datetime import datetime
import datetime as dt
from xavier_back.extensions import db

class WhatsAppIntegration(db.Model):
    """
    Model to store WhatsApp integration settings for chatbots
    """
    __tablename__ = 'whatsapp_integration'
    
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id'), nullable=False, unique=True)
    whatsapp_number = db.Column(db.String(20), nullable=False)  # Customer's WhatsApp number
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(dt.timezone.utc), 
                           onupdate=lambda: datetime.now(dt.timezone.utc))
    
    # Define relationship with Chatbot
    chatbot = db.relationship('Chatbot', backref=db.backref('whatsapp_integration', uselist=False))
    
    def __repr__(self):
        return f"<WhatsAppIntegration chatbot_id={self.chatbot_id}, number={self.whatsapp_number}>"
