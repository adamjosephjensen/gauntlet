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
@login_required
def list_channels():
    """
    Return a list of all channels, including IDs of recently deleted channels.
    """
    # Get timestamp filter from query params for polling
    after_timestamp = request.args.get('after')
    query = Channel.query.filter(Channel.deleted_at.is_(None))
    
    if after_timestamp:
        try:
            after_dt = datetime.fromisoformat(after_timestamp)
            query = query.filter(Channel.created_at > after_dt)
        except ValueError:
            return jsonify({"error": "Invalid timestamp format"}), 400
            
    # Get active channels
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

    # Get IDs of channels deleted since last poll
    deleted_channels_query = Channel.query.filter(
        Channel.deleted_at.isnot(None)
    )
    if after_timestamp:
        deleted_channels_query = deleted_channels_query.filter(
            Channel.deleted_at > after_dt
        )
    deleted_channel_ids = [ch.id for ch in deleted_channels_query.all()]
    
    return jsonify({
        "channels": results,
        "deleted_channel_ids": deleted_channel_ids
    }), 200

@channel_bp.route('/channels/<int:channel_id>', methods=['DELETE'])
@login_required
def delete_channel(channel_id):
    """
    Delete a channel by ID.
    """
    channel = Channel.query.get_or_404(channel_id)
    if channel.creator_id != current_user.id:
        return jsonify({"error": "Not authorized to delete this channel"}), 403

    # Soft delete the channel
    channel.deleted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": f"Channel {channel_id} deleted.",
        "deleted_channel_id": channel_id
    }), 200
