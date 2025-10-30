from __future__ import annotations
from typing import List
from fastapi import HTTPException
from ..models import UploadBacklogIn, SelectStoryIn, Story
from ..storage import get_session, save_session

def upload_backlog(session_id: str, payload: UploadBacklogIn):
    sess = get_session(session_id)
    if not sess: 
        raise HTTPException(status_code=404, detail="Session introuvable")
    if sess.is_closed:
        raise HTTPException(status_code=400, detail="Session fermée")

    # Remplace le backlog courant par celui fourni
    sess.backlog.project = payload.project or "Planning Poker"
    sess.backlog.version = payload.version
    sess.backlog.stories = payload.stories
    sess.backlog.currentIndex = 0
    save_session(sess)
    return sess.backlog

def select_current_story(session_id: str, payload: SelectStoryIn):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session introuvable")
    if sess.is_closed:
        raise HTTPException(status_code=400, detail="Session fermée")

    # vérifier que le vote n'est pas en cours : on verra ça à l’étape 3 (états de vote)
    # on cherche l'index
    idx = next((i for i, s in enumerate(sess.backlog.stories) if s.id == payload.storyId), -1)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Story introuvable dans le backlog")
    sess.backlog.currentIndex = idx
    # marquer la story comme in_progress
    story = sess.backlog.stories[idx]
    story.status = "in_progress"
    save_session(sess)
    return story

def get_state(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return {
        "sessionId": sess.id,
        "name": sess.name,
        "mode": sess.mode,
        "players": [p.nickname for p in sess.players],
        "is_closed": sess.is_closed,
        "backlog": {
            "currentIndex": sess.backlog.currentIndex,
            "stories": [
                {
                    "id": s.id, "title": s.title, "status": s.status, "finalEstimate": s.finalEstimate
                } for s in sess.backlog.stories
            ]
        }
    }
