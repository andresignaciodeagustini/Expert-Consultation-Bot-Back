import json  # Añade esta importación al principio del archivo
import pytest
from flask import Flask

def test_name_capture_registered_user(client):
    response = client.post('/api/ai/name/capture',
        json={'text': 'John', 'is_registered': True})
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'options' in data
    assert len(data['options']) == 2  # Yes/No options

def test_name_capture_unregistered_user(client):
    response = client.post('/api/ai/name/capture',
        json={'text': 'John', 'is_registered': False})
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking_link' in data