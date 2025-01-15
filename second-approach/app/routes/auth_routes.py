import os
from datetime import datetime, timedelta
import secrets
import logging
from flask import Blueprint, request, jsonify, current_app, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from sqlalchemy import or_

from .. import db, mail
from ..models import User, MagicLink

auth_bp = Blueprint('auth_bp', __name__)
logger = logging.getLogger(__name__)

def is_valid_email(email):
    """Check if email ends with @gauntletai.com or @bloomtech.com"""
    return email.endswith(('@gauntletai.com', '@bloomtech.com'))

def create_magic_link(user):
    """Create a new magic link for the user"""
    token = secrets.token_urlsafe(32)
    magic_link = MagicLink(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.session.add(magic_link)
    db.session.commit()
    return token

def send_magic_link_email(user_email, verify_url):
    """Send magic link email with proper logging"""
    try:
        logger.info(f"Attempting to send magic link email to {user_email}")
        
        msg = Message(
            "Your Chat Genius Login Link",
            recipients=[user_email]
        )
        msg.body = f"""
        Hello!

        Click the following link to log in to Chat Genius:
        {verify_url}

        This link will expire in 15 minutes.

        If you didn't request this link, you can safely ignore this email.
        """
        
        mail.send(msg)
        logger.info(f"Successfully sent magic link email to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send magic link email to {user_email}: {str(e)}")
        return False

@auth_bp.route('/magic-link', methods=['POST'])
def request_magic_link():
    """Request a magic link for authentication"""
    if not current_app.config['AUTH_REQUIRED']:
        # In development mode, auto-login as user 1
        user = User.query.get(1)
        if user:
            login_user(user)
            return jsonify({"message": "Development mode: Automatically logged in"}), 200
        return jsonify({"error": "Development user not found"}), 500

    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"error": "Email is required"}), 400

    email = data['email'].lower()
    if not is_valid_email(email):
        return jsonify({
            "error": "Invalid email domain. Must be @gauntletai.com or @bloomtech.com"
        }), 400

    # Get or create user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()

    # Create magic link
    token = create_magic_link(user)
    verify_url = url_for('auth_bp.verify_token', token=token, _external=True)

    # For development, return the URL directly
    if current_app.debug:
        logger.debug(f"Debug mode: Magic link URL for {email}: {verify_url}")
        return jsonify({
            "message": "Magic link created",
            "debug_verify_url": verify_url
        }), 200

    # Send email in production
    if send_magic_link_email(email, verify_url):
        return jsonify({"message": "Magic link sent to your email"}), 200
    else:
        return jsonify({"error": "Failed to send magic link email"}), 500

@auth_bp.route('/verify/<token>')
def verify_token(token):
    """Verify a magic link token and log the user in"""
    if not current_app.config['AUTH_REQUIRED']:
        user = User.query.get(1)
        if user:
            login_user(user)
            return redirect(url_for('index'))
        return jsonify({"error": "Development user not found"}), 500

    magic_link = MagicLink.query.filter_by(
        token=token,
        used_at=None
    ).first()

    if not magic_link:
        return jsonify({"error": "Invalid or expired token"}), 400

    if magic_link.expires_at < datetime.utcnow():
        return jsonify({"error": "Token has expired"}), 400

    # Mark token as used
    magic_link.used_at = datetime.utcnow()
    db.session.commit()

    # Log the user in
    login_user(magic_link.user)
    return redirect(url_for('index'))

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log the user out"""
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route('/me')
def get_current_user():
    """Get the current user's information"""
    if not current_app.config['AUTH_REQUIRED']:
        user = User.query.get(1)
        if not user:
            return jsonify({"error": "Development user not found"}), 500
        return jsonify({
            "id": user.id,
            "email": user.email,
            "is_authenticated": True
        }), 200

    if not current_user.is_authenticated:
        return jsonify({
            "is_authenticated": False
        }), 200

    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "is_authenticated": True
    }), 200 