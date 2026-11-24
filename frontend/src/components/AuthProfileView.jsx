import React, { useEffect, useState } from "react";
import { apiRequest, setStoredToken } from "../api.js";

const DEMO_ACCOUNTS = [
  { label: "Ina (Lyon)", email: "ina.lyon@fithub.fr", password: "Password123!" },
  { label: "Lucas (Paris)", email: "lucas.paris@fithub.fr", password: "Password123!" },
  { label: "Sarah (Bordeaux)", email: "sarah.bordeaux@fithub.fr", password: "Password123!" },
  { label: "Mehdi (Lille)", email: "mehdi.lille@fithub.fr", password: "Password123!" }
];

const LEVELS = ["Débutant", "Intermédiaire", "Avancé", "Compétiteur"];

export default function AuthProfileView({ user, campuses, onAuthChange, onDataRefresh }) {
  const [mode, setMode] = useState("login");
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [registerForm, setRegisterForm] = useState({
    email: "",
    username: "",
    password: "",
    campus_id: campuses[0]?.id || 1,
    favorite_sports: "Running, Fitness",
    level: "Intermédiaire",
    bio: ""
  });

  const [profileForm, setProfileForm] = useState({
    username: "",
    campus_id: 1,
    favorite_sports: "",
    level: "Intermédiaire",
    bio: ""
  });

  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (campuses.length > 0 && !registerForm.campus_id) {
      setRegisterForm((prev) => ({ ...prev, campus_id: campuses[0].id }));
    }
  }, [campuses]);

  useEffect(() => {
    if (user) {
      setProfileForm({
        username: user.username || "",
        campus_id: user.campus_id || campuses[0]?.id || 1,
        favorite_sports: user.favorite_sports || "",
        level: user.level || "Intermédiaire",
        bio: user.bio || ""
      });
    }
  }, [user, campuses]);

  async function handleLogin(e, customCredentials = null) {
    if (e) e.preventDefault();
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const creds = customCredentials || loginForm;
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: creds
      });
      setStoredToken(data.access_token);
      onAuthChange(data.user);
      onDataRefresh();
      setFeedback({ type: "ok", text: `Bienvenue ${data.user.username} !` });
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const data = await apiRequest("/api/auth/register", {
        method: "POST",
        body: {
          ...registerForm,
          campus_id: Number(registerForm.campus_id)
        }
      });
      setStoredToken(data.access_token);
      onAuthChange(data.user);
      onDataRefresh();
      setFeedback({ type: "ok", text: "Compte étudiant créé et connecté !" });
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleProfileUpdate(e) {
    e.preventDefault();
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const data = await apiRequest("/api/users/me", {
        method: "PUT",
        body: {
          ...profileForm,
          campus_id: Number(profileForm.campus_id)
        }
      });
      onAuthChange(data.user);
      onDataRefresh();
      setFeedback({ type: "ok", text: "Profil sportif mis à jour avec succès." });
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleAvatarChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const formData = new FormData();
      formData.append("avatar", file);
      const data = await apiRequest("/api/users/me/avatar", {
        method: "POST",
        body: formData,
        isFormData: true
      });
      onAuthChange(data.user);
      setFeedback({ type: "ok", text: "Nouvel avatar enregistré sur le volume persistant !" });
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  function handleLogout() {
    setStoredToken("");
    onAuthChange(null);
    setFeedback({ type: "ok", text: "Session déconnectée." });
  }

  if (!user) {
    return (
      <div className="grid-cards">
        <section className="card">
          <div className="seg-tabs">
            <button
              type="button"
              className={`seg-btn ${mode === "login" ? "active" : ""}`}
              onClick={() => {
                setMode("login");
                setFeedback({ type: "", text: "" });
              }}
            >
              Connexion
            </button>
            <button
              type="button"
              className={`seg-btn ${mode === "register" ? "active" : ""}`}
              onClick={() => {
                setMode("register");
                setFeedback({ type: "", text: "" });
              }}
            >
              Inscription Étudiant
            </button>
          </div>

          {feedback.text && (
            <div className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}>
              {feedback.text}
            </div>
          )}

          {mode === "login" ? (
            <form className="form-stack" onSubmit={handleLogin}>
              <label className="field">
                <span>Email universitaire / campus</span>
                <input
                  type="email"
                  required
                  placeholder="prenom.nom@fithub.fr"
                  value={loginForm.email}
                  onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Mot de passe</span>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                />
              </label>
              <button type="submit" className="primary-btn" disabled={busy}>
                {busy ? "Connexion..." : "Se connecter (JWT)"}
              </button>
            </form>
          ) : (
            <form className="form-stack" onSubmit={handleRegister}>
              <label className="field">
                <span>Pseudo sportif</span>
                <input
                  type="text"
                  required
                  minLength={2}
                  placeholder="Ex : AlexRun_Lyon"
                  value={registerForm.username}
                  onChange={(e) => setRegisterForm({ ...registerForm, username: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Email étudiant</span>
                <input
                  type="email"
                  required
                  placeholder="alex@campus.fr"
                  value={registerForm.email}
                  onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Mot de passe (min. 8 caractères, haché bcrypt)</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Au moins 8 caractères"
                  value={registerForm.password}
                  onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Campus de rattachement</span>
                <select
                  value={registerForm.campus_id}
                  onChange={(e) =>
                    setRegisterForm({ ...registerForm, campus_id: Number(e.target.value) })
                  }
                >
                  {campuses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.city})
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-row-2">
                <label className="field">
                  <span>Sports favoris</span>
                  <input
                    type="text"
                    value={registerForm.favorite_sports}
                    onChange={(e) =>
                      setRegisterForm({ ...registerForm, favorite_sports: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  <span>Niveau</span>
                  <select
                    value={registerForm.level}
                    onChange={(e) => setRegisterForm({ ...registerForm, level: e.target.value })}
                  >
                    {LEVELS.map((lvl) => (
                      <option key={lvl} value={lvl}>
                        {lvl}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button type="submit" className="primary-btn" disabled={busy}>
                {busy ? "Création..." : "Créer mon compte étudiant"}
              </button>
            </form>
          )}
        </section>

        <section className="card">
          <h2>Comptes Étudiants de Démonstration</h2>
          <p className="muted-text">
            Testez immédiatement l&apos;authentification JWT et l&apos;adhésion aux groupes avec un des 3 comptes pré-seedés :
          </p>
          <div className="demo-list">
            {DEMO_ACCOUNTS.map((acc) => (
              <div key={acc.email} className="demo-item">
                <div>
                  <strong>{acc.label}</strong>
                  <span>{acc.email}</span>
                </div>
                <button
                  type="button"
                  className="secondary-btn"
                  disabled={busy}
                  onClick={() => handleLogin(null, { email: acc.email, password: acc.password })}
                >
                  Connexion 1-clic
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>
    );
  }

  const initials = (user.username || "FH").slice(0, 2).toUpperCase();
  const stats = user.stats || {
    xp_points: user.xp_points || 0,
    workouts_count: 0,
    groups_count: 0,
    badges_count: 0
  };

  return (
    <div className="grid-cards">
      <section className="card">
        <div className="profile-header">
          <div className="avatar-wrap">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt={user.username} className="avatar-img" />
            ) : (
              <div className="avatar-fallback">{initials}</div>
            )}
          </div>
          <div className="profile-meta">
            <h2>{user.username}</h2>
            <p className="muted-text">
              {user.campus_name} • Niveau <strong>{user.level}</strong>
            </p>
            <div className="profile-actions">
              <label className="upload-label">
                Changer d&apos;avatar
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleAvatarChange}
                  disabled={busy}
                  hidden
                />
              </label>
              <button type="button" className="outline-btn" onClick={handleLogout}>
                Déconnexion
              </button>
            </div>
          </div>
        </div>

        <div className="stats-strip">
          <div className="stat-box">
            <strong>{stats.xp_points}</strong>
            <span>Points XP</span>
          </div>
          <div className="stat-box">
            <strong>{stats.groups_count}</strong>
            <span>Groupes</span>
          </div>
          <div className="stat-box">
            <strong>{stats.workouts_count}</strong>
            <span>Séances</span>
          </div>
          <div className="stat-box">
            <strong>{stats.badges_count}</strong>
            <span>Badges</span>
          </div>
        </div>

        {user.bio && <p className="bio-quote">« {user.bio} »</p>}
      </section>

      <section className="card">
        <h2>Éditer mon Profil Sportif</h2>
        {feedback.text && (
          <div className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}>
            {feedback.text}
          </div>
        )}
        <form className="form-stack" onSubmit={handleProfileUpdate}>
          <label className="field">
            <span>Pseudo</span>
            <input
              type="text"
              required
              minLength={2}
              value={profileForm.username}
              onChange={(e) => setProfileForm({ ...profileForm, username: e.target.value })}
            />
          </label>
          <label className="field">
            <span>Campus</span>
            <select
              value={profileForm.campus_id}
              onChange={(e) =>
                setProfileForm({ ...profileForm, campus_id: Number(e.target.value) })
              }
            >
              {campuses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.city})
                </option>
              ))}
            </select>
          </label>
          <div className="form-row-2">
            <label className="field">
              <span>Sports pratiqués</span>
              <input
                type="text"
                value={profileForm.favorite_sports}
                onChange={(e) =>
                  setProfileForm({ ...profileForm, favorite_sports: e.target.value })
                }
              />
            </label>
            <label className="field">
              <span>Niveau</span>
              <select
                value={profileForm.level}
                onChange={(e) => setProfileForm({ ...profileForm, level: e.target.value })}
              >
                {LEVELS.map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {lvl}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="field">
            <span>Bio / Objectif personnel</span>
            <textarea
              rows={3}
              placeholder="Présente tes objectifs sportifs sur le campus..."
              value={profileForm.bio}
              onChange={(e) => setProfileForm({ ...profileForm, bio: e.target.value })}
            />
          </label>
          <button type="submit" className="primary-btn" disabled={busy}>
            {busy ? "Enregistrement..." : "Enregistrer mon profil"}
          </button>
        </form>
      </section>
    </div>
  );
}
