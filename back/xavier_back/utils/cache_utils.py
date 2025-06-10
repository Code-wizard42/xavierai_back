"""
Cache Utilities Module

This module provides caching mechanisms for the application.
It implements both Redis and in-memory caching to improve performance.
"""

import os
import json
import logging
import pickle
import time
import hashlib
from functools import wraps
from typing import Any, Dict, Optional, Callable, Tuple, Union

# Initialize logger
logger = logging.getLogger(__name__)

# Try to import Redis
REDIS_AVAILABLE = False
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError, TimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis package not installed. Using in-memory caching only.")

# In-memory cache as fallback
in_memory_cache = {}
in_memory_ttl = {}

# Redis client initialization
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            # Configure SSL settings for Redis Cloud
            if redis_url.startswith('rediss://'):
                # For SSL connections, try multiple SSL configurations for compatibility
                redis_client = None
                
                # Try basic SSL config first
                try:
                    redis_client = redis.from_url(
                        redis_url,
                        ssl_cert_reqs=None,
                        ssl_check_hostname=False,
                        ssl_ca_certs=None,
                        decode_responses=False,
                        socket_timeout=10,
                        socket_connect_timeout=10,
                        retry_on_timeout=True,
                        health_check_interval=30
                    )
                    redis_client.ping()
                    logger.info("Redis SSL connection successful with basic SSL config")
                except Exception as ssl_error:
                    logger.warning(f"Basic SSL config failed: {str(ssl_error)}. Trying alternative SSL config.")
                    try:
                        # Try with specific TLS version and connection pool
                        import ssl
                        
                        # Create SSL context with specific TLS version
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        # Try to force TLS 1.2 or higher
                        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                        
                        pool = redis.ConnectionPool.from_url(
                            redis_url,
                            ssl_context=ssl_context,
                            decode_responses=False,
                            socket_timeout=10,
                            socket_connect_timeout=10,
                            retry_on_timeout=True,
                            health_check_interval=30
                        )
                        redis_client = redis.Redis(connection_pool=pool)
                        redis_client.ping()
                        logger.info("Redis SSL connection successful with TLS context")
                    except Exception as alt_error:
                        logger.warning(f"TLS context config also failed: {str(alt_error)}. Trying non-SSL approach.")
                        try:
                            # Last resort: try converting rediss:// to redis:// (non-SSL)
                            non_ssl_url = redis_url.replace('rediss://', 'redis://')
                            redis_client = redis.from_url(
                                non_ssl_url,
                                decode_responses=False,
                                socket_timeout=10,
                                socket_connect_timeout=10,
                                retry_on_timeout=True,
                                health_check_interval=30
                            )
                            redis_client.ping()
                            logger.info("Redis connection successful without SSL")
                        except Exception as final_error:
                            logger.warning(f"All Redis connection attempts failed: {str(final_error)}. Will fall back to in-memory cache.")
                            redis_client = None
            else:
                # For non-SSL connections
                redis_client = redis.from_url(
                    redis_url, 
                    decode_responses=False,
                    socket_timeout=10,
                    socket_connect_timeout=10,
                    retry_on_timeout=True
                )
            
            # Test the connection (only if not already tested in SSL block)
            if redis_client and not redis_url.startswith('rediss://'):
                redis_client.ping()
            
            if redis_client:
                logger.info(f"Connected to Redis successfully")
        else:
            # Try individual Redis environment variables if REDIS_URL is not set
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_db = int(os.environ.get('REDIS_DB', 0))
            redis_password = os.environ.get('REDIS_PASSWORD')
            
            # Check if we have Redis Cloud individual variables
            if redis_host != 'localhost' or redis_password:
                # Looks like Redis Cloud configuration via individual variables
                try:
                    # Try SSL connection first for cloud Redis
                    try:
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                        
                        redis_client = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            db=redis_db,
                            password=redis_password,
                            ssl=True,
                            ssl_context=ssl_context,
                            socket_timeout=10,
                            socket_connect_timeout=10,
                            retry_on_timeout=True,
                            decode_responses=False
                        )
                        redis_client.ping()
                        logger.info(f"Connected to Redis Cloud at {redis_host}:{redis_port} with SSL")
                    except Exception as ssl_error:
                        logger.warning(f"SSL connection failed: {str(ssl_error)}. Trying non-SSL.")
                        # Try without SSL
                        redis_client = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            db=redis_db,
                            password=redis_password,
                            ssl=False,
                            socket_timeout=10,
                            socket_connect_timeout=10,
                            retry_on_timeout=True,
                            decode_responses=False
                        )
                        redis_client.ping()
                        logger.info(f"Connected to Redis at {redis_host}:{redis_port} without SSL")
                except Exception as e:
                    logger.warning(f"Failed to connect to Redis cloud with individual vars: {str(e)}")
                    redis_client = None
            else:
                # Local Redis configuration
                try:
                    redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password,
                        socket_timeout=10,
                        socket_connect_timeout=10,
                        retry_on_timeout=True,
                        decode_responses=False
                    )
                    redis_client.ping()
                    logger.info(f"Connected to local Redis at {redis_host}:{redis_port}/{redis_db}")
                except Exception as e:
                    logger.warning(f"Failed to connect to local Redis: {str(e)}")
                    redis_client = None
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {str(e)}. Using in-memory caching only.")
        redis_client = None

