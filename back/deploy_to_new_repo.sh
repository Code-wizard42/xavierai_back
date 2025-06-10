#!/bin/bash

# Xavier Backend Deployment Script
# This script helps deploy the xavier_back backend to a new GitHub repository

set -e

echo "🚀 Xavier Backend Deployment Setup"
echo "=================================="

# Check if repository URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <new-repository-url> [local-directory-name]"
    echo "Example: $0 https://github.com/username/xavier-backend.git xavier-backend"
    exit 1
fi

REPO_URL=$1
LOCAL_DIR=${2:-"xavier-backend-deploy"}
CURRENT_DIR=$(pwd)

echo "Repository URL: $REPO_URL"
echo "Local directory: $LOCAL_DIR"

# Clone the new repository
echo "📁 Cloning new repository..."
git clone "$REPO_URL" "$LOCAL_DIR"
cd "$LOCAL_DIR"

# Copy essential files
echo "📂 Copying backend files..."

# Create the main directory structure
mkdir -p xavier_back

# Copy the entire xavier_back directory
cp -r "$CURRENT_DIR/xavier_back/"* ./xavier_back/

# Copy essential configuration files
cp "$CURRENT_DIR/requirements.txt" ./
cp "$CURRENT_DIR/Procfile" ./
cp "$CURRENT_DIR/run_app.py" ./
cp "$CURRENT_DIR/run_app_fast.py" ./
cp "$CURRENT_DIR/setup.py" ./
cp "$CURRENT_DIR/.gitignore" ./

# Copy README if it exists
if [ -f "$CURRENT_DIR/README.md" ]; then
    cp "$CURRENT_DIR/README.md" ./
fi

# Create environment template
echo "🔧 Creating environment template..."
cat > .env.template << EOF
# Core Application
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
FLASK_CONFIG=production

# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# Session Storage
REDIS_URL=redis://user:password@host:port

# AI Services
OPENAI_API_KEY=your-openai-api-key

# Vector Database
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-api-key

# Firebase (if using)
FIREBASE_CREDENTIALS=your-firebase-credentials

# CORS (if needed)
FRONTEND_URL=https://your-frontend-domain.com
EOF

# Create deployment README
echo "📝 Creating deployment README..."
cat > DEPLOYMENT.md << EOF
# Xavier Backend Deployment

This repository contains the Xavier AI backend ready for deployment.

## Quick Deploy

### Railway
1. Connect this repository to Railway
2. Set environment variables from \`.env.template\`
3. Deploy

### Heroku
\`\`\`bash
heroku create your-app-name
heroku config:set FLASK_ENV=production
# Set other environment variables...
git push heroku main
\`\`\`

### Render
1. Connect this repository to Render
2. Set build command: \`pip install -r requirements.txt\`
3. Set start command: \`gunicorn --bind 0.0.0.0:\$PORT xavier_back.app:create_app()\`
4. Set environment variables
5. Deploy

## Environment Variables

Copy \`.env.template\` to \`.env\` and fill in your values, then set them in your deployment platform.

## Database Initialization

After deployment, initialize the database:
\`\`\`bash
python -c "from xavier_back.app import create_app; from xavier_back.models import db; app = create_app(); app.app_context().push(); db.create_all()"
\`\`\`
EOF

# Clean up any development files
echo "🧹 Cleaning up development files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name ".env" -delete 2>/dev/null || true

# Remove instance directory if it exists (contains local development data)
rm -rf instance/ 2>/dev/null || true
rm -rf flask_session/ 2>/dev/null || true
rm -rf logs/ 2>/dev/null || true
rm -rf uploads/* 2>/dev/null || true

# Create uploads directory with gitkeep
mkdir -p uploads
touch uploads/.gitkeep

# Commit and push
echo "📤 Committing and pushing to repository..."
git add .
git commit -m "Initial backend deployment setup

- Added Xavier AI backend application
- Added deployment configuration
- Added environment template
- Ready for production deployment"

git push origin main

echo "✅ Deployment setup complete!"
echo ""
echo "Next steps:"
echo "1. Go to your deployment platform (Railway, Heroku, Render, etc.)"
echo "2. Connect this repository: $REPO_URL"
echo "3. Set environment variables from .env.template"
echo "4. Deploy the application"
echo "5. Initialize the database using the commands in DEPLOYMENT.md"
echo ""
echo "Repository location: $(pwd)"
EOF 