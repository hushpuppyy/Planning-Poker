# Architecture

- **Backend** : Flask + Flask-SocketIO
- **Temps réel** : Socket.IO (événements: create_session, join_session, select_story, open_vote, submit_vote, reveal_votes, validate_story, close_session)
- **Frontend** : HTML + Tailwind CDN + JavaScript (SPA légère)
- **Hébergement** : Render (Web Service)
- **CI** : GitHub Actions (tests + build documentation)
