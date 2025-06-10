import firebase_admin
from firebase_admin import credentials, auth
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug: Print environment variables (without sensitive data)
# print("Firebase config check:")
# print(f"FIREBASE_PRIVATE_KEY_ID exists: {bool(os.getenv('FIREBASE_PRIVATE_KEY_ID'))}")
# print(f"FIREBASE_PRIVATE_KEY exists: {bool(os.getenv('FIREBASE_PRIVATE_KEY'))}")
# print(f"FIREBASE_CLIENT_EMAIL exists: {bool(os.getenv('FIREBASE_CLIENT_EMAIL'))}")
# print(f"FIREBASE_CLIENT_ID exists: {bool(os.getenv('FIREBASE_CLIENT_ID'))}")
# print(f"FIREBASE_CLIENT_CERT_URL exists: {bool(os.getenv('FIREBASE_CLIENT_CERT_URL'))}")

# Get Firebase service account credentials from environment variables
SERVICE_ACCOUNT_KEY = {
    "type": "service_account",
    "project_id": "xavierai-754e3",
    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL'),
    "universe_domain": "googleapis.com"
}

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if already initialized
        firebase_admin.get_app()
        print("Firebase already initialized")
    except ValueError:
        # Validate required fields
        required_fields = ['private_key_id', 'private_key', 'client_email', 'client_id']
        missing_fields = [field for field in required_fields if not SERVICE_ACCOUNT_KEY.get(field)]

        if missing_fields:
            print(f"Error: Missing required Firebase credentials: {', '.join(missing_fields)}")
            raise ValueError(f"Missing required Firebase credentials: {', '.join(missing_fields)}")

        try:
            # Initialize with service account
            print("Initializing Firebase with service account credentials")
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Error initializing Firebase: {str(e)}")
            # Print service account key structure (without actual private key)
            safe_key = {k: ('***' if k in ['private_key', 'private_key_id'] else v) for k, v in SERVICE_ACCOUNT_KEY.items()}
            print(f"Service account key structure: {safe_key}")
            raise

    return firebase_admin.get_app()

def verify_firebase_token(id_token):
    """Verify Firebase ID token and return user info"""
    if not id_token:
        print("No token provided")
        return {'verified': False, 'error': "No authentication token provided"}

    try:
        # Initialize Firebase if not already initialized
        initialize_firebase()

        # Verify the ID token
        print(f"Verifying token: {id_token[:10]}...")
        decoded_token = auth.verify_id_token(id_token)

        # Get user info
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        picture = decoded_token.get('picture', '')

        # Extract additional claims if available
        claims = {k: v for k, v in decoded_token.items()
                 if k not in ['iss', 'aud', 'auth_time', 'user_id', 'sub', 'iat', 'exp', 'email', 'email_verified', 'firebase']}

        # Log successful verification
        print(f"Firebase token verified successfully for UID: {uid}, Email: {email}")

        if claims:
            print(f"Additional claims: {claims}")

        return {
            'uid': uid,
            'email': email,
            'name': name,
            'picture': picture,
            'claims': claims,
            'verified': True
        }
    except auth.InvalidIdTokenError as e:
        print(f"Invalid Firebase ID token: {str(e)}")
        return {'verified': False, 'error': f"Invalid Firebase ID token: {str(e)}"}
    except auth.ExpiredIdTokenError as e:
        print(f"Expired Firebase ID token: {str(e)}")
        return {'verified': False, 'error': "Your session has expired. Please sign in again."}
    except auth.RevokedIdTokenError as e:
        print(f"Revoked Firebase ID token: {str(e)}")
        return {'verified': False, 'error': "Your session has been revoked. Please sign in again."}
    except auth.CertificateFetchError as e:
        print(f"Certificate fetch error: {str(e)}")
        return {'verified': False, 'error': "Could not verify your authentication. Please try again later."}
    except ValueError as e:
        print(f"Value error verifying token: {str(e)}")
        return {'verified': False, 'error': f"Invalid token format: {str(e)}"}
    except Exception as e:
        print(f"Error verifying Firebase token: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'verified': False, 'error': f"Authentication error: {str(e)}"}
