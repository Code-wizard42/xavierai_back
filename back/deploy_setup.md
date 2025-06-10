# Xavier Backend Deployment Setup Guide

## Files to Copy to New Repository

When setting up the backend in a new GitHub repository, copy these files and directories:

### Required Files and Directories:
```
xavier_back/              # Main application directory
requirements.txt          # Python dependencies
Procfile                 # For Heroku/Railway deployment
run_app.py              # Main application runner
run_app_fast.py         # Fast application runner
setup.py                # Package setup
.gitignore              # Git ignore rules
README.md               # Documentation
```

### Optional Files:
```
config_fast.env         # Environment configuration template
scripts/                # Utility scripts
```

## Step-by-Step Deployment Process

### 1. Create New GitHub Repository

1. Go to the target GitHub account
2. Create a new repository (e.g., `xavier-backend`)
3. Initialize with README if desired

### 2. Clone and Setup Local Repository

```bash
# Clone the new repository
git clone https://github.com/[ACCOUNT]/[REPO-NAME].git
cd [REPO-NAME]

# Copy backend files from your current project
# (Adjust the source path as needed)
cp -r /path/to/xavierAI/back/xavier_back ./
cp /path/to/xavierAI/back/requirements.txt ./
cp /path/to/xavierAI/back/Procfile ./
cp /path/to/xavierAI/back/run_app.py ./
cp /path/to/xavierAI/back/run_app_fast.py ./
cp /path/to/xavierAI/back/setup.py ./
cp /path/to/xavierAI/back/.gitignore ./
```

### 3. Update Configuration for New Environment

Create a new environment configuration file:

```bash
# Create .env file for production
touch .env
```

Add these environment variables to `.env`:
```
FLASK_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
REDIS_URL=your-redis-url
OPENAI_API_KEY=your-openai-key
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-key
# Add other required environment variables
```

### 4. Platform-Specific Deployment

#### For Railway Deployment:
1. Connect your GitHub account to Railway
2. Select the new repository
3. Railway will automatically detect the Python project
4. Set environment variables in Railway dashboard
5. Deploy

#### For Heroku Deployment:
```bash
# Install Heroku CLI and login
heroku login

# Create Heroku app
heroku create your-app-name

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
# Add other environment variables...

# Deploy
git add .
git commit -m "Initial deployment"
git push heroku main
```

#### For Render Deployment:
1. Connect GitHub account to Render
2. Select the repository
3. Choose "Web Service"
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn --bind 0.0.0.0:$PORT xavier_back.app:create_app()`
6. Add environment variables
7. Deploy

### 5. Database Setup

After deployment, you'll need to initialize the database:

```bash
# For Heroku
heroku run python -c "from xavier_back.app import create_app; from xavier_back.models import db; app = create_app(); app.app_context().push(); db.create_all()"

# For Railway/Render (use their console or one-off commands)
python -c "from xavier_back.app import create_app; from xavier_back.models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

## Environment Variables Required

Make sure to set these environment variables in your deployment platform:

```
# Core Application
FLASK_ENV=production
SECRET_KEY=your-secret-key
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
```

## Security Considerations

1. **Never commit sensitive data**: Ensure `.env` files are in `.gitignore`
2. **Use different secrets**: Generate new SECRET_KEY for each deployment
3. **Database isolation**: Use separate databases for each deployment
4. **Environment separation**: Keep development and production configurations separate

## Testing the Deployment

After deployment, test these endpoints:

```bash
# Health check
curl https://your-app.com/health

# API endpoints
curl https://your-app.com/api/chatbots
```

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Database Connection**: Verify DATABASE_URL format
3. **Environment Variables**: Check all required variables are set
4. **Port Issues**: Ensure the app binds to `0.0.0.0:$PORT`

### Logs:
```bash
# Heroku
heroku logs --tail

# Railway
railway logs

# Render
Check logs in Render dashboard
``` 