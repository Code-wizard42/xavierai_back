"""
Chatbot Routes Module

This module contains route handlers for chatbot-related operations.
It uses the service layer for business logic.
"""
from flask import Blueprint, request, jsonify, session, current_app, url_for, send_file
from werkzeug.utils import secure_filename
import json
import os
import io
import logging
from functools import wraps
from flask_cors import cross_origin, CORS
from PIL import Image
import time

from xavier_back.models import Chatbot, ChatbotAvatar, Feedback
from xavier_back.extensions import db
from xavier_back.services.chatbot_service import ChatbotService
from xavier_back.services.analytics_service import AnalyticsService
from xavier_back.services.ticket_service import TicketService
from xavier_back.utils.auth_utils import login_required
from xavier_back.utils.response_utils import optimize_json_response, paginated_response, with_pagination
from xavier_back.utils.subscription_utils import check_chatbot_limit
from xavier_back.middleware.subscription_middleware import subscription_required
from xavier_back.middleware.chatbot_access_middleware import public_chatbot_subscription_required

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Create blueprint
chatbot_bp = Blueprint('chatbot', __name__)

# Constants for file uploads
UPLOAD_FOLDER = 'static/uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if a filename has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_errors(f):
    """Decorator to handle errors in route handlers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"error": "An unexpected error occurred"}), 500
    return decorated_function

@chatbot_bp.route('/create_chatbot', methods=['POST'])
@login_required
@subscription_required()
@check_chatbot_limit
@handle_errors
def create_chatbot():
    """Create a new chatbot"""
    data = request.json
    name = data.get('name')

    if not name:
        return jsonify({"error": "Name is required"}), 400

    # Use the service to create the chatbot
    chatbot, error = ChatbotService.create_chatbot(name, session['user_id'])

    if error:
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Chatbot created successfully",
        "chatbot_id": chatbot.id
    }), 201

@chatbot_bp.route('/chatbots', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_chatbots():
    """Get all chatbots for the current user"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        # Get total count
        total = Chatbot.query.filter_by(user_id=session['user_id']).count()

        # Get paginated results
        chatbots = Chatbot.query.filter_by(user_id=session['user_id']) \
            .order_by(Chatbot.name) \
            .offset((page - 1) * per_page) \
            .limit(per_page) \
            .all()

        # Format the response
        chatbot_list = [{
            "id": chatbot.id,
            "name": chatbot.name
        } for chatbot in chatbots]

        # Return optimized paginated response
        return optimize_json_response({
            "chatbots": chatbot_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page < ((total + per_page - 1) // per_page),
                "has_prev": page > 1
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving chatbots: {str(e)}")
        return jsonify({"error": "Failed to retrieve chatbots"}), 500

@chatbot_bp.route('/chatbot/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_chatbot_data(chatbot_id):
    """Get data for a specific chatbot"""
    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404

    # Get customization data if available
    customization = {}
    if chatbot.data:
        try:
            if isinstance(chatbot.data, str):
                data = json.loads(chatbot.data)
            else:
                data = chatbot.data

            if isinstance(data, dict) and 'customization' in data:
                customization = data['customization']
        except json.JSONDecodeError:
            pass

    # Return optimized response
    return optimize_json_response({
        "id": chatbot.id,
        "name": chatbot.name,
        "data": chatbot.data,
        "customization": customization
    })

@chatbot_bp.route('/chatbot/<chatbot_id>', methods=['PUT'])
@login_required
@subscription_required()
@handle_errors
def update_chatbot_data(chatbot_id):
    """Update a chatbot's data"""
    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404

    data = request.json

    # Update basic properties
    if 'name' in data:
        chatbot.name = data['name']

    # Update data if provided
    if 'data' in data:
        success, error = ChatbotService.update_chatbot_data(chatbot_id, data['data'])
        if not success:
            return jsonify({"error": error}), 500

    db.session.commit()

    return jsonify({"message": "Chatbot updated successfully"}), 200

@chatbot_bp.route('/chatbot/<chatbot_id>', methods=['DELETE'])
@login_required
@subscription_required()
@handle_errors
def delete_chatbot(chatbot_id):
    """Delete a chatbot"""
    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404

    success, error = ChatbotService.delete_chatbot(chatbot_id)

    if not success:
        return jsonify({"error": error}), 500

    return jsonify({"message": "Chatbot deleted successfully"}), 200

@chatbot_bp.route('/chatbot/<chatbot_id>/train', methods=['POST'])
@login_required
@subscription_required()
@handle_errors
def train_chatbot(chatbot_id):
    """Train a chatbot with new data"""
    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404

    # Check current data size limit (400 KB)
    MAX_DATA_SIZE_KB = 400
    if chatbot.data:
        try:
            current_size_bytes = len(chatbot.data.encode('utf-8'))
            current_size_kb = current_size_bytes / 1024
            
            if current_size_kb >= MAX_DATA_SIZE_KB:
                return jsonify({
                    "error": f"❌ TRAINING BLOCKED: Data limit exceeded!\n\nCurrent size: {current_size_kb:.2f} KB\nMaximum allowed: {MAX_DATA_SIZE_KB} KB\n\nYou must remove some existing data before training new content."
                }), 400
                
            # Warn if approaching limit (90% of max)
            if current_size_kb > MAX_DATA_SIZE_KB * 0.9:
                logger.warning(f"Chatbot {chatbot_id} approaching data limit: {current_size_kb:.2f} KB / {MAX_DATA_SIZE_KB} KB")
                
        except Exception as e:
            logger.error(f"Error checking data size for chatbot {chatbot_id}: {str(e)}")

    # Extract training data from request
    file = request.files.get('file')
    api_url = request.form.get('api_url')
    folder_path = request.form.get('folder_path')
    website_url = request.form.get('website_url')

    # Process file if provided
    pdf_files = []
    text_files = []
    if file:
        filename = secure_filename(file.filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Check file type and categorize appropriately
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension in ['.txt', '.md', '.rst']:
            text_files.append(filepath)
            logger.info(f"Added text file for training: {filepath}")
        elif file_extension in ['.doc', '.docx']:
            # Process DOC/DOCX files as text files since they're handled by file_utils
            text_files.append(filepath)
            logger.info(f"Added {file_extension.upper()} file for training: {filepath}")
        elif file_extension == '.pdf':
            pdf_files.append(filepath)
            logger.info(f"Added PDF file for training: {filepath}")
        else:
            # Default to PDF processing for unknown file types
            pdf_files.append(filepath)
            logger.info(f"Added file (unknown type, treating as PDF) for training: {filepath}")

    # Use the service to train the chatbot
    success, error = ChatbotService.train_chatbot(
        chatbot_id,
        pdf_files=pdf_files,
        text_files=text_files,
        api_url=api_url,
        folder_path=folder_path,
        website_url=website_url
    )

    # Clean up temporary files
    for filepath in pdf_files + text_files:
        if os.path.exists(filepath):
            os.remove(filepath)

    if not success:
        return jsonify({"error": error}), 400

    # Get the updated chatbot data to return to the frontend
    updated_chatbot = ChatbotService.get_chatbot(chatbot_id)
    if updated_chatbot:
        return jsonify({
            "message": "Chatbot trained successfully",
            "data": updated_chatbot.data
        }), 200
    else:
        return jsonify({"message": "Chatbot trained successfully"}), 200

@chatbot_bp.route('/train_chatbot/<chatbot_id>', methods=['POST'])
@login_required
@subscription_required()
@handle_errors
def train_chatbot_alt(chatbot_id):
    """Alternative endpoint for training a chatbot"""
    return train_chatbot(chatbot_id)

@chatbot_bp.route('/chatbot/<chatbot_id>/cancel-training', methods=['POST'])
@login_required
@subscription_required()
@handle_errors
def cancel_chatbot_training(chatbot_id):
    """Cancel ongoing chatbot training"""
    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot or chatbot.user_id != session['user_id']:
        return jsonify({"error": "Chatbot not found or unauthorized"}), 404

    # Note: Due to the nature of the training process (which involves file processing,
    # vector database operations, and potentially long-running embeddings generation),
    # it's difficult to implement true mid-process cancellation without significant
    # architectural changes. The frontend HTTP request cancellation is the primary
    # mechanism for stopping the training.
    
    # For now, we'll just log the cancellation request and return success
    # In a more sophisticated implementation, you might:
    # 1. Store training job IDs in a database
    # 2. Use a task queue like Celery with cancellation support
    # 3. Implement threading with cancellation tokens
    
    logger.info(f"Training cancellation requested for chatbot {chatbot_id} by user {session['user_id']}")
    
    return jsonify({
        "message": "Training cancellation processed. The training process will stop processing new data.",
        "note": "Some operations may continue to completion due to the nature of the training pipeline."
    }), 200

@chatbot_bp.route('/chatbot/<chatbot_id>/ask', methods=['POST'])
@public_chatbot_subscription_required
@handle_errors
def chatbot_ask(chatbot_id):
    """Ask a question to the chatbot"""
    # Start timing for performance tracking
    start_time = time.time()
    
    # Validate request
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported content type"}), 415

    data = request.json
    question = data.get('question')
    conversation_id = data.get('conversation_id')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Use the service to get an answer
    result = ChatbotService.get_answer(chatbot_id, question, conversation_id)

    if 'error' in result:
        return jsonify({"error": result['error']}), 404

    # Calculate processing time
    processing_time = time.time() - start_time
    processing_time_ms = int(processing_time * 1000)
    
    # Add processing time to result for monitoring
    result['processing_time_ms'] = processing_time_ms
    
    # Log performance metrics
    logging.info(f"Request processed in {processing_time_ms}ms for chatbot {chatbot_id}")

    # Track the question for analytics
    AnalyticsService.track_question(chatbot_id, {
        "question": question,
        "answer": result['answer'],
        "conversation_id": result.get('conversation_id'),
        "processing_time_ms": processing_time_ms
    })

    # Return optimized response with proper caching headers
    response = optimize_json_response({
        "question": question,
        "answer": result['answer'],
        "conversation_id": result.get('conversation_id'),
        "processing_time_ms": processing_time_ms
    })
    
    # Set additional caching headers for GET requests
    if not conversation_id:
        # Only cache stateless queries (without conversation context)
        response.headers['Cache-Control'] = 'private, max-age=300'
    
    return response

@chatbot_bp.route('/chatbot/<chatbot_id>/feedback', methods=['POST'])
@handle_errors
def submit_feedback(chatbot_id):
    """Submit feedback for a chatbot"""
    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404

    data = request.json
    feedback_text = data.get('feedback')
    user_id = request.headers.get('User-ID', '4269')  # Default to guest user if not provided

    if not feedback_text:
        return jsonify({"error": "Feedback is missing"}), 400

    # Create feedback record
    try:
        new_feedback = Feedback(
            chatbot_id=chatbot_id,
            user_id=user_id,
            feedback=feedback_text
        )
        db.session.add(new_feedback)
        db.session.commit()

        return jsonify({"message": "Feedback submitted successfully"}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting feedback: {str(e)}")
        return jsonify({"error": "Failed to submit feedback"}), 500

@chatbot_bp.route('/chatbot/<chatbot_id>/customize', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@handle_errors
def get_chatbot_customization(chatbot_id):
    """Get a chatbot's customization settings"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        current_app.logger.info(f"Getting customization settings for chatbot {chatbot_id}")
        
        # Use service to get chatbot but skip cache to ensure we have latest data
        from xavier_back.utils.cache_utils import cache_invalidate
        cache_key_prefix = f"chatbot:{chatbot_id}"
        cache_invalidate(cache_key_prefix)
        current_app.logger.info(f"Invalidated cache for prefix {cache_key_prefix}")
        
        chatbot = ChatbotService.get_chatbot(chatbot_id)
        if not chatbot:
            current_app.logger.error(f"Chatbot not found: {chatbot_id}")
            return jsonify({"error": "Chatbot not found"}), 404

        # Initialize default customization with all properties
        customization = {
            "theme_color": "#0084ff",  # Default blue color
            "avatar_url": "",  # Default empty avatar URL
            "enable_tickets": True,  # Default to enabled
            "enable_leads": False,  # Default to disabled
            "enable_smart_lead_detection": True,  # Default to enabled
            "enable_avatar": True,  # Default to enabled
            "enable_sentiment": True,  # Default to enabled
            "widget_position": "bottom-right",  # Default position
            "widget_radius": 45  # Default radius in pixels
        }

        # Get customization settings if they exist
        if chatbot.data:
            current_app.logger.info(f"Raw chatbot data type: {type(chatbot.data)}")
            try:
                # Handle string data
                if isinstance(chatbot.data, str):
                    data = json.loads(chatbot.data)
                    current_app.logger.info(f"Parsed string data for chatbot {chatbot_id}")
                else:
                    data = chatbot.data
                    current_app.logger.info(f"Using non-string data for chatbot {chatbot_id}")

                # Get customization from dictionary
                if isinstance(data, dict) and 'customization' in data:
                    current_app.logger.info(f"Found customization in data for chatbot {chatbot_id}: {data['customization']}")
                    customization.update(data['customization'])
                    current_app.logger.info(f"Final customization data to return: {customization}")
                else:
                    current_app.logger.warning(f"Couldn't find customization key in data for chatbot {chatbot_id}")
                    if isinstance(data, dict):
                        current_app.logger.info(f"Available keys in data: {data.keys()}")
                    else:
                        current_app.logger.info(f"Data is not a dict, it's a {type(data)}")

            except json.JSONDecodeError:
                current_app.logger.error(f"Invalid JSON in chatbot data for {chatbot_id}: {chatbot.data}")
                pass  # Use default customization

        # Set Cache-Control to prevent browser caching
        response = jsonify(customization)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200

    except Exception as e:
        current_app.logger.error(f"Error in get_chatbot_customization: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@chatbot_bp.route('/chatbot/<chatbot_id>/customize', methods=['PUT', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@login_required
@subscription_required()
@handle_errors
def customize_chatbot(chatbot_id):
    """Customize a chatbot's appearance and settings"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Methods', 'PUT')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    chatbot = ChatbotService.get_chatbot(chatbot_id)

    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404

    data = request.json
    current_app.logger.info(f"Received customization data: {data}")

    # Extract all customization properties
    theme_color = data.get('theme_color')
    avatar_url = data.get('avatar_url')
    enable_tickets = data.get('enable_tickets')
    enable_leads = data.get('enable_leads')
    enable_smart_lead_detection = data.get('enable_smart_lead_detection')
    enable_avatar = data.get('enable_avatar')
    enable_sentiment = data.get('enable_sentiment')
    widget_position = data.get('widget_position')
    widget_radius = data.get('widget_radius')

    # Validate theme color if provided
    if theme_color and (not isinstance(theme_color, str) or not theme_color.startswith('#') or len(theme_color) != 7):
        return jsonify({"error": "Invalid theme color format. Use hex format (e.g., #FF0000)"}), 400

    # Use the service to update customization with all properties
    customization, error = ChatbotService.update_customization(
        chatbot_id,
        theme_color=theme_color,
        avatar_url=avatar_url,
        enable_tickets=enable_tickets,
        enable_leads=enable_leads,
        enable_smart_lead_detection=enable_smart_lead_detection,
        enable_avatar=enable_avatar,
        enable_sentiment=enable_sentiment,
        widget_position=widget_position,
        widget_radius=widget_radius
    )

    if error:
        return jsonify({"error": error}), 500

    current_app.logger.info(f"Saved customization: {customization}")

    return jsonify({
        "message": "Chatbot customization updated successfully",
        "customization": customization
    }), 200

@chatbot_bp.route('/chatbot/<chatbot_id>/upload-avatar', methods=['POST'])
@handle_errors
def upload_avatar(chatbot_id):
    """Upload an avatar image for a chatbot"""
    try:
        if 'avatar' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
            # Process the image
            try:
                # Open the image and resize it
                img = Image.open(file)
                img = img.convert('RGB')  # Convert to RGB to ensure JPEG compatibility

                # Resize to a reasonable size (e.g., 200x200 pixels)
                img.thumbnail((200, 200))

                # Save to a bytes buffer
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                image_data = img_buffer.getvalue()

                # Generate a unique filename
                filename = f"{chatbot_id}_{secure_filename(file.filename)}"

                # Check if avatar already exists for this chatbot
                existing_avatar = ChatbotAvatar.query.filter_by(chatbot_id=chatbot_id).first()
                if existing_avatar:
                    # Update existing avatar
                    existing_avatar.filename = filename
                    existing_avatar.image_data = image_data
                    existing_avatar.content_type = 'image/jpeg'
                    db.session.commit()
                else:
                    # Create new avatar record
                    new_avatar = ChatbotAvatar(
                        chatbot_id=chatbot_id,
                        filename=filename,
                        image_data=image_data,
                        content_type='image/jpeg'
                    )
                    db.session.add(new_avatar)
                    db.session.commit()

                # Generate URL for the saved image
                avatar_url = url_for('chatbot.get_avatar_image', chatbot_id=chatbot_id, _external=True)

                # Update the chatbot's customization settings
                ChatbotService.update_customization(chatbot_id, avatar_url=avatar_url)

                return jsonify({"avatar_url": avatar_url}), 200
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                db.session.rollback()
                return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

        return jsonify({"error": "Invalid file type"}), 400
    except Exception as e:
        logger.error(f"Error uploading avatar: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@chatbot_bp.route('/chatbot/<chatbot_id>/avatar', methods=['GET'])
@handle_errors
def get_avatar_image(chatbot_id):
    """Get the avatar image for a chatbot"""
    try:
        avatar = ChatbotAvatar.query.filter_by(chatbot_id=chatbot_id).first()

        if not avatar:
            return jsonify({"error": "Avatar not found"}), 404

        # Create a file-like object from the binary data
        img_io = io.BytesIO(avatar.image_data)

        # Return the image
        return send_file(
            img_io,
            mimetype=avatar.content_type,
            as_attachment=False,
            download_name=avatar.filename
        )
    except Exception as e:
        logger.error(f"Error retrieving avatar: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@chatbot_bp.route('/get_chatbot_script/<chatbot_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins="*", methods=['GET', 'OPTIONS'], supports_credentials=False)
@handle_errors
def get_chatbot_script(chatbot_id):
    """Get integration script for embedding the chatbot in a website"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Max-Age', '604800')  # Increase to 7 days (604800 seconds)
        return response

    # Simple logging for script access
    chatbot = ChatbotService.get_chatbot(chatbot_id)
    if not chatbot:
        return jsonify({"error": "Chatbot not found"}), 404

    # Get customization settings with defaults
    customization = {
        "theme_color": "#0084ff",
        "avatar_url": ""
    }
    if chatbot.data:
        try:
            chatbot_data = json.loads(chatbot.data) if isinstance(chatbot.data, str) else chatbot.data

            # Handle list data (take the last item if it's a list)
            if isinstance(chatbot_data, list) and chatbot_data:
                chatbot_data = chatbot_data[-1]

            if isinstance(chatbot_data, dict):
                stored_custom = chatbot_data.get('customization', {})
                customization.update(stored_custom)
        except json.JSONDecodeError:
            pass

    # Get settings if available
    enable_tickets = customization.get('enable_tickets', True)
    enable_leads = customization.get('enable_leads', False)
    enable_smart_lead_detection = customization.get('enable_smart_lead_detection', True)
    enable_avatar = customization.get('enable_avatar', True)
    enable_sentiment = customization.get('enable_sentiment', True)
    widget_position = customization.get('widget_position', 'bottom-right')
    widget_radius = customization.get('widget_radius', 45)

    # Use the same protocol as the request
    is_https = request.is_secure
    scheme = 'https' if is_https else 'http'

    # Generate URLs with the correct protocol
    static_url = url_for('static', filename='js/widget.js', _external=True, _scheme=scheme)
    api_url = request.url_root

    # If avatar URL is empty, use the default avatar endpoint
    avatar_url = customization['avatar_url']
    if not avatar_url:
        avatar_url = f"{scheme}://{request.host}/chatbot/{chatbot_id}/avatar"

    script = (
        f'''<script src="{static_url}" data-id="{chatbot_id}" data-name="{chatbot.name}" data-theme="{customization['theme_color']}" data-avatar="{avatar_url}" data-api="{api_url}" data-enable-leads="{str(enable_leads).lower()}" data-enable-tickets="{str(enable_tickets).lower()}" data-enable-smart-lead-detection="{str(enable_smart_lead_detection).lower()}" data-enable-avatar="{str(enable_avatar).lower()}" data-enable-sentiment="{str(enable_sentiment).lower()}" data-position="{widget_position}" data-radius="{widget_radius}"></script>'''
    )

    # Create the response with the integration code
    response_data = {
        'integration_code': script,
        'preview': script
    }

    return jsonify(response_data), 200

@chatbot_bp.route('/ticket/create/<chatbot_id>', methods=['POST'])
@login_required
@subscription_required()
@handle_errors
def create_ticket(chatbot_id):
    """Create a support ticket"""
    data = request.json

    # Validate required fields
    required_fields = ['subject', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Extract ticket data
    subject = data.get('subject')
    description = data.get('description')
    priority = data.get('priority', 'medium')
    account_details = data.get('account_details')

    # Use the service to create the ticket
    ticket, error = TicketService.create_ticket(
        chatbot_id=chatbot_id,
        subject=subject,
        description=description,
        priority=priority,
        account_details=account_details
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Ticket created successfully",
        "ticket_id": ticket.id
    }), 201

@chatbot_bp.route('/ticket/<ticket_id>', methods=['GET'])
@handle_errors
def get_ticket(ticket_id):
    """Get a ticket by ID"""
    ticket = TicketService.get_ticket(ticket_id)

    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    # Get responses for the ticket
    responses = TicketService.get_ticket_responses(ticket.id)

    return jsonify({
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat(),
            "account_details": ticket.account_details if hasattr(ticket, 'account_details') else None
        },
        "responses": [{
            "id": response.id,
            "message": response.message if hasattr(response, 'message') else response.response,
            "user_id": response.user_id,
            "created_at": response.created_at.isoformat()
        } for response in responses]
    }), 200

@chatbot_bp.route('/ticket/<ticket_id>/update-status', methods=['PATCH', 'OPTIONS'])
@login_required
@subscription_required()
@handle_errors
def update_ticket_status(ticket_id):
    """Update a ticket's status"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Methods', 'PATCH')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    data = request.json
    if 'status' not in data:
        return jsonify({"error": "Status is required"}), 400

    # Use the service to update the ticket status
    success, error = TicketService.update_ticket_status(ticket_id, data['status'])

    if not success:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Ticket status updated successfully",
        "ticket_id": ticket_id,
        "status": data['status']
    }), 200

@chatbot_bp.route('/ticket/<ticket_id>/priority', methods=['PUT', 'OPTIONS'])
@handle_errors
def update_ticket_priority(ticket_id):
    """Update a ticket's priority"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Methods', 'PUT')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    data = request.json
    if 'priority' not in data:
        return jsonify({"error": "Priority is required"}), 400

    # Use the service to update the ticket priority
    success, error = TicketService.update_ticket_priority(ticket_id, data['priority'])

    if not success:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Ticket priority updated successfully",
        "ticket_id": ticket_id,
        "priority": data['priority']
    }), 200

@chatbot_bp.route('/ticket/delete/<ticket_id>', methods=['DELETE', 'OPTIONS'])
@handle_errors
def delete_ticket(ticket_id):
    """Delete a ticket"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Methods', 'DELETE')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    # Use the service to delete the ticket
    success, error = TicketService.delete_ticket(ticket_id)

    if not success:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Ticket deleted successfully",
        "ticket_id": ticket_id
    }), 200

@chatbot_bp.route('/tickets/<chatbot_id>', methods=['GET'])
@login_required
@subscription_required()
@handle_errors
def get_tickets_by_chatbot(chatbot_id):
    """Get all tickets for a specific chatbot"""
    # Use the service to get tickets for the chatbot
    tickets = TicketService.get_tickets_for_chatbot(chatbot_id)

    return jsonify({
        "tickets": [{
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat(),
            "chatbot_id": ticket.chatbot_id,
            "user_id": ticket.user_id,
            "account_details": ticket.account_details if hasattr(ticket, 'account_details') else None
        } for ticket in tickets]
    }), 200

# Add an endpoint that matches the frontend's expected delete endpoint
@chatbot_bp.route('/delete_chatbot/<chatbot_id>', methods=['DELETE', 'OPTIONS'])
@login_required
@subscription_required()
@handle_errors
def delete_chatbot_alt(chatbot_id):
    """Alternative endpoint for deleting a chatbot that matches the frontend's expected URL"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Methods', 'DELETE')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    # Reuse the existing delete_chatbot logic
    return delete_chatbot(chatbot_id)

# Handle removed features gracefully
@chatbot_bp.route('/agent/escalations/<chatbot_id>', methods=['GET'])
def handle_removed_escalation(chatbot_id):
    """Handle requests to the removed escalation feature"""
    logger.info(f"Escalation endpoint called for chatbot: {chatbot_id}")
    return jsonify({
        "message": "Escalation feature has been removed",
        "status": "disabled"
    }), 200
