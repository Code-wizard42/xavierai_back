"""
Response Utilities Module

This module provides utility functions for optimizing API responses.
"""
import json
from flask import jsonify, Response, request
from functools import wraps
from typing import Dict, List, Any, Optional, Union, Callable
import time

def optimize_json_response(data: Any, status_code: int = 200) -> Response:
    """
    Optimize a JSON response with proper headers and formatting.
    
    Args:
        data: The data to be returned as JSON
        status_code: HTTP status code
        
    Returns:
        Flask Response object with optimized JSON
    """
    response = jsonify(data)
    response.status_code = status_code
    
    # Add response timestamp for client-side caching
    if isinstance(data, dict):
        if 'timestamp' not in data:
            response.set_data(json.dumps({**json.loads(response.get_data(as_text=True)), 'timestamp': time.time()}))
    
    return response

def paginated_response(query_function: Callable, **kwargs) -> Dict:
    """
    Create a paginated response for database queries.
    
    Args:
        query_function: Function that returns query results
        **kwargs: Additional parameters including page, per_page
        
    Returns:
        Dictionary with paginated results and metadata
    """
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # Get total count and paginated results
    total, items = query_function(page=page, per_page=per_page, **kwargs)
    
    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev
        }
    }

def with_pagination(f):
    """
    Decorator to add pagination to API endpoints.
    
    Usage:
        @app.route('/api/items')
        @with_pagination
        def get_items():
            # Your query logic here
            return items_query
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Call the original function to get the query
        query = f(*args, **kwargs)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Serialize items if needed
        if hasattr(items[0], '__dict__') if items else False:
            serialized_items = [item.to_dict() if hasattr(item, 'to_dict') else item.__dict__ for item in items]
        else:
            serialized_items = items
        
        # Return paginated response
        return {
            'items': serialized_items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page,
                'has_next': page < ((total + per_page - 1) // per_page),
                'has_prev': page > 1
            }
        }
    
    return decorated_function
