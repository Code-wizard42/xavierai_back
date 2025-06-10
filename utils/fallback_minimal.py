"""
Fallback functions for when AI/ML dependencies are not available.
This allows the app to run without heavy dependencies while providing basic functionality.
"""
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def simple_text_similarity(text1: str, text2: str) -> float:
    """Simple text similarity without numpy or advanced NLP."""
    if not text1 or not text2:
        return 0.0
    
    # Convert to lowercase and split into words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

def basic_text_search(query: str, documents: List[Dict[str, Any]], threshold: float = 0.1) -> List[Dict[str, Any]]:
    """Basic text search without vector embeddings."""
    if not query or not documents:
        return []
    
    results = []
    for doc in documents:
        content = doc.get('content', '')
        similarity = simple_text_similarity(query, content)
        
        if similarity >= threshold:
            doc_copy = doc.copy()
            doc_copy['similarity'] = similarity
            results.append(doc_copy)
    
    # Sort by similarity (descending)
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:5]  # Return top 5 results

def basic_sentiment_analysis(text: str) -> str:
    """Basic sentiment analysis without NLTK."""
    if not text:
        return "neutral"
    
    text_lower = text.lower()
    
    # Simple positive/negative word lists
    positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'happy', 'pleased']
    negative_words = ['bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'angry', 'frustrated', 'disappointed', 'sad']
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

def basic_text_cleanup(text: str) -> str:
    """Basic text cleanup without advanced NLP."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters (keep basic punctuation)
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    return text.strip()

def mock_embedding_search(query: str, chatbot_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
    """Mock embedding search that returns empty results."""
    logger.warning(f"Vector search not available. Query: {query}, Chatbot: {chatbot_id}")
    return []

def mock_generate_embedding(text: str) -> List[float]:
    """Mock embedding generation."""
    logger.warning("Embedding generation not available")
    return [0.0] * 384  # Return zero vector of typical embedding size 