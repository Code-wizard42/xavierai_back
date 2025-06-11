# Caching & Performance Optimization Guide

This document outlines the caching and performance optimizations implemented to improve system performance under high traffic conditions.

## Optimizations Implemented

1. **Redis Caching Layer**
   - In-memory caching with Redis for frequently accessed data
   - Fallback to local in-memory cache when Redis is unavailable
   - Configurable TTL (Time-To-Live) for different types of data

2. **Database Optimizations**
   - Connection pooling with optimized settings
   - Query optimization utilities for pagination and bulk operations
   - Retry mechanism for handling database connection issues

3. **HTTP Response Optimizations**
   - Response compression with Flask-Compress
   - HTTP caching headers with proper Cache-Control directives
   - ETag support for conditional requests

4. **Application-Level Caching**
   - Cached vector database searches
   - Cached LLM responses for repeated questions
   - Cached analytics queries

## Configuration

### Environment Variables

Add these environment variables to enable Redis caching:

```
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
# Or set individual components
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password  # Optional
```

### Cache TTL Settings

Cache expiration times are configurable in the relevant files:

- `nlp_utils_enhanced.py`: LLM and vector search caching settings
- `chatbot_service.py`: Chatbot data caching settings
- `analytics_service.py`: Analytics data caching settings

## Deployment

### Option 1: Using Docker Compose

1. Start Redis and optional PostgreSQL with Docker Compose:

```bash
docker-compose up -d redis
```

2. Set the `REDIS_URL` environment variable in your application:

```bash
export REDIS_URL=redis://localhost:6379/0
```

3. Run the application:

```bash
cd back
pip install -r requirements.txt
python run_app.py
```

### Option 2: Using Existing Redis Instance

1. Set the Redis connection environment variables:

```bash
export REDIS_URL=redis://your-redis-host:6379/0
```

2. Run the application as normal:

```bash
cd back
pip install -r requirements.txt
python run_app.py
```

## Monitoring

The system logs performance metrics:

- Slow requests (taking more than 1 second) are logged with warning level
- Redis connection issues will fall back to in-memory caching
- Cache hit/miss statistics are logged at the info level

Check the logs at `logs/info.log` for performance information.

## Troubleshooting

### Redis Connection Issues

If Redis connection fails, the system will automatically fall back to in-memory caching. Check the logs for warnings about Redis connection failures.

### Database Connection Pool Exhaustion

If you see database connection errors under high load, you may need to adjust the pool settings in `extensions.py`:

```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,      # Increase for higher concurrency
    'max_overflow': 40,   # Increase for higher peak loads
    'pool_recycle': 1800  # Adjust based on database connection lifetime
}
```

### High Memory Usage

If the application uses too much memory due to caching:

1. Reduce cache TTL values in the settings
2. Lower the maximum size of the in-memory cache in `cache_utils.py`
3. Use Redis with proper memory limits configured

## Performance Testing

To verify the performance improvements:

1. Test with and without Redis to compare performance
2. Monitor response times for repeated queries to verify caching
3. Use tools like Apache Benchmark or JMeter for load testing

Example Apache Benchmark command:

```bash
ab -n 1000 -c 10 http://localhost:5000/chatbot/{your_chatbot_id}/ask
``` 