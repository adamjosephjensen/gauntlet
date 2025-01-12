# services/websocket.py

from flask_socketio import join_room, emit
from ..models import db, Channel, ChannelMembership, Message

def init_socket_handlers(socketio):
    """
    Attach all socket event handlers to the provided SocketIO instance.
    Call this once in your create_app or equivalent setup.
    """

    @socketio.on('join_channel')
    def handle_join_channel(data):
        """
        data example: { "user_id": 1, "channel_id": 2 }
        """
        user_id = data.get("user_id")
        channel_id = data.get("channel_id")

        # Check if channel and membership exist
        channel = Channel.query.get(channel_id)
        if not channel:
            emit("error", {"message": f"Channel {channel_id} not found."})
            return

        membership = ChannelMembership.query.filter_by(
            user_id=user_id, channel_id=channel_id
        ).first()
        if not membership:
            emit("error", {"message": "User not a member of this channel."})
            return

        # Join a named room for that channel
        join_room(str(channel_id))

        # Notify room that user joined (optional)
        emit("user_joined", {"user_id": user_id}, to=str(channel_id))
        # Could also just confirm to the sender
        emit("joined_channel_ok", {"channel_id": channel_id})

    @socketio.on('send_message')
    def handle_send_message(data):
        """
        data example: { "user_id": 1, "channel_id": 2, "content": "Hello world" }
        """
        user_id = data.get("user_id")
        channel_id = data.get("channel_id")
        content = data.get("content")

        # Check membership
        membership = ChannelMembership.query.filter_by(
            user_id=user_id, channel_id=channel_id
        ).first()
        if not membership:
            emit("error", {"message": "User not a member of this channel."})
            return

        # Create message in DB
        new_msg = Message(
            user_id=user_id,
            channel_id=channel_id,
            content=content
        )
        db.session.add(new_msg)
        db.session.commit()

        # Broadcast 'new_message' to everyone in channel's room
        emit(
            "new_message",
            {
                "message_id": new_msg.id,
                "user_id": new_msg.user_id,
                "content": new_msg.content,
                "created_at": new_msg.created_at.isoformat(),
            },
            to=str(channel_id)
        )

