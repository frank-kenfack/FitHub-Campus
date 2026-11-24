import React, { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { apiRequest, getStoredToken } from "../api.js";

const QUICK_BOOSTS = [
  "🔥 Go training !",
  "👏 GG pour ta séance !",
  "💪 On garde notre streak !",
  "🏃 Dispo footing à 18h ?"
];

const SPORTS = [
  "",
  "Running",
  "Calisthenics",
  "Cross-Training",
  "Fitness",
  "Musculation",
  "Natation",
  "Escalade"
];

const LEVELS = ["", "Débutant", "Intermédiaire", "Avancé", "Compétiteur"];

export default function FitBuddyView({ user, campuses, onRequireAuth, onActivityChanged }) {
  const [accepted, setAccepted] = useState([]);
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [selectedPartner, setSelectedPartner] = useState(null);
  const [activeStreak, setActiveStreak] = useState(0);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");

  const [candidates, setCandidates] = useState([]);
  const [filters, setFilters] = useState({ campus_id: "", sport: "", level: "", q: "" });

  const [wsConnected, setWsConnected] = useState(false);
  const [liveToast, setLiveToast] = useState("");
  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const [busy, setBusy] = useState(false);

  const socketRef = useRef(null);
  const selectedPartnerRef = useRef(null);

  useEffect(() => {
    selectedPartnerRef.current = selectedPartner;
  }, [selectedPartner]);

  async function loadBuddies() {
    if (!user) return;
    try {
      const data = await apiRequest("/api/buddies");
      const acc = data.accepted || [];
      setAccepted(acc);
      setIncoming(data.incoming_pending || []);
      setOutgoing(data.outgoing_pending || []);

      if (acc.length > 0) {
        const current = selectedPartnerRef.current;
        const match = current
          ? acc.find((r) => r.partner.id === current.id)
          : acc[0];
        const chosen = match || acc[0];
        setSelectedPartner(chosen.partner);
        setActiveStreak(chosen.streak_days || 1);
      } else {
        setSelectedPartner(null);
        setMessages([]);
      }
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function loadDiscover(activeFilters = filters) {
    if (!user) return;
    try {
      const params = new URLSearchParams();
      if (activeFilters.campus_id) params.set("campus_id", activeFilters.campus_id);
      if (activeFilters.sport) params.set("sport", activeFilters.sport);
      if (activeFilters.level) params.set("level", activeFilters.level);
      if (activeFilters.q.trim()) params.set("q", activeFilters.q.trim());
      const qs = params.toString();
      const data = await apiRequest(`/api/buddies/discover${qs ? `?${qs}` : ""}`);
      setCandidates(data.candidates || []);
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function loadConversation(partnerId) {
    if (!user || !partnerId) return;
    try {
      const data = await apiRequest(`/api/buddies/${partnerId}/encouragements`);
      setMessages(data.encouragements || []);
      if (typeof data.streak_days === "number") {
        setActiveStreak(data.streak_days);
      }
    } catch {
      setMessages([]);
    }
  }

  useEffect(() => {
    if (!user) return;
    loadBuddies();
    loadDiscover(filters);
  }, [user?.id]);

  useEffect(() => {
    if (!user) return;
    loadDiscover(filters);
  }, [filters.campus_id, filters.sport, filters.level]);

  useEffect(() => {
    if (selectedPartner?.id) {
      loadConversation(selectedPartner.id);
    }
  }, [selectedPartner?.id]);

  // Connexion WebSocket temps reel (Socket.IO)
  useEffect(() => {
    if (!user) {
      setWsConnected(false);
      return undefined;
    }
    const token = getStoredToken();
    if (!token) return undefined;

    const sock = io("/", {
      path: "/socket.io",
      auth: { token },
      transports: ["websocket", "polling"]
    });
    socketRef.current = sock;

    sock.on("connect", () => setWsConnected(true));
    sock.on("disconnect", () => setWsConnected(false));

    sock.on("new_encouragement", (msg) => {
      const partner = selectedPartnerRef.current;
      if (
        partner &&
        (msg.sender_id === partner.id || msg.receiver_id === partner.id)
      ) {
        setMessages((prev) =>
          prev.some((existing) => existing.id === msg.id) ? prev : [...prev, msg]
        );
        if (typeof msg.streak_days === "number") {
          setActiveStreak(msg.streak_days);
        }
      }
      if (msg.sender_id !== user.id) {
        setLiveToast(`⚡ Encouragement reçu en direct de ${msg.sender_username} : « ${msg.message} »`);
      }
    });

    sock.on("buddy_request", () => {
      setLiveToast("⚡ Nouvelle demande de Fit-Buddy reçue en direct !");
      loadBuddies();
      loadDiscover();
    });

    sock.on("buddy_updated", () => {
      setLiveToast("⚡ Votre demande Fit-Buddy a été mise à jour !");
      loadBuddies();
      loadDiscover();
      onActivityChanged();
    });

    return () => {
      sock.disconnect();
      socketRef.current = null;
    };
  }, [user?.id]);

  async function sendBoostMessage(textToSend) {
    if (!selectedPartner || !textToSend.trim()) return;
    const cleanText = textToSend.trim();
    setBusy(true);
    setFeedback({ type: "", text: "" });

    try {
      const sock = socketRef.current;
      if (sock && sock.connected) {
        await new Promise((resolve, reject) => {
          sock.emit(
            "send_encouragement",
            { receiver_id: selectedPartner.id, message: cleanText },
            (ack) => {
              if (ack && ack.ok && ack.encouragement) {
                const msg = ack.encouragement;
                setMessages((prev) =>
                  prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]
                );
                if (typeof msg.streak_days === "number") {
                  setActiveStreak(msg.streak_days);
                }
                resolve();
              } else {
                reject(new Error(ack?.error || "Erreur d'envoi WebSocket."));
              }
            }
          );
        });
      } else {
        const res = await apiRequest(
          `/api/buddies/${selectedPartner.id}/encouragements`,
          { method: "POST", body: { message: cleanText } }
        );
        const msg = res.encouragement;
        setMessages((prev) =>
          prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]
        );
      }
      setDraft("");
      onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleSendRequest(candidateId) {
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      await apiRequest("/api/buddies/request", {
        method: "POST",
        body: { addressee_id: candidateId }
      });
      setFeedback({ type: "ok", text: "Demande de Fit-Buddy envoyée !" });
      await loadBuddies();
      await loadDiscover();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleRespondRequest(relationId, decision) {
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      await apiRequest(`/api/buddies/${relationId}/respond`, {
        method: "POST",
        body: { decision }
      });
      setFeedback({
        type: "ok",
        text:
          decision === "accept"
            ? "Nouveau Fit-Buddy accepté (+25 XP) !"
            : "Demande refusée."
      });
      await loadBuddies();
      await loadDiscover();
      onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <section className="card">
        <h2>Motivation Fit-Buddy &amp; Encouragements Temps Réel</h2>
        <p className="muted-text">
          Connectez-vous avec votre compte étudiant pour trouver un binôme sportif compatible et échanger des encouragements instantanés via WebSocket.
        </p>
        <button type="button" className="primary-btn" onClick={onRequireAuth}>
          Se connecter pour accéder à Fit-Buddy
        </button>
      </section>
    );
  }

  return (
    <div>
      {/* BANDEAU STATUT WEBSOCKET & NOTIFICATIONS LIVE */}
      <section className="card" style={{ marginBottom: "14px" }}>
        <div className="topbar-row">
          <div>
            <h2 style={{ margin: 0 }}>Espace Fit-Buddy &amp; Motivation Temps Réel</h2>
            <p className="muted-text" style={{ margin: "2px 0 0" }}>
              Binômes actifs : <strong>{accepted.length}</strong> • Demandes reçues :{" "}
              <strong>{incoming.length}</strong>
            </p>
          </div>
          <span className={`badge ${wsConnected ? "badge-ok" : "badge-err"}`}>
            {wsConnected ? "🟢 Live WebSocket Connecté" : "🟠 Connexion temps réel..."}
          </span>
        </div>

        {liveToast && (
          <div className="alert alert-ok" style={{ marginTop: "10px", marginBottom: 0 }}>
            {liveToast}
          </div>
        )}
        {feedback.text && (
          <div
            className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}
            style={{ marginTop: "10px", marginBottom: 0 }}
          >
            {feedback.text}
          </div>
        )}
      </section>

      {/* PANNEAU PRINCIPAL : BINÔMES + MESSAGERIE D'ENCOURAGEMENTS */}
      <div className="grid-cards">
        <section className="card">
          <h2>Mes Fit-Buddies &amp; Demandes</h2>

          {incoming.length > 0 && (
            <div className="pending-box">
              <strong>Demandes reçues ({incoming.length})</strong>
              {incoming.map((rel) => (
                <div key={rel.id} className="buddy-item">
                  <div>
                    <strong>{rel.partner.username}</strong>
                    <span>
                      {rel.partner.campus_name} • {rel.partner.favorite_sports}
                    </span>
                  </div>
                  <div className="group-btns">
                    <button
                      type="button"
                      className="primary-btn"
                      disabled={busy}
                      onClick={() => handleRespondRequest(rel.id, "accept")}
                    >
                      Accepter (+25 XP)
                    </button>
                    <button
                      type="button"
                      className="outline-btn"
                      disabled={busy}
                      onClick={() => handleRespondRequest(rel.id, "decline")}
                    >
                      Refuser
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {accepted.length === 0 ? (
            <p className="muted-text">
              Aucun binôme actif pour l&apos;instant. Choisissez un partenaire ci-dessous !
            </p>
          ) : (
            <div className="buddy-list">
              {accepted.map((rel) => {
                const active = selectedPartner?.id === rel.partner.id;
                return (
                  <button
                    key={rel.id}
                    type="button"
                    className={`buddy-select-card ${active ? "selected" : ""}`}
                    onClick={() => {
                      setSelectedPartner(rel.partner);
                      setActiveStreak(rel.streak_days || 1);
                    }}
                  >
                    <div className="post-author">
                      {rel.partner.avatar_url ? (
                        <img
                          src={rel.partner.avatar_url}
                          alt={rel.partner.username}
                          className="post-avatar"
                        />
                      ) : (
                        <span className="post-initials">
                          {rel.partner.username.slice(0, 2).toUpperCase()}
                        </span>
                      )}
                      <div style={{ textAlign: "left" }}>
                        <strong>{rel.partner.username}</strong>
                        <span className="post-sub">
                          {rel.partner.campus_name} • {rel.partner.favorite_sports}
                        </span>
                      </div>
                    </div>
                    <span className="streak-pill">🔥 {rel.streak_days} j streak</span>
                  </button>
                );
              })}
            </div>
          )}

          {outgoing.length > 0 && (
            <div style={{ marginTop: "12px" }}>
              <span className="muted-text">
                En attente de réponse :{" "}
                <strong>{outgoing.map((r) => r.partner.username).join(", ")}</strong>
              </span>
            </div>
          )}
        </section>

        <section className="card">
          {selectedPartner ? (
            <>
              <div className="topbar-row" style={{ marginBottom: "10px" }}>
                <div>
                  <h2 style={{ margin: 0 }}>
                    Encouragements avec {selectedPartner.username}
                  </h2>
                  <span className="muted-text">{selectedPartner.campus_name}</span>
                </div>
                <span className="streak-pill">🔥 Série : {activeStreak} jours</span>
              </div>

              <div className="quick-boost-bar">
                {QUICK_BOOSTS.map((boost) => (
                  <button
                    key={boost}
                    type="button"
                    className="boost-chip"
                    disabled={busy}
                    onClick={() => sendBoostMessage(boost)}
                  >
                    {boost}
                  </button>
                ))}
              </div>

              <div className="chat-stream">
                {messages.length === 0 ? (
                  <p className="muted-text" style={{ margin: 0 }}>
                    Envoyez le premier encouragement temps réel à {selectedPartner.username} !
                  </p>
                ) : (
                  messages.map((m) => {
                    const mine = m.sender_id === user.id;
                    return (
                      <div
                        key={m.id}
                        className={`chat-bubble ${mine ? "mine" : "theirs"}`}
                      >
                        <span className="chat-author">
                          {mine ? "Moi" : m.sender_username}
                        </span>
                        <p>{m.message}</p>
                      </div>
                    );
                  })
                )}
              </div>

              <form
                className="comment-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  sendBoostMessage(draft);
                }}
              >
                <input
                  type="text"
                  maxLength={280}
                  placeholder={`Encourager ${selectedPartner.username} en direct...`}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                />
                <button type="submit" className="primary-btn" disabled={busy}>
                  Envoyer ⚡
                </button>
              </form>
            </>
          ) : (
            <p className="muted-text">
              Sélectionnez ou acceptez un Fit-Buddy pour démarrer les encouragements en direct.
            </p>
          )}
        </section>
      </div>

      {/* RECHERCHE & MATCHING DE NOUVEAUX FIT-BUDDIES */}
      <section className="card">
        <div className="topbar-row" style={{ marginBottom: "10px" }}>
          <h2 style={{ margin: 0 }}>Trouver un Fit-Buddy Compatible ({candidates.length})</h2>
        </div>

        <div className="filters-bar" style={{ marginBottom: "12px" }}>
          <select
            value={filters.campus_id}
            onChange={(e) => setFilters({ ...filters, campus_id: e.target.value })}
          >
            <option value="">Tous les campus</option>
            {campuses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <select
            value={filters.sport}
            onChange={(e) => setFilters({ ...filters, sport: e.target.value })}
          >
            <option value="">Tous les sports</option>
            {SPORTS.filter(Boolean).map((sp) => (
              <option key={sp} value={sp}>
                {sp}
              </option>
            ))}
          </select>

          <div className="search-inline">
            <select
              value={filters.level}
              onChange={(e) => setFilters({ ...filters, level: e.target.value })}
            >
              <option value="">Tous niveaux</option>
              {LEVELS.filter(Boolean).map((lvl) => (
                <option key={lvl} value={lvl}>
                  {lvl}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="secondary-btn"
              onClick={() => loadDiscover(filters)}
            >
              Filtrer
            </button>
          </div>
        </div>

        <div className="grid-cards" style={{ marginBottom: 0 }}>
          {candidates.map((cand) => (
            <article key={cand.id} className="buddy-cand-card">
              <div className="topbar-row">
                <div className="post-author">
                  {cand.avatar_url ? (
                    <img
                      src={cand.avatar_url}
                      alt={cand.username}
                      className="post-avatar"
                    />
                  ) : (
                    <span className="post-initials">
                      {cand.username.slice(0, 2).toUpperCase()}
                    </span>
                  )}
                  <div>
                    <strong>{cand.username}</strong>
                    <span className="post-sub">{cand.campus_name}</span>
                  </div>
                </div>
                <span className="badge badge-ok">
                  Affinité {cand.compatibility_score} %
                </span>
              </div>

              <p className="muted-text" style={{ margin: "8px 0" }}>
                <strong>Sports :</strong> {cand.favorite_sports} •{" "}
                <strong>Niveau :</strong> {cand.level}
              </p>

              <div className="group-footer">
                <span className="muted-text" style={{ fontSize: "12px" }}>
                  {cand.xp_points} XP
                </span>
                {cand.relation_status === "accepted" && (
                  <span className="badge badge-soon">Déjà Fit-Buddy</span>
                )}
                {cand.relation_status === "pending_sent" && (
                  <span className="badge badge-soon">Demande envoyée</span>
                )}
                {cand.relation_status === "pending_received" && (
                  <button
                    type="button"
                    className="primary-btn"
                    disabled={busy}
                    onClick={() => handleRespondRequest(cand.relation_id, "accept")}
                  >
                    Accepter la demande
                  </button>
                )}
                {(cand.relation_status === "none" ||
                  cand.relation_status === "declined") && (
                  <button
                    type="button"
                    className="secondary-btn"
                    disabled={busy}
                    onClick={() => handleSendRequest(cand.id)}
                  >
                    + Demander en Fit-Buddy
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
