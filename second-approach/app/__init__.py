# __init__.py

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

import os

# 1. Create extensions first. NEVER import routes outside of create_app.
# otherwise you'll get circular imports.
db = SQLAlchemy()
# Configure SocketIO with proper settings
socketio = SocketIO(
    cors_allowed_origins="*",  # For development. Be more specific in production
    async_mode='eventlet',     # Use eventlet as async mode
    logger=True,              # Enable logging for debugging
    engineio_logger=True      # Enable Engine.IO logging
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

    # 2. Initialize extensions
    db.init_app(app)
    socketio.init_app(app)

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
    
    # 5. Register blueprints
    app.register_blueprint(channel_bp, url_prefix='/api')
    app.register_blueprint(message_bp, url_prefix='/api')

    # 6. Define routes
    @app.route('/')
    def index(): # type: ignore
        return render_template('index.html')
    
    with app.app_context():
        db.create_all()

    return app

