"""
Ultra-lightweight avatar upload without image processing dependencies.
Only validates format and stores raw images - no resizing.
"""

import io
import logging
from flask import Blueprint, request, jsonify, url_for, send_file
from werkzeug.utils import secure_filename

from ..models.chatbot_avatar import ChatbotAvatar
from ..models import db
from ..utils.image_utils import light_processor

logger = logging.getLogger(__name__)

# Supported formats (by magic bytes)
SUPPORTED_FORMATS = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png', 
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
}

def upload_avatar_light(chatbot_id):
    """Ultra-lightweight avatar upload without image processing."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file selected"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Read file data
        file.seek(0)
        image_data = file.read()
        
        # Basic validation using magic bytes
        if not light_processor.validate_image_format(image_data):
            return jsonify({"error": "Unsupported image format"}), 400
        
        # Get image info without loading
        dimensions = light_processor.get_image_dimensions(image_data)
        if not dimensions:
            return jsonify({"error": "Invalid image file"}), 400
        
        width, height = dimensions
        file_size = light_processor.estimate_file_size(image_data)
        
        # Optional: Size limits (without resizing)
        max_size = 5 * 1024 * 1024  # 5MB limit
        if len(image_data) > max_size:
            return jsonify({"error": f"File too large. Max size: 5MB, your file: {file_size}"}), 400
        
        # Determine content type
        content_type = 'image/jpeg'  # Default
        for magic_bytes, mime_type in SUPPORTED_FORMATS.items():
            if image_data.startswith(magic_bytes):
                content_type = mime_type
                break
        
        # Generate filename
        filename = f"{chatbot_id}_{secure_filename(file.filename)}"
        
        # Store in database (raw, no processing)
        existing_avatar = ChatbotAvatar.query.filter_by(chatbot_id=chatbot_id).first()
        if existing_avatar:
            existing_avatar.filename = filename
            existing_avatar.image_data = image_data
            existing_avatar.content_type = content_type
            db.session.commit()
        else:
            new_avatar = ChatbotAvatar(
                chatbot_id=chatbot_id,
                filename=filename,
                image_data=image_data,
                content_type=content_type
            )
            db.session.add(new_avatar)
            db.session.commit()
        
        avatar_url = url_for('chatbot.get_avatar_image', chatbot_id=chatbot_id, _external=True)
        
        return jsonify({
            "avatar_url": avatar_url,
            "info": {
                "dimensions": f"{width}x{height}",
                "size": file_size,
                "format": content_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading avatar: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500 