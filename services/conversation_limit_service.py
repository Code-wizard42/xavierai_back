"""
Conversation Limit Service

This service manages conversation limits and usage tracking for chatbots.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import logging
from xavier_back.extensions import db
from xavier_back.models.conversation_usage import ConversationUsage
from xavier_back.models import Chatbot, User, Plan
from xavier_back.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class ConversationLimitService:
    
    @staticmethod
    def check_conversation_limit(chatbot_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a chatbot has reached its conversation limit for the current month.
        
        Returns:
            Tuple[bool, Dict]: (can_proceed, info_dict)
            - can_proceed: True if conversation is allowed, False if limit exceeded
            - info_dict: Contains usage info and limit details
        """
        try:
            # Get chatbot and owner information
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot or not chatbot.user_id:
                logger.error(f"Chatbot {chatbot_id} not found or has no owner")
                return False, {"error": "Chatbot not found"}
            
            user_id = chatbot.user_id
            
            # Get user's subscription and plan
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            if not subscription_data or not subscription_data.get('is_active'):
                logger.warning(f"User {user_id} has no active subscription")
                return False, {"error": "No active subscription", "subscription_required": True}
            
            # Get conversation limit from plan
            plan = subscription_data.get('plan', {})
            conversation_limit = plan.get('max_conversations_per_month', 1000)  # Default to 1000
            
            # Get current usage
            current_usage = ConversationUsage.get_current_usage(chatbot_id, user_id)
            
            # Check if limit is exceeded
            limit_exceeded = current_usage >= conversation_limit
            remaining_conversations = max(0, conversation_limit - current_usage)
            
            usage_info = {
                "current_usage": current_usage,
                "conversation_limit": conversation_limit,
                "remaining_conversations": remaining_conversations,
                "limit_exceeded": limit_exceeded,
                "plan_name": plan.get('name', 'Unknown'),
                "chatbot_id": chatbot_id,
                "user_id": user_id
            }
            
            if limit_exceeded:
                logger.warning(f"Conversation limit exceeded for chatbot {chatbot_id}: {current_usage}/{conversation_limit}")
                usage_info["error"] = "Monthly conversation limit exceeded"
                return False, usage_info
            
            return True, usage_info
            
        except Exception as e:
            logger.error(f"Error checking conversation limit for chatbot {chatbot_id}: {str(e)}")
            return False, {"error": "Failed to check conversation limit"}
    
    @staticmethod
    def record_conversation(chatbot_id: str) -> bool:
        """
        Record a conversation and increment the usage count.
        
        Returns:
            bool: True if recorded successfully, False otherwise
        """
        try:
            # Get chatbot and owner information
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot or not chatbot.user_id:
                logger.error(f"Chatbot {chatbot_id} not found or has no owner")
                return False
            
            user_id = chatbot.user_id
            
            # Record the conversation
            ConversationUsage.increment_conversation_count(chatbot_id, user_id)
            logger.info(f"Recorded conversation for chatbot {chatbot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording conversation for chatbot {chatbot_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_usage_summary(user_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        Get conversation usage summary for a user's chatbots.
        
        Returns:
            Dict containing usage summary for all user's chatbots
        """
        try:
            now = datetime.now(timezone.utc)
            if year is None:
                year = now.year
            if month is None:
                month = now.month
            
            # Get user's subscription to determine limits
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            conversation_limit = 1000  # Default
            plan_name = "Unknown"
            
            if subscription_data and subscription_data.get('plan'):
                conversation_limit = subscription_data['plan'].get('max_conversations_per_month', 1000)
                plan_name = subscription_data['plan'].get('name', 'Unknown')
            
            # Get usage records for the user's chatbots
            usage_records = ConversationUsage.get_usage_for_user_chatbots(user_id, year, month)
            
            chatbot_usage = []
            total_usage = 0
            
            for usage in usage_records:
                chatbot = Chatbot.query.get(usage.chatbot_id)
                chatbot_name = chatbot.name if chatbot else "Unknown"
                
                chatbot_info = {
                    "chatbot_id": usage.chatbot_id,
                    "chatbot_name": chatbot_name,
                    "conversation_count": usage.conversation_count,
                    "conversation_limit": conversation_limit,
                    "remaining_conversations": max(0, conversation_limit - usage.conversation_count),
                    "limit_exceeded": usage.conversation_count >= conversation_limit,
                    "last_conversation_at": usage.last_conversation_at.isoformat() if usage.last_conversation_at else None,
                    "usage_percentage": round((usage.conversation_count / conversation_limit) * 100, 1) if conversation_limit > 0 else 0
                }
                
                chatbot_usage.append(chatbot_info)
                total_usage += usage.conversation_count
            
            # Get all user's chatbots to include those with zero usage
            user_chatbots = Chatbot.query.filter_by(user_id=user_id).all()
            tracked_chatbot_ids = {usage.chatbot_id for usage in usage_records}
            
            for chatbot in user_chatbots:
                if chatbot.id not in tracked_chatbot_ids:
                    chatbot_info = {
                        "chatbot_id": chatbot.id,
                        "chatbot_name": chatbot.name,
                        "conversation_count": 0,
                        "conversation_limit": conversation_limit,
                        "remaining_conversations": conversation_limit,
                        "limit_exceeded": False,
                        "last_conversation_at": None,
                        "usage_percentage": 0
                    }
                    chatbot_usage.append(chatbot_info)
            
            summary = {
                "user_id": user_id,
                "year": year,
                "month": month,
                "plan_name": plan_name,
                "conversation_limit_per_chatbot": conversation_limit,
                "total_conversations_used": total_usage,
                "chatbot_count": len(chatbot_usage),
                "chatbots": chatbot_usage,
                "has_exceeded_limits": any(cb["limit_exceeded"] for cb in chatbot_usage)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting usage summary for user {user_id}: {str(e)}")
            return {"error": "Failed to get usage summary"}
    
    @staticmethod
    def get_chatbot_usage_info(chatbot_id: str) -> Dict[str, Any]:
        """
        Get detailed usage information for a specific chatbot.
        
        Returns:
            Dict containing detailed usage info
        """
        try:
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot or not chatbot.user_id:
                return {"error": "Chatbot not found"}
            
            user_id = chatbot.user_id
            
            # Get subscription and plan info
            subscription_data = SubscriptionService.get_user_subscription(user_id)
            conversation_limit = 1000
            plan_name = "Unknown"
            
            if subscription_data and subscription_data.get('plan'):
                conversation_limit = subscription_data['plan'].get('max_conversations_per_month', 1000)
                plan_name = subscription_data['plan'].get('name', 'Unknown')
            
            # Get current usage
            current_usage = ConversationUsage.get_current_usage(chatbot_id, user_id)
            
            # Get usage record for additional info
            now = datetime.now(timezone.utc)
            usage_record = ConversationUsage.query.filter_by(
                chatbot_id=chatbot_id,
                user_id=user_id,
                year=now.year,
                month=now.month
            ).first()
            
            info = {
                "chatbot_id": chatbot_id,
                "chatbot_name": chatbot.name,
                "user_id": user_id,
                "plan_name": plan_name,
                "current_month": f"{now.year}-{now.month:02d}",
                "conversation_count": current_usage,
                "conversation_limit": conversation_limit,
                "remaining_conversations": max(0, conversation_limit - current_usage),
                "limit_exceeded": current_usage >= conversation_limit,
                "usage_percentage": round((current_usage / conversation_limit) * 100, 1) if conversation_limit > 0 else 0,
                "last_conversation_at": usage_record.last_conversation_at.isoformat() if usage_record and usage_record.last_conversation_at else None
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting usage info for chatbot {chatbot_id}: {str(e)}")
            return {"error": "Failed to get usage info"} 