# tests/test_channels.py

import pytest
from app import create_app, db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_create_channel(client):
    resp = client.post('/api/channels', json={
        "name": "test-channel",
        "creator_id": 1,
        "is_dm": False
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["channel_id"] is not None

def test_list_channels(client):
    # create one channel
    client.post('/api/channels', json={
        "name": "test-channel",
        "creator_id": 1,
        "is_dm": False
    })
    # list
    resp = client.get('/api/channels')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "test-channel"

