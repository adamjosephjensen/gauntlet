# services/websocket.py

from flask import request, session
from flask_socketio import join_room, emit, disconnect
from flask_login import current_user
from datetime import datetime, timedelta
import threading
import time

from .. import db, socketio

from ..models import Channel, ChannelMembership, Message, User

# Session storage
active_sessions = {}
SESSION_TIMEOUT = timedelta(minutes=30)  # Timeout inactive sessions after 30 minutes

def cleanup_old_sessions():
    """Remove expired sessions"""
    while True:
        current_time = datetime.now()
        # Create a list of sessions to remove to avoid modifying dict during iteration
        to_remove = []
        
        for sid, session_data in active_sessions.items():
            if current_time - session_data['last_active'] > SESSION_TIMEOUT:
                to_remove.append(sid)
                print(f"[SERVER] Cleaning up inactive session: {sid}")
        
        # Remove expired sessions
        for sid in to_remove:
            del active_sessions[sid]
            
        time.sleep(60)  # Run cleanup every minute

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_sessions, daemon=True)
cleanup_thread.start()

def update_session_activity(sid):
    """Update last activity time for a session"""
    if sid in active_sessions:
        active_sessions[sid]['last_active'] = datetime.now()

def create_and_broadcast_message(channel_id, user_id, content):
    """Centralized function for message creation and broadcasting"""
    try:
        # Create message
        message = Message(
            channel_id=channel_id,
            user_id=user_id,
            content=content
        )
        db.session.add(message)
        db.session.commit()

        # Get user info for the response
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Broadcast to the channel room
        response_data = {
            "id": message.id,
            "channel_id": channel_id,
            "user_id": user_id,
            "user_email": user.email,
            "content": content,
            "created_at": message.created_at.isoformat()
        }
        
        emit("new_message", response_data, to=str(channel_id))
        print(f"[SERVER] Message broadcast to channel {channel_id}: {message.id}")
        
        return message
    except Exception as e:
        print(f"[SERVER] Error in create_and_broadcast_message: {str(e)}")
        db.session.rollback()
        raise

def create_and_broadcast_channel(name, creator_id, is_dm=False):
    """Centralized function for channel creation and broadcasting"""
    try:
        # Create channel in DB
        new_channel = Channel(
            name=name,
            creator_id=creator_id,
            is_dm=is_dm
        )
        db.session.add(new_channel)
        db.session.commit()

        # Prepare channel data
        channel_data = {
            "id": new_channel.id,
            "name": name,
            "creator_id": creator_id,
            "is_dm": is_dm,
            "created_at": new_channel.created_at.isoformat()
        }
        
        # Broadcast to all connected clients
        socketio.emit('new_channel', channel_data)
        
        return new_channel, None
    except Exception as e:
        print(f"[SERVER] Error in create_and_broadcast_channel: {str(e)}")
        return None, str(e)

@socketio.on('connect')
def handle_connect():
    print(f"[SERVER] Client attempting connection: {request.sid}")
    if not current_user.is_authenticated:
        print(f"[SERVER] Rejecting unauthenticated connection: {request.sid}")
        return False
    
    # Store session info
    active_sessions[request.sid] = {
        'user_id': current_user.id,
        'email': current_user.email,
        'created_at': datetime.now(),
        'last_active': datetime.now()
    }
    
    print(f"[SERVER] Authenticated client connected: {request.sid} (User: {current_user.email})")
    return True

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_sessions:
        session_data = active_sessions[request.sid]
        print(f"[SERVER] User {session_data['email']} disconnected: {request.sid}")
        del active_sessions[request.sid]
    else:
        print(f"[SERVER] Unknown client disconnected: {request.sid}")

@socketio.on('join_channel')
def handle_join_channel(data):
    if not verify_socket_session():
        return
        
    channel_id = data.get('channel_id')
    if not channel_id:
        return
        
    # Verify channel membership
    if not verify_channel_membership(current_user.id, channel_id):
        emit('error', {'message': 'Not a member of this channel'})
        return
        
    join_room(str(channel_id))
    emit('joined_channel_ok', {'channel_id': channel_id})

@socketio.on('send_message')
def handle_send_message(data):
    if not verify_socket_session():
        return

    print(f"[SERVER] Message from {current_user.email} - {data}")
    channel_id = data.get("channel_id")
    content = data.get("content")

    if not channel_id or not content:
        emit("error", {"message": "Missing required fields"})
        print(f"Message Error: Missing required fields")
        return

    if not content.strip():
        emit("error", {"message": "Message content cannot be empty"})
        print(f"Message Error: Empty content")
        return

    # Check if channel exists
    channel = Channel.query.get(channel_id)
    if not channel:
        emit("error", {"message": f"Channel {channel_id} not found."})
        print(f"Message Error: Channel {channel_id} not found.")
        return

    try:
        # Create and broadcast the message
        message = create_and_broadcast_message(
            channel_id=channel_id,
            user_id=current_user.id,
            content=content
        )
        print(f"[SERVER] Message broadcast successful: {message.id}")
    except Exception as e:
        print(f"[SERVER] Error broadcasting message: {str(e)}")
        emit("error", {"message": "Failed to send message"})

@socketio.on('user_logout')
def handle_logout():
    """Handle user logout broadcast"""
    print(f"[SERVER] Broadcasting logout for user {current_user.id if current_user.is_authenticated else 'anonymous'}")
    # Broadcast to all clients except sender
    emit('logout_broadcast', broadcast=True, include_self=False)

def verify_socket_session():
    """Verify socket session is valid and active"""
    if request.sid not in active_sessions:
        print(f"[SERVER] Invalid session: {request.sid}")
        disconnect()
        return False
        
    # Update last activity time
    update_session_activity(request.sid)
    return True