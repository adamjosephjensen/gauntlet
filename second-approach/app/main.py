# app/main.py
# Entry point for local development

from app import create_app, db
from app.models import User
import logging
from sqlalchemy.exc import ProgrammingError, OperationalError

app = create_app()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database tables and create test user if needed"""
    with app.app_context():
        try:
            # Create tables first
            logger.info("Creating database tables...")
            db.create_all()
            
            # Check if our test user exists
            existing_user = User.query.get(1)
            logger.debug(f"Existing user check: {existing_user}")
            
            if not existing_user:
                test_user = User(
                    id=1,
                    email="adam.jensen@gauntletai.com"
                )
                db.session.add(test_user)
                try:
                    db.session.commit()
                    logger.info("Created test user with ID 1")
                    
                    # Verify the user was created
                    new_user = User.query.get(1)
                    logger.debug(f"Verification - Created user: {new_user}")
                except Exception as e:
                    logger.error(f"Error creating test user: {e}")
                    db.session.rollback()
            
            # Double check all users in database
            all_users = User.query.all()
            logger.debug(f"All users in database: {all_users}")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            db.session.rollback()
            raise

# Initialize database
init_db()

