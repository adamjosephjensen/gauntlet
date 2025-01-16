# app/main.py
# Entry point for local development

from app import create_app
import logging

# Create the app
app = create_app()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