def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a deterministic cache key from arguments.
    
    Args:
        prefix: Prefix for the cache key
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key
        
    Returns:
        A string cache key
    """
    # Convert args and kwargs to a string representation
    key_parts = [prefix]
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))
    
    # Sort kwargs for deterministic ordering
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if v is not None:
            key_parts.append(f"{k}:{v}")
    
    # Create full key string
    key_str = ":".join(key_parts)
    
    # If key is too long, hash it
    if len(key_str) > 250:
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        key_str = f"{prefix}:hash:{key_hash}"
    
    return key_str

def cache_get(key: str) -> Tuple[bool, Any]:
    """Get a value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Tuple of (success, value)
    """
    # Try Redis first if available
    if redis_client:
        try:
            value = redis_client.get(key)
            if value:
                return True, pickle.loads(value)
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis get error for key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Redis get for key {key}: {str(e)}")
    
    # Fallback to in-memory cache
    if key in in_memory_cache:
        # Check if TTL has expired
        if key in in_memory_ttl and in_memory_ttl[key] < time.time():
            # Expired, remove from cache
            del in_memory_cache[key]
            del in_memory_ttl[key]
            return False, None
        
        return True, in_memory_cache[key]
    
    return False, None

def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set a value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: 5 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    # Try Redis first if available
    if redis_client:
        try:
            serialized = pickle.dumps(value)
            redis_client.setex(key, ttl, serialized)
            return True
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis set error for key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Redis set for key {key}: {str(e)}")
    
    # Fallback to in-memory cache
    in_memory_cache[key] = value
    in_memory_ttl[key] = time.time() + ttl
    
    # Clean expired in-memory cache entries if we have too many
    if len(in_memory_cache) > 1000:  # Limit cache size
        current_time = time.time()
        # Get expired keys
        expired_keys = [k for k, expire_time in in_memory_ttl.items() 
                        if expire_time < current_time]
        # Remove expired entries
        for k in expired_keys:
            if k in in_memory_cache:
                del in_memory_cache[k]
            if k in in_memory_ttl:
                del in_memory_ttl[k]
    
    return True

def cache_invalidate(key_prefix: str = None) -> bool:
    """Invalidate cache entries with the given prefix.
    
    Args:
        key_prefix: Prefix of keys to invalidate (None for all keys)
        
    Returns:
        True if successful, False otherwise
    """
    success = True
    
    # Try Redis first if available
    if redis_client:
        try:
            if key_prefix:
                # Delete keys matching the pattern
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, f"{key_prefix}*", 100)
                    if keys:
                        redis_client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                # Flush all keys in the current DB (careful with this!)
                redis_client.flushdb()
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis invalidate error: {str(e)}")
            success = False
        except Exception as e:
            logger.error(f"Unexpected error during Redis invalidate: {str(e)}")
            success = False
    
    # Also clear in-memory cache
    if key_prefix:
        # Delete keys with matching prefix
        keys_to_delete = [k for k in in_memory_cache.keys() if k.startswith(key_prefix)]
        for k in keys_to_delete:
            if k in in_memory_cache:
                del in_memory_cache[k]
            if k in in_memory_ttl:
                del in_memory_ttl[k]
    else:
        # Clear all in-memory cache
        in_memory_cache.clear()
        in_memory_ttl.clear()
    
    return success

def cache_delete(key: str) -> bool:
    """Delete a specific cache key.
    
    Args:
        key: Cache key to delete
        
    Returns:
        True if successful, False otherwise
    """
    # For Redis
    if redis_client:
        try:
            redis_client.delete(key)
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis delete error for key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Redis delete for key {key}: {str(e)}")
    
    # For in-memory cache
    if key in in_memory_cache:
        del in_memory_cache[key]
    if key in in_memory_ttl:
        del in_memory_ttl[key]
    
    return True

def cached(prefix: str, ttl: int = 300):
    """Decorator to cache function results.
    
    Args:
        prefix: Prefix for cache keys
        ttl: Time to live in seconds (default: 5 minutes)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            found, value = cache_get(cache_key)
            if found:
                return value
            
            # Call original function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Singleton instance
cache = {
    'get': cache_get,
    'set': cache_set,
    'invalidate': cache_invalidate,
    'generate_key': generate_cache_key,
    'delete': cache_delete
} 