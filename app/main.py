from fastapi import FastAPI
from .models import CreateSessionIn, JoinSessionIn, UploadBacklogIn, SelectStoryIn
from .services.session_service import create_session, join_session
from .services.story_service import upload_backlog, select_current_story, get_state

description = """
Application **Planning Poker** 🃏  
Créez une session d’estimation que des **joueurs externes** peuvent rejoindre.

Fonctionnalités :
- Créer une session (facilitateur)
- Rejoindre une session (joueurs)
- Importer un backlog
- Sélectionner la story courante
- Consulter l’état de la session
"""

app = FastAPI(
    title="Planning Poker (FR)",
    description=description,
    version="0.2.0",
)

@app.get("/", summary="Accueil", tags=["Système"])
def root():
    return {"status": "ok", "message": "Bienvenue dans l’application Planning Poker 👋"}

@app.get("/health", summary="Vérifier la santé du serveur", tags=["Système"])
def health():
    return {"healthy": True}

# --- Sessions ---
@app.post("/sessions", summary="Créer une session", tags=["Session"])
def api_create_session(payload: CreateSessionIn):
    sess = create_session(payload)
    return {"sessionId": sess.id, "nom": sess.name, "mode": sess.mode,"facilitateur": sess.owner, "joueurs": []}

@app.post("/sessions/{session_id}/join", summary="Rejoindre une session", tags=["Session"])
def api_join_session(session_id: str, payload: JoinSessionIn):
    sess = join_session(session_id, payload)
    return {"sessionId": sess.id, "joueurs": [p.nickname for p in sess.players]}

# --- Backlog & Story ---
@app.post("/sessions/{session_id}/backlog", summary="Importer un backlog", tags=["Backlog"])
def api_upload_backlog(session_id: str, payload: UploadBacklogIn):
    backlog = upload_backlog(session_id, payload)
    return {"projet": backlog.project, "version": backlog.version, "stories": len(backlog.stories)}

@app.post("/sessions/{session_id}/stories/current", summary="Sélectionner la story courante", tags=["Backlog"])
def api_select_current_story(session_id: str, payload: SelectStoryIn):
    story = select_current_story(session_id, payload)
    return {"id": story.id, "titre": story.title, "statut": story.status}

@app.get("/sessions/{session_id}/state", summary="Voir l’état de la session", tags=["Session"])
def api_state(session_id: str):
    return get_state(session_id)
    from .storage import get_session
    sess = get_session(session_id)
    if sess:
        state["owner"] = sess.owner
    return state

