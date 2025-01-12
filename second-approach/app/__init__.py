# __init__.py

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os

from .models import db

from .routes.channel_routes import channel_bp
from .routes.message_routes import message_bp

from .services.websocket import init_socket_handlers

# note: we do not initialize db = SQLAlchemy here because that is done in models.py
# if you tried to do it here and import it over there then you'd get circular imports it seems
socketio = SocketIO()

def create_app():
    app = Flask(__name__)

    # Basic config
    # Fallback to an in-memory SQLite db if no DATABASE_URL is set
    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    socketio.init_app(app)

    # Register Blueprints (import routes)
    app.register_blueprint(channel_bp, url_prefix='/api')
    app.register_blueprint(message_bp, url_prefix='/api')

    # Define routes
    @app.route('/')
    def index():
        return render_template('index.html')
    

    with app.app_context():
        init_socket_handlers(socketio)
        db.create_all()

    return app

