import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load .env in local dev (docker-compose will also pass these in)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallbacksecret")

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/slackdb")
print("my SQLALCHEMY_DATABASE_URI", app.config['SQLALCHEMY_DATABASE_URI'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Flask-Mail TODO put real values
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", "127.0.0.1")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 1025))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "False") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER", None)

db = SQLAlchemy(app)
mail = Mail(app)

# ------------------
# Database Models
# ------------------

class User(db.Model):
    __tablename__ = 'users'

    email = db.Column(db.String(255), primary_key=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.email}>"

class AuthToken(db.Model):
    __tablename__ = 'auth_tokens'

    token = db.Column(db.String(64), primary_key=True, nullable=False)
    user_email = db.Column(db.String(255), db.ForeignKey('users.email'), nullable=False)
    user = db.relationship('User', backref='tokens')
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<AuthToken {self.token[:8]}... for User {self.user_email}>"

class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by_email = db.Column(db.String(255), db.ForeignKey('users.email'), nullable=False)
    
    # Relationships
    created_by = db.relationship('User', backref='created_channels')
    members = db.relationship('User', secondary='channel_members', backref='channels')

class ChannelMember(db.Model):
    __tablename__ = 'channel_members'

    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), primary_key=True)
    user_email = db.Column(db.String(255), db.ForeignKey('users.email'), primary_key=True)
    joined_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ChannelMessage(db.Model):
    __tablename__ = 'channel_messages'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sender_email = db.Column(db.String(255), db.ForeignKey('users.email'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    
    # Relationships
    sender = db.relationship('User', backref='channel_messages')
    channel = db.relationship('Channel', backref='messages')

class DirectMessage(db.Model):
    __tablename__ = 'direct_messages'

    id = db.Column(db.Integer, primary_key=True)
    user1_email = db.Column(db.String(255), db.ForeignKey('users.email'), nullable=False)
    user2_email = db.Column(db.String(255), db.ForeignKey('users.email'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_email], backref='dms_initiated')
    user2 = db.relationship('User', foreign_keys=[user2_email], backref='dms_received')

class DirectMessageContent(db.Model):
    __tablename__ = 'direct_message_contents'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sender_email = db.Column(db.String(255), db.ForeignKey('users.email'), nullable=False)
    dm_id = db.Column(db.Integer, db.ForeignKey('direct_messages.id'), nullable=False)
    
    # Relationships
    sender = db.relationship('User', backref='direct_messages')
    direct_message = db.relationship('DirectMessage', backref='messages')

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
    
    # Explicitly create timezone-aware datetime
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    # Debug print
    print(f"Creating token that expires at: {expires} (tzinfo: {expires.tzinfo})")

    auth_token = AuthToken(
        token=token_value,
        user_email=user.email,
        expires_at=expires
    )
    db.session.add(auth_token)
    db.session.commit()

    # Add another debug print after commit
    print(f"Stored token expires at: {auth_token.expires_at} (tzinfo: {auth_token.expires_at.tzinfo})")

    # Construct verify link
    verify_url = url_for('verify_token', token=token_value, _external=True)

    # Send email
    if app.config['MAIL_DEFAULT_SENDER']:
        msg = Message("Your Magic Link", recipients=[email])
        msg.body = f"Hi,\n\nClick here to log in: {verify_url}\n\nThis link expires in 30 minutes."
        mail.send(msg)
        return f"Magic link sent to {email}. Please check your inbox."
    else:
        # Return HTML that will be rendered properly
        return render_template_string(
            'Email not configured. Use this link: <a href="{{ url }}">{{ url }}</a>',
            url=verify_url
        )

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

    current_time = datetime.now(timezone.utc)
    print(f"Current time: {current_time} (tzinfo: {current_time.tzinfo})")
    print(f"Token expires: {auth_token.expires_at} (tzinfo: {auth_token.expires_at.tzinfo})")
    
    if datetime.now(timezone.utc) > auth_token.expires_at:
        return "Token expired", 403

    # Mark token as used
    auth_token.used = True
    db.session.commit()

    # Log user in (simple session-based auth for demonstration)
    user = auth_token.user
    session['user_email'] = user.email

    return f"Welcome, {user.email}! You are now logged in."

# ------------------
# CLI / Entry
# ------------------

def init_db():
    with app.app_context():
        db.create_all()
        print("init_db ran and created tables")

# Call init_db() once at import time.
# This is important because gunicorn will not call `python app.py` so it won't run __main__
init_db()


if __name__ == '__main__':
    print("my __main__ ran")
    init_db()
    app.run(debug=True, host='0.0.0.0', port=4992)