# app/routes/message_routes.py

from flask import Blueprint, request, jsonify
from ..models import db, Message, Channel

message_bp = Blueprint('message_bp', __name__)

@message_bp.route('/channels/<int:channel_id>/messages', methods=['POST'])
def create_message(channel_id):
    """
    Post a message in the given channel.
    Expects JSON: { "user_id": 1, "content": "Hello world" }
    """
    channel = Channel.query.get_or_404(channel_id)
    data = request.get_json()

    new_message = Message(
        channel_id=channel.id,
        user_id=data.get('user_id'),
        content=data.get('content')
    )
    db.session.add(new_message)
    db.session.commit()

    return jsonify({"message": "Message created", "message_id": new_message.id}), 201


@message_bp.route('/channels/<int:channel_id>/messages', methods=['GET'])
def list_messages(channel_id):
    """
    List all messages for a given channel, in chronological order by default.
    """
    channel = Channel.query.get_or_404(channel_id)
    messages = Message.query.filter_by(channel_id=channel.id).order_by(Message.created_at.asc()).all()

    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "user_id": msg.user_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        })
    return jsonify(result), 200


@message_bp.route('/channels/<int:channel_id>/messages/<int:message_id>', methods=['DELETE'])
def delete_message(channel_id, message_id):
    """
    Delete a message by ID within a specific channel.
    """
    channel = Channel.query.get_or_404(channel_id)
    message = Message.query.filter_by(id=message_id, channel_id=channel.id).first_or_404()

    db.session.delete(message)
    db.session.commit()
    return jsonify({"message": f"Message {message_id} deleted."}), 200

