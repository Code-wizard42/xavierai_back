"""
Analytics Service Module

This module contains business logic for analytics operations, separating it from the route handlers.
"""
import logging
import datetime
import os
from datetime import timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import Counter
from sqlalchemy import func, text, desc, and_
from sqlalchemy.exc import SQLAlchemyError
import nltk

from xavier_back.extensions import db
from xavier_back.models.question_analytics import QuestionAnalytics
from xavier_back.models.sentiment_analytics import SentimentAnalytics
from xavier_back.utils.cache_utils import cached, cache

logger = logging.getLogger(__name__)

# Cache TTL settings
ANALYTICS_TTL = 900  # 15 minutes
COMMON_QUESTIONS_TTL = 3600  # 1 hour

# Ensure NLTK resources are downloaded - skip in fast mode
# if not os.environ.get('FAST_MODE') and not os.environ.get('DISABLE_NLTK'):
#     try:
#         nltk.download('punkt', quiet=True)
#         nltk.download('averaged_perceptron_tagger', quiet=True)
#     except Exception as e:
#         logging.warning(f"Failed to download NLTK resources: {str(e)}")
# else:
#     logging.info("NLTK downloads skipped in analytics service (Fast Mode)")

class AnalyticsService:
    """Service class for analytics-related operations"""

    @staticmethod
    def track_question(chatbot_id: str, question_data: Dict[str, Any]) -> bool:
        """
        Track a question asked to a chatbot

        Args:
            chatbot_id: ID of the chatbot
            question_data: Dictionary with question details

        Returns:
            bool: True if tracking was successful, False otherwise
        """
        try:
            # Extract data from question_data
            question = question_data.get('question', '')
            answer = question_data.get('answer', '')
            conversation_id = question_data.get('conversation_id')
            
            # Create the QuestionAnalytics object
            analytics = QuestionAnalytics(
                chatbot_id=chatbot_id,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                question=question,
                answer=answer,
                created_at=datetime.datetime.now(datetime.timezone.utc),
                conversation_id=conversation_id
            )
            
            # Add to the database
            db.session.add(analytics)
            db.session.commit()
            
            # Invalidate analytics cache for this chatbot
            cache['invalidate'](f'analytics:{chatbot_id}')
            
            return True
        except Exception as e:
            logger.error(f"Database error tracking question: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    @cached('analytics', ttl=ANALYTICS_TTL)
    def get_chatbot_analytics(chatbot_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            days: Number of days to include in the analytics

        Returns:
            Dictionary with analytics data
        """
        try:
            # Calculate the date range
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get total questions count with optimized query
            total_questions = db.session.query(func.count(QuestionAnalytics.id))\
                .filter(
                    QuestionAnalytics.chatbot_id == chatbot_id,
                    QuestionAnalytics.timestamp >= start_date,
                    QuestionAnalytics.timestamp <= end_date
                ).scalar() or 0
            
            # Get questions by day with optimized query
            questions_by_day_raw = db.session.query(
                func.date_trunc('day', QuestionAnalytics.timestamp).label('day'),
                func.count(QuestionAnalytics.id).label('count')
            ).filter(
                QuestionAnalytics.chatbot_id == chatbot_id,
                QuestionAnalytics.timestamp >= start_date,
                QuestionAnalytics.timestamp <= end_date
            ).group_by(text('day')).order_by(text('day')).all()
            
            # Format the results
            questions_by_day = {
                day.strftime('%Y-%m-%d'): count
                for day, count in questions_by_day_raw
            }
            
            # Get unique conversation count
            unique_conversations = db.session.query(func.count(func.distinct(QuestionAnalytics.conversation_id)))\
                .filter(
                    QuestionAnalytics.chatbot_id == chatbot_id,
                    QuestionAnalytics.timestamp >= start_date,
                    QuestionAnalytics.timestamp <= end_date,
                    QuestionAnalytics.conversation_id != None
                ).scalar() or 0
            
            return {
                "total_questions": total_questions,
                "questions_by_day": questions_by_day,
                "unique_conversations": unique_conversations
            }
        except Exception as e:
            logger.error(f"Error getting chatbot analytics: {str(e)}")
            return {
                "total_questions": 0,
                "questions_by_day": {},
                "unique_conversations": 0,
                "error": str(e)
            }

    @staticmethod
    @cached('common_questions', ttl=COMMON_QUESTIONS_TTL)
    def get_common_questions(chatbot_id: str, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get the most common questions for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            limit: Maximum number of questions to return
            days: Number of days to look back

        Returns:
            List of common questions with counts
        """
        try:
            # Calculate the date range
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Use a more efficient query with SQL lower() function for case-insensitivity
            common_questions_raw = db.session.query(
                func.lower(QuestionAnalytics.question).label('question_lower'),
                func.count(QuestionAnalytics.id).label('count')
            ).filter(
                QuestionAnalytics.chatbot_id == chatbot_id,
                QuestionAnalytics.timestamp >= start_date,
                QuestionAnalytics.timestamp <= end_date
            ).group_by(text('question_lower'))\
             .order_by(desc('count'))\
             .limit(limit)\
             .all()

            # Format the results
            result = [
                {"question": question_lower, "count": count}
                for question_lower, count in common_questions_raw
            ]

            return result
        except Exception as e:
            logger.error(f"Error getting common questions: {str(e)}")
            return []

    @staticmethod
    @cached('question_timeline', ttl=ANALYTICS_TTL)
    def get_question_timeline(chatbot_id: str, interval: str = 'day', days: int = 30) -> List[Dict[str, Any]]:
        """
        Get a timeline of questions for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            interval: Time interval for grouping ('day', 'hour', 'week')
            days: Number of days to look back

        Returns:
            List of time periods with question counts
        """
        try:
            # Calculate the date range
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Validate interval
            if interval not in ['day', 'hour', 'week']:
                interval = 'day'  # Default to day
            
            # Use an optimized query with SQL date_trunc
            timeline_raw = db.session.query(
                func.date_trunc(interval, QuestionAnalytics.timestamp).label('period'),
                func.count(QuestionAnalytics.id).label('count')
            ).filter(
                QuestionAnalytics.chatbot_id == chatbot_id,
                QuestionAnalytics.timestamp >= start_date,
                QuestionAnalytics.timestamp <= end_date
            ).group_by(text('period'))\
             .order_by(text('period'))\
             .all()
            
            # Format the results
            result = [
                {
                    "period": period.strftime('%Y-%m-%d %H:%M:%S'),
                    "count": count
                }
                for period, count in timeline_raw
            ]
            
            return result
        except Exception as e:
            logger.error(f"Error getting question timeline: {str(e)}")
            return []

    @staticmethod
    def invalidate_analytics_cache(chatbot_id: str) -> bool:
        """
        Invalidate analytics cache for a chatbot

        Args:
            chatbot_id: The ID of the chatbot

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Invalidate all analytics caches for this chatbot
            cache['invalidate'](f'analytics:{chatbot_id}')
            cache['invalidate'](f'common_questions:{chatbot_id}')
            cache['invalidate'](f'question_timeline:{chatbot_id}')
            cache['invalidate'](f'question_clusters:{chatbot_id}')
            return True
        except Exception as e:
            logger.error(f"Error invalidating analytics cache: {str(e)}")
            return False
            
    @staticmethod
    @cached('question_clusters', ttl=ANALYTICS_TTL)
    def get_question_clusters(chatbot_id: str, num_clusters: int = 8, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get intelligent clusters of similar questions by topic using semantic analysis

        Args:
            chatbot_id: The ID of the chatbot
            num_clusters: Number of topic clusters to generate
            days: Number of days to look back

        Returns:
            List of topic clusters with representative questions
        """
        try:
            # Calculate the date range
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get questions from the period
            questions_raw = db.session.query(QuestionAnalytics.question)\
                .filter(
                    QuestionAnalytics.chatbot_id == chatbot_id,
                    QuestionAnalytics.timestamp >= start_date,
                    QuestionAnalytics.timestamp <= end_date
                ).all()
                
            questions = [q[0] for q in questions_raw if q[0] and len(q[0].strip()) > 0]
            
            # If we don't have enough questions, return empty result
            if len(questions) < 3:
                logger.warning(f"Not enough questions for clustering: {len(questions)}")
                return []
            
            # Smart topic detection using semantic patterns and intent analysis
            clusters = AnalyticsService._smart_topic_clustering(questions, num_clusters)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error clustering questions: {str(e)}")
            return []
    
    @staticmethod
    def _smart_topic_clustering(questions: List[str], max_clusters: int = 8) -> List[Dict[str, Any]]:
        """
        Intelligent topic clustering using semantic patterns and intent detection
        """
        import re
        from collections import defaultdict
        from nltk.tokenize import word_tokenize
        from nltk.tag import pos_tag
        
        # Define smart topic patterns with semantic understanding
        topic_patterns = {
            'Pricing & Billing': {
                'keywords': ['price', 'cost', 'billing', 'payment', 'subscription', 'plan', 'fee', 'charge', 'money', 'pay', 'invoice', 'refund', 'discount'],
                'patterns': [r'\b(how much|what.*cost|price|pricing|bill|payment|subscription|plan)\b'],
                'intent': 'pricing_inquiry'
            },
            'Technical Issues': {
                'keywords': ['error', 'problem', 'issue', 'bug', 'broken', 'not working', 'failed', 'crash', 'freeze', 'slow', 'loading'],
                'patterns': [r'\b(error|problem|issue|bug|broken|not working|failed|crash|freeze|slow)\b'],
                'intent': 'technical_support'
            },
            'Account Management': {
                'keywords': ['account', 'login', 'password', 'profile', 'settings', 'email', 'username', 'register', 'signup', 'access'],
                'patterns': [r'\b(account|login|password|profile|settings|email|username|register|signup|access)\b'],
                'intent': 'account_management'
            },
            'Product Features': {
                'keywords': ['feature', 'function', 'capability', 'option', 'tool', 'how to', 'can i', 'does it', 'support'],
                'patterns': [r'\b(how to|can i|does it|feature|function|capability|option|tool|support)\b'],
                'intent': 'feature_inquiry'
            },
            'Integration & API': {
                'keywords': ['integration', 'api', 'webhook', 'connect', 'sync', 'import', 'export', 'third party', 'plugin'],
                'patterns': [r'\b(integration|api|webhook|connect|sync|import|export|third party|plugin)\b'],
                'intent': 'integration_support'
            },
            'Getting Started': {
                'keywords': ['start', 'begin', 'setup', 'install', 'configure', 'tutorial', 'guide', 'first time', 'new user'],
                'patterns': [r'\b(start|begin|setup|install|configure|tutorial|guide|first time|new user|getting started)\b'],
                'intent': 'onboarding'
            },
            'Data & Analytics': {
                'keywords': ['data', 'analytics', 'report', 'statistics', 'metrics', 'dashboard', 'export', 'download'],
                'patterns': [r'\b(data|analytics|report|statistics|metrics|dashboard|export|download)\b'],
                'intent': 'data_inquiry'
            },
            'Security & Privacy': {
                'keywords': ['security', 'privacy', 'safe', 'secure', 'protection', 'gdpr', 'compliance', 'encrypt'],
                'patterns': [r'\b(security|privacy|safe|secure|protection|gdpr|compliance|encrypt)\b'],
                'intent': 'security_inquiry'
            }
        }
        
        # Classify questions into topics
        question_classifications = []
        for question in questions:
            question_lower = question.lower()
            scores = {}
            
            for topic_name, topic_data in topic_patterns.items():
                score = 0
                
                # Keyword matching with weighted scoring
                for keyword in topic_data['keywords']:
                    if keyword in question_lower:
                        # Give higher weight to exact matches
                        if f" {keyword} " in f" {question_lower} ":
                            score += 3
                        else:
                            score += 1
                
                # Pattern matching
                for pattern in topic_data['patterns']:
                    if re.search(pattern, question_lower, re.IGNORECASE):
                        score += 5
                
                scores[topic_name] = score
            
            # Find the best matching topic
            if scores and max(scores.values()) > 0:
                best_topic = max(scores, key=scores.get)
                confidence = scores[best_topic]
            else:
                best_topic = 'General Inquiries'
                confidence = 1
            
            question_classifications.append({
                'question': question,
                'topic': best_topic,
                'confidence': confidence
            })
        
        # Group questions by topic
        topic_groups = defaultdict(list)
        for classification in question_classifications:
            topic_groups[classification['topic']].append(classification)
        
        # Create clusters with enhanced metadata
        clusters = []
        for topic_name, topic_questions in topic_groups.items():
            if len(topic_questions) == 0:
                continue
                
            # Sort by confidence and take representative questions
            topic_questions.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Extract key terms from questions in this topic - NOUNS ONLY
            all_nouns = []
            for tq in topic_questions:
                try:
                    # Tokenize the question
                    tokens = word_tokenize(tq['question'].lower())
                    
                    # Get part-of-speech tags
                    pos_tags = pos_tag(tokens)
                    
                    # Extract only nouns (NN, NNS, NNP, NNPS)
                    nouns = [word for word, pos in pos_tags 
                           if pos in ['NN', 'NNS', 'NNP', 'NNPS'] and len(word) > 2]
                    
                    all_nouns.extend(nouns)
                except Exception as e:
                    # Fallback to simple word extraction if NLTK fails
                    logging.warning(f"NLTK processing failed for question '{tq['question']}': {str(e)}")
                    words = re.findall(r'\b\w{3,}\b', tq['question'].lower())
                    all_nouns.extend(words)
            
            # Define comprehensive stop words including common non-meaningful nouns
            stop_words = {
                'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
                'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
                'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
                'did', 'she', 'use', 'her', 'way', 'many', 'oil', 'sit', 'set', 'run', 
                'eat', 'far', 'sea', 'eye', 'ask', 'own', 'say', 'too', 'any', 'try', 
                'let', 'put', 'end', 'why', 'turn', 'here', 'show', 'every', 'good', 
                'me', 'give', 'our', 'under', 'name', 'very', 'through', 'just', 'form', 
                'sentence', 'great', 'think', 'where', 'help', 'much', 'before', 'move', 
                'right', 'too', 'means', 'old', 'any', 'same', 'tell', 'boy', 'follow', 
                'came', 'want', 'show', 'also', 'around', 'farm', 'three', 'small', 'set', 
                'put', 'end', 'does', 'another', 'well', 'large', 'must', 'big', 'even', 
                'such', 'because', 'turn', 'here', 'why', 'ask', 'went', 'men', 'read', 
                'need', 'land', 'different', 'home', 'us', 'move', 'try', 'kind', 'hand', 
                'picture', 'again', 'change', 'off', 'play', 'spell', 'air', 'away', 
                'animal', 'house', 'point', 'page', 'letter', 'mother', 'answer', 'found', 
                'study', 'still', 'learn', 'should', 'america', 'world', 'thing', 'things', 
                'way', 'ways', 'time', 'times', 'people', 'person', 'someone', 'something', 
                'somewhere', 'anybody', 'anyone', 'anything', 'anywhere', 'everybody', 
                'everyone', 'everything', 'everywhere', 'somebody', 'nobody', 'nothing', 
                'nowhere', 'guy', 'guys', 'stuff', 'lot', 'lots', 'part', 'parts', 
                'bit', 'bits', 'piece', 'pieces', 'place', 'places'
            }
            
            # Filter nouns and count frequency
            meaningful_nouns = [noun for noun in all_nouns 
                              if noun not in stop_words and len(noun) > 2]
            
            noun_counts = Counter(meaningful_nouns)
            top_terms = [noun for noun, _ in noun_counts.most_common(5)]
            
            # Get sample questions (up to 3 most representative)
            sample_questions = [tq['question'] for tq in topic_questions[:3]]
            
            cluster = {
                'topic': topic_name,
                'topic_terms': top_terms,
                'questions': sample_questions,
                'count': len(topic_questions),
                'question_count': len(topic_questions),
                'avg_confidence': sum(tq['confidence'] for tq in topic_questions) / len(topic_questions)
            }
            
            clusters.append(cluster)
        
        # Sort clusters by question count (most popular first)
        clusters.sort(key=lambda x: x['count'], reverse=True)
        
        # Limit to max_clusters
        return clusters[:max_clusters]
            
    @staticmethod
    def track_sentiment(chatbot_id: str, sentiment: bool, conversation_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Track user sentiment for a chat interaction

        Args:
            chatbot_id: ID of the chatbot
            sentiment: Boolean sentiment (True for positive, False for negative)
            conversation_id: Optional conversation ID

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create the SentimentAnalytics object
            sentiment_record = SentimentAnalytics(
                chatbot_id=chatbot_id,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                user_sentiment=sentiment,
                conversation_id=conversation_id
            )
            
            # Add to the database
            db.session.add(sentiment_record)
            db.session.commit()
            
            return True, None
        except Exception as e:
            logger.error(f"Error tracking sentiment: {str(e)}")
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_usage_patterns(chatbot_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get usage patterns and trends for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            days: Number of days to look back

        Returns:
            Dictionary with usage pattern data
        """
        try:
            # Calculate the date range
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Query for questions in the date range
            questions = QuestionAnalytics.query.filter(
                QuestionAnalytics.chatbot_id == chatbot_id,
                QuestionAnalytics.timestamp >= start_date,
                QuestionAnalytics.timestamp <= end_date
            ).all()

            # Count questions by day
            daily_counts = {}
            for q in questions:
                day = q.timestamp.strftime('%Y-%m-%d')
                if day not in daily_counts:
                    daily_counts[day] = 0
                daily_counts[day] += 1

            # Fill in missing days
            current_date = start_date
            while current_date <= end_date:
                day = current_date.strftime('%Y-%m-%d')
                if day not in daily_counts:
                    daily_counts[day] = 0
                current_date += timedelta(days=1)

            # Sort by date
            sorted_daily_counts = [
                {"date": day, "count": count}
                for day, count in sorted(daily_counts.items())
            ]

            # Count questions by hour
            hourly_counts = {}
            for q in questions:
                hour = q.timestamp.hour
                if hour not in hourly_counts:
                    hourly_counts[hour] = 0
                hourly_counts[hour] += 1

            # Fill in missing hours
            for hour in range(24):
                if hour not in hourly_counts:
                    hourly_counts[hour] = 0

            # Sort by hour
            sorted_hourly_counts = [
                {"hour": hour, "count": count}
                for hour, count in sorted(hourly_counts.items())
            ]

            # Count unique conversations safely
            unique_conversations = 0
            try:
                unique_conversations = len(set(q.conversation_id for q in questions if hasattr(q, 'conversation_id') and q.conversation_id))
            except Exception as e:
                logger.error(f"Error counting unique conversations: {str(e)}")

            return {
                "daily": sorted_daily_counts,
                "hourly": sorted_hourly_counts,
                "total_questions": len(questions),
                "unique_conversations": unique_conversations
            }
        except Exception as e:
            logger.error(f"Error getting usage patterns: {str(e)}")
            return {
                "daily": [],
                "hourly": [],
                "total_questions": 0,
                "unique_conversations": 0
            }

    @staticmethod
    def get_sentiment_analytics(chatbot_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get sentiment analytics for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            days: Number of days to look back

        Returns:
            Dictionary with sentiment analytics data
        """
        try:
            # Calculate the date range
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Query for sentiment records in the date range
            sentiments = SentimentAnalytics.query.filter(
                SentimentAnalytics.chatbot_id == chatbot_id,
                SentimentAnalytics.timestamp >= start_date,
                SentimentAnalytics.timestamp <= end_date
            ).all()

            # Count positive and negative sentiments
            total_records = len(sentiments)
            positive_count = sum(1 for s in sentiments if s.user_sentiment)
            negative_count = total_records - positive_count

            # Calculate satisfaction rate
            satisfaction_rate = (positive_count / total_records * 100) if total_records > 0 else 0

            # Count sentiments by day
            daily_sentiment = {}
            for s in sentiments:
                day = s.timestamp.strftime('%Y-%m-%d')
                if day not in daily_sentiment:
                    daily_sentiment[day] = {"positive": 0, "negative": 0}

                if s.user_sentiment:
                    daily_sentiment[day]["positive"] += 1
                else:
                    daily_sentiment[day]["negative"] += 1

            # Fill in missing days
            current_date = start_date
            while current_date <= end_date:
                day = current_date.strftime('%Y-%m-%d')
                if day not in daily_sentiment:
                    daily_sentiment[day] = {"positive": 0, "negative": 0}
                current_date += timedelta(days=1)

            # Sort by date
            sorted_daily_sentiment = [
                {
                    "date": day,
                    "positive": data["positive"],
                    "negative": data["negative"]
                }
                for day, data in sorted(daily_sentiment.items())
            ]

            return {
                "total_ratings": total_records,
                "positive_ratings": positive_count,
                "negative_ratings": negative_count,
                "satisfaction_rate": round(satisfaction_rate, 2),
                "daily_sentiment": sorted_daily_sentiment
            }
        except Exception as e:
            logger.error(f"Error getting sentiment analytics: {str(e)}")
            return {
                "total_ratings": 0,
                "positive_ratings": 0,
                "negative_ratings": 0,
                "satisfaction_rate": 0,
                "daily_sentiment": []
            }

    @staticmethod
    def get_dashboard_analytics(chatbot_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive dashboard analytics for a chatbot

        Args:
            chatbot_id: The ID of the chatbot
            days: Number of days to look back

        Returns:
            Dictionary with dashboard analytics data
        """
        try:
            # Get data from all analytics methods
            common_questions = AnalyticsService.get_common_questions(chatbot_id, days=days)
            clusters = AnalyticsService.get_question_clusters(chatbot_id, days=days)
            usage_patterns = AnalyticsService.get_usage_patterns(chatbot_id, days=days)
            sentiment_data = AnalyticsService.get_sentiment_analytics(chatbot_id, days=days)

            # Combine into a single dashboard
            dashboard = {
                "common_questions": {
                    "top_questions": common_questions,
                    "total_questions": usage_patterns.get("total_questions", 0)
                },
                "question_clusters": clusters,
                "usage_patterns": usage_patterns,
                "sentiment": sentiment_data,
                "days_analyzed": days
            }

            return dashboard
        except Exception as e:
            logger.error(f"Error getting dashboard analytics: {str(e)}")
            return {
                "error": str(e),
                "days_analyzed": days
            }
