// static/js/app.js

console.log("app.js chargé ✅");

const { CARD_DECK = [], NUMERIC_CARDS = [], ERROR = null } = window.APP_CONFIG || {};

// Messages de chat stockés côté client (par onglet)
const CHAT_MESSAGES = [];

// Etat global
const APP_STATE = {
    view: "home",          // 'home' | 'create' | 'join' | 'session'
    sessionId: null,
    userId: null,
    userName: null,
    session: null,         // état reçu du serveur
    selectedCard: null,
    error: ERROR,
};

let socket = null;

/* ==============================
   RENDER PRINCIPAL
   ============================== */

function renderApp() {
    const app = document.getElementById("app");
    if (!app) return;

    let html = "";

    if (APP_STATE.error) {
        html += `
        <div class="max-w-3xl mx-auto mt-4">
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                <strong class="font-bold">Erreur :</strong>
                <span class="ml-2">${APP_STATE.error}</span>
            </div>
        </div>`;
    }

    switch (APP_STATE.view) {
        case "home":
            html += renderHomeView();
            break;
        case "create":
            html += renderCreateSessionForm();
            break;
        case "join":
            html += renderJoinSessionForm();
            break;
        case "session":
            html += renderSessionView();
            break;
        default:
            html += renderHomeView();
    }

    app.innerHTML = html;
}

/* ==============================
   VUES
   ============================== */

function renderHomeView() {
    return `
    <div class="max-w-xl mx-auto mt-12 bg-white p-10 rounded-xl shadow-2xl">
        <h1 class="text-6xl font-extrabold text-center text-gray-800 mb-4">
            Planning Poker
        </h1>
        <p class="text-center text-gray-600 mb-8">
            Estimez vos user stories en équipe, en temps réel.
        </p>
        <div class="space-y-4">
            <button onclick="setView('create')"
                class="w-full p-4 rounded-xl font-bold text-lg bg-gray-700 hover:bg-gray-800 text-white transition-colors shadow-lg">
                Créer une Session (Facilitateur)
            </button>
            <button onclick="setView('join')"
                class="w-full p-4 rounded-xl font-bold text-lg bg-gray-200 hover:bg-gray-300 text-gray-800 transition-colors shadow-lg">
                Rejoindre une Session (Joueur)
            </button>
        </div>
        <div class="mt-8 text-center text-sm text-gray-500">
            <p>Cartes disponibles : ${CARD_DECK.join(", ")}</p>
            <div class="mt-3">
                <p><strong>Petit chiffre</strong> = tâche simple, rapide, bien comprise.</p>
                <p><strong>Grand chiffre</strong> = tâche complexe, longue, incertaine.</p>
                <p><strong>☕</strong> = j'ai besoin d'une pause.</p>
                <p><strong>?</strong> = je ne me sens pas compétent pour estimer.</p>
            </div>
        </div>
    </div>`;
}

function renderCreateSessionForm() {
    return `
    <div class="max-w-md mx-auto mt-12 bg-white p-8 rounded-xl shadow-2xl">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Créer une nouvelle session</h2>
        <form onsubmit="createSession(event)">
            <div class="mb-4">
                <label class="block text-gray-700 font-semibold mb-2" for="sessionName">
                    Nom de la session
                </label>
                <input id="sessionName" type="text" required
                    placeholder="Ex: Estimation User Story"
                    class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 font-semibold mb-2" for="facilitatorName">
                    Votre nom (Facilitateur)
                </label>
                <input id="facilitatorName" type="text" required
                    placeholder="Votre pseudo"
                    class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
            <div class="mb-6">
                <label class="block text-gray-700 font-semibold mb-2" for="gameMode">
                    Mode de validation
                </label>
                <select id="gameMode" required
                    class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-700">
                    <option value="strict">Unanimité stricte (recommandé)</option>
                    <option value="average">Moyenne (tours suivants)</option>
                    <option value="median">Médiane (tours suivants)</option>
                </select>
                <p class="text-xs text-gray-500 mt-1">
                    Le premier tour utilise toujours l'unanimité stricte.
                </p>
            </div>
            <div class="flex space-x-4">
                <button type="button" onclick="setView('home')"
                    class="flex-1 p-3 rounded-lg font-bold bg-gray-300 hover:bg-gray-400 text-gray-800 transition-colors">
                    Annuler
                </button>
                <button type="submit"
                    class="flex-1 p-3 rounded-lg font-bold bg-gray-700 hover:bg-gray-800 text-white transition-colors">
                    Créer & démarrer
                </button>
            </div>
        </form>
    </div>`;
}

