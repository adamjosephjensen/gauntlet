# app/main.py
# Entry point for local development

from app import create_app
import logging
import os

# Create the app
app = create_app()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure server name for production
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', '18.224.56.202.nip.io')

