# Planning-Poker
Projet planning poker de IMANSOUREN Selma et LYONNET Andrea 

Objectif du Jeu

Le Planning Poker est un outil d’estimation agile utilisé en équipe pour évaluer la complexité des user stories.
Chaque joueur choisit une carte représentant son estimation, puis les votes sont révélés simultanément.

Comment Jouer 

lien : 
Facilitateur : crée une session, choisit le mode, obtient un code à donner aux joueurs.
Joueurs : entrent le code et rejoignent la session.
Déroulement :
    Le facilitateur choisit une story.
    Discussion éventuelle.
    Le facilitateur ouvre le vote.
    Les joueurs votent.
    Le facilitateur révèle les votes.
    En cas de désaccord → discussion puis estimation finale.
    Le facilitateur valide la story, on passe à la suivante.
Fin :
La session peut être clôturée et exportée en JSON.
Reconnexion automatique en cas de coupure.

Le système permet de 

Créer une session d’estimation

Rejoindre une session via un code unique

Voter secrètement grâce aux cartes du Planning Poker

Révéler les votes simultanément

Détecter automatiquement l'unanimité ou le besoin de discussion

Utiliser un chat en direct pour échanger en cas de désaccord

Le facilitateur peut valider l’estimation finale

Gestion complète des stories, du backlog et des participants

Interface dynamique via WebSockets (Socket.IO)