function renderJoinSessionForm() {
    let presetId = "";
    const parts = window.location.pathname.split("/");
    if (parts.length === 3 && parts[1] === "session") {
        presetId = parts[2];
    }

    return `
    <div class="max-w-md mx-auto mt-12 bg-white p-8 rounded-xl shadow-2xl">
        <h2 class="text-3xl font-bold text-gray-700 mb-6">Rejoindre une session</h2>
        <form onsubmit="joinSession(event)">
            <div class="mb-4">
                <label class="block text-gray-700 font-semibold mb-2" for="joinSessionId">
                    Code de session (ID)
                </label>
                <input id="joinSessionId" type="text" required
                    value="${presetId}"
                    placeholder="Ex: 1234"
                    class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
            <div class="mb-6">
                <label class="block text-gray-700 font-semibold mb-2" for="joinUserName">
                    Votre pseudo
                </label>
                <input id="joinUserName" type="text" required
                    placeholder="Votre nom"
                    class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
            <div class="flex space-x-4">
                <button type="button" onclick="setView('home')"
                    class="flex-1 p-3 rounded-lg font-bold bg-gray-300 hover:bg-gray-400 text-gray-800 transition-colors">
                    Annuler
                </button>
                <button type="submit"
                    class="flex-1 p-3 rounded-lg font-bold bg-gray-700 hover:bg-gray-800 text-white transition-colors">
                    Rejoindre
                </button>
            </div>
        </form>
    </div>`;
}

function renderSessionView() {
    const s = APP_STATE.session;
    if (!s) {
        return `
        <div class="max-w-xl mx-auto mt-12 bg-white p-10 rounded-xl shadow-xl">
            <p class="text-gray-700">Connexion à la session...</p>
        </div>`;
    }

    const isFac = APP_STATE.userId === s.facilitator_id;
    const current = s.current_story || null;

    let main = "";

    if (!current) {
        main = `
        <div class="text-center p-12 bg-gray-100 rounded-xl shadow-xl">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">En attente d'une user story</h2>
            <p class="text-gray-600 mb-4">
                Le facilitateur doit sélectionner une user story à estimer.
            </p>
            ${isFac ? `<p class="text-sm text-indigo-600">Utilisez le panneau Backlog pour choisir une story.</p>` : ""}
        </div>`;
    } else {
        const stateLabel = {
            selection: "Discussion / préparation",
            voting: "Vote en cours",
            revealed: "Résultats révélés",
            validated: "Story validée",
        }[current.state] || current.state;

        main = `
        <div class="bg-white p-6 rounded-xl shadow-xl mb-6 border-l-4 border-indigo-500">
            <h2 class="text-2xl font-bold text-gray-800">
                ${current.id} - ${current.title}
            </h2>
            <p class="text-gray-600 mt-2">${current.description || ""}</p>
            <p class="text-sm mt-1">
                Priorité :
                <span class="font-semibold text-yellow-700">${current.priority || "-"}</span>
            </p>
            <p class="mt-3 text-sm text-indigo-700">
                État : <strong>${stateLabel}</strong>
            </p>
            <p class="mt-1 text-xs text-gray-500">
                ${s.status_message || ""}
            </p>

            ${current.state === "voting" ? renderVotingPanel(current) : ""}
            ${(current.state === "revealed" || current.state === "validated") && current.stats
                ? renderResultsPanel(current)
                : ""}
        </div>
        ${isFac ? renderFacilitatorActions(s, current) : ""}`;
    }

    const participantsPanel = renderParticipantsPanel(s, current);
    const backlogPanel = isFac ? renderBacklogPanel(s) : "";

    // Zone de chat commune quand pas d'unanimité
    let chatPanel = "";
    if (current && current.state === "revealed" && current.stats) {
        const stats = current.stats;
        const isUnanimous = stats.min === stats.max && stats.min != null;
        if (!isUnanimous) {
            chatPanel = `
            <div class="mt-4">
                <div class="p-3 mb-2 bg-yellow-100 border border-yellow-300 rounded-lg text-sm text-yellow-900">
                    💬 Nous ne sommes pas d'accord. Discutons pour trouver un consensus !
                </div>
                ${renderChatBox()}
            </div>`;
        }
    }

    return `
    <div class="max-w-7xl mx-auto">
        <h1 class="text-4xl font-extrabold text-center text-gray-100 mb-4">
            Session Planning Poker : ${s.name}
            <span class="ml-4 text-sm font-bold text-center text-gray-300">
                ID: ${s.id} • Mode: ${s.mode}
            </span>
        </h1>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-2">
                ${main}
                ${chatPanel}
            </div>
            <div class="lg:col-span-1 space-y-6">
                ${participantsPanel}
                ${backlogPanel}
            </div>
        </div>
    </div>`;
}

