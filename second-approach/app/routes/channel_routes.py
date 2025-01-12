# app/routes/channel_routes.py

from flask import Blueprint, request, jsonify
from ..models import db, Channel, User

channel_bp = Blueprint('channel_bp', __name__)

@channel_bp.route('/channels', methods=['POST'])
def create_channel():
    """
    Create a new channel. Expects JSON with { "name": "someName", "creator_id": 1, "is_dm": false }
    """
    data = request.get_json()
    creator = User.query.get(data.get('creator_id'))
    if not creator:
        return jsonify({'error': 'Creator not found'}), 400

    new_channel = Channel(
        name=data.get('name'),
        creator_id=data.get('creator_id'),
        is_dm=data.get('is_dm', False)
    )
    db.session.add(new_channel)
    db.session.commit()
    return jsonify({"message": "Channel created", "channel_id": new_channel.id}), 201

@channel_bp.route('/channels', methods=['GET'])
def list_channels():
    """
    Return a list of all channels.
    """
    channels = Channel.query.all()
    results = []
    for ch in channels:
        results.append({
            "id": ch.id,
            "name": ch.name,
            "creator_id": ch.creator_id,
            "is_dm": ch.is_dm
        })
    return jsonify(results), 200

@channel_bp.route('/channels/<int:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """
    Delete a channel by ID.
    """
    channel = Channel.query.get_or_404(channel_id)
    db.session.delete(channel)
    db.session.commit()
    return jsonify({"message": f"Channel {channel_id} deleted."}), 200

# Optionally add an update channel endpoint (PUT/PATCH)
@channel_bp.route('/channels/<int:channel_id>', methods=['PATCH'])
def update_channel(channel_id):
    """
    Update channel name or is_dm if needed.
    """
    channel = Channel.query.get_or_404(channel_id)
    data = request.get_json()
    if 'name' in data:
        channel.name = data['name']
    if 'is_dm' in data:
        channel.is_dm = data['is_dm']
    db.session.commit()
    return jsonify({"message": f"Channel {channel_id} updated."}), 200

