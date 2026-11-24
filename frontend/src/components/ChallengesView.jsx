import React, { useEffect, useState } from "react";
import { apiRequest } from "../api.js";

const SPORTS = [
  "Running",
  "Calisthenics",
  "Cross-Training",
  "Fitness",
  "Musculation",
  "Cyclisme",
  "Natation"
];

const UNITS = ["km", "reps", "min", "séances"];

function medalForRank(rank) {
  if (rank === 1) return "🥇 1er";
  if (rank === 2) return "🥈 2e";
  if (rank === 3) return "🥉 3e";
  return `#${rank}`;
}

export default function ChallengesView({ user, onRequireAuth, onScoreChanged }) {
  const [challenges, setChallenges] = useState([]);
  const [statusFilter, setStatusFilter] = useState("active"); // active | completed | all
  const [sportFilter, setSportFilter] = useState("");
  const [boardMode, setBoardMode] = useState("challenge"); // challenge | global
  const [selectedChallengeId, setSelectedChallengeId] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    sport: "Running",
    target_value: "100",
    unit: "km",
    duration_days: "7",
    description: ""
  });

  const [openPerfId, setOpenPerfId] = useState(null);
  const [perfValue, setPerfValue] = useState("");
  const [perfFile, setPerfFile] = useState(null);

  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function fetchChallenges(st = statusFilter, sp = sportFilter) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (st) params.set("status", st);
      if (sp) params.set("sport", sp);
      const data = await apiRequest(`/api/challenges?${params.toString()}`);
      const list = data.challenges || [];
      setChallenges(list);

      if (list.length > 0) {
        const stillExists = list.some((c) => c.id === selectedChallengeId);
        const nextId = stillExists ? selectedChallengeId : list[0].id;
        setSelectedChallengeId(nextId);
      }
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function fetchLeaderboard(mode = boardMode, chId = selectedChallengeId) {
    try {
      if (mode === "global" || !chId) {
        const data = await apiRequest("/api/challenges/leaderboard/global");
        setLeaderboard({ mode: "global", ...data });
      } else {
        const data = await apiRequest(`/api/challenges/${chId}/leaderboard`);
        setLeaderboard({ mode: "challenge", ...data });
      }
    } catch {
      // ignore transient fetch errors
    }
  }

  useEffect(() => {
    fetchChallenges(statusFilter, sportFilter);
  }, [statusFilter, sportFilter, user?.id]);

  useEffect(() => {
    fetchLeaderboard(boardMode, selectedChallengeId);
  }, [boardMode, selectedChallengeId, user?.id]);

  async function handleCreateChallenge(e) {
    e.preventDefault();
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const data = await apiRequest("/api/challenges", {
        method: "POST",
        body: {
          title: createForm.title,
          sport: createForm.sport,
          target_value: Number(createForm.target_value),
          unit: createForm.unit,
          duration_days: Number(createForm.duration_days),
          description: createForm.description
        }
      });
      setShowCreate(false);
      setCreateForm({
        title: "",
        sport: "Running",
        target_value: "100",
        unit: "km",
        duration_days: "7",
        description: ""
      });
      setBoardMode("challenge");
      setSelectedChallengeId(data.challenge.id);
      setFeedback({ type: "ok", text: `Défi « ${data.challenge.title} » lancé (+15 XP) !` });
      await fetchChallenges();
      await fetchLeaderboard("challenge", data.challenge.id);
      onScoreChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleJoinChallenge(chId) {
    if (!user) {
      onRequireAuth();
      return;
    }
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      await apiRequest(`/api/challenges/${chId}/join`, { method: "POST" });
      setFeedback({ type: "ok", text: "Inscription validée pour votre campus (+10 XP) !" });
      await fetchChallenges();
      if (selectedChallengeId === chId || boardMode === "global") {
        await fetchLeaderboard(boardMode, chId);
      }
      onScoreChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitPerformance(e, challenge) {
    e.preventDefault();
    if (!perfValue) return;
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      let data;
      if (perfFile) {
        const fd = new FormData();
        fd.append("value", perfValue);
        fd.append("proof_image", perfFile);
        data = await apiRequest(`/api/challenges/${challenge.id}/performances`, {
          method: "POST",
          body: fd,
          isFormData: true
        });
      } else {
        data = await apiRequest(`/api/challenges/${challenge.id}/performances`, {
          method: "POST",
          body: { value: Number(perfValue) }
        });
      }
      setOpenPerfId(null);
      setPerfValue("");
      setPerfFile(null);
      setBoardMode("challenge");
      setSelectedChallengeId(challenge.id);
      setLeaderboard({ mode: "challenge", ...data });
      setFeedback({
        type: "ok",
        text: `Performance ajoutée au cumul de votre campus (+20 XP) !`
      });
      await fetchChallenges();
      onScoreChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteChallenge(chId) {
    try {
      await apiRequest(`/api/challenges/${chId}`, { method: "DELETE" });
      setFeedback({ type: "ok", text: "Défi supprimé." });
      await fetchChallenges();
      onScoreChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  const campusRows = leaderboard?.campus_leaderboard || [];
  const indivRows = leaderboard?.individual_leaderboard || [];
  const top3Campuses = campusRows.slice(0, 3);
  const unitSuffix =
    leaderboard?.mode === "global"
      ? "XP"
      : leaderboard?.challenge?.unit || "pts";

  return (
    <div>
      {/* SECTION PODIUMS & CLASSEMENTS */}
      <section className="card" style={{ marginBottom: "14px" }}>
        <div className="topbar-row" style={{ marginBottom: "10px" }}>
          <div>
            <h2 style={{ margin: 0 }}>
              {leaderboard?.mode === "global"
                ? "Podium Général Inter-Campus (XP Cumulés)"
                : `Podium du Défi : ${leaderboard?.challenge?.title || "Sélectionnez un défi"}`}
            </h2>
            {user && leaderboard && (
              <p className="muted-text" style={{ margin: "3px 0 0" }}>
                Mon Campus :{" "}
                <strong>
                  {leaderboard.my_campus_rank ? `#${leaderboard.my_campus_rank}` : "—"}
                </strong>{" "}
                • Mon Rang Personnel :{" "}
                <strong>
                  {leaderboard.my_rank ? `#${leaderboard.my_rank}` : "Non inscrit"}
                </strong>
              </p>
            )}
          </div>
          <div className="quick-actions">
            <button
              type="button"
              className={`nav-btn ${boardMode === "challenge" ? "active" : ""}`}
              onClick={() => setBoardMode("challenge")}
            >
              Classement par Défi
            </button>
            <button
              type="button"
              className={`nav-btn ${boardMode === "global" ? "active" : ""}`}
              onClick={() => setBoardMode("global")}
            >
              Classement Général
            </button>
          </div>
        </div>

        {/* TOP 3 PODIUM VISUEL DES CAMPUS */}
        {top3Campuses.length > 0 && (
          <div className="podium-grid">
            {top3Campuses.map((c) => {
              const val = leaderboard?.mode === "global" ? c.total_xp : c.total_score;
              return (
                <div
                  key={c.campus_id}
                  className={`podium-card rank-${c.rank} ${c.is_my_campus ? "my-highlight" : ""}`}
                >
                  <span className="podium-medal">{medalForRank(c.rank)}</span>
                  <strong>{c.campus_name}</strong>
                  <span className="podium-score">
                    {val} {unitSuffix}
                  </span>
                  <span className="muted-text" style={{ fontSize: "11.5px" }}>
                    {leaderboard?.mode === "global"
                      ? `${c.students_count} étudiant(s)`
                      : `${c.participants_count} participant(s)`}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* TABLEAUX DÉTAILLÉS CAMPUS + INDIVIDUEL */}
        <div className="grid-cards" style={{ marginBottom: 0, marginTop: "12px" }}>
          <div className="lb-panel">
            <h3>Classement Complet des Écoles / Campus</h3>
            {campusRows.map((c) => {
              const val = leaderboard?.mode === "global" ? c.total_xp : c.total_score;
              return (
                <div
                  key={c.campus_id}
                  className={`lb-row ${c.is_my_campus ? "lb-me" : ""}`}
                >
                  <div className="lb-left">
                    <span className="lb-rank">{medalForRank(c.rank)}</span>
                    <div>
                      <strong>
                        {c.campus_name} {c.is_my_campus && <em>(Mon campus)</em>}
                      </strong>
                      <span className="lb-sub">
                        {c.gap_to_leader > 0
                          ? `À ${c.gap_to_leader} ${unitSuffix} du leader`
                          : "Leader actuel"}
                      </span>
                    </div>
                  </div>
                  <strong className="lb-val">
                    {val} {unitSuffix}
                  </strong>
                </div>
              );
            })}
          </div>

          <div className="lb-panel">
            <h3>Classement Individuel des Étudiants</h3>
            {indivRows.length === 0 ? (
              <p className="muted-text">Aucun participant enregistré pour le moment.</p>
            ) : (
              indivRows.slice(0, 8).map((u) => {
                const val = leaderboard?.mode === "global" ? u.xp_points : u.score;
                return (
                  <div key={u.user_id} className={`lb-row ${u.is_me ? "lb-me" : ""}`}>
                    <div className="lb-left">
                      <span className="lb-rank">{medalForRank(u.rank)}</span>
                      <div>
                        <strong>
                          {u.username} {u.is_me && <em>(Moi)</em>}
                        </strong>
                        <span className="lb-sub">
                          {u.campus_name}
                          {u.proof_media_url ? " • Preuve photo vérifiée" : ""}
                        </span>
                      </div>
                    </div>
                    <strong className="lb-val">
                      {val} {unitSuffix}
                    </strong>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </section>

      {/* BARRE D'ACTIONS & FILTRES DES DÉFIS */}
      <section className="card" style={{ marginBottom: "14px" }}>
        <div className="topbar-row">
          <div className="quick-actions">
            {[
              { id: "active", label: "Défis actifs" },
              { id: "completed", label: "Défis terminés" },
              { id: "all", label: "Tous" }
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                className={`nav-btn ${statusFilter === f.id ? "active" : ""}`}
                onClick={() => setStatusFilter(f.id)}
              >
                {f.label}
              </button>
            ))}

            <select
              className="campus-select-inline"
              value={sportFilter}
              onChange={(e) => setSportFilter(e.target.value)}
            >
              <option value="">Toutes disciplines</option>
              {SPORTS.map((sp) => (
                <option key={sp} value={sp}>
                  {sp}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="primary-btn"
            onClick={() => (user ? setShowCreate(!showCreate) : onRequireAuth())}
          >
            {showCreate ? "Fermer" : "+ Lancer un défi"}
          </button>
        </div>

        {feedback.text && (
          <div
            className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}
            style={{ marginTop: "10px", marginBottom: 0 }}
          >
            {feedback.text}
          </div>
        )}

        {showCreate && user && (
          <form className="form-stack create-panel" onSubmit={handleCreateChallenge}>
            <h3 style={{ margin: 0, color: "#1E2E5C", fontSize: "15px" }}>
              Créer un Défi Sportif Inter-Campus (+15 XP)
            </h3>
            <div className="form-row-2">
              <label className="field">
                <span>Titre du défi</span>
                <input
                  type="text"
                  required
                  minLength={3}
                  placeholder="Ex : 200 km Running Inter-Campus"
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Discipline</span>
                <select
                  value={createForm.sport}
                  onChange={(e) => setCreateForm({ ...createForm, sport: e.target.value })}
                >
                  {SPORTS.map((sp) => (
                    <option key={sp} value={sp}>
                      {sp}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="metrics-inputs">
              <label className="field">
                <span>Objectif collectif</span>
                <input
                  type="number"
                  min={1}
                  step="0.5"
                  required
                  value={createForm.target_value}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, target_value: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Unité</span>
                <select
                  value={createForm.unit}
                  onChange={(e) => setCreateForm({ ...createForm, unit: e.target.value })}
                >
                  {UNITS.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Durée (jours)</span>
                <input
                  type="number"
                  min={1}
                  max={90}
                  required
                  value={createForm.duration_days}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, duration_days: e.target.value })
                  }
                />
              </label>
            </div>
            <label className="field">
              <span>Règles &amp; description du défi</span>
              <textarea
                rows={2}
                placeholder="Expliquez comment comptabiliser les points pour chaque campus..."
                value={createForm.description}
                onChange={(e) =>
                  setCreateForm({ ...createForm, description: e.target.value })
                }
              />
            </label>
            <button type="submit" className="primary-btn" disabled={busy}>
              {busy ? "Création..." : "Publier le défi inter-campus"}
            </button>
          </form>
        )}
      </section>

      {/* CARTES DES DÉFIS */}
      {loading ? (
        <div className="card">Chargement des défis inter-campus...</div>
      ) : challenges.length === 0 ? (
        <div className="card">Aucun défi pour ce filtre.</div>
      ) : (
        <div className="grid-cards">
          {challenges.map((ch) => {
            const isSelected =
              boardMode === "challenge" && selectedChallengeId === ch.id;
            const isCreator = user && user.id === ch.created_by;
            return (
              <article
                key={ch.id}
                className={`card challenge-card ${isSelected ? "selected-challenge" : ""}`}
              >
                <div>
                  <div className="topbar-row">
                    <div className="quick-actions">
                      <span className="badge badge-soon">{ch.sport}</span>
                      <span
                        className={`badge ${ch.is_active ? "badge-ok" : "badge-err"}`}
                      >
                        {ch.is_active ? "Actif" : "Terminé"}
                      </span>
                    </div>
                    {ch.top_campus_name && (
                      <span className="muted-text" style={{ fontSize: "12px" }}>
                        🥇 {ch.top_campus_name}
                      </span>
                    )}
                  </div>

                  <h3 className="group-title">{ch.title}</h3>
                  <p className="group-desc">{ch.description}</p>

                  <div className="ch-progress-meta">
                    <span>
                      Cumul inter-campus :{" "}
                      <strong>
                        {ch.total_score} / {ch.target_value} {ch.unit}
                      </strong>
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

                <div>
                  <div className="group-footer" style={{ marginTop: "12px" }}>
                    <span className="muted-text" style={{ fontSize: "12px" }}>
                      <strong>{ch.participants_count}</strong> inscrit(s)
                      {ch.is_joined ? ` • Mon score : ${ch.my_score} ${ch.unit}` : ""}
                    </span>

                    <div className="group-btns">
                      <button
                        type="button"
                        className="outline-btn"
                        onClick={() => {
                          setBoardMode("challenge");
                          setSelectedChallengeId(ch.id);
                        }}
                      >
                        Podium
                      </button>

                      {ch.is_active && !ch.is_joined && (
                        <button
                          type="button"
                          className="primary-btn"
                          disabled={busy}
                          onClick={() => handleJoinChallenge(ch.id)}
                        >
                          Rejoindre
                        </button>
                      )}

                      {ch.is_active && ch.is_joined && (
                        <button
                          type="button"
                          className="secondary-btn"
                          onClick={() =>
                            setOpenPerfId(openPerfId === ch.id ? null : ch.id)
                          }
                        >
                          {openPerfId === ch.id ? "Fermer" : "+ Performance"}
                        </button>
                      )}

                      {isCreator && (
                        <button
                          type="button"
                          className="danger-btn"
                          onClick={() => handleDeleteChallenge(ch.id)}
                        >
                          Suppr.
                        </button>
                      )}
                    </div>
                  </div>

                  {openPerfId === ch.id && ch.is_active && (
                    <form
                      className="perf-drawer"
                      onSubmit={(e) => handleSubmitPerformance(e, ch)}
                    >
                      <div className="form-row-2">
                        <label className="field">
                          <span>Performance à ajouter ({ch.unit})</span>
                          <input
                            type="number"
                            step="0.1"
                            min="0.1"
                            required
                            placeholder={`Ex : 5 (${ch.unit})`}
                            value={perfValue}
                            onChange={(e) => setPerfValue(e.target.value)}
                          />
                        </label>
                        <label className="field">
                          <span>Preuve photo (optionnelle)</span>
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            onChange={(e) => setPerfFile(e.target.files?.[0] || null)}
                          />
                        </label>
                      </div>
                      <button
                        type="submit"
                        className="primary-btn"
                        style={{ marginTop: "8px", width: "100%" }}
                        disabled={busy}
                      >
                        {busy ? "Enregistrement..." : `Valider ma performance (+20 XP)`}
                      </button>
                    </form>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
