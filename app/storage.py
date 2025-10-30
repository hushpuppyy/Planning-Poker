from __future__ import annotations
from typing import Dict, Optional
from .models import Session

# “DB” en mémoire pour démarrer (on passera à un fichier/SQLite + sauvegarde JSON plus tard)
_SESSIONS: Dict[str, Session] = {}

def save_session(sess: Session) -> None:
    _SESSIONS[sess.id] = sess

def get_session(session_id: str) -> Optional[Session]:
    return _SESSIONS.get(session_id)

def all_sessions() -> Dict[str, Session]:
    return _SESSIONS

def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
