# __init__.py

from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create extensions first. NEVER import routes outside of create_app.
# otherwise you'll get circular imports.
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

ECHO_BOT_EMAIL = "bot@gauntletai.com"

def ensure_bot_exists():
    """Ensure the echo bot user exists"""
    from .models import User
    
    bot = User.query.filter_by(email=ECHO_BOT_EMAIL).first()
    if not bot:
        bot = User(email=ECHO_BOT_EMAIL)
        db.session.add(bot)
        db.session.commit()
    return bot

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

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = "auth_bp.login"
    login_manager.login_message = "Please log in to access this page."

    # Import models to ensure they are registered with SQLAlchemy
    from .models import User, Channel, Message, MagicLink, ChannelMembership

    # Initialize database tables
    with app.app_context():
        try:
            app.logger.info("Creating database tables...")
            db.create_all()
            app.logger.info("Database tables created successfully")
            # Ensure bot exists
            ensure_bot_exists()
        except Exception as e:
            app.logger.error(f"Error during database initialization: {e}")
            db.session.rollback()
            raise

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    # Import routes INSIDE create_app to avoid circular imports.
    from .routes.channel_routes import channel_bp
    from .routes.message_routes import message_bp
    from .routes.auth_routes import auth_bp
    
    # Register blueprints
    app.register_blueprint(channel_bp, url_prefix='/api')
    app.register_blueprint(message_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # Define routes
    @app.route('/')
    def index():
        if app.config['AUTH_REQUIRED'] and not current_user.is_authenticated:
            return redirect(url_for('auth_bp.login'))
        return render_template('index.html')

    return app

