"""
Fallback utilities for embedding and LLM services.
This module provides simplified implementations that work without API keys.
"""

import logging
import hashlib
import numpy as np
import re
import os
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_fallback_embeddings(texts: List[str], dimension: int = 384) -> List[List[float]]:
    """Generate deterministic fallback embeddings for texts.
    
    Args:
        texts: List of text strings
        dimension: Embedding dimension
        
    Returns:
        List of embedding vectors
    """
    logger.info(f"Generating {len(texts)} fallback embeddings with dimension {dimension}")
    embeddings = []
    
    for text in texts:
        # Create a hash of the text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        # Use the hash to seed a random number generator
        np.random.seed(int(text_hash, 16) % (2**32))
        # Generate a random embedding with the correct dimension
        embedding = np.random.random(dimension).astype(np.float32)
        # Normalize to unit length
        embedding = embedding / np.linalg.norm(embedding)
        embeddings.append(embedding.tolist())
    
    return embeddings

def search_text_similarity(query: str, texts: List[str], top_k: int = 3) -> List[int]:
    """Simple text-based similarity search without embeddings.
    
    Args:
        query: Search query
        texts: List of text strings to search
        top_k: Number of results to return
        
    Returns:
        List of indices of most similar texts
    """
    # Simple word overlap similarity
    query_words = set(re.findall(r'\w+', query.lower()))
    
    similarities = []
    for i, text in enumerate(texts):
        text_words = set(re.findall(r'\w+', text.lower()))
        
        # Calculate jaccard similarity
        if not query_words or not text_words:
            similarities.append(0)
        else:
            intersection = len(query_words.intersection(text_words))
            union = len(query_words.union(text_words))
            similarities.append(intersection / union if union > 0 else 0)
    
    # Get indices of top_k most similar texts
    return sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]

def generate_simple_answer(question: str, context: List[str]) -> str:
    """Generate a simple answer when LLM is not available.
    
    Args:
        question: User's question
        context: List of relevant text chunks
        
    Returns:
        Generated answer
    """
    if not context:
        return "I don't have enough information to answer that question. Would you like to create a support ticket so someone can help you with this?"
    
    # Find most relevant context based on word overlap
    most_relevant_idx = search_text_similarity(question, context, top_k=1)[0]
    most_relevant = context[most_relevant_idx]
    
    # Create a simple response
    response = f"Based on the information available, I can provide this answer: {most_relevant}"
    
    # Truncate if too long
    if len(response) > 500:
        response = response[:497] + "..."
        
    return response

def ensure_directory_exists(dir_path: str) -> None:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Path to directory
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory: {dir_path}") 