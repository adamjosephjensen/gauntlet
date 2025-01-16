# app/routes/message_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from .. import db
from ..models import Message, Channel, User
from datetime import datetime

message_bp = Blueprint('message_bp', __name__)

@message_bp.route('/channels/<int:channel_id>/messages', methods=['POST'])
@login_required
def create_message(channel_id):
    """Create a new message"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({"error": "Missing content field"}), 400
        
    if not data.get("content").strip():
        return jsonify({"error": "Message content cannot be empty"}), 400

    try:
        # Create message
        message = Message(
            channel_id=channel_id,
            user_id=current_user.id,
            content=data['content']
        )
        db.session.add(message)
        db.session.commit()

        # Format response
        response_data = {
            "id": message.id,
            "channel_id": channel_id,
            "user_id": current_user.id,
            "user_email": current_user.email,
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
@login_required
def list_messages(channel_id):
    """
    List all messages for a given channel, with optional timestamp filter for polling.
    Also returns IDs of messages that were deleted since the last poll.
    """
    channel = Channel.query.get_or_404(channel_id)
    
    # Get timestamp filter from query params for polling
    after_timestamp = request.args.get('after')
    query = Message.query.filter_by(channel_id=channel.id)
    
    # Get new messages (not deleted)
    if after_timestamp:
        try:
            after_dt = datetime.fromisoformat(after_timestamp)
            query = query.filter(
                Message.created_at > after_dt,
                Message.deleted_at.is_(None)
            )
        except ValueError:
            return jsonify({"error": "Invalid timestamp format"}), 400
    else:
        query = query.filter(Message.deleted_at.is_(None))
    
    messages = query.order_by(Message.created_at.asc()).all()

    # Get IDs of messages deleted since last poll
    deleted_messages_query = Message.query.filter(
        Message.channel_id == channel.id,
        Message.deleted_at.isnot(None)
    )
    if after_timestamp:
        deleted_messages_query = deleted_messages_query.filter(
            Message.deleted_at > after_dt
        )
    deleted_message_ids = [msg.id for msg in deleted_messages_query.all()]

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
    
    return jsonify({
        "messages": result,
        "deleted_message_ids": deleted_message_ids
    }), 200

@message_bp.route('/channels/<int:channel_id>/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(channel_id, message_id):
    """Delete a message by ID within a specific channel."""
    channel = Channel.query.get_or_404(channel_id)
    message = Message.query.filter_by(id=message_id, channel_id=channel.id).first_or_404()
    
    # Check if current user is the message author
    if message.user_id != current_user.id:
        return jsonify({"error": "Not authorized to delete this message"}), 403

    # Soft delete the message
    message.deleted_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "message": f"Message {message_id} deleted.",
        "deleted_message_id": message_id
    }), 200