/* ----- Sous-vues ----- */

function renderVotingPanel(current) {
    const hasSelected = APP_STATE.selectedCard !== null;

    const cardsHtml = CARD_DECK.map((val) => {
        const selected = APP_STATE.selectedCard === val;
        return `
        <button
            type="button"
            onclick="handleCardSelection('${val}')"
            class="poker-card ${selected ? "selected" : ""}">
            ${val}
        </button>`;
    }).join("");

    return `
    <div class="mt-6">
        <h3 class="text-xl font-semibold mb-3 text-gray-700">Votre vote</h3>
        <div class="flex flex-wrap gap-3 justify-center">
            ${cardsHtml}
        </div>
        <button
            type="button"
            onclick="submitVote()"
            ${hasSelected ? "" : "disabled"}
            class="w-full mt-4 p-3 rounded-lg font-bold transition-colors
                   ${hasSelected
                       ? "bg-gray-600 hover:bg-gray-700 text-white"
                       : "bg-gray-300 text-gray-500 cursor-not-allowed"}">
            Soumettre le vote
        </button>
    </div>`;
}

function renderParticipantsPanel(s, current) {
    const entries = Object.entries(s.participants);

    const rows = entries.map(([uid, p]) => {
        const isSelf = uid === APP_STATE.userId;
        const isFac = uid === s.facilitator_id;

        let voteBadge = '<span class="text-xs text-gray-400">-</span>';
        if (current && current.votes_info && current.votes_info[uid]) {
            const v = current.votes_info[uid];
            if (current.state === "voting") {
                voteBadge = v.has_voted
                    ? '<span class="text-xs text-green-600">A voté</span>'
                    : '<span class="text-xs text-gray-400">En attente</span>';
            } else if (current.state === "revealed" || current.state === "validated") {
                voteBadge = `<span class="text-xs font-semibold text-indigo-700">${v.vote_display}</span>`;
            }
        }

        return `
        <div class="flex items-center justify-between p-2 bg-gray-50 border rounded-md">
            <div class="flex items-center gap-2">
                <span class="font-semibold ${isSelf ? "text-indigo-700" : "text-gray-800"}">
                    ${p.name}
                </span>
                ${isFac ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700">Facilitateur</span>' : ""}
                ${isSelf ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">Vous</span>' : ""}
            </div>
            <div>${voteBadge}</div>
        </div>`;
    }).join("");

    return `
    <div class="bg-gray-100 p-4 rounded-xl shadow-xl">
        <h3 class="text-lg font-bold text-gray-800 mb-3">
            Participants (max 5) (${entries.length})
        </h3>
        <div class="space-y-2 max-h-80 overflow-y-auto">
            ${rows || '<p class="text-sm text-gray-500">Aucun participant.</p>'}
        </div>
    </div>`;
}

