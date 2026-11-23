import React, { useEffect, useState } from "react";

const TABS = [
  { id: "home", label: "Accueil", step: "Étape 1 (Actif)" },
  { id: "social", label: "Social", step: "Étape 3" },
  { id: "challenges", label: "Défis", step: "Étape 4" },
  { id: "buddy", label: "Fit-Buddy", step: "Étape 5" },
  { id: "map", label: "Carte", step: "Étape 6" }
];

export default function App() {
  const [activeTab, setActiveTab] = useState("home");
  const [health, setHealth] = useState(null);
  const [campuses, setCampuses] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadBackendState() {
    setLoading(true);
    setError("");
    try {
      const [healthRes, campusesRes] = await Promise.all([
        fetch("/api/health"),
        fetch("/api/campuses")
      ]);
      const healthData = await healthRes.json();
      const campusesData = await campusesRes.json();
      setHealth(healthData);
      setCampuses(campusesData.campuses || []);
    } catch (err) {
      setError("Impossible de joindre l'API backend pour le moment.");
    } finally {
      setLoading(false);
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
          <h1 className="brand">FitHub Campus</h1>
          <span className="step-pill">step-01/socle-docker • 4 conteneurs</span>
        </div>
        <p className="topbar-sub">
          Réseau Social Fitness Étudiant — Socle Docker, PostgreSQL, Redis &amp; Interface Mobile-First
        </p>
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

      {activeTab === "home" ? (
        <>
          <div className="grid-cards">
            <section className="card">
              <div className="topbar-row" style={{ marginBottom: "8px" }}>
                <h2 style={{ margin: 0 }}>État des Services Docker</h2>
                <button type="button" className="refresh-btn" onClick={loadBackendState}>
                  Actualiser
                </button>
              </div>
              {loading && <p>Vérification de l'API en cours...</p>}
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
                    <span className={`badge ${health.checks?.database === "ok" ? "badge-ok" : "badge-err"}`}>
                      {health.checks?.database === "ok" ? "Connecté" : "Erreur"}
                    </span>
                  </div>
                  <div className="status-row">
                    <span>Redis (Broker temps réel)</span>
                    <span className={`badge ${health.checks?.redis === "ok" ? "badge-ok" : "badge-err"}`}>
                      {health.checks?.redis === "ok" ? "Connecté" : "Erreur"}
                    </span>
                  </div>
                  <div className="status-row">
                    <span>Données seedées</span>
                    <span className="badge badge-soon">
                      {health.stats?.campuses ?? 0} campus • {health.stats?.badges ?? 0} badges • {health.stats?.places ?? 0} lieux
                    </span>
                  </div>
                </div>
              )}
            </section>

            <section className="card">
              <h2>Prochaines Étapes du MVP</h2>
              <div className="status-row">
                <span>Authentification JWT &amp; Groupes</span>
                <span className="badge badge-soon">Étape 2</span>
              </div>
              <div className="status-row">
                <span>Stories Workouts &amp; Photos Avant/Après</span>
                <span className="badge badge-soon">Étape 3</span>
              </div>
              <div className="status-row">
                <span>Défis Inter-Campus &amp; Podiums</span>
                <span className="badge badge-soon">Étape 4</span>
              </div>
              <div className="status-row">
                <span>Fit-Buddy Temps Réel &amp; Carte OSM</span>
                <span className="badge badge-soon">Étapes 5–6</span>
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
      ) : (
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
