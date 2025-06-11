# Xavier AI Backend

This is the backend service for Xavier AI, built with Flask.

## Structure

```
back/
├── xavier_back/          # Main application package
│   ├── config/          # Configuration files
│   ├── models/          # Database models
│   ├── routes/          # API routes
│   ├── services/        # Business logic services
│   ├── middleware/      # Custom middleware
│   ├── utils/           # Utility functions
│   ├── static/          # Static files
│   ├── migrations/      # Database migrations
│   ├── logs/            # Application logs
│   ├── instance/        # Instance-specific files
│   ├── flask_session/   # Flask session files
│   ├── uploads/         # File uploads
│   └── vector_db/       # Vector database files
├── scripts/             # Utility and maintenance scripts
├── requirements.txt     # Python dependencies
├── setup.py            # Package setup
└── Procfile            # Deployment configuration
```

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python run_app.py
   ```

3. For fast development (with minimal components):
   ```bash
   python run_app_fast.py
   ```

## Development Scripts

Utility scripts are located in the `scripts/` directory. See `scripts/README.md` for details.

## Configuration

- Main config: `xavier_back/config.py`
- Environment variables: `.env` file
- Fast mode config: `config_fast.env`

## Notes

- The application uses Flask with SQLAlchemy for database operations
- Vector database integration with Qdrant
- Firebase integration for authentication
- PayPal, LemonSqueezy, and Flutterwave payment integrations 