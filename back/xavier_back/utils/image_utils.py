"""
Lightweight image processing utilities without heavy dependencies.
Alternative to Pillow/OpenCV for basic operations.
"""

import io
import base64
import struct
from typing import Tuple, Optional


class LightImageProcessor:
    """Ultra-lightweight image processor for basic operations."""
    
    @staticmethod
    def get_image_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
        """Get image dimensions without loading the full image.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            (width, height) tuple or None if format not supported
        """
        # JPEG format
        if image_data.startswith(b'\xff\xd8\xff'):
            return LightImageProcessor._get_jpeg_dimensions(image_data)
        
        # PNG format
        elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return LightImageProcessor._get_png_dimensions(image_data)
        
        # GIF format
        elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
            return LightImageProcessor._get_gif_dimensions(image_data)
        
        # WebP format
        elif image_data[8:12] == b'WEBP':
            return LightImageProcessor._get_webp_dimensions(image_data)
        
        return None
    
    @staticmethod
    def _get_jpeg_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
        """Extract dimensions from JPEG image header."""
        try:
            i = 2
            while i < len(image_data):
                if image_data[i] == 0xFF:
                    marker = image_data[i + 1]
                    if marker in [0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF]:
                        height = struct.unpack('>H', image_data[i + 5:i + 7])[0]
                        width = struct.unpack('>H', image_data[i + 7:i + 9])[0]
                        return width, height
                    else:
                        length = struct.unpack('>H', image_data[i + 2:i + 4])[0]
                        i += 2 + length
                else:
                    i += 1
        except (struct.error, IndexError):
            pass
        return None
    
    @staticmethod
    def _get_png_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
        """Extract dimensions from PNG image header."""
        try:
            if len(image_data) >= 24:
                width = struct.unpack('>I', image_data[16:20])[0]
                height = struct.unpack('>I', image_data[20:24])[0]
                return width, height
        except struct.error:
            pass
        return None
    
    @staticmethod
    def _get_gif_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
        """Extract dimensions from GIF image header."""
        try:
            if len(image_data) >= 10:
                width = struct.unpack('<H', image_data[6:8])[0]
                height = struct.unpack('<H', image_data[8:10])[0]
                return width, height
        except struct.error:
            pass
        return None
    
    @staticmethod
    def _get_webp_dimensions(image_data: bytes) -> Optional[Tuple[int, int]]:
        """Extract dimensions from WebP image header."""
        try:
            if len(image_data) >= 30 and image_data[12:16] == b'VP8 ':
                width = struct.unpack('<H', image_data[26:28])[0] & 0x3fff
                height = struct.unpack('<H', image_data[28:30])[0] & 0x3fff
                return width, height
        except struct.error:
            pass
        return None
    
    @staticmethod
    def validate_image_format(image_data: bytes) -> bool:
        """Validate if the data is a supported image format.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            True if format is supported
        """
        return LightImageProcessor.get_image_dimensions(image_data) is not None
    
    @staticmethod
    def calculate_thumbnail_size(original_width: int, original_height: int, 
                               target_size: int = 200) -> Tuple[int, int]:
        """Calculate thumbnail dimensions while maintaining aspect ratio.
        
        Args:
            original_width: Original image width
            original_height: Original image height
            target_size: Target maximum dimension
            
        Returns:
            (new_width, new_height) tuple
        """
        scale = min(target_size / original_width, target_size / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        return new_width, new_height
    
    @staticmethod
    def create_data_url(image_data: bytes, mime_type: str = 'image/jpeg') -> str:
        """Create a data URL from image bytes.
        
        Args:
            image_data: Raw image bytes
            mime_type: MIME type of the image
            
        Returns:
            Data URL string
        """
        encoded = base64.b64encode(image_data).decode('ascii')
        return f"data:{mime_type};base64,{encoded}"
    
    @staticmethod
    def estimate_file_size(image_data: bytes) -> str:
        """Estimate and format file size.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Formatted file size string
        """
        size_bytes = len(image_data)
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


# Convenience instance
light_processor = LightImageProcessor() 