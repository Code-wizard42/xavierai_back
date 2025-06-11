"""
Enhanced NLP utilities for chatbot question answering.
Uses vector database for efficient retrieval and context management.
"""

import json
import logging
import os
import time
from typing import List, Dict, Any, Optional, Union
from functools import lru_cache
import numpy as np
from dotenv import load_dotenv
from collections import Counter
from sqlalchemy import func, text, desc, and_
from sqlalchemy.exc import SQLAlchemyError
import nltk
import re
from difflib import SequenceMatcher
import random

# Import our custom services
from utils.vector_db import vector_db
from utils.text_processing import text_processor
from utils.embedding_service import embedding_service
from utils.cache_utils import cached, cache
from utils.response_formatter import response_formatter
from extensions import db
from models.question_analytics import QuestionAnalytics
from models.sentiment_analytics import SentimentAnalytics

# Load environment variables
load_dotenv()

# Initialize Groq client for LLM
try:
    from groq import Groq
    groq_token = os.getenv('GROQ_API_KEY')
    if groq_token:
        groq_client = Groq(api_key=groq_token)
    else:
        logging.warning("GROQ_API_KEY not found in environment variables")
        groq_client = None
except ImportError:
    logging.warning("Groq package not installed")
    groq_client = None

# Cache for parsed chatbot data
chatbot_data_cache = {}
CACHE_EXPIRY = 300
# Cache TTL settings
CHATBOT_DATA_TTL = 600  # 10 minutes
VECTOR_SEARCH_TTL = 300  # 5 minutes
LLM_RESPONSE_TTL = 1800  # 30 minutes
ANALYTICS_TTL = 900  # 15 minutes
COMMON_QUESTIONS_TTL = 3600  # 1 hour
ANSWER_CONFIDENCE_TTL = 300  # 5 minutes

# Confidence thresholds for different response strategies
CONFIDENCE_THRESHOLDS = {
    'HIGH': 70,      # Confident answer, provide direct response
    'MEDIUM': 50,    # Partial confidence, provide answer with disclaimer
    'LOW': 20,       # Low confidence, provide related info + alternatives
    'VERY_LOW': 0    # Very low confidence, suggest ticket as last resort
}

# Ensure NLTK resources are downloaded
# Skip NLTK downloads in development/fast mode
# if not os.environ.get('FAST_MODE') and not os.environ.get('DISABLE_NLTK'):
#     try:
#         nltk.download('punkt', quiet=True)
#         nltk.download('averaged_perceptron_tagger', quiet=True)
#         nltk.download('stopwords', quiet=True)
#     except Exception as e:
#         logging.warning(f"Failed to download NLTK resources: {str(e)}")
# else:
#     logging.info("NLTK downloads skipped (Fast Mode)")

def parse_chatbot_data(data: Union[str, Dict, List], chatbot_id: str) -> Optional[Dict[str, Any]]:
    """Parse chatbot data from various formats.

    Args:
        data: Chatbot data (string, dict, or list)
        chatbot_id: ID of the chatbot

    Returns:
        Dictionary with parsed data components or None if parsing fails
    """
    # Check cache first
    cache_key = f"{chatbot_id}_{hash(str(data))}"
    current_time = time.time()

    if cache_key in chatbot_data_cache:
        cached_data, timestamp = chatbot_data_cache[cache_key]
        if current_time - timestamp < CACHE_EXPIRY:
            return cached_data

    # Parse the data
    try:
        chatbot_data = None
        if isinstance(data, str):
            try:
                chatbot_data = json.loads(data)
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON for chatbot {chatbot_id}")
                return None
        else:
            chatbot_data = data

        # Log the data structure for debugging
        logging.info(f"Parsing chatbot data for {chatbot_id}, type: {type(chatbot_data)}")

        # Handle the 'sources' format (new format)
        if isinstance(chatbot_data, dict) and 'sources' in chatbot_data:
            logging.info(f"Found 'sources' in chatbot data for {chatbot_id}")
            sources = chatbot_data['sources']

            # Convert sources to the expected format
            pdf_data = []
            folder_data = []
            web_data = {}

            # Process each source
            if isinstance(sources, list):
                for source in sources:
                    if isinstance(source, dict):
                        source_type = source.get('type')
                        if source_type in ['file', 'pdf']:
                            # Use the full text instead of just the preview
                            pdf_data.append({
                                'filename': source.get('name', 'unknown'),
                                'text': source.get('text', source.get('preview', '')),
                                'page': 'file' if source_type == 'file' else 1
                            })
                        elif source_type == 'folder_file':
                            # Use the full text instead of just the preview
                            folder_data.append({
                                'filename': source.get('name', 'unknown'),
                                'text': source.get('text', source.get('preview', ''))
                            })
                        elif source_type == 'web':
                            if not web_data:
                                web_data = {
                                    'url': source.get('name', 'unknown'),
                                    'title': 'Web Content',
                                    'sections': []
                                }
                            # Use the full text instead of just the preview
                            web_data['sections'].append({
                                'heading': source.get('name', 'Web Content'),
                                'content': [source.get('text', source.get('preview', ''))]
                            })

            result = {
                'pdf_data': pdf_data,
                'folder_data': folder_data,
                'web_data': web_data
            }

            # Cache the result
            chatbot_data_cache[cache_key] = (result, current_time)
            logging.info(f"Parsed 'sources' format: {len(pdf_data)} PDF items, {len(folder_data)} folder items, {'web data present' if web_data else 'no web data'}")
            return result

        # Handle different data formats (legacy format)
        if isinstance(chatbot_data, list) and chatbot_data:
            chatbot_data = chatbot_data[-1]  # Get the latest data

        # Extract data components
        if isinstance(chatbot_data, dict):
            result = {
                'pdf_data': chatbot_data.get('pdf_data', []),
                'folder_data': chatbot_data.get('folder_data', []),
                'web_data': chatbot_data.get('web_data', {})
            }

            # Cache the result
            chatbot_data_cache[cache_key] = (result, current_time)
            logging.info(f"Parsed legacy format: {len(result['pdf_data'])} PDF items, {len(result['folder_data'])} folder items, {'web data present' if result['web_data'] else 'no web data'}")
            return result
        else:
            logging.warning(f"Unrecognized chatbot data format for {chatbot_id}")
            return None
    except Exception as e:
        logging.error(f"Error parsing chatbot data: {str(e)}")
        return None

