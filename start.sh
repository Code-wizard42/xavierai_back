#!/bin/bash

# Xavier AI Backend Startup Script for Coolify

echo "Starting Xavier AI Backend..."

# Set environment variables
export FLASK_ENV=production
export PORT=${PORT:-5000}
export PYTHONPATH=/app

# Install dependencies if requirements changed
echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations if needed
echo "Running database setup..."
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from xavier_back.extensions import db
    db.create_all()
    print('Database tables created successfully')
"

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --preload app:app 