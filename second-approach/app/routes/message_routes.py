# app/routes/message_routes.py

from flask import Blueprint, request, jsonify
from .. import db
from ..models import Message, Channel, User
from datetime import datetime

message_bp = Blueprint('message_bp', __name__)

@message_bp.route('/channels/<int:channel_id>/messages', methods=['POST'])
def create_message(channel_id):
    """Create a new message"""
    data = request.get_json()
    
    if not data or not all(key in data for key in ['user_id', 'content']):
        return jsonify({"error": "Missing required fields"}), 400
        
    if not data.get("content").strip():
        return jsonify({"error": "Message content cannot be empty"}), 400

    try:
        # Create message
        message = Message(
            channel_id=channel_id,
            user_id=data['user_id'],
            content=data['content']
        )
        db.session.add(message)
        db.session.commit()

        # Get user info
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({"error": f"User {data['user_id']} not found"}), 404

        # Format response
        response_data = {
            "id": message.id,
            "channel_id": channel_id,
            "user_id": user.id,
            "user_email": user.email,
            "content": data['content'],
            "created_at": message.created_at.isoformat()
        }
        
        return jsonify({
            "message": "Message created",
            "message_id": message.id,
            "data": response_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@message_bp.route('/channels/<int:channel_id>/messages', methods=['GET'])
def list_messages(channel_id):
    """
    List all messages for a given channel, with optional timestamp filter for polling.
    """
    channel = Channel.query.get_or_404(channel_id)
    
    # Get timestamp filter from query params for polling
    after_timestamp = request.args.get('after')
    query = Message.query.filter_by(channel_id=channel.id)
    
    if after_timestamp:
        try:
            after_dt = datetime.fromisoformat(after_timestamp)
            query = query.filter(Message.created_at > after_dt)
        except ValueError:
            return jsonify({"error": "Invalid timestamp format"}), 400
    
    messages = query.order_by(Message.created_at.asc()).all()

    result = []
    for msg in messages:
        user = User.query.get(msg.user_id)
        result.append({
            "id": msg.id,
            "user_id": msg.user_id,
            "user_email": user.email if user else None,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        })
    return jsonify(result), 200

@message_bp.route('/channels/<int:channel_id>/messages/<int:message_id>', methods=['DELETE'])
def delete_message(channel_id, message_id):
    """Delete a message by ID within a specific channel."""
    channel = Channel.query.get_or_404(channel_id)
    message = Message.query.filter_by(id=message_id, channel_id=channel.id).first_or_404()

    db.session.delete(message)
    db.session.commit()
    return jsonify({"message": f"Message {message_id} deleted."}), 200

