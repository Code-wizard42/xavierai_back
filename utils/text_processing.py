"""
Text processing utilities for chatbot knowledge base.
Provides functions for chunking, cleaning, and preprocessing text.
"""

import re
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

# Ensure NLTK resources are downloaded - skip in fast mode
# if not os.environ.get('FAST_MODE') and not os.environ.get('DISABLE_NLTK'):
#     try:
#         nltk.download('punkt', quiet=True)
#     except Exception as e:
#         logging.warning(f"Failed to download NLTK punkt: {str(e)}")
# else:
#     logging.info("NLTK downloads skipped in text processing (Fast Mode)")

class TextProcessor:
    """Text processing utilities for chatbot knowledge base."""
    
    def __init__(self, 
                 chunk_size: int = 800,  # Increased from 500 for more context per chunk
                 chunk_overlap: int = 200,  # Increased from 100 for better continuity
                 min_chunk_size: int = 100):  # Increased from 50 to avoid tiny chunks
        """Initialize the text processor.
        
        Args:
            chunk_size: Target size of text chunks in characters (800 for better context)
            chunk_overlap: Overlap between chunks in characters (200 for continuity)
            min_chunk_size: Minimum size of a chunk to be included (100 to avoid fragments)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that don't add meaning
        text = re.sub(r'[^\w\s.,;:!?\'"\-()]', ' ', text)
        
        # Normalize whitespace again
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of approximately equal size.
        
        Args:
            text: Input text
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Try to split by sentences first
        try:
            sentences = sent_tokenize(text)
            
            chunks = []
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                sentence_len = len(sentence)
                
                # If a single sentence is longer than chunk_size, split it further
                if sentence_len > self.chunk_size:
                    # Add any existing chunk if not empty
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_length = 0
                    
                    # Add long sentence as its own chunk(s)
                    for i in range(0, sentence_len, self.chunk_size - self.chunk_overlap):
                        chunk = sentence[i:i + self.chunk_size]
                        if len(chunk) >= self.min_chunk_size:
                            chunks.append(chunk)
                
                # If adding this sentence would exceed the chunk size, start a new chunk
                elif current_length + sentence_len > self.chunk_size:
                    # Only add the current chunk if it's not empty and meets the minimum size
                    if current_chunk and len(" ".join(current_chunk)) >= self.min_chunk_size:
                        chunks.append(" ".join(current_chunk))
                    
                    # Start a new chunk with the current sentence
                    current_chunk = [sentence]
                    current_length = sentence_len
                else:
                    # Add sentence to the current chunk
                    current_chunk.append(sentence)
                    current_length += sentence_len
            
            # Add the last chunk if not empty
            if current_chunk and len(" ".join(current_chunk)) >= self.min_chunk_size:
                chunks.append(" ".join(current_chunk))
                
            return chunks
        except Exception as e:
            logging.error(f"Error chunking text: {str(e)}")
            
            # Fall back to simple character-based chunking
            chunks = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk = text[i:i + self.chunk_size]
                if len(chunk) >= self.min_chunk_size:
                    chunks.append(chunk)
            
            return chunks
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of documents into chunks with metadata.
        
        Args:
            documents: List of document dictionaries with 'text' field
            
        Returns:
            List of chunk dictionaries with 'content' and 'metadata' fields
        """
        chunks = []
        
        try:
            for doc in documents:
                # Ensure document has text field
                if not doc or 'text' not in doc or not doc['text']:
                    continue
                
                # Get text and metadata
                text = doc['text']
                metadata = {k: v for k, v in doc.items() if k != 'text'}
                
                # Clean text
                cleaned_text = self.clean_text(text)
                
                # Chunk text
                text_chunks = self.chunk_text(cleaned_text)
                
                # Create chunk objects
                for i, chunk_text in enumerate(text_chunks):
                    chunk = {
                        'content': chunk_text,
                        'metadata': {
                            **metadata,
                            'chunk_index': i
                        }
                    }
                    chunks.append(chunk)
                
            logging.info(f"Processed {len(documents)} documents into {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logging.error(f"Error processing documents: {str(e)}")
            
            # Create at least one chunk from each document as fallback
            fallback_chunks = []
            for i, doc in enumerate(documents):
                if not doc or 'text' not in doc or not doc['text']:
                    continue
                
                text = str(doc['text'])[:1000]  # Limit to 1000 chars for fallback
                metadata = {k: v for k, v in doc.items() if k != 'text'}
                
                fallback_chunks.append({
                    'content': text,
                    'metadata': {
                        **metadata,
                        'chunk_index': 0,
                        'is_fallback': True
                    }
                })
            
            logging.info(f"Created {len(fallback_chunks)} fallback chunks")
            return fallback_chunks

# Create a singleton instance
text_processor = TextProcessor()
