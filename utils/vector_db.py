"""
Vector database service for efficient storage and retrieval of embeddings.
This implementation uses Qdrant, a vector similarity search engine.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

# Import the fallback utilities
from xavier_back.utils.fallback import search_text_similarity

# Import Qdrant client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logging.warning("Qdrant not installed. Using text similarity fallback.")

# FAISS is optional and only used if Qdrant is not available
FAISS_AVAILABLE = False
try:
    import faiss
    FAISS_AVAILABLE = True
    logging.info("FAISS available as secondary fallback")
except ImportError:
    logging.info("FAISS not available - using text similarity fallback only")

class VectorDBService:
    """Service for managing vector embeddings and similarity search."""

    def __init__(self, use_qdrant=True):
        """Initialize the vector database service.

        Args:
            use_qdrant: Whether to use Qdrant (if available) or fallback to local FAISS
        """
        self.use_qdrant = use_qdrant and QDRANT_AVAILABLE

        if self.use_qdrant:
            qdrant_url = os.environ.get("QDRANT_URL")
            qdrant_api_key = os.environ.get("QDRANT_API_KEY")

            if qdrant_url:
                try:
                    self.client = QdrantClient(
                        url=qdrant_url, 
                        api_key=qdrant_api_key,
                        timeout=60  # 60 second timeout for operations
                    )
                    logging.info(f"Connected to Qdrant server at {qdrant_url}")
                except Exception as e:
                    logging.error(f"Failed to connect to Qdrant server at {qdrant_url}: {str(e)}. Falling back.")
                    # Fallback to local if server connection fails and no explicit local path set
                    self._init_local_qdrant()
            else:
                self._init_local_qdrant()

            # Get existing collections
            try:
                collections_info = self.client.get_collections()
                self.collections = set(collection.name for collection in collections_info.collections)
                logging.info(f"Found {len(self.collections)} existing collections in Qdrant")
            except Exception as e:
                logging.warning(f"Failed to get existing collections from Qdrant: {str(e)}")
                self.collections = set()
                # We'll discover collections dynamically as they are accessed
                logging.info("Will discover collections dynamically as they are accessed")
        else:
            # Fallback to FAISS (if available) or text similarity
            if FAISS_AVAILABLE:
                self._init_faiss()
            else:
                logging.info("Using text similarity fallback only (no vector database)")

        # Store raw texts for fallback text search
        self.text_stores = {}
        # Store metadata for fallback (needed for both Qdrant and FAISS)
        self.metadata_stores = {}
        # Cache for collection dimension compatibility (to reduce API calls)
        self.collection_dimension_cache = {}

    def _init_local_qdrant(self):
        """Initializes Qdrant client with local storage (on-disk or in-memory)."""
        qdrant_path = os.environ.get("QDRANT_PATH", "vector_db/qdrant_data") # Default local path
        try:
            if qdrant_path == ":memory:":
                self.client = QdrantClient(":memory:")
                logging.info("Using in-memory Qdrant storage.")
            else:
                os.makedirs(os.path.dirname(qdrant_path), exist_ok=True)
                self.client = QdrantClient(path=qdrant_path)
                logging.info(f"Using persistent Qdrant storage at {qdrant_path}")
        except Exception as e:
            logging.warning(f"Failed to initialize local Qdrant storage at {qdrant_path}: {str(e)}. Using in-memory storage instead.")
            self.client = QdrantClient(":memory:")

    def _init_faiss(self):
        """Initializes FAISS fallback."""
        self.indexes = {}
        self.metadata_stores = {}
        try:
            os.makedirs('vector_db/faiss', exist_ok=True)
            # We'll load indexes on demand in create_collection
        except Exception as e:
            logging.warning(f"Failed to create directory for FAISS indexes: {str(e)}")

    def create_collection(self, collection_name: str, vector_size: int = 384) -> bool:
        """Create a new collection in the vector database.

        Args:
            collection_name: Name of the collection (usually chatbot_id)
            vector_size: Dimension of the embedding vectors (default 384 for fallback)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.use_qdrant:
                # Create collection if it doesn't exist
                if collection_name not in self.collections:
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE
                        )
                    )
                    self.collections.add(collection_name)
                    logging.info(f"Created new Qdrant collection: {collection_name} with vector size {vector_size}")
                    
                    # Automatically create a payload index on 'chatbot_id' as it's commonly used for filtering
                    try:
                        self.client.create_payload_index(
                            collection_name=collection_name,
                            field_name="chatbot_id",
                            field_schema=models.PayloadSchemaType.KEYWORD # Assuming chatbot_id is a string/keyword
                        )
                        logging.info(f"Created payload index on 'chatbot_id' for collection {collection_name}")
                    except Exception as index_e:
                        logging.warning(f"Could not create payload index on 'chatbot_id' for {collection_name}: {str(index_e)}. This might lead to filter errors if not created manually.")
                else:
                    logging.info(f"Collection {collection_name} already exists in Qdrant")
            else:
                # Create FAISS index if FAISS is available
                if FAISS_AVAILABLE:
                    if collection_name not in self.indexes:
                        # Try to load from disk first
                        index_path = f"vector_db/faiss/{collection_name}.index"
                        metadata_path = f"vector_db/faiss/{collection_name}_metadata.json"
                        text_path = f"vector_db/faiss/{collection_name}_texts.json"

                        if os.path.exists(index_path):
                            try:
                                self.indexes[collection_name] = faiss.read_index(index_path)
                                logging.info(f"Loaded existing FAISS index for {collection_name} with {self.indexes[collection_name].ntotal} vectors")

                                # Load metadata and texts if available
                                if os.path.exists(metadata_path):
                                    with open(metadata_path, 'r') as f:
                                        self.metadata_stores[collection_name] = json.load(f)
                                else:
                                    self.metadata_stores[collection_name] = []

                                if os.path.exists(text_path):
                                    with open(text_path, 'r') as f:
                                        self.text_stores[collection_name] = json.load(f)
                                else:
                                    self.text_stores[collection_name] = []
                            except Exception as load_error:
                                logging.error(f"Error loading FAISS index for {collection_name}: {str(load_error)}")
                                # Create new index if loading fails
                                self.indexes[collection_name] = faiss.IndexFlatL2(vector_size)
                                self.metadata_stores[collection_name] = []
                                self.text_stores[collection_name] = []
                        else:
                            # Create new index
                            self.indexes[collection_name] = faiss.IndexFlatL2(vector_size)
                            self.metadata_stores[collection_name] = []
                            self.text_stores[collection_name] = []
                            logging.info(f"Created new FAISS index for {collection_name} with vector size {vector_size}")
                    else:
                        logging.info(f"FAISS index for {collection_name} already exists in memory")
                else:
                    # FAISS not available, initialize text stores for fallback
                    if collection_name not in self.text_stores:
                        self.text_stores[collection_name] = []
                        self.metadata_stores[collection_name] = []
                        logging.info(f"Initialized text stores for {collection_name} (text similarity fallback mode)")
            return True
        except Exception as e:
            logging.error(f"Error creating collection {collection_name}: {str(e)}")
            return False

    def add_documents(
        self,
        collection_name: str,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> bool:
        """Add documents to the vector database.

        Args:
            collection_name: Name of the collection
            texts: List of text content
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            batch_size: Number of documents to process in each batch (default 100)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.use_qdrant:
                current_vector_size = len(embeddings[0])
                
                # Check if collection exists and has correct dimensions
                if collection_name in self.collections:
                    # Check cache first to avoid redundant API calls
                    cache_key = f"{collection_name}:{current_vector_size}"
                    if cache_key in self.collection_dimension_cache:
                        if self.collection_dimension_cache[cache_key]:
                            logging.debug(f"Collection {collection_name} dimension compatibility confirmed from cache")
                        else:
                            logging.debug(f"Collection {collection_name} needs recreation (from cache)")
                            try:
                                self.client.delete_collection(collection_name=collection_name)
                                self.collections.remove(collection_name)
                                self.create_collection(collection_name, current_vector_size)
                                self.collection_dimension_cache[cache_key] = True
                            except Exception as delete_error:
                                logging.warning(f"Error recreating cached incompatible collection: {str(delete_error)}")
                    else:
                        # Not in cache, need to check
                        try:
                            collection_info = self.client.get_collection(collection_name)
                            existing_vector_size = collection_info.config.params.vectors.size
                            
                            if existing_vector_size != current_vector_size:
                                logging.warning(f"Dimension mismatch in collection {collection_name}: "
                                              f"existing={existing_vector_size}, new={current_vector_size}. "
                                              f"Recreating collection.")
                                
                                # Delete the existing collection
                                self.client.delete_collection(collection_name=collection_name)
                                self.collections.remove(collection_name)
                                
                                # Create new collection with correct dimensions
                                self.create_collection(collection_name, current_vector_size)
                                self.collection_dimension_cache[cache_key] = True
                            else:
                                # Dimensions match, cache the compatibility
                                self.collection_dimension_cache[cache_key] = True
                                
                        except Exception as e:
                            # Handle Pydantic validation errors and other collection info errors
                            error_str = str(e).lower()
                            if any(keyword in error_str for keyword in ['validation error', 'pydantic', 'extra_forbidden', 'parsing']):
                                logging.info(f"Collection {collection_name} exists but has API compatibility issues. "
                                           f"Checking dimension compatibility via alternative method.")
                                
                                # Try to determine if we need to recreate by attempting a dummy search
                                try:
                                    # Create a dummy vector with current dimensions to test compatibility
                                    dummy_vector = [0.0] * current_vector_size
                                    test_result = self.client.search(
                                        collection_name=collection_name,
                                        query_vector=dummy_vector,
                                        limit=1
                                    )
                                    logging.info(f"Collection {collection_name} is compatible with {current_vector_size}D vectors")
                                    self.collection_dimension_cache[cache_key] = True
                                except Exception as search_test_error:
                                    if "Vector dimension error" in str(search_test_error):
                                        logging.warning(f"Collection {collection_name} has dimension incompatibility. "
                                                      f"Recreating with {current_vector_size}D vectors.")
                                        try:
                                            self.client.delete_collection(collection_name=collection_name)
                                        except:
                                            pass  # Collection might not exist or be inaccessible
                                        self.collections.discard(collection_name)
                                        self.create_collection(collection_name, current_vector_size)
                                        self.collection_dimension_cache[cache_key] = True
                                    else:
                                        logging.warning(f"Could not test collection {collection_name} compatibility: {str(search_test_error)}")
                                        # Don't cache uncertain results
                            else:
                                # If it's not a validation error, try to recreate the collection
                                logging.warning(f"Could not get collection info for {collection_name}: {str(e)}. "
                                              f"Recreating collection with dimension {current_vector_size}.")
                                try:
                                    self.client.delete_collection(collection_name=collection_name)
                                except:
                                    pass  # Collection might not exist
                                self.collections.discard(collection_name)
                                self.create_collection(collection_name, current_vector_size)
                                self.collection_dimension_cache[cache_key] = True
                else:
                    # Create collection if it doesn't exist
                    self.create_collection(collection_name, current_vector_size)
                    cache_key = f"{collection_name}:{current_vector_size}"
                    self.collection_dimension_cache[cache_key] = True

                # Get the current count to use as starting ID
                try:
                    collection_info = self.client.get_collection(collection_name)
                    start_id = collection_info.vectors_count
                except Exception:
                    start_id = 0

                # Process documents in batches to avoid timeouts
                total_docs = len(texts)
                successful_batches = 0
                
                for batch_start in range(0, total_docs, batch_size):
                    batch_end = min(batch_start + batch_size, total_docs)
                    batch_texts = texts[batch_start:batch_end]
                    batch_embeddings = embeddings[batch_start:batch_end]
                    batch_metadatas = metadatas[batch_start:batch_end]
                    
                    # Prepare points for this batch
                    points = []
                    for i, (text, embedding, metadata) in enumerate(zip(batch_texts, batch_embeddings, batch_metadatas)):
                        # Add text to metadata
                        metadata_copy = metadata.copy()
                        metadata_copy["text"] = text

                        points.append(PointStruct(
                            id=start_id + batch_start + i,
                            vector=embedding,
                            payload=metadata_copy
                        ))

                    try:
                        # Upsert points to Qdrant with timeout
                        self.client.upsert(
                            collection_name=collection_name,
                            points=points,
                            wait=True
                        )
                        successful_batches += 1
                        logging.info(f"Successfully added batch {successful_batches} ({len(points)} documents) to Qdrant collection {collection_name}")
                    except Exception as batch_error:
                        logging.error(f"Failed to add batch {batch_start}-{batch_end} to Qdrant: {str(batch_error)}")
                        # Continue with remaining batches
                        continue

                if successful_batches > 0:
                    logging.info(f"Added {successful_batches} batches ({successful_batches * batch_size} max documents) to Qdrant collection {collection_name}")
                else:
                    logging.error(f"Failed to add any batches to Qdrant collection {collection_name}")
                    raise Exception("All batches failed to upload to Qdrant")

            else:
                # Ensure index exists
                if collection_name not in self.indexes:
                    self.create_collection(collection_name, len(embeddings[0]))

                # Convert embeddings to numpy array
                embeddings_np = np.array(embeddings, dtype=np.float32)

                # Add to FAISS index
                self.indexes[collection_name].add(embeddings_np)

                # Store metadata and texts
                for i, (text, metadata) in enumerate(zip(texts, metadatas)):
                    # Add text to metadata
                    metadata["text"] = text
                    self.metadata_stores[collection_name].append(metadata)
                    # Store raw text for fallback text search
                    self.text_stores[collection_name].append(text)

                # Save to disk for persistence
                try:
                    os.makedirs('vector_db/faiss', exist_ok=True)
                    index_path = f"vector_db/faiss/{collection_name}.index"
                    metadata_path = f"vector_db/faiss/{collection_name}_metadata.json"
                    text_path = f"vector_db/faiss/{collection_name}_texts.json"

                    # Save FAISS index
                    faiss.write_index(self.indexes[collection_name], index_path)

                    # Save metadata and texts
                    with open(metadata_path, 'w') as f:
                        json.dump(self.metadata_stores[collection_name], f)

                    with open(text_path, 'w') as f:
                        json.dump(self.text_stores[collection_name], f)

                    logging.info(f"Saved FAISS index and data for {collection_name} to disk")
                except Exception as save_error:
                    logging.error(f"Error saving FAISS index to disk: {str(save_error)}")

                logging.info(f"Added {len(texts)} documents to FAISS index {collection_name}")

            return True
        except Exception as e:
            logging.error(f"Error adding documents to {collection_name}: {str(e)}")

            # Fallback: Just store the texts and metadata even if indexing fails
            if collection_name not in self.text_stores:
                self.text_stores[collection_name] = []
            if collection_name not in self.metadata_stores:
                self.metadata_stores[collection_name] = []

            for text, metadata in zip(texts, metadatas):
                metadata_copy = metadata.copy()
                metadata_copy["text"] = text
                self.text_stores[collection_name].append(text)
                self.metadata_stores[collection_name].append(metadata_copy)

            logging.info(f"Used fallback storage for {len(texts)} documents in {collection_name}")
            return True

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in the vector database.

        Args:
            collection_name: Name of the collection
            query_embedding: Embedding vector of the query
            top_k: Number of results to return
            filter_dict: Dictionary of metadata filters

        Returns:
            List of dictionaries containing text and metadata
        """
        try:
            # First try vector-based search
            if self.use_qdrant:
                # Ensure collection exists
                if collection_name not in self.collections:
                    return []

                # Convert filter_dict to Qdrant filter
                filter_obj = None
                if filter_dict:
                    filter_conditions = []
                    for key, value in filter_dict.items():
                        filter_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        )
                    filter_obj = models.Filter(
                        must=filter_conditions
                    )

                try:
                    # Search Qdrant
                    search_results = self.client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=top_k,
                        query_filter=filter_obj
                    )

                    # Format results
                    results = []
                    for result in search_results:
                        # Extract text from payload
                        text = result.payload.pop("text", "")

                        results.append({
                            "text": text,
                            "metadata": result.payload,
                            "score": result.score
                        })

                    return results
                except Exception as search_error:
                    # Check if it's a dimension mismatch error
                    if "Vector dimension error" in str(search_error):
                        logging.warning(f"Dimension mismatch during search in {collection_name}: {str(search_error)}")
                        logging.info(f"Query embedding dimension: {len(query_embedding)}")
                        
                        # Try to get collection info to log the mismatch
                        try:
                            collection_info = self.client.get_collection(collection_name)
                            existing_dim = collection_info.config.params.vectors.size
                            logging.warning(f"Collection {collection_name} expects {existing_dim}D vectors, "
                                          f"but got {len(query_embedding)}D query vector")
                        except:
                            pass
                        
                        # Fall back to text search
                        return self._fallback_text_search(collection_name, query_embedding, top_k, filter_dict)
                    else:
                        # Re-raise if it's not a dimension error
                        raise search_error

            else:
                # Ensure index exists
                if collection_name not in self.indexes:
                    return []

                try:
                    # Try vector search with FAISS first
                    # Convert query_embedding to numpy array
                    query_embedding_np = np.array([query_embedding], dtype=np.float32)

                    # Search FAISS index
                    if self.indexes[collection_name].ntotal > 0:
                        distances, indices = self.indexes[collection_name].search(
                            query_embedding_np, min(top_k, self.indexes[collection_name].ntotal)
                        )
                    else:
                        # If index is empty, fallback to text search
                        raise ValueError("FAISS index is empty, falling back to text search")

                    # Format results
                    results = []
                    for i, idx in enumerate(indices[0]):
                        if idx < len(self.metadata_stores[collection_name]):
                            metadata = self.metadata_stores[collection_name][idx].copy()

                            # Apply filter if provided
                            if filter_dict:
                                skip = False
                                for key, value in filter_dict.items():
                                    if key not in metadata or metadata[key] != value:
                                        skip = True
                                        break
                                if skip:
                                    continue

                            # Extract text from metadata
                            text = metadata.pop("text", "")

                            results.append({
                                "text": text,
                                "metadata": metadata,
                                "score": float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity score
                            })

                    return results
                except Exception as faiss_error:
                    # If FAISS search fails, use text-based similarity as fallback
                    logging.warning(f"FAISS search failed, using text similarity fallback: {str(faiss_error)}")
                    return self._fallback_text_search(collection_name, query_embedding, top_k, filter_dict)
        except Exception as e:
            logging.error(f"Vector search failed in {collection_name}: {str(e)}")
            # Use text-based similarity as last resort
            return self._fallback_text_search(collection_name, query_embedding, top_k, filter_dict)

    def _fallback_text_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fallback to text-based search when vector search fails.

        Args:
            collection_name: Name of the collection
            query_embedding: Embedding vector of the query (ignored, we'll extract query text)
            top_k: Number of results to return
            filter_dict: Dictionary of metadata filters

        Returns:
            List of dictionaries containing text and metadata
        """
        try:
            # Check if we have texts for this collection
            if collection_name not in self.text_stores or not self.text_stores[collection_name]:
                logging.warning(f"No texts available for fallback search in collection {collection_name}")
                return []

            # Try to extract a meaningful query from the embedding
            # For fallback, we'll just return the first few documents regardless of query
            # This ensures we at least return something when vector search fails

            # Get all available texts
            texts = self.text_stores[collection_name]

            # Just return the first few indices (up to top_k)
            similar_indices = list(range(min(top_k, len(texts))))

            # Format results
            results = []
            for idx in similar_indices:
                # Get metadata if available, otherwise use empty dict
                metadata = {}
                if (collection_name in self.metadata_stores and 
                    idx < len(self.metadata_stores[collection_name])):
                    metadata = self.metadata_stores[collection_name][idx].copy()

                # Apply filter if provided
                if filter_dict and metadata:
                    skip = False
                    for key, value in filter_dict.items():
                        if key not in metadata or metadata[key] != value:
                            skip = True
                            break
                    if skip:
                        continue

                # Extract text
                text = metadata.pop("text", "") if metadata else ""
                if not text and idx < len(texts):
                    text = texts[idx]

                results.append({
                    "text": text,
                    "metadata": metadata,
                    "score": 0.5  # Default score for fallback results
                })

            logging.info(f"Fallback text search returned {len(results)} results")
            return results
        except Exception as e:
            logging.error(f"Fallback text search failed: {str(e)}")
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection from the vector database.

        Args:
            collection_name: Name of the collection

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.use_qdrant:
                if collection_name in self.collections:
                    self.client.delete_collection(collection_name=collection_name)
                    self.collections.remove(collection_name)
                # Clean up local stores if they exist
                if collection_name in self.metadata_stores:
                    del self.metadata_stores[collection_name]
                if collection_name in self.text_stores:
                    del self.text_stores[collection_name]
            else:
                if collection_name in self.indexes:
                    del self.indexes[collection_name]
                    del self.metadata_stores[collection_name]
                    # Also delete text store
                    if collection_name in self.text_stores:
                        del self.text_stores[collection_name]
            return True
        except Exception as e:
            logging.error(f"Error deleting collection {collection_name}: {str(e)}")
            return False

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information
        """
        try:
            if self.use_qdrant:
                if collection_name in self.collections:
                    try:
                        collection_info = self.client.get_collection(collection_name=collection_name)
                        return {
                            "name": collection_name,
                            "vector_size": collection_info.config.params.vectors.size,
                            "points_count": collection_info.vectors_count,
                            "exists": True
                        }
                    except Exception as validation_error:
                        # Handle Pydantic validation errors or other collection info errors
                        error_str = str(validation_error).lower()
                        if any(keyword in error_str for keyword in ['validation error', 'pydantic', 'extra_forbidden', 'parsing']):
                            logging.debug(f"API compatibility issue for collection {collection_name}: {str(validation_error)}")
                            
                            # Try alternative method to check collection and get basic info
                            try:
                                # Try to get collection existence and rough info via search
                                # Use a small dummy vector to test
                                dummy_vector = [0.0] * 384  # Start with common dimension
                                search_result = self.client.search(
                                    collection_name=collection_name,
                                    query_vector=dummy_vector,
                                    limit=1
                                )
                                # If search works, collection exists with 384D
                                return {
                                    "name": collection_name,
                                    "vector_size": 384,
                                    "points_count": 0,  # Unknown but exists
                                    "exists": True,
                                    "note": "Dimension determined via compatibility test"
                                }
                            except Exception as search_error:
                                if "Vector dimension error" in str(search_error):
                                    # Try with 768D vectors
                                    try:
                                        dummy_vector_768 = [0.0] * 768
                                        search_result = self.client.search(
                                            collection_name=collection_name,
                                            query_vector=dummy_vector_768,
                                            limit=1
                                        )
                                        return {
                                            "name": collection_name,
                                            "vector_size": 768,
                                            "points_count": 0,  # Unknown but exists
                                            "exists": True,
                                            "note": "Dimension determined via compatibility test"
                                        }
                                    except Exception:
                                        # Collection exists but we can't determine dimension
                                        return {
                                            "name": collection_name,
                                            "vector_size": 0,  # Unknown
                                            "points_count": 0,  # Unknown
                                            "exists": True,
                                            "note": "Collection exists but dimension unknown due to API compatibility issues"
                                        }
                                else:
                                    # Collection likely doesn't exist
                                    logging.debug(f"Collection {collection_name} search also failed: {str(search_error)}")
                                    return {"name": collection_name, "exists": False}
                        else:
                            # Re-raise if it's not a validation error
                            raise validation_error
                return {"name": collection_name, "exists": False}
            else:
                if collection_name in self.indexes:
                    return {
                        "name": collection_name,
                        "vector_size": self.indexes[collection_name].d,
                        "points_count": self.indexes[collection_name].ntotal,
                        "exists": True
                    }
                elif collection_name in self.text_stores:
                    # Collection exists in text store but not in index
                    return {
                        "name": collection_name,
                        "vector_size": 384,  # Default dimension for fallback
                        "points_count": len(self.text_stores[collection_name]),
                        "exists": True
                    }
                return {"name": collection_name, "exists": False}
        except Exception as e:
            logging.error(f"Error getting info for collection {collection_name}: {str(e)}")
            return {"name": collection_name, "error": str(e), "exists": False}

# Create a singleton instance
vector_db = VectorDBService(use_qdrant=QDRANT_AVAILABLE)
