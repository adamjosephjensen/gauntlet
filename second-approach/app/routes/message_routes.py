# app/routes/message_routes.py

from flask import Blueprint, request, jsonify

from .. import db
from ..services.websocket import create_and_broadcast_message
from ..models import Message, Channel

message_bp = Blueprint('message_bp', __name__)

@message_bp.route('/channels/<int:channel_id>/messages', methods=['POST'])
def create_message(channel_id):
    """
    Fallback REST endpoint for message creation when WebSocket is unavailable.
    WebSocket is the preferred method for message creation - use this only as a fallback.
    
    Expects JSON: { "user_id": 1, "content": "Hello world" }
    """
    data = request.get_json()
    
    if not data or not all(key in data for key in ['user_id', 'content']):
        return jsonify({"error": "Missing required fields"}), 400
        
    if not data.get("content").strip():
        return jsonify({"error": "Message content cannot be empty"}), 400

    msg, error = create_and_broadcast_message(
        data.get('user_id'),
        channel_id,
        data.get('content')
    )
    
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify({
        "message": "Message created", 
        "message_id": msg.id
    }), 201


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

