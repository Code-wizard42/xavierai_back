"""
Auth Service Module

This module contains business logic for authentication operations, separating it from the route handlers.
"""
import logging
from typing import Dict, Any, Optional, Tuple

from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError

from xavier_back.extensions import db
from xavier_back.models import User
from xavier_back.firebase_config import verify_firebase_token

logger = logging.getLogger(__name__)

class AuthService:
    """Service class for authentication-related operations"""

    @staticmethod
    def register_user(username: str, password: str, email: Optional[str] = None) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user with username and password

        Args:
            username: Username for the new user
            password: Password for the new user
            email: Optional email address

        Returns:
            Tuple containing (user, error_message)
        """
        try:
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return None, "Username already exists"

            # Check if email already exists (if provided)
            if email:
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    return None, "Email already exists"

            # Create new user
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
                auth_provider='local'
            )

            db.session.add(new_user)
            db.session.commit()

            return new_user, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error registering user: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def login_user(username: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Login a user with username and password

        Args:
            username: Username of the user
            password: Password of the user

        Returns:
            Tuple containing (user, error_message)
        """
        try:
            # Find user by username
            user = User.query.filter_by(username=username).first()

            # Check if user exists and password is correct
            if not user or not check_password_hash(user.password_hash, password):
                return None, "Invalid credentials"

            return user, None
        except SQLAlchemyError as e:
            error_msg = f"Database error logging in user: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def verify_firebase_auth(id_token: str) -> Tuple[Optional[User], Dict[str, Any], Optional[str]]:
        """
        Verify Firebase ID token and get or create user

        Args:
            id_token: Firebase ID token

        Returns:
            Tuple containing (user, user_info, error_message)
        """
        try:
            # Verify token with Firebase
            user_info = verify_firebase_token(id_token)

            if not user_info.get('verified'):
                return None, {}, "Invalid token"

            # Extract user data
            firebase_uid = user_info.get('uid')
            email = user_info.get('email')
            display_name = user_info.get('name')
            profile_picture = user_info.get('picture')

            # Check if user already exists by Firebase UID
            user = User.query.filter_by(firebase_uid=firebase_uid).first()

            if user:
                # Update user information if needed
                if email and user.email != email:
                    user.email = email

                if profile_picture and user.profile_picture != profile_picture:
                    user.profile_picture = profile_picture

                if display_name and user.username != display_name:
                    # Only update username if it's not already taken by another user
                    existing_user = User.query.filter_by(username=display_name).first()
                    if not existing_user or existing_user.id == user.id:
                        user.username = display_name

                db.session.commit()
            else:
                # Create new user
                # Generate a unique username if display_name is not provided or already taken
                username = display_name
                if not username:
                    username = f"user_{firebase_uid[:8]}"

                # Check if username already exists
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    # Append a unique suffix
                    username = f"{username}_{firebase_uid[:8]}"

                # Create user
                user = User(
                    username=username,
                    email=email,
                    firebase_uid=firebase_uid,
                    profile_picture=profile_picture,
                    auth_provider='firebase'
                )

                db.session.add(user)
                db.session.commit()

            return user, user_info, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error verifying Firebase auth: {str(e)}"
            logger.error(error_msg)
            return None, {}, error_msg
        except Exception as e:
            error_msg = f"Error verifying Firebase auth: {str(e)}"
            logger.error(error_msg)
            return None, {}, error_msg

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """
        Get a user by ID

        Args:
            user_id: The ID of the user

        Returns:
            The user object or None if not found
        """
        try:
            return User.query.get(user_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user {user_id}: {str(e)}")
            return None

    @staticmethod
    def update_user_profile(user_id: int, data: Dict[str, Any]) -> Tuple[Optional[User], Optional[str]]:
        """
        Update a user's profile

        Args:
            user_id: The ID of the user
            data: Dictionary with profile data to update

        Returns:
            Tuple containing (user, error_message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return None, "User not found"

            # Update fields if provided
            if 'username' in data and data['username'] != user.username:
                # Check if username already exists
                existing_user = User.query.filter_by(username=data['username']).first()
                if existing_user and existing_user.id != user.id:
                    return None, "Username already exists"
                user.username = data['username']

            if 'email' in data and data['email'] != user.email:
                # Check if email already exists
                existing_user = User.query.filter_by(email=data['email']).first()
                if existing_user and existing_user.id != user.id:
                    return None, "Email already exists"
                user.email = data['email']

            if 'profile_picture' in data:
                user.profile_picture = data['profile_picture']

            db.session.commit()

            return user, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating user profile: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Change a user's password

        Args:
            user_id: The ID of the user
            current_password: Current password for verification
            new_password: New password

        Returns:
            Tuple containing (success, error_message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"

            # Verify current password
            if not check_password_hash(user.password_hash, current_password):
                return False, "Current password is incorrect"

            # Update password
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()

            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error changing password: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
