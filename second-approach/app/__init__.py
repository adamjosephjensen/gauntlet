# __init__.py

from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager, current_user
from flask_mail import Mail
from dotenv import load_dotenv

import os

# Load environment variables from .env.prod in production
if os.environ.get('FLASK_ENV') == 'production':
    load_dotenv('.env.prod')
else:
    load_dotenv()  # Load from .env in development

# 1. Create extensions first. NEVER import routes outside of create_app.
# otherwise you'll get circular imports.
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
socketio = SocketIO(
    cors_allowed_origins="*",  # For development. Be more specific in production
    async_mode='eventlet',     # Use eventlet as async mode
    logger=True,              # Enable logging for debugging
    engineio_logger=True,      # Enable Engine.IO logging
    manage_session=True,       # Let Flask-SocketIO handle the session
    cookie={'name': 'io', 'path': '/'}  # Proper cookie configuration
)

def create_app():
    """
    Create and configure the Flask app. Import routes inside this function to avoid circular imports.
    """
    app = Flask(__name__)

    # Basic config
    # Fallback to an in-memory SQLite db if no DATABASE_URL is set
    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")  # Change in production!
    app.config["AUTH_REQUIRED"] = os.environ.get("AUTH_REQUIRED", "true").lower() == "true"

    # Mail configuration with proper defaults
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or 587)  # Default to 587 if not set or empty
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    # 2. Initialize extensions
    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = "auth_bp.login"
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    # 3. Import websocket handlers AFTER socketio is initialized
    # IMPORTANT PYTHON/FLASK GOTCHA:
    # a. Decorators execute when modules are imported
    # b. @socketio.on() decorators need initialized socketio
    # c. Therefore: import modules with socket handlers AFTER socketio.init_app()
    # d. Yes, this is a "side effect import" - you import but never use the module directly!
    from .services import websocket  # Magic import that registers @socketio.on handlers

    # 4. Import routes INSIDE create_app to avoid circular imports.
    from .routes.channel_routes import channel_bp
    from .routes.message_routes import message_bp
    from .routes.auth_routes import auth_bp
    
    # 5. Register blueprints
    app.register_blueprint(channel_bp, url_prefix='/api')
    app.register_blueprint(message_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # 6. Define routes
    @app.route('/')
    def index():
        if app.config['AUTH_REQUIRED'] and not current_user.is_authenticated:
            return render_template('login.html')
        return render_template('index.html')

    @app.route('/login')
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('login.html')

    return app