def preprocess_and_index_data(chatbot_id: str, pdf_data: List[Dict[str, Any]] = None, folder_data: List[Dict[str, Any]] = None, web_data: List[Dict[str, Any]] = None, db_data: List[Dict[str, Any]] = None) -> tuple[bool, Union[str, Dict[str, Any]]]:
    """Preprocess and index chatbot data into the vector database.

    Args:
        chatbot_id: ID of the chatbot
        pdf_data: List of PDF/text file data dictionaries
        folder_data: List of folder content dictionaries
        web_data: List of web content dictionaries
        db_data: List of database content dictionaries

    Returns:
        Tuple: (success_boolean, message_or_data_map_dict)
               On success, dict contains {"processed_sources": [...], "message": "..."}
               On failure, dict contains {"message": "error description"}
    """
    if pdf_data is None: pdf_data = []
    if folder_data is None: folder_data = []
    if web_data is None: web_data = []
    if db_data is None: db_data = []

    processed_sources_metadata = [] # To store metadata like {"type": "file", "name": "..."}

    try:
        logging.info(f"Processing data for chatbot {chatbot_id}: {len(pdf_data)} PDF/text items, {len(folder_data)} folder items, {len(web_data)} web items, {len(db_data)} db items")

        all_documents = []

        # Process PDF data (which includes text files marked with 'page': 'file')
        for item in pdf_data:
            if isinstance(item, dict) and 'text' in item:
                filename = item.get('filename', 'unknown_pdf_or_file')
                source_type = "file" if item.get('page') == 'file' else "pdf_page"

                doc = {
                    'text': item['text'],
                    'source': source_type,
                    'filename': filename, # filename for both pdf and text files
                    'page_info': item.get('page', 'N/A') if source_type == 'pdf_page' else 'file_content',
                    'chatbot_id': chatbot_id
                }
                all_documents.append(doc)
                # Add to metadata if it's a unique file source
                is_file_source = item.get('page') == 'file' or (source_type == 'pdf_page' and item.get('page') == 1) # Consider first page of PDF as a source item
                if filename != 'unknown_pdf_or_file' and not any(ps['name'] == filename and ps['type'] == ('file' if item.get('page') == 'file' else 'pdf') for ps in processed_sources_metadata):
                     processed_sources_metadata.append({
                         "type": 'file' if item.get('page') == 'file' else 'pdf',
                         "name": filename,
                         "text": item['text'] if 'text' in item else ""
                     })
                logging.debug(f"Added {source_type} document '{filename}' with {len(item['text'])} characters")


        # Process folder data
        for item in folder_data:
            if isinstance(item, dict) and 'text' in item:
                filename = item.get('filename', 'unknown_folder_file')
                doc = {
                    'text': item['text'],
                    'source': 'folder_file',
                    'filename': filename,
                    'chatbot_id': chatbot_id
                }
                all_documents.append(doc)
                if filename != 'unknown_folder_file' and not any(ps['name'] == filename and ps['type'] == 'folder_file' for ps in processed_sources_metadata):
                    processed_sources_metadata.append({
                        "type": "folder_file",
                        "name": filename,
                        "text": item['text'] if 'text' in item else ""
                    })
                logging.debug(f"Added folder document '{filename}' with {len(item['text'])} characters")

        # Process web data
        for item in web_data:
            if isinstance(item, dict) and 'text' in item:
                url = item.get('url', 'unknown_url')
                doc = {
                    'text': item['text'],
                    'source': 'web',
                    'url': url,
                    'chatbot_id': chatbot_id
                }
                all_documents.append(doc)
                if url != 'unknown_url' and not any(ps['name'] == url and ps['type'] == 'web' for ps in processed_sources_metadata):
                     processed_sources_metadata.append({
                         "type": "web",
                         "name": url,
                         "text": item['text'] if 'text' in item else ""
                     })
                logging.debug(f"Added web document from '{url}' with {len(item['text'])} characters")

        # Process DB data (assuming similar structure with a 'name' or 'identifier')
        for item in db_data:
            if isinstance(item, dict) and 'text' in item:
                identifier = item.get('identifier', 'unknown_db_source') # Or 'name'
                doc = {
                    'text': item['text'],
                    'source': 'database',
                    'identifier': identifier,
                    'chatbot_id': chatbot_id
                }
                all_documents.append(doc)
                if identifier != 'unknown_db_source' and not any(ps['name'] == identifier and ps['type'] == 'database' for ps in processed_sources_metadata):
                     processed_sources_metadata.append({
                         "type": "database",
                         "name": identifier,
                         "text": item['text'] if 'text' in item else ""
                     })
                logging.debug(f"Added database source '{identifier}' with {len(item['text'])} characters")


        if not all_documents:
            logging.warning(f"No documents found for chatbot {chatbot_id} after processing all sources.")
            return True, {"processed_sources": [], "message": "No content provided for training."}


        logging.info(f"Total documents to process for vector DB: {len(all_documents)}")

        # Process documents into chunks
        chunks = text_processor.process_documents(all_documents)

        if not chunks:
            logging.warning(f"No chunks generated for chatbot {chatbot_id}")
            # Create a placeholder chunk
            chunks = [{
                'content': "This chatbot has no training data yet. Please add some content to train it.",
                'metadata': {
                    'source': 'placeholder',
                    'chatbot_id': chatbot_id
                }
            }]
            logging.info("Added placeholder chunk")

        logging.info(f"Generated {len(chunks)} chunks")

        # Extract text content for embedding
        texts = [chunk['content'] for chunk in chunks]

        # Generate embeddings
        try:
            # Always use the fallback embedding service
            # Get the embedding dimension first to ensure consistency
            embedding_dim = embedding_service.get_embedding_dimension()
            logging.info(f"Using embedding dimension: {embedding_dim}")

            # Generate embeddings
            embeddings = embedding_service.get_embeddings(texts)
            logging.info(f"Generated {len(embeddings)} embeddings with dimension {len(embeddings[0])}")
        except Exception as emb_error:
            logging.error(f"Error generating embeddings: {str(emb_error)}")
            # Create fallback deterministic embeddings
            logging.info(f"Creating deterministic fallback embeddings with dimension {embedding_dim}")
            embeddings = []
            for text in texts:
                # Create a hash of the text to ensure deterministic embeddings
                import hashlib
                text_hash = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
                np.random.seed(text_hash)
                # Generate a random embedding with the correct dimension
                embedding = np.random.random(embedding_dim).astype(np.float32)
                # Normalize to unit length
                embedding = embedding / np.linalg.norm(embedding)
                embeddings.append(embedding.tolist())
            logging.info(f"Created {len(embeddings)} fallback embeddings with dimension {embedding_dim}")

        # Get embedding dimension
        embedding_dim = embedding_service.get_embedding_dimension()

        # Create vector database collection
        vector_db.create_collection(chatbot_id, embedding_dim)

        # Add documents to vector database
        try:
            vector_db.add_documents(
                collection_name=chatbot_id,
                texts=texts,
                embeddings=embeddings,
                metadatas=chunks  # Pass full chunk objects as metadatas
            )
            logging.info(f"Added {len(texts)} documents to vector database for chatbot {chatbot_id}")
            return True, {"processed_sources": processed_sources_metadata, "message": f"Successfully processed and indexed {len(all_documents)} documents into {len(chunks)} chunks."}
        except Exception as db_error:
            logging.error(f"Error adding documents to vector database: {str(db_error)}")
            return False, {"message": f"Failed to process and index data: {str(db_error)}"}

    except Exception as e:
        logging.exception(f"Error in preprocess_and_index_data for chatbot {chatbot_id}: {str(e)}")
        return False, {"message": f"Failed to process and index data: {str(e)}"}

