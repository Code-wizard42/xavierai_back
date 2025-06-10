"""
Chatbot Service Module

This module contains business logic for chatbot operations, separating it from the route handlers.
"""
import json
import uuid
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import Chatbot, ConversationMessage
from xavier_back.utils.nlp_utils_enhanced import get_enhanced_answer, preprocess_and_index_data, parse_chatbot_data
from xavier_back.utils.file_utils import extract_text_from_pdf, read_text_file, extract_folder_content, extract_text_from_url
from xavier_back.utils.api_utils import fetch_real_time_data
from xavier_back.utils.cache_utils import cached, cache
from xavier_back.utils.vector_db import vector_db

logger = logging.getLogger(__name__)

# Cache TTL settings
CHATBOT_TTL = 1800  # 30 minutes
ANSWER_TTL = 300    # 5 minutes

class ChatbotService:
    """Service class for chatbot-related operations"""

    @staticmethod
    def get_chatbot(chatbot_id: str) -> Optional[Chatbot]:
        """
        Get a chatbot by ID

        Args:
            chatbot_id: The ID of the chatbot to retrieve

        Returns:
            The chatbot object or None if not found
        """
        try:
            # Always get a fresh instance from the database to avoid detached instance issues
            # This solves the SQLAlchemy DetachedInstanceError that was occurring with cached objects
            return Chatbot.query.get(chatbot_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving chatbot {chatbot_id}: {str(e)}")
            return None

    @staticmethod
    def create_chatbot(name: str, user_id: int) -> Tuple[Optional[Chatbot], Optional[str]]:
        """
        Create a new chatbot

        Args:
            name: The name of the chatbot
            user_id: The ID of the user creating the chatbot

        Returns:
            Tuple containing (chatbot, error_message)
            If successful, chatbot will be the new Chatbot object and error_message will be None
            If failed, chatbot will be None and error_message will contain the error
        """
        try:
            chatbot_id = str(uuid.uuid4())
            new_chatbot = Chatbot(
                id=chatbot_id,
                name=name,
                user_id=user_id,
                data=json.dumps({})
            )
            db.session.add(new_chatbot)
            db.session.commit()
            return new_chatbot, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error creating chatbot: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def delete_chatbot(chatbot_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a chatbot

        Args:
            chatbot_id: The ID of the chatbot to delete

        Returns:
            Tuple containing (success, error_message)
            If successful, success will be True and error_message will be None
            If failed, success will be False and error_message will contain the error
        """
        try:
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot:
                return False, "Chatbot not found"

            # Delete all related records with foreign key constraints
            # This is necessary because these tables have NOT NULL constraints on chatbot_id

            # Delete conversation messages
            from xavier_back.models import ConversationMessage
            ConversationMessage.query.filter_by(chatbot_id=chatbot_id).delete()

            # Delete feedback records
            from xavier_back.models import Feedback
            Feedback.query.filter_by(chatbot_id=chatbot_id).delete()

            # Delete tickets
            try:
                from xavier_back.models import Ticket
                Ticket.query.filter_by(chatbot_id=chatbot_id).delete()
            except Exception as e:
                logger.warning(f"Error deleting tickets for chatbot {chatbot_id}: {str(e)}")
                # Continue even if Ticket model doesn't exist

            # Delete question analytics if they exist
            try:
                from xavier_back.models import QuestionAnalytics
                QuestionAnalytics.query.filter_by(chatbot_id=chatbot_id).delete()
            except Exception as e:
                logger.warning(f"Error deleting question analytics for chatbot {chatbot_id}: {str(e)}")
                # Continue even if QuestionAnalytics model doesn't exist

            # Delete chatbot avatars
            try:
                from xavier_back.models import ChatbotAvatar
                ChatbotAvatar.query.filter_by(chatbot_id=chatbot_id).delete()
            except Exception as e:
                logger.warning(f"Error deleting avatars for chatbot {chatbot_id}: {str(e)}")
                # Continue even if ChatbotAvatar model doesn't exist

            # Note: Leads should be handled by the cascade="all, delete-orphan" in the relationship

            # Then delete the chatbot
            db.session.delete(chatbot)
            db.session.commit()
            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error deleting chatbot: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def update_chatbot_data(chatbot_id: str, data_as_json_string: str) -> Tuple[bool, Optional[str]]:
        """
        Update chatbot data.
        Expects data_as_json_string to be a valid JSON string.
        """
        try:
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot:
                return False, "Chatbot not found"

            # Optional: Validate if the incoming string is valid JSON before storing.
            # The frontend should ideally always send a valid JSON string.
            try:
                parsed_data = json.loads(data_as_json_string)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON string received for chatbot {chatbot_id} during update: {data_as_json_string}. Error: {e}")
                return False, f"Invalid JSON data format: {e}"

            # Clear vector database if data is being cleared or significantly changed
            data_is_cleared = (
                not parsed_data or 
                (isinstance(parsed_data, list) and len(parsed_data) == 0) or
                (isinstance(parsed_data, dict) and len(parsed_data) == 0)
            )
            
            if data_is_cleared:
                logger.info(f"Data is being cleared for chatbot {chatbot_id}, clearing vector database")
                success = vector_db.delete_collection(chatbot_id)
                if success:
                    logger.info(f"Successfully cleared vector database for chatbot {chatbot_id}")
                else:
                    logger.warning(f"Failed to clear vector database for chatbot {chatbot_id}")
                
                # Clear any cached answers for this chatbot
                try:
                    # Clear specific chatbot cache entries
                    cache['delete'](f'chatbot:{chatbot_id}')
                    logger.info(f"Cleared cache for chatbot {chatbot_id}")
                    
                    # Also invalidate all answer caches for this chatbot
                    cache['invalidate'](f'chatbot_answer:{chatbot_id}')
                    logger.info(f"Invalidated all answer caches for chatbot {chatbot_id}")
                except Exception as cache_error:
                    logger.warning(f"Failed to clear cache for chatbot {chatbot_id}: {cache_error}")
            else:
                # If data is not being cleared but updated, we should still clear the old vectors
                # and let the system re-index when the chatbot is used next
                logger.info(f"Data is being updated for chatbot {chatbot_id}, clearing old vector database")
                vector_db.delete_collection(chatbot_id)
                
                # Also invalidate answer caches when data is updated
                try:
                    cache['invalidate'](f'chatbot_answer:{chatbot_id}')
                    logger.info(f"Invalidated all answer caches for chatbot {chatbot_id}")
                except Exception as cache_error:
                    logger.warning(f"Failed to invalidate answer cache for chatbot {chatbot_id}: {cache_error}")

            chatbot.data = data_as_json_string  # Store the JSON string directly
            db.session.commit()
            
            # Clear the get_chatbot cache since we updated the data
            try:
                cache['delete'](f'chatbot:{chatbot_id}')
            except:
                pass
                
            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating chatbot data: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def get_answer(chatbot_id: str, question: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an answer to a question from the chatbot

        Args:
            chatbot_id: The ID of the chatbot
            question: The user's question
            conversation_id: Optional conversation ID for context

        Returns:
            Dictionary with answer and metadata
        """
        try:
            # Get start time for performance tracking
            start_time = time.time()
            
            # For stateless queries (no conversation), check cache
            if not conversation_id:
                cache_key = cache['generate_key']('chatbot_answer', chatbot_id, question)
                found, cached_result = cache['get'](cache_key)
                if found:
                    logger.info(f"Cache hit for chatbot {chatbot_id} question")
                    # Add processing time for monitoring
                    processing_time = time.time() - start_time
                    cached_result['processing_time_ms'] = int(processing_time * 1000)
                    return cached_result
            
            # Get chatbot (this uses the cached method)
            chatbot = ChatbotService.get_chatbot(chatbot_id)
            if not chatbot:
                return {"error": "Chatbot not found", "answer": "Sorry, this chatbot is not available."}

            # Generate a conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            # Get conversation history if available
            conversation_history = None
            if conversation_id:
                # Get the last 5 messages from this conversation
                messages = ConversationMessage.query.filter_by(
                    conversation_id=conversation_id,
                    chatbot_id=chatbot_id
                ).order_by(ConversationMessage.timestamp.desc()).limit(5).all()

                if messages:
                    # Format messages for the NLP module
                    conversation_history = [
                        {"role": "user" if i % 2 == 0 else "assistant", "content": msg.message if i % 2 == 0 else msg.response}
                        for i, msg in enumerate(reversed(messages))
                    ]

            # Get answer using the enhanced NLP module with confidence tracking
            answer = get_enhanced_answer(chatbot.data, question, chatbot_id, conversation_history)

            # Store the conversation
            try:
                new_message = ConversationMessage(
                    conversation_id=conversation_id,
                    chatbot_id=chatbot_id,
                    message=question,
                    response=answer
                )
                db.session.add(new_message)
                db.session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error storing conversation: {str(e)}")
                db.session.rollback()
                # Continue even if storing fails

            # Record conversation for usage tracking
            try:
                from xavier_back.services.conversation_limit_service import ConversationLimitService
                ConversationLimitService.record_conversation(chatbot_id)
            except Exception as e:
                logger.error(f"Error recording conversation usage for chatbot {chatbot_id}: {str(e)}")
                # Continue even if usage tracking fails

            # Create result with timing information
            processing_time = time.time() - start_time
            result = {
                "answer": answer,
                "conversation_id": conversation_id,
                "processing_time_ms": int(processing_time * 1000)
            }
            
            # Cache result for stateless queries
            if not conversation_id:
                cache['set'](cache_key, result, ttl=ANSWER_TTL)
                
            return result
        except Exception as e:
            logger.error(f"Error getting answer: {str(e)}")
            return {
                "answer": "I'm sorry, I encountered an error while processing your question. Please try again.",
                "error": str(e)
            }

    @staticmethod
    def train_chatbot(chatbot_id: str, pdf_files=None, text_files=None, db_data_input=None, api_url=None, folder_path=None, website_url=None) -> Tuple[bool, Optional[str]]:
        """
        Train a chatbot with new data

        Args:
            chatbot_id: The ID of the chatbot to train
            pdf_files: Optional list of PDF files
            text_files: Optional list of text files
            db_data_input: Optional database data
            api_url: Optional API URL for real-time data
            folder_path: Optional folder path for content extraction
            website_url: Optional website URL for content extraction

        Returns:
            Tuple containing (success, message)
        """
        try:
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot:
                return False, "Chatbot not found"
            
            # Clear existing vector database before training with new data
            # This ensures the chatbot only uses the newly trained data
            logger.info(f"Clearing existing vector database for chatbot {chatbot_id} before training")
            try:
                success = vector_db.delete_collection(chatbot_id)
                if success:
                    logger.info(f"Successfully cleared vector database for chatbot {chatbot_id}")
                else:
                    logger.warning(f"Failed to clear vector database for chatbot {chatbot_id}, but continuing with training")
                    
                # Clear any cached answers for this chatbot
                cache['delete'](f'chatbot:{chatbot_id}')
                logger.info(f"Cleared cache for chatbot {chatbot_id}")
                
                # Also invalidate all answer caches for this chatbot
                cache['invalidate'](f'chatbot_answer:{chatbot_id}')
                logger.info(f"Invalidated all answer caches for chatbot {chatbot_id}")
            except Exception as clear_error:
                logger.warning(f"Error clearing vector database/cache for chatbot {chatbot_id}: {clear_error}, but continuing with training")

            # Initialize lists for data to be passed to preprocess_and_index_data
            pdf_data_list = []
            folder_data_list = []
            web_data_list = []
            # db_data_list = [] # Assuming db_data_input is already in the correct list format if used

            # Process PDF files (these are actual PDF files from upload)
            if pdf_files:
                for pdf_file_path in pdf_files:
                    pdf_content_pages = extract_text_from_pdf(pdf_file_path) # Returns list of page texts
                    if pdf_content_pages:
                        # preprocess_and_index_data expects a list of dicts, each dict being a source item
                        # For a PDF, we can pass its content page by page, or as a single item.
                        # Let's pass it as a single item with filename, and its text being all joined pages.
                        # Or better, pass each page if preprocess_and_index handles pages with filenames.
                        # The current preprocess_and_index_data seems to prefer items with 'text' and 'filename'.
                        full_text = "\n\n".join(p['text'] for p in pdf_content_pages if isinstance(p, dict) and 'text' in p)
                        if full_text:
                            pdf_data_list.append({
                                'text': full_text,
                                'filename': os.path.basename(pdf_file_path),
                                'page': 'pdf_document' # Special marker for preprocess_and_index_data to know it's a full PDF
                            })
                            logger.info(f"Successfully processed PDF file: {pdf_file_path}")

            # Process text files (includes TXT, MD, RST, DOC, DOCX files from upload)
            if text_files:
                for text_file_path in text_files:
                    try:
                        file_extension = os.path.splitext(text_file_path)[1].lower()
                        
                        if file_extension == '.docx':
                            # Use DOCX extraction function
                            from xavier_back.utils.file_utils import extract_text_from_docx
                            docx_data = extract_text_from_docx(text_file_path)
                            for item in docx_data:
                                if item.get('text'):
                                    pdf_data_list.append({
                                        'text': item['text'],
                                        'filename': item.get('filename', os.path.basename(text_file_path)),
                                        'page': 'file'  # Marker for preprocess_and_index_data
                                    })
                            logger.info(f"Successfully processed DOCX file: {text_file_path}")
                        elif file_extension == '.doc':
                            # Use DOC extraction function
                            from xavier_back.utils.file_utils import extract_text_from_doc
                            doc_data = extract_text_from_doc(text_file_path)
                            for item in doc_data:
                                if item.get('text'):
                                    pdf_data_list.append({
                                        'text': item['text'],
                                        'filename': item.get('filename', os.path.basename(text_file_path)),
                                        'page': 'file'  # Marker for preprocess_and_index_data
                                    })
                            logger.info(f"Successfully processed DOC file: {text_file_path}")
                        else:
                            # Process as regular text file (TXT, MD, RST)
                            text_content = read_text_file(text_file_path)
                            if text_content:
                                pdf_data_list.append({
                                    'text': text_content,
                                    'filename': os.path.basename(text_file_path),
                                    'page': 'file'  # Marker for preprocess_and_index_data
                                })
                                logger.info(f"Successfully processed text file: {text_file_path}")
                    except Exception as e:
                        logger.error(f"Error processing text file {text_file_path}: {e}")
                        # Optionally add error info to be stored or reported

            # Process folder_path
            if folder_path:
                folder_contents = extract_folder_content(folder_path) # Expects list of {'filename': ..., 'text': ...}
                if folder_contents:
                    folder_data_list.extend(folder_contents)
                    logger.info(f"Successfully processed folder: {folder_path} with {len(folder_contents)} items.")

            # Process website_url
            if website_url:
                web_text = extract_text_from_url(website_url)
                if web_text:
                    web_data_list.append({'text': web_text, 'url': website_url, 'filename': website_url})
                    logger.info(f"Successfully processed website: {website_url}")

            # Process api_url (assuming it returns a list of items or a single item with text)
            if api_url:
                api_content = fetch_real_time_data(api_url) # Expects {'text': ...} or list of such
                if api_content:
                    if isinstance(api_content, list):
                        # Assuming api_content is a list of dicts with 'text' and some identifier
                        for item in api_content:
                            item['filename'] = item.get('id', api_url) # Use id or url as filename
                        web_data_list.extend(api_content) # Or a different list type if needed
                    elif isinstance(api_content, dict) and 'text' in api_content:
                        api_content['filename'] = api_content.get('id', api_url)
                        web_data_list.append(api_content)
                    logger.info(f"Successfully processed API URL: {api_url}")

            # db_data_input is assumed to be already a list of dicts if provided
            # db_data_list = db_data_input if db_data_input else []

            # Check if there is any data to process
            if not any([pdf_data_list, folder_data_list, web_data_list, db_data_input]):
                logger.info(f"No new data sources provided for training chatbot {chatbot_id}.")
                # Even if no new data, we might want to re-index existing data if logic changes
                # For now, let's return success if no new files and no errors.
                # Or, we can force re-indexing existing chatbot.data sources if that's desired.
                # Let's assume for now, if no new files, it means no operation needed beyond what preprocess does.
                # However, preprocess_and_index_data itself now returns an empty list if its inputs are empty.

            # Call the enhanced NLP utility to process and index the data
            success, result_map = preprocess_and_index_data(
                chatbot_id=chatbot_id,
                pdf_data=pdf_data_list,
                folder_data=folder_data_list,
                web_data=web_data_list,
                db_data=db_data_input # Pass directly if already in list format
            )

            if not success:
                error_message = result_map.get("message", "Failed to preprocess and index data.") if isinstance(result_map, dict) else str(result_map)
                return False, error_message

            # Persist the structured data map (returned by preprocess_and_index_data)
            if isinstance(result_map, dict) and "processed_sources" in result_map:
                newly_processed_sources = result_map.get("processed_sources", [])
                if not isinstance(newly_processed_sources, list):
                    logger.warning(f"'processed_sources' from preprocess_and_index_data is not a list for chatbot {chatbot_id}. Received: {newly_processed_sources}")
                    newly_processed_sources = []

                try:
                    current_chatbot_data_str = chatbot.data if chatbot.data else "{}"
                    current_data_obj = json.loads(current_chatbot_data_str)

                    # Ensure current_data_obj is a dictionary and has a 'sources' list
                    if not isinstance(current_data_obj, dict):
                        logger.warning(f"Chatbot {chatbot_id} data was not a dict. Initializing. Old data: {current_chatbot_data_str}")
                        current_data_obj = {}

                    if 'sources' not in current_data_obj or not isinstance(current_data_obj.get('sources'), list):
                        current_data_obj['sources'] = []

                    # Preserve other top-level keys like 'customization'
                    # For example, if chatbot.data was '[{"pdf_data":[]}]', this needs careful handling.
                    # Let's simplify: if it's the old list format, we start fresh for sources but try to keep customization.
                    if isinstance(current_data_obj, list) and len(current_data_obj) > 0 and isinstance(current_data_obj[0], dict):
                        old_format_dict = current_data_obj[0]
                        new_data_obj = {}
                        if 'customization' in old_format_dict:
                            new_data_obj['customization'] = old_format_dict['customization']
                        elif 'customization' in current_data_obj: # if customization was accidentally at top level of list
                             new_data_obj['customization'] = current_data_obj['customization']
                        new_data_obj['sources'] = []
                        current_data_obj = new_data_obj
                        logger.info(f"Chatbot {chatbot_id} data was in old list format, converted to new dict format.")


                except json.JSONDecodeError:
                    logger.error(f"Failed to parse existing chatbot.data for {chatbot_id}. Initializing to empty sources. Data: {chatbot.data}")
                    current_data_obj = {"sources": [], "customization": {}} # Default customization

                # Ensure 'sources' is a list
                if not isinstance(current_data_obj.get('sources'), list):
                    current_data_obj['sources'] = []

                existing_sources = current_data_obj['sources']
                added_count = 0
                for new_source in newly_processed_sources:
                    if isinstance(new_source, dict) and 'name' in new_source and 'type' in new_source:
                        is_duplicate = any(
                            ex_source.get('name') == new_source['name'] and ex_source.get('type') == new_source['type']
                            for ex_source in existing_sources
                        )
                        if not is_duplicate:
                            existing_sources.append(new_source)
                            added_count += 1
                    else:
                        logger.warning(f"Skipping invalid new_source format: {new_source} for chatbot {chatbot_id}")

                current_data_obj['sources'] = existing_sources # Update with potentially new sources
                chatbot.data = json.dumps(current_data_obj)
                logger.info(f"Appended {added_count} new unique sources to chatbot {chatbot_id}. Total sources: {len(existing_sources)}.")
            else:
                logger.warning(f"preprocess_and_index_data did not return a dictionary with 'processed_sources' for chatbot {chatbot_id}. Result: {result_map}")
                # Not necessarily an error if no new files were processed and indexing was just for existing.
                # However, the frontend expects chatbot.data to be updated with source list.

            db.session.commit()
            training_message = result_map.get("message", "Chatbot trained successfully") if isinstance(result_map, dict) else "Chatbot trained successfully"
            return True, training_message

        except Exception as e:
            logger.error(f"Error training chatbot: {str(e)}")
            return False, str(e)

    @staticmethod
    def update_customization(chatbot_id: str, theme_color=None, avatar_url=None, enable_tickets=None,
                            enable_leads=None, enable_smart_lead_detection=None, enable_avatar=None,
                            enable_sentiment=None, widget_position=None, widget_radius=None) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Update chatbot customization settings

        Args:
            chatbot_id: The ID of the chatbot to update
            theme_color: Optional theme color
            avatar_url: Optional avatar URL
            enable_tickets: Optional boolean to enable/disable tickets
            enable_leads: Optional boolean to enable/disable leads
            enable_smart_lead_detection: Optional boolean to enable/disable smart lead detection
            enable_avatar: Optional boolean to enable/disable avatar display
            enable_sentiment: Optional boolean to enable/disable sentiment feedback
            widget_position: Optional string for widget position ('bottom-right' or 'bottom-left')
            widget_radius: Optional integer for widget radius in pixels (35-80)

        Returns:
            Tuple containing (customization_data, error_message)
        """
        try:
            logger.info(f"Updating customization for chatbot {chatbot_id} with widget_position={widget_position}")
            
            chatbot = Chatbot.query.get(chatbot_id)
            if not chatbot:
                logger.error(f"Chatbot not found with ID: {chatbot_id}")
                return {}, "Chatbot not found"

            # Parse existing data
            if not chatbot.data:
                logger.info(f"No existing data for chatbot {chatbot_id}, initializing new data")
                current_data = {}
            elif isinstance(chatbot.data, str):
                try:
                    current_data = json.loads(chatbot.data)
                    logger.info(f"Parsed string data for chatbot {chatbot_id}: {type(current_data)}")
                except json.JSONDecodeError:
                    logger.error(f"JSON decode error for chatbot {chatbot_id} data: {chatbot.data}")
                    current_data = {}
            else:
                current_data = chatbot.data
                logger.info(f"Using non-string data for chatbot {chatbot_id}: {type(current_data)}")

            # Handle case where current_data is a list
            if isinstance(current_data, list):
                # If it's a list, convert to a dictionary or use the last item
                if current_data:
                    # Use the last item if it's a dictionary, otherwise create a new dictionary
                    if isinstance(current_data[-1], dict):
                        current_data = current_data[-1]
                        logger.info(f"Using last item from list data for chatbot {chatbot_id}")
                    else:
                        current_data = {}
                        logger.info(f"Last item in list is not a dict for chatbot {chatbot_id}, using empty dict")
                else:
                    current_data = {}
                    logger.info(f"Empty list data for chatbot {chatbot_id}, using empty dict")

            # Initialize customization if it doesn't exist
            if not isinstance(current_data, dict):
                logger.info(f"Current data is not a dict for chatbot {chatbot_id}, initializing new dict")
                current_data = {}

            if 'customization' not in current_data:
                logger.info(f"No customization key in data for chatbot {chatbot_id}, creating it")
                current_data['customization'] = {}

            # Update customization settings
            if theme_color is not None:
                current_data['customization']['theme_color'] = theme_color
                logger.info(f"Set theme_color to {theme_color} for chatbot {chatbot_id}")

            if avatar_url is not None:
                current_data['customization']['avatar_url'] = avatar_url
                logger.info(f"Set avatar_url to {avatar_url} for chatbot {chatbot_id}")

            if enable_tickets is not None:
                current_data['customization']['enable_tickets'] = enable_tickets
                logger.info(f"Set enable_tickets to {enable_tickets} for chatbot {chatbot_id}")

            # Add support for new customization options
            if enable_leads is not None:
                current_data['customization']['enable_leads'] = enable_leads
                logger.info(f"Set enable_leads to {enable_leads} for chatbot {chatbot_id}")

            if enable_smart_lead_detection is not None:
                current_data['customization']['enable_smart_lead_detection'] = enable_smart_lead_detection
                logger.info(f"Set enable_smart_lead_detection to {enable_smart_lead_detection} for chatbot {chatbot_id}")

            if enable_avatar is not None:
                current_data['customization']['enable_avatar'] = enable_avatar
                logger.info(f"Set enable_avatar to {enable_avatar} for chatbot {chatbot_id}")

            if enable_sentiment is not None:
                current_data['customization']['enable_sentiment'] = enable_sentiment
                logger.info(f"Set enable_sentiment to {enable_sentiment} for chatbot {chatbot_id}")
                
            # Add support for widget position
            if widget_position is not None:
                current_data['customization']['widget_position'] = widget_position
                logger.info(f"Set widget_position to {widget_position} for chatbot {chatbot_id}")

            # Add support for widget radius
            if widget_radius is not None:
                current_data['customization']['widget_radius'] = widget_radius
                logger.info(f"Set widget_radius to {widget_radius} for chatbot {chatbot_id}")

            # Log the updated customization data for debugging
            logger.info(f"Final customization for chatbot {chatbot_id}: {current_data['customization']}")

            # Save updated data
            json_data = json.dumps(current_data)
            logger.info(f"Serialized data size: {len(json_data)} bytes")
            chatbot.data = json_data
            
            # Commit the changes
            db.session.commit()
            logger.info(f"Committed changes to database for chatbot {chatbot_id}")
            
            # Clear any cached data for this chatbot
            try:
                from xavier_back.utils.cache_utils import cache_invalidate
                cache_key_prefix = f"chatbot:{chatbot_id}"
                cache_invalidate(cache_key_prefix)
                logger.info(f"Invalidated cache for prefix {cache_key_prefix}")
            except Exception as cache_err:
                logger.warning(f"Error invalidating cache: {str(cache_err)}")

            return current_data['customization'], None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating customization: {str(e)}"
            logger.error(error_msg)
            return {}, error_msg
        except Exception as e:
            error_msg = f"Error updating customization: {str(e)}"
            logger.error(error_msg)
            return {}, error_msg
