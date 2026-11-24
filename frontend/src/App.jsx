import React, { useEffect, useState } from "react";
import { apiRequest, getStoredToken, setStoredToken } from "./api.js";
import AuthProfileView from "./components/AuthProfileView.jsx";
import ChallengesView from "./components/ChallengesView.jsx";
import FitBuddyView from "./components/FitBuddyView.jsx";
import GamificationView from "./components/GamificationView.jsx";
import GroupsView from "./components/GroupsView.jsx";
import MapEventsView from "./components/MapEventsView.jsx";
import SocialFeedView from "./components/SocialFeedView.jsx";

const TABS = [
  { id: "home", label: "Accueil" },
  { id: "social", label: "Fil Social" },
  { id: "challenges", label: "Défis" },
  { id: "buddy", label: "Fit-Buddy" },
  { id: "map", label: "Carte & Spots" },
  { id: "groups", label: "Clubs" },
  { id: "badges", label: "Récompenses" },
  { id: "profile", label: "Mon Espace" }
];

const QUICK_DEMO_USERS = [
  { label: "Ina • Lyon", email: "ina.lyon@fithub.fr", password: "Password123!" },
  { label: "Lucas • Paris", email: "lucas.paris@fithub.fr", password: "Password123!" },
  { label: "Sarah • Bordeaux", email: "sarah.bordeaux@fithub.fr", password: "Password123!" },
  { label: "Mehdi • Lille", email: "mehdi.lille@fithub.fr", password: "Password123!" }
];

function medalIcon(rank) {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `#${rank}`;
}