@cached('context', ttl=VECTOR_SEARCH_TTL)
def retrieve_relevant_context(question: str, chatbot_id: str, top_k: int = 8) -> List[str]:
    """Retrieve relevant context from the vector database.

    Args:
        question: User's question
        chatbot_id: ID of the chatbot
        top_k: Number of top chunks to retrieve (increased for better coverage)

    Returns:
        List of relevant text chunks
    """
    try:
        # Generate embedding for the question
        question_embedding = embedding_service.get_embeddings([question])[0]

        # First try with chatbot_id filter
        search_results = vector_db.search(
            collection_name=chatbot_id,
            query_embedding=question_embedding,
            top_k=top_k,
            filter_dict={"chatbot_id": chatbot_id}
        )

        # If no results, try without the filter
        if not search_results:
            logging.info(f"No results found with chatbot_id filter, trying without filter")
            search_results = vector_db.search(
                collection_name=chatbot_id,
                query_embedding=question_embedding,
                top_k=top_k,
                filter_dict=None  # Remove the filter
            )

        # Extract text from search results
        relevant_chunks = [result['text'] for result in search_results]
        return relevant_chunks
    except Exception as e:
        logging.exception(f"Error retrieving context: {str(e)}")
        return []

def format_conversation_history(conversation_history: List[Dict[str, Any]]) -> str:
    """Format conversation history for the LLM prompt.

    Args:
        conversation_history: List of conversation messages

    Returns:
        Formatted conversation history string
    """
    if not conversation_history:
        return ""

    formatted_history = "\nPrevious conversation:\n"
    for message in conversation_history:
        role = "User" if message["role"] == "user" else "Assistant"
        formatted_history += f"{role}: {message['content']}\n"

    return formatted_history

