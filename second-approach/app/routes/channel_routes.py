# app/routes/channel_routes.py

from flask import Blueprint, request, jsonify, current_app
import logging
from flask_login import current_user, login_required
from datetime import datetime

from .. import db
from ..models import Channel, User

channel_bp = Blueprint('channel_bp', __name__)

@channel_bp.route('/channels', methods=['POST'])
@login_required
def create_channel():
    """
    Create a new channel. Expects JSON with { "name": "someName", "is_dm": false }
    """
    data = request.get_json()
    current_app.logger.debug(f"Received channel creation request with data: {data}")
    
    # Validate required fields
    if not data or 'name' not in data:
        current_app.logger.error(f"Missing required fields. Received: {data}")
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        new_channel = Channel(
            name=data.get('name'),
            creator_id=current_user.id,
            is_dm=data.get('is_dm', False)
        )
        db.session.add(new_channel)
        db.session.commit()
        
        response_data = {
            "id": new_channel.id,
            "name": new_channel.name,
            "creator_id": new_channel.creator_id,
            "is_dm": new_channel.is_dm,
            "created_at": new_channel.created_at.isoformat()
        }
            
        return jsonify({
            "message": "Channel created", 
            "channel_id": new_channel.id,
            "data": response_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating channel: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@channel_bp.route('/channels', methods=['GET'])
def list_channels():
    """
    Return a list of all channels.
    """
    # Get timestamp filter from query params for polling
    after_timestamp = request.args.get('after')
    query = Channel.query
    
    if after_timestamp:
        try:
            after_dt = datetime.fromisoformat(after_timestamp)
            query = query.filter(Channel.created_at > after_dt)
        except ValueError:
            return jsonify({"error": "Invalid timestamp format"}), 400
            
    channels = query.all()
    results = []
    for ch in channels:
        results.append({
            "id": ch.id,
            "name": ch.name,
            "creator_id": ch.creator_id,
            "is_dm": ch.is_dm,
            "created_at": ch.created_at.isoformat()
        })
    return jsonify(results), 200

@channel_bp.route('/channels/<int:channel_id>', methods=['DELETE'])
@login_required
def delete_channel(channel_id):
    """
    Delete a channel by ID.
    """
    channel = Channel.query.get_or_404(channel_id)
    if channel.creator_id != current_user.id:
        return jsonify({"error": "Not authorized to delete this channel"}), 403
    db.session.delete(channel)
    db.session.commit()
    return jsonify({"message": f"Channel {channel_id} deleted."}), 200

@channel_bp.route('/channels/<int:channel_id>', methods=['PATCH'])
@login_required
def update_channel(channel_id):
    """
    Update channel name or is_dm if needed.
    """
    channel = Channel.query.get_or_404(channel_id)
    if channel.creator_id != current_user.id:
        return jsonify({"error": "Not authorized to update this channel"}), 403
    data = request.get_json()
    if 'name' in data:
        channel.name = data['name']
    if 'is_dm' in data:
        channel.is_dm = data['is_dm']
    db.session.commit()
    return jsonify({"message": f"Channel {channel_id} updated."}), 200

