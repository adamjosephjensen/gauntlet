# app/main.py
# Entry point for local development

from . import create_app, db
from .models import User

app = create_app()

if __name__ == "__main__":
    # Create tables if running with in-memory or fresh database
    with app.app_context():
        db.create_all()

        # Seed user
        if not User.query.filter_by(email="adam.jensen@gauntletai.com").first():
            test_user = User(email="adam.jensen@gauntletai.com")
            db.session.add(test_user)
            db.session.commit()

    app.run(debug=True, host="0.0.0.0")