export default function App() {
  const [activeTab, setActiveTab] = useState("home");
  const [campuses, setCampuses] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [homeData, setHomeData] = useState({
    campusLeaderboard: [],
    activeChallenges: [],
    recentPosts: [],
    featuredPlaces: []
  });
  const [loading, setLoading] = useState(true);
  const [quickAuthBusy, setQuickAuthBusy] = useState(false);

  async function loadHomeAndSession() {
    setLoading(true);
    try {
      const [campusesData, lbData, chData, postsData, placesData] = await Promise.all([
        apiRequest("/api/campuses"),
        apiRequest("/api/challenges/leaderboard/global").catch(() => ({})),
        apiRequest("/api/challenges?status=active").catch(() => ({})),
        apiRequest("/api/social/posts").catch(() => ({})),
        apiRequest("/api/places").catch(() => ({}))
      ]);

      setCampuses(campusesData.campuses || []);
      setHomeData({
        campusLeaderboard: lbData.campus_leaderboard || [],
        activeChallenges: (chData.challenges || []).slice(0, 2),
        recentPosts: (postsData.posts || []).slice(0, 2),
        featuredPlaces: (placesData.places || []).slice(0, 3)
      });

      if (getStoredToken()) {
        try {
          const meData = await apiRequest("/api/users/me");
          setCurrentUser(meData.user);
        } catch {
          setStoredToken("");
          setCurrentUser(null);
        }
      }
    } finally {
      setLoading(false);
    }
  }

  async function refreshSessionAndStats() {
    try {
      const [lbData, chData, postsData, placesData] = await Promise.all([
        apiRequest("/api/challenges/leaderboard/global").catch(() => ({})),
        apiRequest("/api/challenges?status=active").catch(() => ({})),
        apiRequest("/api/social/posts").catch(() => ({})),
        apiRequest("/api/places").catch(() => ({}))
      ]);
      setHomeData({
        campusLeaderboard: lbData.campus_leaderboard || [],
        activeChallenges: (chData.challenges || []).slice(0, 2),
        recentPosts: (postsData.posts || []).slice(0, 2),
        featuredPlaces: (placesData.places || []).slice(0, 3)
      });
      if (getStoredToken()) {
        const meData = await apiRequest("/api/users/me");
        setCurrentUser(meData.user);
      }
    } catch {
      // ignore transient refresh issue
    }
  }

  async function handleQuickDemoLogin(acc) {
    setQuickAuthBusy(true);
    try {
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: { email: acc.email, password: acc.password }
      });
      setStoredToken(data.access_token);
      setCurrentUser(data.user);
      await refreshSessionAndStats();
    } finally {
      setQuickAuthBusy(false);
    }
  }

  useEffect(() => {
    loadHomeAndSession();
  }, []);

  const userStats = currentUser?.stats || {
    total_xp: currentUser?.xp_points || 0,
    workouts_count: 0,
    badges_count: currentUser?.badges?.length || 0,
    groups_count: 0
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-row">
          <div
            className="brand-block"
            role="button"
            tabIndex={0}
            onClick={() => setActiveTab("home")}
            onKeyDown={(e) => e.key === "Enter" && setActiveTab("home")}
          >
            <span className="brand-logo">FH</span>
            <div>
              <h1 className="brand">FitHub Campus</h1>
              <p className="topbar-sub">
                Le réseau social sportif des étudiants &amp; compétitions inter-campus
              </p>
            </div>
          </div>

          <div className="topbar-right">
            {currentUser ? (
              <>
                <span className="campus-header-pill">
                  📍 {currentUser.campus_city || currentUser.campus_name}
                </span>
                <button
                  type="button"
                  className="xp-header-pill"
                  onClick={() => setActiveTab("badges")}
                  title="Voir mes récompenses et badges"
                >
                  ⚡ {userStats.total_xp ?? currentUser.xp_points} XP
                </button>
                <button
                  type="button"
                  className="user-pill-btn"
                  onClick={() => setActiveTab("profile")}
                >
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
                </button>
              </>
            ) : (
              <button
                type="button"
                className="user-pill-btn"
                onClick={() => setActiveTab("profile")}
              >
                <span>Connexion / Inscription</span>
              </button>
            )}
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
        <div className="home-stack">
          {/* BANNIÈRE D'ACCUEIL PERSONNALISÉE */}
          <section className="hero-banner-card">
            <div className="hero-banner-content">
              {currentUser ? (
                <>
                  <span className="hero-kicker">
                    {currentUser.campus_name} • Niveau {currentUser.level}
                  </span>
                  <h2>
                    Bonjour {currentUser.username} 👋 Prêt(e) pour ta séance du jour ?
                  </h2>
                  <p>
                    Partage tes entraînements, cumule des points pour ton école et retrouve tes partenaires sur le campus.
                  </p>
                  <div className="quick-actions" style={{ marginTop: "14px" }}>
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={() => setActiveTab("social")}
                    >
                      + Publier une séance
                    </button>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => setActiveTab("challenges")}
                    >
                      Relever un défi
                    </button>
                    <button
                      type="button"
                      className="outline-btn"
                      onClick={() => setActiveTab("map")}
                    >
                      Carte des spots &amp; RDV
                    </button>
                    <button
                      type="button"
                      className="outline-btn"
                      onClick={() => setActiveTab("buddy")}
                    >
                      Mon Fit-Buddy
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <span className="hero-kicker">Communauté Sportive Étudiante</span>
                  <h2>Bougez entre étudiants. Faites gagner votre campus.</h2>
                  <p>
                    Rejoignez les clubs sportifs de votre école, trouvez un binôme Fit-Buddy compatible et participez aux défis inter-campus à Lyon, Paris, Bordeaux et Lille.
                  </p>
                  <div className="quick-actions" style={{ marginTop: "14px" }}>
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={() => setActiveTab("profile")}
                    >
                      Créer mon compte / Me connecter
                    </button>
                    <button
                      type="button"
                      className="outline-btn"
                      onClick={() => setActiveTab("challenges")}
                    >
                      Voir les défis inter-campus
                    </button>
                    <button
                      type="button"
                      className="outline-btn"
                      onClick={() => setActiveTab("map")}
                    >
                      Explorer la carte des spots
                    </button>
                  </div>
                  <div className="demo-quick-strip">
                    <span>Connexion rapide démo :</span>
                    {QUICK_DEMO_USERS.map((acc) => (
                      <button
                        key={acc.email}
                        type="button"
                        className="chip-filter-btn"
                        disabled={quickAuthBusy}
                        onClick={() => handleQuickDemoLogin(acc)}
                      >
                        {acc.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {currentUser && (
              <div className="hero-stats-grid">
                <div className="hero-stat-tile" onClick={() => setActiveTab("badges")}>
                  <strong>{userStats.total_xp ?? currentUser.xp_points}</strong>
                  <span>Points XP</span>
                </div>
                <div className="hero-stat-tile" onClick={() => setActiveTab("social")}>
                  <strong>{userStats.workouts_count}</strong>
                  <span>Séances</span>
                </div>
                <div className="hero-stat-tile" onClick={() => setActiveTab("badges")}>
                  <strong>{userStats.badges_count}</strong>
                  <span>Badges</span>
                </div>
                <div className="hero-stat-tile" onClick={() => setActiveTab("groups")}>
                  <strong>{userStats.groups_count}</strong>
                  <span>Clubs</span>
                </div>
              </div>
            )}
          </section>

          {/* PODIUM INTER-CAMPUS & DÉFIS DE LA SEMAINE */}
          <div className="grid-cards">
            <section className="card">
              <div className="topbar-row" style={{ marginBottom: "10px" }}>
                <div>
                  <h2 style={{ margin: 0 }}>Classement Inter-Campus en Direct</h2>
                  <p className="muted-text" style={{ margin: "2px 0 0" }}>
                    Chaque séance et chaque défi rapportent des points à votre campus
                  </p>
                </div>
                <button
                  type="button"
                  className="outline-btn"
                  onClick={() => setActiveTab("challenges")}
                >
                  Podiums complets →
                </button>
              </div>

              {loading ? (
                <p className="muted-text">Chargement du classement...</p>
              ) : (
                <div className="home-list-stack">
                  {homeData.campusLeaderboard.map((c) => (
                    <div
                      key={c.campus_id}
                      className={`lb-row ${
                        currentUser?.campus_id === c.campus_id ? "lb-me" : ""
                      }`}
                    >
                      <div className="lb-left">
                        <span className="lb-rank">{medalIcon(c.rank)}</span>
                        <div>
                          <strong>
                            {c.campus_name}{" "}
                            {currentUser?.campus_id === c.campus_id && (
                              <em>(Mon campus)</em>
                            )}
                          </strong>
                          <span className="lb-sub">
                            {c.city} • {c.students_count} étudiant
                            {c.students_count > 1 ? "s" : ""} actif
                            {c.students_count > 1 ? "s" : ""}
                          </span>
                        </div>
                      </div>
                      <strong className="lb-val">{c.total_xp} XP</strong>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card">
              <div className="topbar-row" style={{ marginBottom: "10px" }}>
                <div>
                  <h2 style={{ margin: 0 }}>Défis Sportifs à la Une</h2>
                  <p className="muted-text" style={{ margin: "2px 0 0" }}>
                    Mobilisez votre promotion autour d&apos;un objectif commun
                  </p>
                </div>
                <button
                  type="button"
                  className="outline-btn"
                  onClick={() => setActiveTab("challenges")}
                >
                  Tous les défis →
                </button>
              </div>

              {homeData.activeChallenges.length === 0 ? (
                <p className="muted-text">Aucun défi en cours actuellement.</p>
              ) : (
                <div className="home-list-stack">
                  {homeData.activeChallenges.map((ch) => (
                    <div key={ch.id} className="home-challenge-item">
                      <div className="topbar-row" style={{ marginBottom: "4px" }}>
                        <span className="badge badge-soon">{ch.sport}</span>
                        {ch.top_campus_name && (
                          <span className="muted-text" style={{ fontSize: "12px" }}>
                            🥇 En tête : <strong>{ch.top_campus_name}</strong>
                          </span>
                        )}
                      </div>
                      <strong className="home-item-title">{ch.title}</strong>
                      <div className="ch-progress-meta" style={{ marginTop: "6px" }}>
                        <span>
                          {ch.total_score} / {ch.target_value} {ch.unit}
                        </span>
                        <strong>{ch.progress_pct} %</strong>
                      </div>
                      <div className="ch-progress-track">
                        <div
                          className="ch-progress-fill"
                          style={{ width: `${ch.progress_pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* DERNIÈRES PUBLICATIONS & SPOTS AUTOUR DES CAMPUS */}
          <div className="grid-cards">
            <section className="card">
              <div className="topbar-row" style={{ marginBottom: "10px" }}>
                <div>
                  <h2 style={{ margin: 0 }}>En Direct de la Communauté</h2>
                  <p className="muted-text" style={{ margin: "2px 0 0" }}>
                    Les dernières séances et progressions partagées par les étudiants
                  </p>
                </div>
                <button
                  type="button"
                  className="outline-btn"
                  onClick={() => setActiveTab("social")}
                >
                  Ouvrir le fil →
                </button>
              </div>

              <div className="home-list-stack">
                {homeData.recentPosts.map((post) => (
                  <div
                    key={post.id}
                    className="home-post-preview"
                    onClick={() => setActiveTab("social")}
                  >
                    <img
                      src={
                        post.kind === "before_after"
                          ? post.after_media_url
                          : post.media_url
                      }
                      alt={post.title}
                      className="home-post-thumb"
                    />
                    <div className="home-post-meta">
                      <div className="topbar-row">
                        <strong>{post.username}</strong>
                        <span className="badge badge-soon">
                          {post.kind === "before_after"
                            ? "Avant / Après"
                            : post.workout?.sport || "Séance"}
                        </span>
                      </div>
                      <span className="home-item-title">{post.title}</span>
                      <span className="muted-text" style={{ fontSize: "12px" }}>
                        {post.campus_name} • 👏 {post.likes_count} • 💬{" "}
                        {post.comments_count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="topbar-row" style={{ marginBottom: "10px" }}>
                <div>
                  <h2 style={{ margin: 0 }}>Salles &amp; Spots Partenaires</h2>
                  <p className="muted-text" style={{ margin: "2px 0 0" }}>
                    Lieux d&apos;entraînement vérifiés autour de vos campus
                  </p>
                </div>
                <button
                  type="button"
                  className="outline-btn"
                  onClick={() => setActiveTab("map")}
                >
                  Voir la carte →
                </button>
              </div>

              <div className="home-list-stack">
                {homeData.featuredPlaces.map((pl) => (
                  <div
                    key={pl.id}
                    className="lb-row"
                    style={{ cursor: "pointer" }}
                    onClick={() => setActiveTab("map")}
                  >
                    <div>
                      <strong>{pl.title}</strong>
                      <span className="lb-sub">
                        {pl.sport} • {pl.address}
                      </span>
                    </div>
                    <span className="badge badge-soon">{pl.campus_city}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === "social" && (
        <SocialFeedView
          user={currentUser}
          campuses={campuses}
          onRequireAuth={() => setActiveTab("profile")}
          onActivityChanged={refreshSessionAndStats}
        />
      )}

      {activeTab === "challenges" && (
        <ChallengesView
          user={currentUser}
          onRequireAuth={() => setActiveTab("profile")}
          onScoreChanged={refreshSessionAndStats}
        />
      )}

      {activeTab === "buddy" && (
        <FitBuddyView
          user={currentUser}
          campuses={campuses}
          onRequireAuth={() => setActiveTab("profile")}
          onActivityChanged={refreshSessionAndStats}
        />
      )}

      {activeTab === "map" && (
        <MapEventsView
          user={currentUser}
          campuses={campuses}
          onRequireAuth={() => setActiveTab("profile")}
          onActivityChanged={refreshSessionAndStats}
        />
      )}

      {activeTab === "badges" && (
        <GamificationView
          user={currentUser}
          onRequireAuth={() => setActiveTab("profile")}
          onActivityChanged={refreshSessionAndStats}
        />
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
          onOpenBadges={() => setActiveTab("badges")}
        />
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
