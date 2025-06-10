"""
Run all migrations
"""
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the app to initialize the database connection
from xavier_back.app import app
from xavier_back.migrations.whatsapp_integration import run_migration

# Run the migrations
with app.app_context():
    run_migration()

print("All migrations completed successfully")
