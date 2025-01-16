# app/models.py

from datetime import datetime
from flask_login import UserMixin

from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('Message', backref='author', lazy='dynamic')
    magic_links = db.relationship('MagicLink', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.id} - {self.email}>'

    @property
    def is_active(self):
        """All users are active since we validate emails during magic link creation"""
        return True


class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    is_dm = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Channel {self.id} - {self.name} (is_dm={self.is_dm})>'


class ChannelMembership(db.Model):
    """
    Tracks which users belong to which channel.
    For DMs (is_dm=True), this table might just have 2 or 3 rows, 
    but for larger channels it may have many members.
    """
    __tablename__ = 'channel_memberships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ChannelMembership user={self.user_id}, channel={self.channel_id}>'


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Add relationship to reactions
    reactions = db.relationship('MessageReaction', backref='message', lazy='dynamic')

    def __repr__(self):
        return f'<Message {self.id} by User {self.user_id} in Channel {self.channel_id}>'


class MessageReaction(db.Model):
    __tablename__ = 'message_reactions'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(32), nullable=False)  # Store the emoji character or code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Ensure a user can't react with the same emoji twice on the same message
        db.UniqueConstraint('message_id', 'user_id', 'emoji', name='unique_user_message_emoji'),
    )

    def __repr__(self):
        return f'<MessageReaction {self.id} - {self.emoji} by User {self.user_id} on Message {self.message_id}>'


class MagicLink(db.Model):
    __tablename__ = 'magic_links'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<MagicLink {self.id} - User {self.user_id}>'

