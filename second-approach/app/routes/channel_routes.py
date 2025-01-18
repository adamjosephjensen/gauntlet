# app/routes/channel_routes.py

from flask import Blueprint, request, jsonify, current_app
import logging
from flask_login import current_user, login_required
from datetime import datetime
from sqlalchemy import or_

from .. import db
from ..models import Channel, User, ChannelMembership

# Constants
ECHO_BOT_EMAIL = "echo.bot@gauntletai.com"

channel_bp = Blueprint('channel_bp', __name__)

@channel_bp.route('/channels', methods=['POST'])
@login_required
def create_channel():
    """
    Create a new channel. Expects JSON with:
    - Regular channel: { "name": "someName" }
    - DM: { "is_dm": true, "participant_id": 123 }
    """
    data = request.get_json()
    current_app.logger.debug(f"Received channel creation request with data: {data}")
    
    # For DMs, we need a participant ID
    is_dm = data.get('is_dm', False)
    if is_dm:
        if not data.get('participant_id'):
            return jsonify({'error': 'participant_id is required for DMs'}), 400
            
        # Find the participant user
        participant = User.query.get(data['participant_id'])
        if not participant:
            return jsonify({'error': 'Participant user not found'}), 404
            
        # For DMs, name is optional - we'll generate one if not provided
        if not data.get('name'):
            data['name'] = f"DM: {current_user.email} & {participant.email}"
    else:
        # Validate required fields for regular channels
        if not data or 'name' not in data:
            current_app.logger.error(f"Missing required fields. Received: {data}")
            return jsonify({'error': 'name is required for channels'}), 400

    try:
        new_channel = Channel(
            name=data.get('name'),
            creator_id=current_user.id,
            is_dm=is_dm
        )
        db.session.add(new_channel)
        db.session.flush()  # Get channel ID without committing
        
        # Add creator to channel membership
        creator_membership = ChannelMembership(
            user_id=current_user.id,
            channel_id=new_channel.id
        )
        db.session.add(creator_membership)
        
        # For DMs, add the participant
        if is_dm and participant:
            participant_membership = ChannelMembership(
                user_id=participant.id,
                channel_id=new_channel.id
            )
            db.session.add(participant_membership)
        
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
    Return a list of all channels and DMs the current user is a member of.
    Includes IDs of recently deleted channels.
    """
    # Get timestamp filter from query params for polling
    after_timestamp = request.args.get('after')
    
    # Get channels where user is a member
    base_query = Channel.query.join(ChannelMembership).filter(
        ChannelMembership.user_id == current_user.id,
        Channel.deleted_at.is_(None)
    )
    
    if after_timestamp:
        try:
            after_dt = datetime.fromisoformat(after_timestamp)
            base_query = base_query.filter(Channel.created_at > after_dt)
        except ValueError:
            return jsonify({"error": "Invalid timestamp format"}), 400
    
    # Get active channels
    channels = base_query.all()
    results = []
    for ch in channels:
        # For DMs, get the other participants
        participants = []
        if ch.is_dm:
            memberships = ChannelMembership.query.filter_by(channel_id=ch.id).all()
            for membership in memberships:
                user = User.query.get(membership.user_id)
                if user and user.id != current_user.id:
                    participants.append({
                        "id": user.id,
                        "email": user.email
                    })
        
        results.append({
            "id": ch.id,
            "name": ch.name,
            "creator_id": ch.creator_id,
            "is_dm": ch.is_dm,
            "created_at": ch.created_at.isoformat(),
            "participants": participants if ch.is_dm else []
        })

    # Get IDs of channels deleted since last poll
    deleted_channels_query = Channel.query.join(ChannelMembership).filter(
        ChannelMembership.user_id == current_user.id,
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
    Delete a channel by ID. For DMs, either participant can delete.
    """
    channel = Channel.query.get_or_404(channel_id)
    
    # Check if user is a member of the channel
    membership = ChannelMembership.query.filter_by(
        channel_id=channel.id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        return jsonify({"error": "Not authorized to access this channel"}), 403
        
    # For regular channels, only creator can delete
    if not channel.is_dm and channel.creator_id != current_user.id:
        return jsonify({"error": "Not authorized to delete this channel"}), 403

    # Soft delete the channel
    channel.deleted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": f"Channel {channel_id} deleted.",
        "deleted_channel_id": channel_id
    }), 200

@channel_bp.route('/users', methods=['GET'])
@login_required
def list_available_users():
    """
    List all users available for DMs, including the current user for self-DMs.
    Optional query param 'search' to filter by email.
    """
    search = request.args.get('search', '').lower()
    
    query = User.query
    if search:
        query = query.filter(User.email.ilike(f'%{search}%'))
    
    users = query.order_by(User.email).all()
    
    return jsonify({
        "users": [{
            "id": user.id,
            "email": user.email,
            "is_bot": user.email == ECHO_BOT_EMAIL
        } for user in users]
    }), 200