@cached('llm_answer', ttl=LLM_RESPONSE_TTL)
def generate_answer_with_llm(question: str, context: List[str], conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Generate an answer using the LLM.

    Args:
        question: User's question
        context: List of relevant text chunks
        conversation_history: Optional conversation history

    Returns:
        Generated answer
    """
    try:
        if not groq_client:
            # Fallback to simple answer generation if LLM not available
            return generate_fallback_answer(question, context)

        if not context:
            return "I don't have enough information to answer that question. Could you try rephrasing or asking about something else?"

        # Combine context chunks
        combined_context = "\n\n".join(context)

        # Limit context size to avoid token limits
        max_context_length = 12000  # Increased from 8000 for better context coverage
        if len(combined_context) > max_context_length:
            combined_context = combined_context[:max_context_length] + "..."

        # Format conversation history if provided
        # Only include recent messages to save tokens
        if conversation_history and len(conversation_history) > 8:
            conversation_history = conversation_history[-8:]  # Increased from 6 to 8 messages

        conversation_context = format_conversation_history(conversation_history) if conversation_history else ""

        # Create system prompt with context
        system_prompt = f"""You are a helpful assistant. Answer the user's question based on the following context, using appropriate formatting to make your response clear and easy to read.

Context:
{combined_context}

{conversation_context}

Formatting Guidelines:
- For lists: Use bullet points (•) or numbered format (**1.** **2.** etc.)
- For tutorials/how-to: Structure as step-by-step with clear headings (## Step-by-Step Guide, ### Steps:)
- For pricing: Use clear headers (## Pricing Information, ### Pricing Details:)
- For comparisons: Use headers and structured points (## Comparison Overview, ### Key Differences:)
- For technical issues: Use clear sections (## Technical Solution, ### Issue Analysis:, ### Solution:)
- Use **bold** for important terms and numbers
- Use headers (##, ###) to organize longer responses
- Break up long text into readable sections

If the context doesn't contain the information needed to answer the question, politely say you don't have that information and suggest they try rephrasing their question or ask about something else."""

        # Get start time for performance measurement
        start_time = time.time()

        # Call LLM with appropriate parameters
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",  # or "mixtral-8x7b-32768" based on needs
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            max_tokens=800,
            top_p=0.9,
            stream=False
        )

        # Log performance metrics
        elapsed_time = time.time() - start_time
        logging.info(f"LLM response generated in {elapsed_time:.2f} seconds")

        # Extract and return answer
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        logging.exception(f"Error generating answer with LLM: {str(e)}")
        # Fallback to simpler approach if LLM fails
        return generate_fallback_answer(question, context)

def generate_fallback_answer(question: str, context: List[str]) -> str:
    """Generate a simple fallback answer when LLM is not available.

    Args:
        question: User's question
        context: List of relevant text chunks

    Returns:
        Generated answer
    """
    if not context:
        return "I don't have enough information to answer that question. Could you try rephrasing or asking about something else?"

    # Join the contexts
    combined_context = " ".join(context)
    # Create a simple response
    response = f"Based on the information available, I can provide this answer: {context[0]}"

    # Truncate if too long
    if len(response) > 500:
        response = response[:497] + "..."

    return response

def calculate_response_confidence(question: str, relevant_chunks: List[str], answer: str) -> float:
    """
    Calculate confidence score for a chatbot response based on multiple factors
    
    Args:
        question: User's question
        relevant_chunks: Retrieved context chunks
        answer: Generated answer
        
    Returns:
        Confidence score (0-100)
    """
    if not relevant_chunks:
        return 0.0
    
    try:
        confidence_factors = []
        
        # Factor 1: Number of relevant chunks found
        chunk_factor = min(len(relevant_chunks) / 3.0, 1.0) * 25  # Max 25 points
        confidence_factors.append(chunk_factor)
        
        # Factor 2: Semantic similarity between question and chunks
        question_words = set(question.lower().split())
        chunk_words = set(' '.join(relevant_chunks).lower().split())
        overlap_ratio = len(question_words.intersection(chunk_words)) / len(question_words) if question_words else 0
        semantic_factor = overlap_ratio * 30  # Max 30 points
        confidence_factors.append(semantic_factor)
        
        # Factor 3: Answer length and completeness
        answer_length_factor = min(len(answer.split()) / 20.0, 1.0) * 20  # Max 20 points
        confidence_factors.append(answer_length_factor)
        
        # Factor 4: Presence of uncertainty markers in answer
        uncertainty_markers = ['i\'m not sure', 'i don\'t know', 'i\'m sorry', 'might be', 'could be', 'possibly']
        uncertainty_penalty = sum(5 for marker in uncertainty_markers if marker in answer.lower())
        
        # Factor 5: Question specificity (more specific questions get higher confidence when answered)
        question_specificity = min(len([w for w in question.split() if len(w) > 3]) / 5.0, 1.0) * 25  # Max 25 points
        confidence_factors.append(question_specificity)
        
        # Calculate final confidence score
        base_confidence = sum(confidence_factors)
        final_confidence = max(0, min(100, base_confidence - uncertainty_penalty))
        
        logging.info(f"Confidence calculation: chunks={chunk_factor:.1f}, semantic={semantic_factor:.1f}, "
                   f"length={answer_length_factor:.1f}, specificity={question_specificity:.1f}, "
                   f"penalty={uncertainty_penalty:.1f}, final={final_confidence:.1f}")
        
        return final_confidence
    
    except Exception as e:
        logging.error(f"Error calculating confidence: {str(e)}")
        return 50.0  # Default medium confidence

def find_partial_matches(question: str, all_content: List[str], threshold: float = 0.3) -> List[Dict[str, Any]]:
    """
    Find partial matches in content using fuzzy string matching
    
    Args:
        question: User's question
        all_content: All available content chunks
        threshold: Minimum similarity threshold
        
    Returns:
        List of partial matches with similarity scores
    """
    if not all_content:
        return []
    
    try:
        question_lower = question.lower()
        partial_matches = []
        
        for content in all_content:
            if not content or len(content.strip()) < 10:
                continue
                
            content_lower = content.lower()
            
            # Calculate similarity using SequenceMatcher
            similarity = SequenceMatcher(None, question_lower, content_lower).ratio()
            
            # Also check for word overlap
            question_words = set(question_lower.split())
            content_words = set(content_lower.split())
            word_overlap = len(question_words.intersection(content_words)) / len(question_words) if question_words else 0
            
            # Combined score
            combined_score = (similarity * 0.4) + (word_overlap * 0.6)
            
            if combined_score >= threshold:
                partial_matches.append({
                    'content': content,
                    'similarity': combined_score,
                    'word_overlap': word_overlap
                })
        
        # Sort by combined score
        partial_matches.sort(key=lambda x: x['similarity'], reverse=True)
        return partial_matches[:3]  # Return top 3 matches
    
    except Exception as e:
        logging.error(f"Error finding partial matches: {str(e)}")
        return []

def extract_topic_keywords(question: str) -> List[str]:
    """
    Extract key topics/keywords from a question for alternative suggestions
    
    Args:
        question: User's question
        
    Returns:
        List of extracted keywords
    """
    try:
        # Remove common stop words and question words
        stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'which', 'can', 'could', 
                     'would', 'should', 'do', 'does', 'did', 'is', 'are', 'was', 'were',
                     'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during'}
        
        # Extract words longer than 2 characters
        words = re.findall(r'\b\w{3,}\b', question.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Remove duplicates while preserving order
        unique_keywords = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)
        
        return unique_keywords[:5]  # Return top 5 keywords
    
    except Exception as e:
        logging.error(f"Error extracting keywords: {str(e)}")
        return []

def generate_clarifying_questions(keywords: List[str]) -> List[str]:
    """
    Generate clarifying questions based on extracted keywords
    
    Args:
        keywords: List of keywords from the original question
        
    Returns:
        List of clarifying questions
    """
    if not keywords:
        return []
    
    clarifying_templates = [
        f"Are you looking for information about {keywords[0]} specifically?",
        f"When you mention {keywords[0]}, do you mean {keywords[0]} in general or something specific?",
        f"Could you tell me more about what aspect of {keywords[0]} you're interested in?",
        f"Are you trying to {keywords[0]} or learn about {keywords[0]}?",
    ]
    
    # Add keyword-specific questions if we have multiple keywords
    if len(keywords) > 1:
        clarifying_templates.extend([
            f"Are you asking about {keywords[0]} or {keywords[1]}?",
            f"Do you need help with {keywords[0]} and {keywords[1]} together?",
        ])
    
    return clarifying_templates[:3]  # Return max 3 questions

def generate_alternative_suggestions(keywords: List[str]) -> List[str]:
    """
    Generate alternative topic suggestions based on keywords
    
    Args:
        keywords: List of keywords from the original question
        
    Returns:
        List of alternative suggestions
    """
    if not keywords:
        return []
    
    suggestions = []
    
    for keyword in keywords[:3]:  # Use first 3 keywords
        suggestions.extend([
            f"Getting started with {keyword}",
            f"Common {keyword} issues",
            f"How to configure {keyword}",
            f"Best practices for {keyword}",
            f"Troubleshooting {keyword}",
        ])
    
    # Remove duplicates and shuffle for variety
    unique_suggestions = list(set(suggestions))
    random.shuffle(unique_suggestions)
    
    return unique_suggestions[:4]  # Return max 4 suggestions

@cached('enhanced_fallback', ttl=ANSWER_CONFIDENCE_TTL)
def generate_enhanced_fallback_response(question: str, relevant_chunks: List[str], 
                                      all_content: List[str] = None, 
                                      conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Generate an enhanced fallback response using multi-level strategy
    
    Args:
        question: User's question
        relevant_chunks: Initially retrieved relevant chunks
        all_content: All available content for partial matching
        conversation_history: Optional conversation history
        
    Returns:
        Dictionary with response, confidence, and strategy level
    """
    try:
        # Calculate initial confidence
        if relevant_chunks:
            # Try to generate a basic answer first
            basic_answer = generate_answer_with_llm(question, relevant_chunks, conversation_history)
            confidence = calculate_response_confidence(question, relevant_chunks, basic_answer)
            
            if confidence >= CONFIDENCE_THRESHOLDS['HIGH']:
                return {
                    'answer': basic_answer,
                    'confidence': confidence,
                    'strategy_level': 1,
                    'response_type': 'direct_answer'
                }
            elif confidence >= CONFIDENCE_THRESHOLDS['MEDIUM']:
                enhanced_answer = f"{basic_answer}\n\n*Please note: This information is based on available content and may not be complete. Feel free to ask for clarification if needed.*"
                return {
                    'answer': enhanced_answer,
                    'confidence': confidence,
                    'strategy_level': 2,
                    'response_type': 'partial_answer_with_disclaimer'
                }
        
        # Level 1: Look for partial matches
        if all_content:
            partial_matches = find_partial_matches(question, all_content)
            if partial_matches:
                match_content = partial_matches[0]['content'][:300] + "..." if len(partial_matches[0]['content']) > 300 else partial_matches[0]['content']
                response = f"I found some related information that might help:\n\n{match_content}\n\nIs this what you were looking for, or would you like me to search for something more specific?"
                return {
                    'answer': response,
                    'confidence': partial_matches[0]['similarity'] * 60,  # Convert to confidence score
                    'strategy_level': 1,
                    'response_type': 'partial_match'
                }
        
        # Level 2: Extract keywords and provide alternatives
        keywords = extract_topic_keywords(question)
        if keywords:
            alternatives = generate_alternative_suggestions(keywords)
            clarifying_questions = generate_clarifying_questions(keywords)
            
            response_parts = ["I want to help you find the right information. "]
            
            if alternatives:
                response_parts.append(f"Here are some related topics that might be relevant:\n")
                for i, alt in enumerate(alternatives, 1):
                    response_parts.append(f"{i}. {alt}\n")
                response_parts.append("\n")
            
            if clarifying_questions:
                response_parts.append("To better assist you, could you help me understand:\n")
                response_parts.append(f"• {clarifying_questions[0]}")
            
            return {
                'answer': ''.join(response_parts),
                'confidence': 35,
                'strategy_level': 2,
                'response_type': 'alternatives_and_clarification'
            }
        
        # Level 3: Suggest rephrasing or broader search
        rephrasing_suggestions = [
            "Could you rephrase your question? I want to make sure I understand correctly.",
            "Let me suggest trying a different approach - could you describe what you're trying to accomplish?",
            "I'd like to help you better. Could you provide more context about what you're looking for?",
            "Maybe we can approach this differently. What specific problem are you trying to solve?"
        ]
        
        selected_suggestion = random.choice(rephrasing_suggestions)
        response = f"{selected_suggestion}\n\nAlternatively, you could try searching for broader topics or breaking down your question into smaller parts."
        
        return {
            'answer': response,
            'confidence': 25,
            'strategy_level': 3,
            'response_type': 'rephrasing_suggestion'
        }
    
    except Exception as e:
        logging.error(f"Error generating enhanced fallback response: {str(e)}")
        # Level 4: Last resort - but still avoid immediate ticket suggestion
        return {
            'answer': "I'm having trouble finding the specific information you're looking for. Could you try rephrasing your question or asking about a related topic?",
            'confidence': 15,
            'strategy_level': 4,
            'response_type': 'basic_fallback'
        }

def should_suggest_ticket(confidence: float, strategy_level: int, consecutive_failures: int = 0) -> bool:
    """
    Determine if a ticket should be suggested based on confidence and context
    
    Args:
        confidence: Response confidence score (0-100)
        strategy_level: Current fallback strategy level
        consecutive_failures: Number of consecutive failed attempts
        
    Returns:
        Boolean indicating whether to suggest ticket creation
    """
    # Only suggest tickets as absolute last resort
    if confidence < CONFIDENCE_THRESHOLDS['VERY_LOW'] and strategy_level >= 4 and consecutive_failures >= 2:
        return True
    
    return False

def get_enhanced_answer(data: Union[str, Dict, List], question: str, chatbot_id: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Get an answer to a question using enhanced context retrieval.

    Args:
        data: Chatbot knowledge base data
        question: User's question
        chatbot_id: ID of the chatbot
        conversation_history: Optional conversation history

    Returns:
        Generated answer
    """
    try:
        # Check cache first
        cache_key = cache['generate_key']('answer', chatbot_id, question, 
                                         str(hash(str(conversation_history)) if conversation_history else None))
        cache_hit, cached_answer = cache['get'](cache_key)
        if cache_hit:
            logging.info(f"Cache hit for question in chatbot {chatbot_id}")
            return cached_answer

        # Log the incoming data type for debugging
        logging.info(f"get_enhanced_answer called for chatbot {chatbot_id}, data type: {type(data)}")

        # Parse chatbot data
        parsed_data = parse_chatbot_data(data, chatbot_id)
        if not parsed_data:
            logging.warning(f"Failed to parse chatbot data for {chatbot_id}")
            return "I don't have any content to answer questions at the moment. Could you try again later or ask about something else?"

        # Check if vector database collection exists
        collection_info = vector_db.get_collection_info(chatbot_id)
        logging.info(f"Vector DB collection info for {chatbot_id}: {collection_info}")

        # If collection doesn't exist or is empty, preprocess and index data
        if not collection_info.get('exists', False) or collection_info.get('points_count', 0) == 0:
            logging.info(f"Vector DB collection doesn't exist or is empty for {chatbot_id}, preprocessing data")
            success, result = preprocess_and_index_data(
                chatbot_id,
                parsed_data.get('pdf_data', []),
                parsed_data.get('folder_data', []),
                parsed_data.get('web_data', {}),
                []
            )
            if not success:
                logging.error(f"Failed to preprocess and index data for {chatbot_id}: {result}")
                return result["message"]
            logging.info(f"Successfully preprocessed and indexed data for {chatbot_id}")

        # Retrieve relevant context
        logging.info(f"Retrieving relevant context for question: {question}")
        relevant_chunks = retrieve_relevant_context(question, chatbot_id, top_k=8)
        logging.info(f"Retrieved {len(relevant_chunks)} relevant chunks for {chatbot_id}")

        # Get all content for enhanced fallback processing
        all_content = []
        if parsed_data:
            # Collect all text content for partial matching
            for pdf in parsed_data.get('pdf_data', []):
                if pdf.get('text'):
                    all_content.append(pdf['text'])
            
            for folder_item in parsed_data.get('folder_data', []):
                if folder_item.get('text'):
                    all_content.append(folder_item['text'])
            
            web_data = parsed_data.get('web_data', {})
            if isinstance(web_data, dict) and 'sections' in web_data:
                for section in web_data['sections']:
                    if isinstance(section, dict) and 'content' in section:
                        for content in section['content']:
                            if content:
                                all_content.append(content)

        # Check if this is a greeting first
        question_lower = question.lower().strip()
        greeting_words = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        
        if any(question_lower == greeting for greeting in greeting_words) or \
           any(question_lower.startswith(greeting) for greeting in greeting_words) or \
           len(question_lower) < 5:
            answer = "Hello! I'm your AI assistant. How can I help you today? Feel free to ask me any questions about our products or services."
            
            # Format the greeting response
            formatted_response = response_formatter.format_response(question, answer, 100.0)  # High confidence for greetings
            final_answer = formatted_response['answer']
            
            cache['set'](cache_key, final_answer, ttl=LLM_RESPONSE_TTL)
            return final_answer

        # Use enhanced fallback system with confidence scoring
        if not relevant_chunks:
            logging.warning(f"No relevant chunks found for question: {question}")
            fallback_response = generate_enhanced_fallback_response(
                question, 
                [], 
                all_content, 
                conversation_history
            )
            
            # Format the fallback response
            formatted_response = response_formatter.format_response(question, fallback_response['answer'], fallback_response['confidence'])
            final_answer = formatted_response['answer']
            
            cache['set'](cache_key, final_answer, ttl=LLM_RESPONSE_TTL)
            logging.info(f"Enhanced fallback used: strategy_level={fallback_response['strategy_level']}, "
                        f"confidence={fallback_response['confidence']:.1f}%, "
                        f"type={fallback_response['response_type']}, "
                        f"question_type={formatted_response['question_type']}")
            return final_answer

        # Generate answer with LLM or fallback
        if groq_client:
            logging.info(f"Using Groq LLM to generate answer for {chatbot_id}")
            answer = generate_answer_with_llm(question, relevant_chunks, conversation_history)
            
            # Calculate confidence for the generated answer
            confidence = calculate_response_confidence(question, relevant_chunks, answer)
            logging.info(f"Answer confidence: {confidence:.1f}%")
            
            # If confidence is low, use enhanced fallback instead
            if confidence < CONFIDENCE_THRESHOLDS['MEDIUM']:
                logging.info(f"Low confidence ({confidence:.1f}%), using enhanced fallback")
                fallback_response = generate_enhanced_fallback_response(
                    question, 
                    relevant_chunks, 
                    all_content, 
                    conversation_history
                )
                
                # Format the fallback response
                formatted_response = response_formatter.format_response(question, fallback_response['answer'], fallback_response['confidence'])
                final_answer = formatted_response['answer']
                
                cache['set'](cache_key, final_answer, ttl=LLM_RESPONSE_TTL)
                logging.info(f"Enhanced fallback used: strategy_level={fallback_response['strategy_level']}, "
                            f"confidence={fallback_response['confidence']:.1f}%, "
                            f"type={fallback_response['response_type']}, "
                            f"question_type={formatted_response['question_type']}")
                return final_answer
            
        else:
            logging.info(f"Using fallback answer generator for {chatbot_id}")
            answer = generate_fallback_answer(question, relevant_chunks)
            confidence = calculate_response_confidence(question, relevant_chunks, answer)
            
            # Always use enhanced fallback if no LLM available and confidence is low
            if confidence < CONFIDENCE_THRESHOLDS['MEDIUM']:
                fallback_response = generate_enhanced_fallback_response(
                    question, 
                    relevant_chunks, 
                    all_content, 
                    conversation_history
                )
                
                # Format the fallback response
                formatted_response = response_formatter.format_response(question, fallback_response['answer'], fallback_response['confidence'])
                final_answer = formatted_response['answer']
                
                cache['set'](cache_key, final_answer, ttl=LLM_RESPONSE_TTL)
                return final_answer
        
        # Format the main answer using the response formatter
        formatted_response = response_formatter.format_response(question, answer, confidence)
        final_answer = formatted_response['answer']
        
        logging.info(f"Response formatted: question_type={formatted_response['question_type']}, "
                    f"confidence={confidence:.1f}%")
        
        # Cache the formatted answer
        cache['set'](cache_key, final_answer, ttl=LLM_RESPONSE_TTL)
        return final_answer
    except Exception as e:
        logging.exception(f"Error getting enhanced answer for {chatbot_id}: {str(e)}")
        return f"I apologize, but I encountered an issue while processing your question. Please try again later."
