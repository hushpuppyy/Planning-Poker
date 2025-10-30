from __future__ import annotations
from typing import Optional
from fastapi import HTTPException
from ..models import Session, CreateSessionIn, JoinSessionIn, Player
from ..storage import save_session, get_session

def create_session(payload: CreateSessionIn) -> Session:
    sess = Session(name=payload.name, mode=payload.mode, owner=payload.owner)
    save_session(sess)
    return sess

def join_session(session_id: str, payload: JoinSessionIn) -> Session:
    sess = get_session(session_id)
    if not sess or sess.is_closed:
        raise HTTPException(status_code=404, detail="Session introuvable ou fermée")
    # pseudo unique
    if any(p.nickname.lower() == payload.nickname.lower() for p in sess.players):
        # suffixe simple automatique
        base = payload.nickname
        i = 2
        candidate = f"{base}({i})"
        while any(p.nickname.lower() == candidate.lower() for p in sess.players):
            i += 1
            candidate = f"{base}({i})"
        nickname = candidate
    else:
        nickname = payload.nickname
    sess.players.append(Player(nickname=nickname))
    save_session(sess)
    return sess
