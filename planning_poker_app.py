import json
import uuid
import random
import time
from copy import deepcopy

from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = str(uuid.uuid4())
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# --- ÉTAT EN MÉMOIRE ---

sessions = {}

CARD_DECK = [1, 2, 3, 5, 8, 13, 20, 40, 100, '?', '☕']
NUMERIC_CARDS = [c for c in CARD_DECK if isinstance(c, int)]

EXAMPLE_BACKLOG = [
    {"id": "US-01", "title": "Affichage de la page d'accueil",
     "description": "En tant qu'utilisateur, je veux voir une page d'accueil simple et attrayante.",
     "priority": "Haute", "estimate": None},
    {"id": "US-02", "title": "Ajouter au panier",
     "description": "En tant qu'acheteur, je peux ajouter des produits à mon panier d'achat.",
     "priority": "Haute", "estimate": None},
    {"id": "US-03", "title": "Filtrage avancé des produits",
     "description": "En tant qu'utilisateur, je veux filtrer les produits par prix, taille et couleur.", 
     "priority": "Moyenne","estimate": None},
    {"id": "US-04", "title": "Passer au paiement",
     "description": "En tant qu'acheteur, je peux initier le processus de paiement depuis mon panier.",
     "priority": "Haute","estimate": None},
    {"id": "US-05","title": "Historique des commandes",
     "description": "En tant qu'utilisateur, je veux consulter l'historique de mes commandes précédentes.",
     "priority": "Moyenne","estimate": None
    },
]

# --- UTILS (median, mean, consensus, etc.) ---