function renderBacklogPanel(s) {
    const items = s.stories.map((story, idx) => {
        const isCurrent = idx === s.current_story_index;
        const est = story.estimate;

        const baseClass = isCurrent
            ? "bg-yellow-50 border-yellow-500"
            : est != null
                ? "bg-green-50 border-green-300"
                : "bg-gray-50 border-gray-200";

        return `
        <div class="p-2 border ${baseClass} rounded-md flex items-center justify-between gap-2">
            <div class="flex-1">
                <div class="text-sm font-semibold">
                    ${story.id}: ${story.title}
                    ${est != null ? `<span class="ml-1 text-xs text-green-700">(Est. ${est})</span>` : ""}
                </div>
            </div>
            <button
                type="button"
                onclick="selectStory(${idx})"
                class="px-2 py-1 text-[11px] rounded-full
                       ${isCurrent
                           ? "bg-gray-300 text-gray-600 cursor-default"
                           : "bg-indigo-500 text-white hover:bg-indigo-600"}">
                ${isCurrent ? "Courante" : "Choisir"}
            </button>
        </div>`;
    }).join("");

    return `
    <div class="bg-gray-100 p-4 rounded-xl shadow-xl">
        <h3 class="text-lg font-bold text-gray-800 mb-2">
            Backlog (${s.backlog_stats.estimated}/${s.backlog_stats.total} estimés)
        </h3>
        <div class="space-y-2 max-h-80 overflow-y-auto">
            ${items}
        </div>
        <button
            type="button"
            onclick="handleCloseSession()"
            class="mt-4 w-full p-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold">
            Clôturer la session
        </button>
    </div>`;
}

function renderFacilitatorActions(s, current) {
    if (!current) return "";

    const allVoted = current.votes_info &&
        Object.values(current.votes_info).length > 0 &&
        Object.values(current.votes_info).every(v => v.has_voted);

    let buttons = "";

    if (current.state === "selection") {
        buttons = `
        <button onclick="openVote()"
            class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold">
            Ouvrir le vote
        </button>`;
    } else if (current.state === "voting") {
        buttons = `
        <button onclick="revealVotes()"
            class="px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold">
            Révéler les votes ${allVoted ? "" : "(même si tout le monde n'a pas voté)"}
        </button>`;
    } else if (current.state === "revealed" && current.stats) {
        const stats = current.stats;
        if (stats.min === stats.max && stats.min != null) {
            buttons = `
            <button onclick="validateStory('${stats.min}')"
                class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold">
                Valider l'estimation (${stats.min})
            </button>`;
        } else {
            buttons = `
            <button onclick="promptForFinalEstimate()"
                class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold">
                Saisir & valider l'estimation finale
            </button>`;
        }
    }

    if (!buttons) return "";

    return `
    <div class="mt-4 p-3 bg-gray-100 rounded-lg flex flex-wrap gap-3 items-center">
        <span class="text-sm font-semibold text-gray-700">Actions facilitateur :</span>
        ${buttons}
    </div>`;
}

function renderResultsPanel(current) {
    const stats = current.stats;
    if (!stats) return "";

    const isUnanimous = stats.min === stats.max && stats.min != null;

    const distributionHtml = Object.entries(stats.distribution || {})
        .filter(([, count]) => count > 0)
        .map(([card, count]) => `
            <span class="inline-block bg-indigo-50 text-indigo-700 text-xs px-2 py-1 rounded-full mr-2 mb-1">
                ${card}: ${count}
            </span>`)
        .join("");

    return `
    <div class="mt-6">
        <h3 class="text-lg font-bold text-center ${isUnanimous ? "text-green-600" : "text-red-600"} mb-4">
            Résultats révélés —
            ${isUnanimous ? "Unanimité atteinte 🎉" : "Pas d'unanimité, discutez ensemble."}
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-center mb-4">
            <div class="p-2 bg-gray-50 rounded border">
                <p class="text-[10px] text-gray-500">Moyenne</p>
                <p class="text-lg font-bold text-indigo-700">${stats.mean}</p>
            </div>
            <div class="p-2 bg-gray-50 rounded border">
                <p class="text-[10px] text-gray-500">Médiane</p>
                <p class="text-lg font-bold text-indigo-700">${stats.median}</p>
            </div>
            <div class="p-2 bg-gray-50 rounded border">
                <p class="text-[10px] text-gray-500">Min</p>
                <p class="text-lg font-bold">${stats.min}</p>
            </div>
            <div class="p-2 bg-gray-50 rounded border">
                <p class="text-[10px] text-gray-500">Max</p>
                <p class="text-lg font-bold">${stats.max}</p>
            </div>
        </div>
        <div class="p-3 bg-gray-50 rounded border text-left">
            <h4 class="text-xs font-semibold text-gray-600 mb-1">Distribution des votes</h4>
            <div>${distributionHtml || '<span class="text-xs text-gray-400">Aucun vote.</span>'}</div>
        </div>
    </div>`;
}

