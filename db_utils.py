"""
Database Utilities Module

This module provides utilities for database operations, including connection pooling,
retry mechanisms, and query optimization.
"""

import time
import logging
import functools
from functools import wraps
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy import text, func
from sqlalchemy.orm.query import Query

from extensions import db

# Configure logger
logger = logging.getLogger(__name__)

def with_db_retry(max_retries=3, retry_delay=1):
    """
    Decorator to retry database operations on connection errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (will be multiplied by attempt number)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, SQLAlchemyError) as e:
                    # Check if it's a connection error
                    if "SSL SYSCALL error" in str(e) or "EOF detected" in str(e) or "connection" in str(e).lower():
                        logger.warning(f"Database connection error on attempt {attempt+1}: {str(e)}")
                        if attempt < max_retries - 1:
                            # Close and recreate the session to get a fresh connection
                            db.session.rollback()
                            db.session.remove()
                            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                            continue
                    # Re-raise the exception if we've exhausted our retries or it's not a connection error
                    if attempt >= max_retries - 1:
                        logger.error(f"Database operation failed after {max_retries} attempts: {str(e)}")
                        raise
            return None  # This should never be reached
        return wrapper
    return decorator

def optimize_query(query, eager_load=None, chunk_size=None):
    """
    Optimize a SQLAlchemy query with eager loading and chunking.
    
    Args:
        query: SQLAlchemy query object
        eager_load: List of relationships to eager load
        chunk_size: Size of chunks for loading large result sets
        
    Returns:
        Optimized SQLAlchemy query
    """
    # Add eager loading if specified
    if eager_load:
        for relationship in eager_load:
            query = query.options(db.joinedload(relationship))
    
    # Add chunking if specified
    if chunk_size:
        query = query.yield_per(chunk_size)
    
    return query

def paginate_query(query, page=1, per_page=20):
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Number of items per page
        
    Returns:
        Tuple of (total, items) where total is the total number of items
        and items is the list of items for the requested page
    """
    # Ensure page and per_page are integers and have reasonable values
    page = max(1, int(page))
    per_page = max(1, min(100, int(per_page)))  # Limit per_page to 100
    
    # Get total count efficiently
    count_query = query.statement.with_only_columns([func.count()]).order_by(None)
    total = query.session.execute(count_query).scalar()
    
    # Apply pagination
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    
    return total, items

def execute_raw_sql(sql, params=None, fetchall=True):
    """
    Execute raw SQL with proper error handling and connection management.
    
    Args:
        sql: SQL query string
        params: Parameters for the query
        fetchall: Whether to fetch all results
        
    Returns:
        Query results
    """
    try:
        result = db.session.execute(text(sql), params)
        if fetchall:
            return result.fetchall()
        return result
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error executing SQL: {str(e)}")
        raise

def bulk_insert(model, records, chunk_size=1000):
    """
    Perform a bulk insert operation.
    
    Args:
        model: SQLAlchemy model class
        records: List of dictionaries with record data
        chunk_size: Number of records to insert in a single operation
        
    Returns:
        Number of records inserted
    """
    try:
        total_inserted = 0
        # Process in chunks to avoid memory issues
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i+chunk_size]
            db.session.bulk_insert_mappings(model, chunk)
            db.session.commit()
            total_inserted += len(chunk)
            logger.info(f"Inserted {len(chunk)} records of {model.__name__}")
        return total_inserted
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk insert: {str(e)}")
        raise

def safe_commit():
    """
    Safely commit changes to the database.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error committing to database: {str(e)}")
        return False
