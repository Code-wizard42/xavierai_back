from xavier_back.extensions import db
from datetime import datetime, timezone
from sqlalchemy import Index


class ConversationUsage(db.Model):
    """Model to track monthly conversation usage per chatbot"""
    __tablename__ = 'conversation_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.String(36), db.ForeignKey('chatbot.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Year (e.g., 2024)
    month = db.Column(db.Integer, nullable=False)  # Month (1-12)
    conversation_count = db.Column(db.Integer, nullable=False, default=0)  # Number of conversations this month
    last_conversation_at = db.Column(db.DateTime, nullable=True)  # Timestamp of last conversation
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    chatbot = db.relationship('Chatbot', backref='usage_records')
    user = db.relationship('User', backref='conversation_usage')

    # Indexes for performance
    __table_args__ = (
        Index('idx_chatbot_year_month', 'chatbot_id', 'year', 'month'),
        Index('idx_user_year_month', 'user_id', 'year', 'month'),
    )

    @classmethod
    def get_or_create_usage_record(cls, chatbot_id: str, user_id: int, year: int = None, month: int = None):
        """Get or create a usage record for the current month"""
        now = datetime.now(timezone.utc)
        if year is None:
            year = now.year
        if month is None:
            month = now.month
            
        usage_record = cls.query.filter_by(
            chatbot_id=chatbot_id,
            user_id=user_id,
            year=year,
            month=month
        ).first()
        
        if not usage_record:
            usage_record = cls(
                chatbot_id=chatbot_id,
                user_id=user_id,
                year=year,
                month=month,
                conversation_count=0
            )
            db.session.add(usage_record)
            db.session.flush()  # Flush to get the ID
            
        return usage_record

    @classmethod
    def increment_conversation_count(cls, chatbot_id: str, user_id: int):
        """Increment the conversation count for current month"""
        now = datetime.now(timezone.utc)
        usage_record = cls.get_or_create_usage_record(chatbot_id, user_id, now.year, now.month)
        
        usage_record.conversation_count += 1
        usage_record.last_conversation_at = now
        usage_record.updated_at = now
        
        db.session.commit()
        return usage_record

    @classmethod
    def get_current_usage(cls, chatbot_id: str, user_id: int):
        """Get current month's conversation count"""
        now = datetime.now(timezone.utc)
        usage_record = cls.query.filter_by(
            chatbot_id=chatbot_id,
            user_id=user_id,
            year=now.year,
            month=now.month
        ).first()
        
        return usage_record.conversation_count if usage_record else 0

    @classmethod
    def get_usage_for_user_chatbots(cls, user_id: int, year: int = None, month: int = None):
        """Get usage for all chatbots owned by a user for a specific month"""
        now = datetime.now(timezone.utc)
        if year is None:
            year = now.year
        if month is None:
            month = now.month
            
        return cls.query.filter_by(
            user_id=user_id,
            year=year,
            month=month
        ).all()

    def __repr__(self):
        return f'<ConversationUsage {self.chatbot_id} {self.year}-{self.month}: {self.conversation_count}>' 