def calculate_median(votes):
    numeric_votes = sorted([v for v in votes if isinstance(v, (int, float))])
    n = len(numeric_votes)
    if n == 0:
        return 0
    if n % 2 == 1:
        return numeric_votes[n // 2]
    return (numeric_votes[n // 2 - 1] + numeric_votes[n // 2]) / 2


def calculate_mean(votes):
    numeric_votes = [v for v in votes if isinstance(v, (int, float))]
    if not numeric_votes:
        return 0
    return sum(numeric_votes) / len(numeric_votes)


def validate_consensus(session):
    story = session['stories'][session['current_story_index']]
    votes = [v['vote'] for v in story['votes'].values()]
    numeric_votes = [v for v in votes if isinstance(v, (int, float))]

    if not numeric_votes:
        return {'status': 'no_numeric_votes', 'estimate': None}

    is_first_round = story['estimation_rounds'] == 1

    if is_first_round or session['mode'] == 'strict':
        if len(set(numeric_votes)) == 1 and len(story['votes']) == len(session['participants']):
            return {'status': 'validated', 'estimate': numeric_votes[0]}
        return {'status': 'needs_reestimation', 'estimate': None}

    if session['mode'] == 'average':
        mean_val = calculate_mean(votes)
        closest = min(NUMERIC_CARDS, key=lambda x: abs(x - mean_val))
        return {'status': 'consensus_by_average', 'estimate': closest}

    if session['mode'] == 'median':
        median_val = calculate_median(votes)
        closest = min(NUMERIC_CARDS, key=lambda x: abs(x - median_val))
        return {'status': 'consensus_by_median', 'estimate': closest}

    return {'status': 'needs_reestimation', 'estimate': None}


def get_session_state(session_id, user_id):
    session = sessions.get(session_id)
    if not session:
        return None

    state = {
        'id': session['id'],
        'name': session['name'],
        'mode': session['mode'],
        'is_locked': session['is_locked'],
        'participants': {
            uid: {
                'id': p['id'],
                'name': p['name'],
                'is_facilitator': p['is_facilitator'],
            }
            for uid, p in session['participants'].items()
        },
        'facilitator_id': session['facilitator_id'],
        'backlog_stats': {
            'total': len(session['stories']),
            'estimated': sum(1 for s in session['stories'] if s.get('estimate') is not None),
        },
        'status_message': session.get(
            'status_message',
            f"Session de Planning Poker : {session['name']}"
        ),
        # 👇 IMPORTANT : ce que le front attend
        'current_story_index': session.get('current_story_index'),
        'stories': [
            {
                'id': s['id'],
                'title': s['title'],
                'description': s.get('description', ''),
                'priority': s.get('priority'),
                'estimate': s.get('estimate'),
                'state': s.get('state', ''),
            }
            for s in session['stories']
        ],
    }

    idx = session.get('current_story_index')
    if idx is not None and 0 <= idx < len(session['stories']):
        story = session['stories'][idx]
        cur = {
            'id': story['id'],
            'title': story['title'],
            'description': story['description'],
            'priority': story['priority'],
            'state': story.get('state', 'selection'),
            'round': story.get('estimation_rounds', 0),
        }

        votes_info = {}
        for uid, p in session['participants'].items():
            v = story['votes'].get(uid, {'vote': None, 'has_voted': False})
            revealed_vote = v['vote'] if story.get('state') == 'revealed' else '?'
            user_card = v['vote'] if v['has_voted'] else None

            votes_info[uid] = {
                'name': p['name'],
                'has_voted': v['has_voted'],
                'vote_display': revealed_vote,
                'user_card': user_card,
            }

        cur['votes_info'] = votes_info

        if story.get('state') == 'revealed' and story['votes']:
            votes = [v['vote'] for v in story['votes'].values()]
            numeric_votes = [v for v in votes if isinstance(v, (int, float))]
            if numeric_votes:
                distribution = {str(c): votes.count(c) for c in CARD_DECK}
                cur['stats'] = {
                    'mean': round(calculate_mean(votes), 2),
                    'median': calculate_median(votes),
                    'min': min(numeric_votes),
                    'max': max(numeric_votes),
                    'distribution': distribution,
                }
            else:
                cur['stats'] = {}
        else:
            cur['stats'] = {}

        state['current_story'] = cur

    state['is_facilitator'] = (user_id == session['facilitator_id'])
    return state



def broadcast_session_state(session_id):
    session = sessions.get(session_id)
    if not session:
        return
    for uid in session['participants']:
        state = get_session_state(session_id, uid)
        if state:
            socketio.emit('session_update', state, room=uid)


def save_session_state(session_id):
    session = sessions.get(session_id)
    if not session:
        return

    save_data = {
        'metadata': {
            'app_version': '1.0',
            'session_name': session['name'],
            'session_id': session['id'],
            'mode': session['mode'],
            'saved_at': time.time(),
        },
        'participants': {
            uid: {
                'id': p['id'],
                'name': p['name'],
                'is_facilitator': p['is_facilitator'],
            }
            for uid, p in session['participants'].items()
        },
        'stories': session['stories'],
        'current_story_index': session.get('current_story_index'),
    }

    filename = f"pause_session_{session_id}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=4)
        print(f"État de la session sauvegardé dans {filename}")
    except Exception as e:
        print(f"Erreur de sauvegarde: {e}")


# --- ROUTES ---

@app.route('/', methods=['GET'])
def home():
    error = request.args.get('error')
    return render_template(
        'index.html',
        card_deck=CARD_DECK,
        numeric_cards=NUMERIC_CARDS,
        error=error,
    )


@app.route('/session/<session_id>', methods=['GET'])
def session_lobby(session_id):
    if session_id not in sessions:
        return redirect(url_for('home', error=f"La session {session_id} est introuvable ou fermée."))
    return render_template(
        'index.html',
        card_deck=CARD_DECK,
        numeric_cards=NUMERIC_CARDS,
        error=None,
    )

# --- SOCKET.IO EVENTS ---
 # assure-toi que c'est bien importé en haut

@socketio.on('connect')
def handle_connect():
    print(f"Client connecté: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    client_sid = request.sid
    print(f"Client déconnecté: {client_sid}")

    for session_id, session in list(sessions.items()):
        user_id_to_remove = None

        for uid, participant in session['participants'].items():
            if participant.get('sid') == client_sid:
                user_id_to_remove = uid
                break

        if user_id_to_remove:
            name = session['participants'][user_id_to_remove]['name']
            was_fac = (user_id_to_remove == session['facilitator_id'])

            session['participants'].pop(user_id_to_remove, None)

            # si le facilitateur part, passer la main au premier participant restant
            if was_fac and session['participants']:
                new_fac_id = next(iter(session['participants'].keys()))
                session['facilitator_id'] = new_fac_id
                session['participants'][new_fac_id]['is_facilitator'] = True
                print(f"Nouveau facilitateur pour {session_id}: {new_fac_id}")

            if session['participants']:
                session['status_message'] = f"{name} a quitté la session."
                broadcast_session_state(session_id)
            else:
                pass

            break



@socketio.on('request_full_state')
def handle_request_full_state(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')
    state = get_session_state(session_id, user_id)
    if state:
        emit('session_update', state, room=user_id)
    else:
        emit('error', {'message': 'Session introuvable.'})


@socketio.on('create_session')
def handle_create_session(data):
    """CU-1 : créer une nouvelle session."""
    try:
        print("🔵 [create_session] data reçu :", data)

        session_name = data.get('sessionName', 'Nouvelle Session')
        game_mode = data.get('gameMode', 'strict')
        facilitator_name = data.get('facilitatorName', 'Facilitateur')

        # ID de session à 4 chiffres
        session_id = str(random.randint(1000, 9999))
        while session_id in sessions:
            session_id = str(random.randint(1000, 9999))

        facilitator_id = str(uuid.uuid4())


        new_session = {
            'id': session_id,
            'name': session_name,
            'mode': game_mode,
            'is_locked': False,
            'facilitator_id': facilitator_id,
            'participants': {},
            'stories': deepcopy(EXAMPLE_BACKLOG),
            'current_story_index': None,
            'created_at': time.time(),
            'status_message': f"Session {session_name} créée.",
        }

        # ajout du facilitateur
        new_session['participants'][facilitator_id] = {
            'id': facilitator_id,
            'name': facilitator_name,
            'is_facilitator': True,
            'sid': request.sid,
        }

        if new_session['stories']:
            new_session['current_story_index'] = 0
            first_story = new_session['stories'][0]
            first_story['state'] = 'selection'
            first_story['votes'] = {}
            first_story['estimation_rounds'] = 0

        sessions[session_id] = new_session

        # rooms
        join_room(session_id)
        join_room(facilitator_id)

        print(f"✅ Session créée: ID={session_id}, Facilitateur={facilitator_name}")

        # renvoyer au client créateur
        emit('session_created', {
            'sessionId': session_id,
            'userId': facilitator_id,
        })

        # envoyer l'état complet au créateur
        state = get_session_state(session_id, facilitator_id)
        if state:
            socketio.emit('session_update', state, room=facilitator_id)

    except Exception as e:
        print(f"❌ Erreur create_session: {e}")
        emit('error', {'message': f"Erreur lors de la création de la session: {str(e)}"})


@socketio.on('join_session')
def handle_join_session(data):
    """CU-2 : rejoindre une session existante."""
    session_id = data.get('sessionId')
    name = data.get('userName')

    session = sessions.get(session_id)
    if not session:
        emit('join_error', {'message': 'Session introuvable ou fermée.'})
        return

    if session['is_locked']:
        emit('join_error', {'message': 'Cette session est verrouillée.'})
        return

    if len(session['participants']) >= 5:
        emit('join_error', {'message': 'Session complète : maximum 5 participants.'})
        return

    # éviter les doublons de pseudo
    existing_names = [p['name'] for p in session['participants'].values()]
    original = name
    suffix = 1
    while name in existing_names:
        name = f"{original}({suffix})"
        suffix += 1

    user_id = str(uuid.uuid4())

    session['participants'][user_id] = {
        'id': user_id,
        'name': name,
        'is_facilitator': False,
        'sid': request.sid,
    }

    join_room(session_id)
    join_room(user_id)

    session['status_message'] = f"{name} a rejoint la session."
    print(f"👤 {name} a rejoint la session {session_id}")

    emit('session_joined', {'sessionId': session_id, 'userId': user_id, 'name': name})
    broadcast_session_state(session_id)


@socketio.on('select_story')
def handle_select_story(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')
    story_index = data.get('storyIndex')

    session = sessions.get(session_id)
    if not session or user_id != session['facilitator_id']:
        return

    if story_index is None or not (0 <= story_index < len(session['stories'])):
        emit('error', {'message': "Index de story invalide."}, room=user_id)
        return

    story = session['stories'][story_index]
    story['state'] = 'selection'
    story['votes'] = {}
    story['estimation_rounds'] = 0

    session['current_story_index'] = story_index
    session['status_message'] = f"Story sélectionnée : {story['title']}. Discussion en cours."
    broadcast_session_state(session_id)


@socketio.on('open_vote')
def handle_open_vote(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')

    session = sessions.get(session_id)
    if not session or user_id != session['facilitator_id']:
        return

    idx = session.get('current_story_index')
    if idx is None:
        return

    story = session['stories'][idx]
    state = story.get('state')
    estimate = story.get('estimate')

    # 1) Si déjà en cours de vote -> refuse
    if state == 'voting':
        emit('error', {'message': "Le vote est déjà ouvert pour cette story."}, room=user_id)
        return

    # 2) Si la story est déjà estimée/validée -> refuse
    if state == 'validated' or estimate is not None:
        emit('error', {'message': "La story est déjà estimée."}, room=user_id)
        return

    # 3) Cas autorisés :
    #    - 'selection' : premier tour
    #    - 'revealed' sans estimate : pas de consensus, on relance un tour
    story['state'] = 'voting'
    story['estimation_rounds'] = story.get('estimation_rounds', 0) + 1
    story['votes'] = {}

    session['status_message'] = (
        f"VOTE OUVERT pour {story['id']} (Tour {story['estimation_rounds']})."
    )
    print(f"🔁 Nouveau tour ouvert pour {story['id']} (Tour {story['estimation_rounds']})")

    broadcast_session_state(session_id)

@socketio.on('submit_vote')
def handle_submit_vote(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')
    vote = data.get('vote')

    session = sessions.get(session_id)
    if not session:
        emit('error', {'message': 'Session introuvable ou fermée.'})
        return

    idx = session.get('current_story_index')
    if idx is None:
        emit('error', {'message': "Aucune story sélectionnée."}, room=user_id)
        return

    story = session['stories'][idx]

    if story.get('state') != 'voting':
        emit('error', {'message': "Le vote n'est pas ouvert."}, room=user_id)
        return

    if user_id in story.get('votes', {}):
        emit('error', {'message': "Vous avez déjà voté pour ce tour."}, room=user_id)
        return

    # Validation de la carte
    if vote not in CARD_DECK:
        try:
            parsed = float(vote)
            if parsed.is_integer():
                parsed = int(parsed)
            if parsed not in CARD_DECK:
                raise ValueError
            vote = parsed
        except Exception:
            emit('error', {'message': "Carte de vote invalide."}, room=user_id)
            return

    story.setdefault('votes', {})
    story['votes'][user_id] = {
        'vote': vote,
        'has_voted': True,
        'timestamp': time.time(),
    }

    total = len(session['participants'])
    count = len(story['votes'])

    if count == total:
        session['status_message'] = "Tous les votes sont enregistrés. Le facilitateur peut révéler."
    else:
        session['status_message'] = f"{count}/{total} participants ont voté."

    broadcast_session_state(session_id)


@socketio.on('reveal_votes')
def handle_reveal_votes(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')

    session = sessions.get(session_id)
    if not session or user_id != session['facilitator_id']:
        return

    idx = session.get('current_story_index')
    if idx is None:
        return

    story = session['stories'][idx]

    if story.get('state') != 'voting':
        emit('error', {'message': "Le vote n'est pas en cours ou déjà révélé."}, room=user_id)
        return

    story['state'] = 'revealed'
    votes_list = [v['vote'] for v in story['votes'].values()]

    # cas 100% café
    if votes_list and all(v == '☕' for v in votes_list):
        story['estimate'] = '☕'
        story['state'] = 'validated'
        session['status_message'] = "Toute l'équipe a voté ☕. Pause !"
        save_session_state(session_id)
        broadcast_session_state(session_id)
        return

    result = validate_consensus(session)

    if result['status'] in ('validated', 'consensus_by_average', 'consensus_by_median'):
        story['estimate'] = result['estimate']
        story['state'] = 'validated'
        session['status_message'] = f"CONSENSUS : estimation {story['estimate']} (mode {session['mode']})."
    else:
        session['status_message'] = "Pas de consensus : discutez ou relancez un tour."

    broadcast_session_state(session_id)


@socketio.on('validate_story')
def handle_validate_story(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')
    final_estimate = data.get('finalEstimate')

    session = sessions.get(session_id)
    if not session or user_id != session['facilitator_id']:
        return

    idx = session.get('current_story_index')
    if idx is None:
        return

    story = session['stories'][idx]

    if story.get('state') != 'revealed':
        emit('error', {'message': "Les votes doivent être révélés avant de valider."}, room=user_id)
        return

    story['estimate'] = final_estimate
    story['state'] = 'validated'
    story['final_decision_timestamp'] = time.time()

    session['status_message'] = f"Story {story['id']} validée avec {final_estimate}."

    next_index = idx + 1
    if next_index < len(session['stories']):
        session['current_story_index'] = next_index
        next_story = session['stories'][next_index]
        next_story['state'] = 'selection'
        next_story['votes'] = {}
        next_story['estimation_rounds'] = 0
        session['status_message'] += f" Prochaine story : {next_story['title']}."
    else:
        session['current_story_index'] = None
        session['status_message'] += " Backlog terminé. Vous pouvez clôturer la session."

    broadcast_session_state(session_id)


@socketio.on('close_session')
def handle_close_session(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')

    session = sessions.get(session_id)
    if not session or user_id != session['facilitator_id']:
        return

    session['is_locked'] = True
    session['closed_at'] = time.time()
    session['status_message'] = f"Session {session['name']} clôturée."

    export_data = {
        'session_id': session['id'],
        'session_name': session['name'],
        'mode': session['mode'],
        'participants': {uid: p['name'] for uid, p in session['participants'].items()},
        'stories_estimated': [
            {
                'id': s['id'],
                'title': s['title'],
                'estimate': s.get('estimate'),
                'rounds': s.get('estimation_rounds', 0),
            }
            for s in session['stories']
        ],
        'stories_remaining': [
            s['title'] for s in session['stories'] if s.get('estimate') is None
        ],
    }

    socketio.emit('session_closed', {'exportData': export_data}, room=session_id)
    print(f"Session {session_id} clôturée.")

# === CHAT TEMPS RÉEL ===

@socketio.on("send_message")
def handle_send_message(data):
    session_id = data.get("sessionId")
    user_id = data.get("userId")
    message = data.get("message", "").strip()
    if not session_id or not user_id or not message:
        return

    # Récupérer le nom d'utilisateur
    session = sessions.get(session_id)
    if not session:
        return

    user = session["participants"].get(user_id)
    user_name = user["name"] if user else "Anonyme"

    # Créer l'objet message
    msg_data = {
        "user": user_name,
        "message": message,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }

    # ✅ Diffuser le message à TOUTE la session
    emit("new_message", msg_data, room=session_id)


# --- MAIN ---

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, use_reloader=False)

