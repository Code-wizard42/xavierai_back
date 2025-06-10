"""
Embedding service for generating and managing text embeddings.
Supports multiple embedding providers with fallback options.
"""

import os
import logging
import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Union
import numpy as np
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import embedding providers
OPENAI_AVAILABLE = False
COHERE_AVAILABLE = False
TOGETHER_AVAILABLE = False
SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import openai
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    import cohere
    # Try to get API key from environment variable (check both variable names)
    COHERE_API_KEY = os.getenv('COHERE_API_KEY') or os.getenv('COHERE_CLIENT')

    if COHERE_API_KEY:
        cohere_client = cohere.Client(COHERE_API_KEY)
        COHERE_AVAILABLE = True
        print("Cohere client initialized successfully")
    else:
        print("Cohere API key not found in environment variables")
except ImportError:
    pass

try:
    from together import Together
    TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY')
    if TOGETHER_API_KEY:
        together_client = Together(api_key=TOGETHER_API_KEY)
        TOGETHER_AVAILABLE = True
        print("Together AI client initialized successfully")
    else:
        print("Together API key not found in environment variables")
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass

class EmbeddingService:
    """Service for generating and managing text embeddings."""

    def __init__(self,
                 provider: str = 'fallback',
                 model_name: str = None,
                 embedding_dim: int = 384,
                 cache_size: int = 1000):
        """Initialize the embedding service.

        Args:
            provider: Embedding provider ('openai', 'cohere', 'sentence-transformers', or 'fallback')
            model_name: Specific model name for the provider
            embedding_dim: Dimension of embeddings (for fallback)
            cache_size: Size of the LRU cache for embeddings
        """
        self.provider = provider
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.cache_size = cache_size

        # Initialize the selected provider
        self._initialize_provider()

        # Create embedding cache
        self.generate_embeddings = lru_cache(maxsize=cache_size)(self._generate_embeddings_uncached)

    def _initialize_provider(self):
        """Initialize the embedding provider based on availability."""
        # OPTIMIZATION: Prioritize local embeddings for speed
        if self.provider == 'auto':
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.provider = 'sentence-transformers'
                self.model_name = 'all-MiniLM-L6-v2'
                self.model = SentenceTransformer(self.model_name)
                logging.info(f"AUTO-SELECTED: Sentence Transformers (LOCAL - FASTEST) with model {self.model_name}")
                return
            elif TOGETHER_AVAILABLE:
                self.provider = 'together'
                self.model_name = 'togethercomputer/m2-bert-80M-8k-retrieval'
                logging.info(f"AUTO-SELECTED: Together AI (OPTIMIZED) with model {self.model_name}")
                return
            elif OPENAI_AVAILABLE:
                self.provider = 'openai'
                self.model_name = 'text-embedding-3-small'
                logging.info(f"AUTO-SELECTED: OpenAI with model {self.model_name}")
                return
        
        # Manual provider selection
        if self.provider == 'sentence-transformers' and SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model_name = self.model_name or 'all-MiniLM-L6-v2'
            self.model = SentenceTransformer(self.model_name)
            logging.info(f"Using Sentence Transformers embeddings with model {self.model_name}")
            return
        elif self.provider == 'together' and TOGETHER_AVAILABLE:
            # Always use the correct model name for Together AI
            self.model_name = 'togethercomputer/m2-bert-80M-8k-retrieval'
            logging.info(f"Using Together AI embeddings with model {self.model_name}")
            return
        elif self.provider == 'openai' and OPENAI_AVAILABLE:
            self.model_name = self.model_name or 'text-embedding-3-small'
            logging.info(f"Using OpenAI embeddings with model {self.model_name}")
            return
        elif self.provider == 'cohere' and COHERE_AVAILABLE:
            self.model_name = self.model_name or 'embed-english-v3.0'
            logging.info(f"Using Cohere embeddings with model {self.model_name}")
            return
        else:
            # Fall back to fallback provider
            self.provider = 'fallback'
            logging.warning(f"Requested provider not available. Using fallback random embeddings.")

    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        try:
            response = openai.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logging.error(f"Error generating OpenAI embeddings: {str(e)}")
            return self._generate_fallback_embeddings(texts)

    def _generate_cohere_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Cohere API.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        try:
            response = cohere_client.embed(
                texts=texts,
                model=self.model_name,
                input_type="search_document"  # Required parameter for newer Cohere API
            )
            return response.embeddings
        except Exception as e:
            logging.error(f"Error generating Cohere embeddings: {str(e)}")
            # Go directly to fallback embeddings to avoid loops
            return self._generate_fallback_embeddings(texts)

    def _generate_together_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Together AI API - OPTIMIZED VERSION.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        try:
            all_embeddings = []
            # INCREASED batch size for better performance
            batch_size = 50  # Increased from 10

            # Ensure we're using the correct model name
            model_name = 'togethercomputer/m2-bert-80M-8k-retrieval'

            start_time = time.time()
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                try:
                    # CRITICAL FIX: Send entire batch in ONE API call instead of individual calls
                    response = together_client.embeddings.create(
                        model=model_name,
                        input=batch  # Send entire batch at once!
                    )
                    
                    # Extract embeddings from batch response
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    
                    logging.info(f"Generated batch {i//batch_size + 1} ({len(batch)} embeddings)")
                    
                except Exception as batch_error:
                    logging.error(f"Error in batch embedding generation: {str(batch_error)}")
                    # Generate fallback embeddings for the entire failed batch
                    for text in batch:
                        embedding_dim = 768  # Together AI model dimension
                        np.random.seed(hash(text) % (2**32))
                        embedding = np.random.random(embedding_dim).astype(np.float32)
                        embedding = embedding / np.linalg.norm(embedding)
                        all_embeddings.append(embedding.tolist())

                # Reduced delay between batches
                if i + batch_size < len(texts):
                    time.sleep(0.05)  # Reduced from 0.1

            elapsed = time.time() - start_time
            logging.info(f"OPTIMIZED: Generated {len(all_embeddings)} embeddings with Together AI in {elapsed:.2f}s (was ~6 minutes!)")
            return all_embeddings
            
        except Exception as e:
            logging.error(f"Error generating Together AI embeddings: {str(e)}")
            return self._generate_fallback_embeddings(texts)

    def _generate_sentence_transformer_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logging.error(f"Error generating Sentence Transformers embeddings: {str(e)}")
            return self._generate_fallback_embeddings(texts)

    def _generate_fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate fallback random embeddings.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        # Get the correct embedding dimension based on the provider
        embedding_dim = self.get_embedding_dimension()
        logging.info(f"Generating fallback embeddings with dimension {embedding_dim}")

        # Generate deterministic "random" embeddings based on text hash
        embeddings = []
        for text in texts:
            # Create a hash of the text - ensure we get consistent embeddings for the same text
            text_hash = hashlib.md5(text.encode()).hexdigest()
            # Use the hash to seed a random number generator
            np.random.seed(int(text_hash, 16) % (2**32))
            # Generate a random embedding with the correct dimension
            embedding = np.random.random(embedding_dim).astype(np.float32)
            # Normalize to unit length
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())

        logging.info(f"Generated {len(embeddings)} deterministic fallback embeddings with dimension {len(embeddings[0])}")
        return embeddings

    def _generate_embeddings_uncached(self, text_key: str) -> List[float]:
        """Generate embeddings for a single text (for caching).

        Args:
            text_key: Text to embed

        Returns:
            Embedding vector
        """
        # Route to the appropriate provider
        if self.provider == 'together':
            embeddings = self._generate_together_embeddings([text_key])
            return embeddings[0]
        elif self.provider == 'openai':
            embeddings = self._generate_openai_embeddings([text_key])
            return embeddings[0]
        elif self.provider == 'cohere':
            embeddings = self._generate_cohere_embeddings([text_key])
            return embeddings[0]
        elif self.provider == 'sentence-transformers':
            embeddings = self._generate_sentence_transformer_embeddings([text_key])
            return embeddings[0]
        else:
            # Fallback embeddings
            embeddings = self._generate_fallback_embeddings([text_key])
            return embeddings[0]

    def get_embeddings(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """Get embeddings for multiple texts, with optimized batching.

        Args:
            texts: List of text strings
            batch_size: Batch size for API calls (increased default)

        Returns:
            List of embedding vectors
        """
        # OPTIMIZATION: Use direct batch processing instead of individual calls
        if len(texts) == 0:
            return []
        
        # Route directly to the appropriate batch method for maximum efficiency
        if self.provider == 'together':
            return self._generate_together_embeddings(texts)
        elif self.provider == 'openai':
            return self._generate_openai_embeddings(texts)
        elif self.provider == 'cohere':
            return self._generate_cohere_embeddings(texts)
        elif self.provider == 'sentence-transformers':
            return self._generate_sentence_transformer_embeddings(texts)
        else:
            return self._generate_fallback_embeddings(texts)

    def clear_cache(self):
        """Clear the embedding cache."""
        self.generate_embeddings.cache_clear()

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings.

        Returns:
            Embedding dimension
        """
        if self.provider == 'together':
            return 768  # Together AI m2-bert-80M-8k-retrieval dimension
        elif self.provider == 'openai':
            return 1536  # OpenAI text-embedding-3-small dimension
        elif self.provider == 'cohere':
            return 1024  # Cohere embed-english-v3.0 dimension
        elif self.provider == 'sentence-transformers':
            return 384  # all-MiniLM-L6-v2 dimension
        else:
            # Fallback dimension
            return 384

# Create a singleton instance optimized for deployment
embedding_service = EmbeddingService(provider='together')  # Use Together AI for deployment
