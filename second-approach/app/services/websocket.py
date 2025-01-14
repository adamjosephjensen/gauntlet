# services/websocket.py

from flask import request
from flask_socketio import join_room, emit

from .. import db, socketio

from ..models import Channel, ChannelMembership, Message

def create_and_broadcast_message(user_id, channel_id, content):
    """Centralized function for message creation and broadcasting"""
    try:
        # Validate channel exists
        channel = Channel.query.get(channel_id)
        if not channel:
            return None, f"Channel {channel_id} not found."

        # Create message in DB
        new_msg = Message(
            user_id=user_id,
            channel_id=channel_id,
            content=content
        )
        db.session.add(new_msg)
        db.session.commit()

        # Prepare message data
        message_data = {
            "id": new_msg.id,
            "channel_id": channel_id,
            "user_id": user_id,
            "content": content,
            "created_at": new_msg.created_at.isoformat()
        }
        
        # Broadcast to the specific channel room
        socketio.emit('new_message', message_data, to=str(channel_id))
        
        return new_msg, None
    except Exception as e:
        print(f"[SERVER] Error in create_and_broadcast_message: {str(e)}")
        return None, str(e)

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
    print(f"[SERVER] Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"[SERVER] Client disconnected: {request.sid}")

@socketio.on('join_channel')
def handle_join_channel(data):
    print(f"[SERVER] Join channel request - {data}")
    user_id = data.get("user_id")
    channel_id = data.get("channel_id")

    # Check if channel exists
    channel = Channel.query.get(channel_id)
    if not channel:
        emit("error", {"message": f"Channel {channel_id} not found."})
        print(f"Join Channel Error: Channel {channel_id} not found.")
        return

    # Join a named room for that channel
    join_room(str(channel_id))
    print(f"[SERVER] User {user_id} joined room {channel_id}")

    # Notify room that user joined
    emit("user_joined", {"user_id": user_id}, to=str(channel_id))
    print(f"[SERVER] Notified room {channel_id} about user {user_id}")
    
    emit("joined_channel_ok", {"channel_id": channel_id})

@socketio.on('send_message')
def handle_send_message(data):
    print("========= HANDLE SEND MESSAGE CALLED =========")
    
    # Validate input
    if not all(key in data for key in ['user_id', 'channel_id', 'content']):
        print("[SERVER] Missing required fields")
        emit("error", {"message": "Missing required fields"})
        return
        
    if not data.get("content").strip():
        print("[SERVER] Empty content")
        emit("error", {"message": "Message content cannot be empty"})
        return

    msg, error = create_and_broadcast_message(
        data.get("user_id"),
        data.get("channel_id"),
        data.get("content")
    )
    
    if error:
        print(f"[SERVER] Error sending message: {error}")
        emit("error", {"message": error})
    else:
        print(f"[SERVER] Message sent successfully: {msg.id}")
        emit("message_sent", {"message_id": msg.id})