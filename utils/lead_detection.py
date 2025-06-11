"""
Lead detection utility functions for Xavier AI.
This module provides functions to analyze conversations and detect potential lead opportunities.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keywords and phrases that might indicate lead intent
LEAD_INTENT_KEYWORDS = [
    # Product interest
    "pricing", "price", "cost", "how much", "subscription", "package", "plan", "trial",
    # Purchase intent
    "buy", "purchase", "interested in", "looking to", "want to get", "considering",
    # Information request
    "more information", "learn more", "tell me more", "details about", "features",
    # Contact request
    "contact", "call me", "email me", "reach out", "get in touch", "sales team",
    # Comparison
    "compare", "versus", "vs", "better than", "difference between",
    # Specific product mentions
    "enterprise", "premium", "professional", "basic", "starter",
    # Timing signals
    "when can i", "how soon", "available now", "launch", "release date"
]

# Phrases that indicate high purchase intent
HIGH_INTENT_PHRASES = [
    "i want to buy", "i need to purchase", "i'm ready to", "how do i sign up",
    "where can i buy", "i'd like to purchase", "can i get a quote", "pricing for",
    "how can i get", "i'm interested in buying", "i want to upgrade"
]

# Phrases that might indicate the user is just browsing or researching
LOW_INTENT_PHRASES = [
    "just looking", "just browsing", "just curious", "just wondering",
    "not interested", "no thanks", "maybe later", "not now"
]

def analyze_conversation(messages: List[Dict[str, Any]]) -> Tuple[bool, float, Optional[str]]:
    """
    Analyze a conversation to detect potential lead intent.

    Args:
        messages: List of conversation messages with 'user'/'bot' type and 'content'

    Returns:
        Tuple containing:
        - Boolean indicating if lead intent is detected
        - Confidence score (0-1)
        - Optional reason for the detection
    """
    if not messages or len(messages) < 2:
        return False, 0.0, None

    # Extract just the user messages
    user_messages = [msg['content'] for msg in messages if msg.get('type') == 'user']

    if not user_messages:
        return False, 0.0, None

    # Combine all user messages into one text for analysis
    combined_text = " ".join(user_messages).lower()

    # Initialize score
    score = 0.0
    reasons = []

    # Check for high intent phrases (strong indicators)
    for phrase in HIGH_INTENT_PHRASES:
        if phrase in combined_text:
            score += 0.4
            reasons.append(f"Used high intent phrase: '{phrase}'")
            break  # One strong phrase is enough

    # Check for lead intent keywords (moderate indicators)
    keyword_matches = []
    for keyword in LEAD_INTENT_KEYWORDS:
        if keyword in combined_text:
            score += 0.15
            keyword_matches.append(keyword)

    if keyword_matches:
        reasons.append(f"Used intent keywords: {', '.join(keyword_matches[:3])}")

    # Check for low intent phrases (negative indicators)
    for phrase in LOW_INTENT_PHRASES:
        if phrase in combined_text:
            score -= 0.3
            reasons.append(f"Used low intent phrase: '{phrase}'")

    # Check for question patterns about products/services
    product_question_pattern = re.compile(r"(how|what|when|where|which|who|can|does|do|is|are|will).{0,30}(product|service|plan|feature|work)")
    if product_question_pattern.search(combined_text):
        score += 0.2
        reasons.append("Asked specific questions about products/services")

    # Check for multiple messages (engagement indicator)
    if len(user_messages) >= 3:
        score += 0.1
        reasons.append("Sustained conversation engagement")

    # Check for message length (engagement indicator)
    if len(combined_text) > 200:
        score += 0.1
        reasons.append("Detailed messages indicating serious interest")

    # Normalize score to 0-1 range
    score = max(0.0, min(1.0, score))

    # Determine if this is a lead opportunity
    is_lead_opportunity = score >= 0.3  # Lower threshold for testing

    reason_text = None
    if reasons:
        reason_text = "; ".join(reasons)

    return is_lead_opportunity, score, reason_text

def should_suggest_lead_form(conversation_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Determine if a lead form should be suggested based on conversation analysis.

    Args:
        conversation_messages: List of conversation messages

    Returns:
        Dict with suggestion decision and metadata
    """
    try:
        is_lead, confidence, reason = analyze_conversation(conversation_messages)

        return {
            "suggest_lead": is_lead,
            "confidence": confidence,
            "reason": reason,
            "threshold_met": confidence >= 0.3  # Lower threshold for testing
        }
    except Exception as e:
        logger.error(f"Error in lead detection: {str(e)}")
        return {
            "suggest_lead": False,
            "confidence": 0.0,
            "reason": f"Error in analysis: {str(e)}",
            "threshold_met": False
        }
