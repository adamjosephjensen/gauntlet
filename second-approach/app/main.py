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

# Configure server name for all environments
app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', 'localhost:5000')

