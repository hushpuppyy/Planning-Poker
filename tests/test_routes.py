import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from planning_poker_app import app  

def test_home_status_code():
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200


def test_home_contains_title():
    client = app.test_client()
    resp = client.get("/")
    html = resp.data.decode("utf-8")
    assert "Planning Poker" in html

