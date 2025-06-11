# Xavier AI - AI-Powered Chatbot Platform

Xavier AI is a comprehensive chatbot platform that provides businesses with AI-powered customer support capabilities. The platform includes features for managing chatbots, analyzing customer interactions, and handling support tickets.

## Project Structure

The project is divided into two main components:

- **Backend**: Flask-based API server with MongoDB integration
- **Frontend**: Angular-based web application

### Backend Structure

```
back/xavier_back/
├── app.py                 # Main application entry point
├── config.py              # Configuration settings
├── extensions.py          # Flask extensions
├── firebase_config.py     # Firebase authentication setup
├── models/                # Database models
├── routes/                # API routes
├── services/              # Business logic services
├── utils/                 # Utility functions
├── migrations/            # Database migrations
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (not in version control)
```

### Frontend Structure

```
front/xavier_front/
├── src/
│   ├── app/               # Angular application code
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API services
│   │   ├── models/        # TypeScript interfaces
│   │   └── shared/        # Shared utilities
│   ├── assets/            # Static assets
│   └── environments/      # Environment configurations
├── angular.json           # Angular configuration
├── package.json           # NPM dependencies
└── tailwind.config.js     # Tailwind CSS configuration
```

## Setup and Installation

### Prerequisites

- Node.js (v18+)
- Python (v3.9+)
- MongoDB Atlas account (free tier)
- Firebase account (for authentication)
- Cohere API key (for embeddings)
- Resend API key (for email)

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd back/xavier_back
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```

5. Edit the `.env` file with your credentials

6. Run the development server:
   ```
   python app.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd front/xavier_front
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   ng serve
   ```

4. Access the application at `http://localhost:4200`

## Deployment

The application is configured for deployment on Render using the `render.yaml` file in the root directory.

### Deployment Steps

1. Create a Render account
2. Connect your GitHub repository
3. Use the "Blueprint" feature with the `render.yaml` file
4. Set up the required environment variables in the Render dashboard

## Environment Variables

See `.env.example` for a list of required environment variables.

## Features

- AI-powered chatbot with natural language understanding
- Knowledge base management with Text-to-JSON/JSON-to-Text conversion
- Analytics dashboard
- Ticket management system
- Email notifications
- Firebase authentication
- Responsive design

## Paystack Integration

Xavier AI now includes Paystack as a payment option. Users can pay for their subscription using the Paystack platform.

### How to use Paystack

1. Configure your Paystack account and create a product in your Paystack dashboard
2. Update the environment file (`front/xavier_front/src/environments/environment.ts`) with your Paystack shop URL:
   ```typescript
   paystackShopUrl: 'https://paystack.shop/pay/u5fps8yjkf'
   ```
3. Set the payment method in the environment file to use Paystack:
   ```typescript
   paymentMethod: 'paystack'
   ```

The Paystack integration includes:
- Frontend component for redirecting to Paystack payment page
- Backend handlers for processing Paystack payments
- Webhook support for receiving Paystack payment notifications

## License

This project is proprietary and confidential.

## Contact

For support or inquiries, please contact [your-email@example.com].
