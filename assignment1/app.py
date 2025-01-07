import os
import secrets
from datetime import datetime, timedelta

from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load .env in local dev (docker-compose will also pass these in)
load_dotenv()

app = Flask(__name__)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///local.db")
print("DATABASE_URL", app.config['SQLALCHEMY_DATABASE_URI'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Flask-Mail TODO put real values
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME", "")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD", "")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER", None)

db = SQLAlchemy(app)
mail = Mail(app)

# ------------------
# Database Models
# ------------------

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.email}>"

class AuthToken(db.Model):
    __tablename__ = 'auth_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='tokens')
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<AuthToken {self.token[:8]}... for User {self.user_id}>"

# ------------------
# Routes
# ------------------

@app.route('/')
def index():
    # A simple index to show a login form
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Slack Clone</title>
    </head>
    <body>
      <h2>Welcome to Slack Clone</h2>
      <form method="POST" action="/request_magic_link">
        <label for="email">Enter your email:</label>
        <input type="email" name="email" required />
        <button type="submit">Request Magic Link</button>
      </form>
    </body>
    </html>
    ''')

@app.route('/request_magic_link', methods=['POST'])
def request_magic_link():
    email = request.form.get('email')
    # Validate domain
    if not email.endswith("@gauntletai.com") and not email.endswith("@bloomtech.com"):
        return "Invalid email domain", 400

    # Check if user exists or create
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()

    # Generate token
    token_value = secrets.token_hex(32)  # 64-char hex
    expires = datetime.utcnow() + timedelta(minutes=30)

    auth_token = AuthToken(
        token=token_value,
        user_id=user.id,
        expires_at=expires
    )
    db.session.add(auth_token)
    db.session.commit()

    # Construct verify link
    verify_url = url_for('verify_token', token=token_value, _external=True)

    # Send email
    if app.config['MAIL_DEFAULT_SENDER']:
        msg = Message("Your Magic Link", recipients=[email])
        msg.body = f"Hi,\n\nClick here to log in: {verify_url}\n\nThis link expires in 30 minutes."
        mail.send(msg)
        return f"Magic link sent to {email}. Please check your inbox."
    else:
        # If email not configured, just display the link for local dev
        return f"Email not configured. Use this link: {verify_url}"

@app.route('/verify')
def verify_token():
    token_value = request.args.get('token')
    if not token_value:
        return "No token provided", 400

    auth_token = AuthToken.query.filter_by(token=token_value).first()
    if not auth_token:
        return "Invalid token", 400

    if auth_token.used:
        return "Token already used", 403

    if datetime.utcnow() > auth_token.expires_at:
        return "Token expired", 403

    # Mark token as used
    auth_token.used = True
    db.session.commit()

    # Update user last_login
    user = auth_token.user
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Log user in (simple session-based auth for demonstration)
    session['user_id'] = user.id

    return f"Welcome, {user.email}! You are now logged in."

# ------------------
# CLI / Entry
# ------------------

if __name__ == '__main__':
    # Create tables if not existing
    with app.app_context():
        db.create_all()

    # Run
    app.run(host='0.0.0.0', port=5000, debug=True)