function renderChatBox() {
    const messagesHtml = CHAT_MESSAGES.map(m => `
        <div class="p-2 bg-white rounded border mb-1">
            <strong class="text-gray-800">${m.user}</strong>
            <span class="text-xs text-gray-400 ml-2">${m.timestamp}</span>
            <p class="text-sm text-gray-700">${m.message}</p>
        </div>
    `).join("");

    return `
    <div class="mt-3 p-3 bg-gray-100 rounded-lg">
        <h4 class="text-sm font-semibold text-gray-700 mb-2">💬 Discussion en direct</h4>
        <div id="chatBox" class="max-h-40 overflow-y-auto mb-2">
            ${messagesHtml || "<p class='text-xs text-gray-400'>Aucun message pour le moment.</p>"}
        </div>
        <div class="flex gap-2">
            <input id="chatInput" type="text" placeholder="Écrivez un message..."
                class="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm">
            <button onclick="sendChatMessage()"
                class="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold">
                Envoyer
            </button>
        </div>
    </div>`;
}


/* ==============================
   CHAT : utilitaires
   ============================== */

function addChatMessage(data) {
    CHAT_MESSAGES.push(data);
    renderApp();
}

function sendChatMessage() {
    const input = document.getElementById("chatInput");
    if (!input) return;
    const message = input.value.trim();
    if (!message || !socket) return;

    socket.emit("send_message", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
        message,
    });

    input.value = "";
}

/* ==============================
   HELPERS & SOCKET.IO
   ============================== */

function setView(view, opts = {}) {
    APP_STATE.view = view;
    APP_STATE.error = opts.error !== undefined ? opts.error : null;
    renderApp();
}

