# Xavier AI Backend Developer Guide

## Overview

The Xavier AI backend follows a modular architecture with clear separation of concerns:

1. **Routes Layer**: Handles HTTP requests and responses
2. **Services Layer**: Contains business logic
3. **Models Layer**: Defines database schema
4. **Utils Layer**: Provides utility functions

## Project Structure

```
back/xavier_back/
├── app.py                  # Application entry point
├── config.py               # Configuration settings
├── extensions.py           # Flask extensions
├── firebase_config.py      # Firebase authentication setup
├── models/                 # Database models
│   ├── __init__.py         # Imports all models
│   ├── user.py             # User model
│   ├── chatbot.py          # Chatbot model
│   └── ...                 # Other models
├── routes/                 # API routes
│   ├── __init__.py
│   ├── analytics.py        # Analytics routes
│   ├── auth.py             # Authentication routes
│   ├── chatbot.py          # Chatbot routes
│   ├── email_service.py    # Email routes
│   └── ...                 # Other routes
├── services/               # Business logic services
│   ├── __init__.py
│   ├── analytics_service.py
│   ├── auth_service.py
│   ├── chatbot_service.py
│   ├── email_service.py
│   └── ...                 # Other services
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── api_utils.py
│   ├── auth_utils.py
│   ├── file_utils.py
│   └── ...                 # Other utilities
└── requirements.txt        # Python dependencies
```

## Core Components

### Routes

Routes are responsible for handling HTTP requests and responses. They use services to perform business logic and return appropriate responses.

Example:

```python
@chatbot_bp.route('/chatbots', methods=['GET'])
@jwt_required()
def get_chatbots():
    user_id = get_jwt_identity()
    chatbots = ChatbotService.get_chatbots(user_id)
    return jsonify(chatbots), 200
```

### Services

Services contain the business logic of the application. They are independent of the web framework and can be tested in isolation.

Example:

```python
class ChatbotService:
    @staticmethod
    def get_chatbots(user_id):
        chatbots = Chatbot.query.filter_by(user_id=user_id).all()
        return [chatbot.to_dict() for chatbot in chatbots]
```

### Models

Models define the database schema using SQLAlchemy ORM.

Example:

```python
class Chatbot(db.Model):
    __tablename__ = 'chatbots'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Utils

Utils provide utility functions used throughout the application.

Example:

```python
def generate_token(user_id):
    return create_access_token(identity=user_id)
```

## Development

### Setting Up the Development Environment

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables
4. Run migrations: `flask db upgrade`
5. Run the application: `python -m xavier_back.app`

### Adding a New Feature

1. Define the database model in `models/`
2. Create or update the service in `services/`
3. Create or update the route in `routes/`
4. Update the application entry point if necessary

### Testing

Run tests with pytest: `pytest`

## Deployment

### Production Setup

1. Set environment variables
2. Configure database connection
3. Configure external services (Firebase, Stripe, etc.)
4. Deploy to production server

### Monitoring

- Use logging to track application behavior
- Set up error tracking and alerts

## Troubleshooting

### Common Issues

- Database connection issues
- API authentication problems
- File permission errors

### Debugging

- Check logs in `logs/`
- Use debugging tools in your IDE
- Enable Flask debug mode during development
