import React, { useEffect, useState } from "react";
import { apiRequest, getStoredToken, setStoredToken } from "./api.js";
import AuthProfileView from "./components/AuthProfileView.jsx";
import GroupsView from "./components/GroupsView.jsx";

const TABS = [
  { id: "home", label: "Accueil", step: "Étapes 1–2" },
  { id: "groups", label: "Groupes", step: "Étape 2 (Actif)" },
  { id: "social", label: "Social", step: "Étape 3" },
  { id: "challenges", label: "Défis", step: "Étape 4" },
  { id: "buddy", label: "Buddy", step: "Étape 5" },
  { id: "profile", label: "Profil", step: "Étape 2 (Actif)" }
];

export default function App() {
  const [activeTab, setActiveTab] = useState("home");
  const [health, setHealth] = useState(null);
  const [campuses, setCampuses] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadBackendState() {
    setLoading(true);
    setError("");
    try {
      const [healthData, campusesData] = await Promise.all([
        apiRequest("/api/health"),
        apiRequest("/api/campuses")
      ]);
      setHealth(healthData);
      setCampuses(campusesData.campuses || []);

      if (getStoredToken()) {
        try {
          const meData = await apiRequest("/api/users/me");
          setCurrentUser(meData.user);
        } catch {
          setStoredToken("");
          setCurrentUser(null);
        }
      }
    } catch {
      setError("Impossible de joindre l'API backend pour le moment.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSessionAndStats() {
    try {
      const healthData = await apiRequest("/api/health");
      setHealth(healthData);
      if (getStoredToken()) {
        const meData = await apiRequest("/api/users/me");
        setCurrentUser(meData.user);
      }
    } catch {
      // ignore background refresh error
    }
  }

  useEffect(() => {
    loadBackendState();
  }, []);

  const currentTabMeta = TABS.find((tab) => tab.id === activeTab);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-row">
          <div>
            <h1 className="brand">FitHub Campus</h1>
            <p className="topbar-sub">
              Réseau Social Fitness Étudiant — Auth JWT, Profils &amp; Groupes Sportifs
            </p>
          </div>
          <div className="topbar-right">
            <span className="step-pill">step-02/auth-profils-groupes</span>
            <button
              type="button"
              className="user-pill-btn"
              onClick={() => setActiveTab("profile")}
            >
              {currentUser ? (
                <>
                  {currentUser.avatar_url ? (
                    <img
                      src={currentUser.avatar_url}
                      alt={currentUser.username}
                      className="mini-avatar"
                    />
                  ) : (
                    <span className="mini-initials">
                      {currentUser.username.slice(0, 2).toUpperCase()}
                    </span>
                  )}
                  <span>{currentUser.username}</span>
                </>
              ) : (
                <span>Connexion / Inscription</span>
              )}
            </button>
          </div>
        </div>
      </header>

      <nav className="desktop-nav" aria-label="Navigation principale">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "home" && (
        <>
          <div className="grid-cards">
            <section className="card">
              <div className="topbar-row" style={{ marginBottom: "8px" }}>
                <h2 style={{ margin: 0 }}>État des Services Docker</h2>
                <button type="button" className="refresh-btn" onClick={loadBackendState}>
                  Actualiser
                </button>
              </div>
              {loading && <p>Vérification de l&apos;API en cours...</p>}
              {error && <p style={{ color: "#BE123C", fontWeight: 700 }}>{error}</p>}
              {health && (
                <div>
                  <div className="status-row">
                    <span>API Flask (<code>/api/health</code>)</span>
                    <span className={`badge ${health.status === "ok" ? "badge-ok" : "badge-err"}`}>
                      {health.status === "ok" ? "Opérationnel" : "Dégradé"}
                    </span>
                  </div>
                  <div className="status-row">
                    <span>PostgreSQL (16 tables migrées)</span>
                    <span
                      className={`badge ${health.checks?.database === "ok" ? "badge-ok" : "badge-err"}`}
                    >
                      {health.checks?.database === "ok" ? "Connecté" : "Erreur"}
                    </span>
                  </div>
                  <div className="status-row">
                    <span>Redis (Broker temps réel)</span>
                    <span
                      className={`badge ${health.checks?.redis === "ok" ? "badge-ok" : "badge-err"}`}
                    >
                      {health.checks?.redis === "ok" ? "Connecté" : "Erreur"}
                    </span>
                  </div>
                  <div className="status-row">
                    <span>Communauté active</span>
                    <span className="badge badge-soon">
                      {health.stats?.users ?? 0} étudiants • {health.stats?.groups ?? 0} groupes •{" "}
                      {health.stats?.campuses ?? 0} campus
                    </span>
                  </div>
                </div>
              )}
            </section>

            <section className="card">
              <h2>Modules Actifs (Étape 2)</h2>
              <p className="muted-text" style={{ marginTop: 0 }}>
                Authentifiez-vous en JWT, personnalisez votre avatar persistant et rejoignez un club sportif sur votre campus :
              </p>
              <div className="quick-actions">
                <button
                  type="button"
                  className="primary-btn"
                  onClick={() => setActiveTab("groups")}
                >
                  Explorer les Groupes Sportifs
                </button>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => setActiveTab("profile")}
                >
                  {currentUser ? `Mon Profil (${currentUser.username})` : "Se connecter / S'inscrire"}
                </button>
              </div>
              <div className="status-row" style={{ marginTop: "8px" }}>
                <span>Stories &amp; Photos Avant/Après</span>
                <span className="badge badge-soon">Étape 3</span>
              </div>
              <div className="status-row">
                <span>Défis Inter-Campus &amp; Fit-Buddy Live</span>
                <span className="badge badge-soon">Étapes 4–5</span>
              </div>
            </section>
          </div>

          <section className="card">
            <h2>Campus Étudiants Disponibles (PostgreSQL)</h2>
            <div className="campus-list">
              {campuses.map((campus) => (
                <article key={campus.id} className="campus-item">
                  <strong>{campus.name}</strong>
                  <span>
                    {campus.city} • GPS : {campus.latitude.toFixed(4)}, {campus.longitude.toFixed(4)}
                  </span>
                </article>
              ))}
            </div>
          </section>
        </>
      )}

      {activeTab === "groups" && (
        <GroupsView
          user={currentUser}
          campuses={campuses}
          onRequireAuth={() => setActiveTab("profile")}
          onMembershipChanged={refreshSessionAndStats}
        />
      )}

      {activeTab === "profile" && (
        <AuthProfileView
          user={currentUser}
          campuses={campuses}
          onAuthChange={setCurrentUser}
          onDataRefresh={refreshSessionAndStats}
        />
      )}

      {!["home", "groups", "profile"].includes(activeTab) && (
        <section className="card">
          <h2>Module {currentTabMeta?.label}</h2>
          <p>
            Ce module sera développé et testé sur sa propre branche lors de{" "}
            <strong>{currentTabMeta?.step}</strong>, conformément au plan de livraison progressif.
          </p>
        </section>
      )}

      <nav className="bottom-nav" aria-label="Navigation mobile">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`bottom-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