function initSocket() {
    if (socket) return;
    socket = io();

    socket.on("connect", () => {
        console.log("Socket connecté", socket.id);

        const storedSessionId = localStorage.getItem("pp_sessionId");
        const storedUserId = localStorage.getItem("pp_userId");
        if (storedSessionId && storedUserId) {
            socket.emit("request_full_state", {
                sessionId: storedSessionId,
                userId: storedUserId,
            });
        }
    });

    socket.on("session_created", (data) => {
        console.log("session_created", data);

        APP_STATE.sessionId = data.sessionId;
        APP_STATE.userId = data.userId;
        APP_STATE.userName =
            document.getElementById("facilitatorName")?.value || "Facilitateur";

        localStorage.setItem("pp_sessionId", data.sessionId);
        localStorage.setItem("pp_userId", data.userId);
        localStorage.setItem("pp_userName", APP_STATE.userName);

        window.history.pushState({}, "", `/session/${data.sessionId}`);
        APP_STATE.view = "session";
        APP_STATE.error = null;

        renderApp();
    });

    socket.on("session_joined", (data) => {
        APP_STATE.sessionId = data.sessionId;
        APP_STATE.userId = data.userId;
        APP_STATE.userName = data.name;

        localStorage.setItem("pp_sessionId", data.sessionId);
        localStorage.setItem("pp_userId", data.userId);
        localStorage.setItem("pp_userName", APP_STATE.userName);

        window.history.pushState({}, "", `/session/${data.sessionId}`);
        APP_STATE.view = "session";
        APP_STATE.error = null;
    });

    socket.on("join_error", (data) => {
        setView("join", {
            error: data.message || "Impossible de rejoindre la session.",
        });
    });

    socket.on("session_update", (sessionData) => {
        APP_STATE.session = sessionData;
        if (!APP_STATE.sessionId) {
            APP_STATE.sessionId = sessionData.id;
        }
        if (APP_STATE.view !== "session") {
            APP_STATE.view = "session";
        }
        renderApp();
    });

    socket.on("session_closed", (data) => {
        const exportJson = JSON.stringify(data.exportData || {}, null, 2);
        const blob = new Blob([exportJson], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `planning_poker_export_${APP_STATE.sessionId || "session"}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        localStorage.removeItem("pp_sessionId");
        localStorage.removeItem("pp_userId");
        localStorage.removeItem("pp_userName");

        APP_STATE.view = "home";
        APP_STATE.session = null;
        APP_STATE.sessionId = null;
        APP_STATE.userId = null;
        APP_STATE.selectedCard = null;
        renderApp();
    });

    socket.on("new_message", (data) => {
        console.log("📨 new_message reçu", data);
        addChatMessage(data);
    });

    socket.on("error", (data) => {
        APP_STATE.error = data && data.message ? data.message : "Erreur Socket.IO";
        renderApp();
    });
}


/* ==============================
   ACTIONS UTILISATEUR
   ============================== */

function createSession(event) {
    event.preventDefault();
    if (!socket) initSocket();

    const sessionName = document.getElementById("sessionName").value.trim();
    const facilitatorName = document.getElementById("facilitatorName").value.trim();
    const gameMode = document.getElementById("gameMode").value;

    socket.emit("create_session", {
        sessionName,
        facilitatorName,
        gameMode,
        deckType: "standard",
    });
}

function joinSession(event) {
    event.preventDefault();
    if (!socket) initSocket();

    const sessionId = document.getElementById("joinSessionId").value.trim();
    const userName = document.getElementById("joinUserName").value.trim();

    socket.emit("join_session", { sessionId, userName });
}

function selectStory(storyIndex) {
    if (!socket || !APP_STATE.sessionId || !APP_STATE.userId) return;
    socket.emit("select_story", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
        storyIndex,
    });
}

function openVote() {
    if (!socket || !APP_STATE.sessionId || !APP_STATE.userId) return;
    socket.emit("open_vote", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
    });
}

function handleCardSelection(value) {
    const s = APP_STATE.session;
    if (!s || !s.current_story || s.current_story.state !== "voting") return;
    APP_STATE.selectedCard = APP_STATE.selectedCard === value ? null : value;
    renderApp();
}

function submitVote() {
    if (!socket || APP_STATE.selectedCard === null) return;

    socket.emit("submit_vote", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
        vote: APP_STATE.selectedCard,
    });

    APP_STATE.selectedCard = null;
}

function revealVotes() {
    if (!socket) return;
    socket.emit("reveal_votes", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
    });
}

function validateStory(finalEstimate) {
    if (!socket) return;
    socket.emit("validate_story", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
        finalEstimate,
    });
}

function promptForFinalEstimate() {
    const s = APP_STATE.session;
    if (!s || !s.current_story || !s.current_story.stats) return;

    const stats = s.current_story.stats;
    const suggestion = stats.mean || stats.median || stats.min || "";

    const input = window.prompt(
        `Saisir l'estimation finale.\nSuggestions: moyenne=${stats.mean}, médiane=${stats.median}`,
        suggestion
    );
    if (!input) return;

    const num = Number(input);
    if (!Number.isNaN(num) && NUMERIC_CARDS.includes(num)) {
        validateStory(num);
    } else {
        alert("Valeur invalide. Utilisez une carte numérique du deck.");
    }
}

function handleCloseSession() {
    if (!socket) return;
    if (!confirm("Clôturer la session pour tous les participants ?")) return;

    socket.emit("close_session", {
        sessionId: APP_STATE.sessionId,
        userId: APP_STATE.userId,
    });
}

/* Expose pour les onclick HTML */
window.setView = setView;
window.createSession = createSession;
window.joinSession = joinSession;
window.selectStory = selectStory;
window.openVote = openVote;
window.handleCardSelection = handleCardSelection;
window.submitVote = submitVote;
window.revealVotes = revealVotes;
window.validateStory = validateStory;
window.promptForFinalEstimate = promptForFinalEstimate;
window.handleCloseSession = handleCloseSession;
window.sendChatMessage = sendChatMessage;

/* ==============================
   INIT
   ============================== */

document.addEventListener("DOMContentLoaded", () => {
    initSocket();

    const parts = window.location.pathname.split("/");
    if (parts.length === 3 && parts[1] === "session" && parts[2]) {
        setView("join");
    } else {
        setView("home");
    }
});
