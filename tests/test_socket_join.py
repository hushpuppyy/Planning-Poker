import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from planning_poker_app import app, socketio


def test_socket_connects():
    client = socketio.test_client(app)
    assert client.is_connected()
    client.disconnect()


def test_join_session_emits_something():
    client = socketio.test_client(app)
    assert client.is_connected()
    
    client.emit("join_session", {
        "sessionId": "1234",
        "playerName": "Alice"
    })

    received = client.get_received()
    assert len(received) > 0 

    client.disconnect()
