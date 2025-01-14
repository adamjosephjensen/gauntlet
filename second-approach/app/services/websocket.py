# services/websocket.py

from flask import request
from flask_socketio import join_room, emit

from .. import db, socketio

from ..models import Channel, ChannelMembership, Message

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

    # Check if channel and membership exist
    channel = Channel.query.get(channel_id)
    if not channel:
        emit("error", {"message": f"Channel {channel_id} not found."})
        print(f"Join Channel Error 1: Channel {channel_id} not found.")
        return

    membership = ChannelMembership.query.filter_by(
        user_id=user_id, channel_id=channel_id
    ).first()
    if not membership:
        emit("error", {"message": "User not a member of this channel."})
        print(f"Error: User is not a member of channel {channel_id}.")
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
    print(f"[SERVER] Message received - {data}")
    
    try:
        # Add input validation
        if not all(key in data for key in ['user_id', 'channel_id', 'content']):
            print("[SERVER] Missing required fields")
            emit("error", {"message": "Missing required fields"})
            return
            
        if not data.get("content").strip():
            print("[SERVER] Empty content")
            emit("error", {"message": "Message content cannot be empty"})
            return

        user_id = data.get("user_id")
        channel_id = data.get("channel_id")
        content = data.get("content")

        print(f"[SERVER] Processing message: user={user_id}, channel={channel_id}, content={content}")

        # Create message in DB
        new_msg = Message(
            user_id=user_id,
            channel_id=channel_id,
            content=content
        )
        db.session.add(new_msg)
        db.session.commit()
        print(f"[SERVER] Message saved to DB: {new_msg.id}")

        # Prepare message data
        message_data = {
            "id": new_msg.id,
            "channel_id": channel_id,
            "user_id": user_id,
            "content": content,
            "created_at": new_msg.created_at.isoformat()
        }
        
        print(f"[SERVER] Emitting message: {message_data}")
        socketio.emit('new_message', message_data)
        print("========= HANDLE SEND MESSAGE COMPLETED =========")
        
        return {"status": "success"}
    except Exception as e:
        print(f"[SERVER] Error: {str(e)}")
        return {"status": "error", "message": str(e)}