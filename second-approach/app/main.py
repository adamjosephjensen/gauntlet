# app/main.py
# Entry point for local development

from . import create_app, db

app = create_app()

if __name__ == "__main__":
    # Create tables if running with in-memory or fresh database
    with app.app_context():
        db.create_all()

    app.run(debug=True, host="0.0.0.0")

