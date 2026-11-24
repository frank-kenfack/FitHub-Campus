import React, { useEffect, useState } from "react";
import { apiRequest } from "../api.js";

const BADGE_ICONS = {
  first_workout: "⚡",
  five_workouts: "🔥",
  fit_buddy_solidarity: "🤝",
  top_campus: "🏆",
  event_participant: "📍"
};

const BADGE_HINTS = {
  first_workout: "Publiez 1 story workout ou importez 1 activité.",
  five_workouts: "Cumulez 5 séances validées (stories, défis ou imports).",
  fit_buddy_solidarity: "Envoyez un encouragement temps réel à votre Fit-Buddy.",
  top_campus: "Contribuez au score d'un défi où votre campus est Top 3.",
  event_participant: "Confirmez votre présence (RSVP) sur la Carte interactive."
};

const GOOGLE_FIT_PRESETS = [
  {
    id: "gfit_run",
    label: "Google Fit — Course Quais du Rhône (8.6 km • 44 min • 530 kcal)",
    activityType: 8,
    sport: "Running",
    durationMinutes: 44,
    distanceMeters: 8600,
    calories: 530
  },
  {
    id: "gfit_hiit",
    label: "Google Fit — Cross-Training & Gainage (50 min • 470 kcal)",
    activityType: 113,
    sport: "Cross-Training",
    durationMinutes: 50,
    distanceMeters: 0,
    calories: 470
  },
  {
    id: "gfit_bike",
    label: "Google Fit — Vélotaf Campus (14.2 km • 38 min • 390 kcal)",
    activityType: 1,
    sport: "Cyclisme",
    durationMinutes: 38,
    distanceMeters: 14200,
    calories: 390
  }
];

const SAMPLE_GPX_CONTENT = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="FitHubCampus" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Sortie Running Campus Gerland</name>
    <type>Running</type>
    <trkseg>
      <trkpt lat="45.7299" lon="4.8273"><time>2026-11-24T07:30:00Z</time></trkpt>
      <trkpt lat="45.7425" lon="4.8320"><time>2026-11-24T07:40:00Z</time></trkpt>
      <trkpt lat="45.7560" lon="4.8365"><time>2026-11-24T07:52:00Z</time></trkpt>
      <trkpt lat="45.7685" lon="4.8390"><time>2026-11-24T08:05:00Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>`;

export default function GamificationView({
  user,
  onRequireAuth,
  onActivityChanged
}) {
  const [summary, setSummary] = useState(null);
  const [activeChallenges, setActiveChallenges] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(GOOGLE_FIT_PRESETS[0].id);
  const [targetChallengeId, setTargetChallengeId] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [feedback, setFeedback] = useState({ type: "", text: "" });

  async function loadGamification() {
    if (!user) return;
    setLoading(true);
    try {
      const [sumData, chData] = await Promise.all([
        apiRequest("/api/gamification/summary"),
        apiRequest("/api/challenges?status=active")
      ]);
      setSummary(sumData);
      setActiveChallenges(chData.challenges || []);
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadGamification();
  }, [user]);

  if (!user) {
    return (
      <section className="card">
        <h2>Badges, Récompenses XP &amp; Synchronisation Sportive</h2>
        <p className="muted-text">
          Connectez-vous à votre compte étudiant pour visualiser vos badges débloqués, votre palier XP et importer vos séances Google Fit ou GPX.
        </p>
        <button type="button" className="primary-btn" onClick={onRequireAuth}>
          Se connecter / Choisir un compte démo
        </button>
      </section>
    );
  }

  async function handleGoogleFitSync(e) {
    e.preventDefault();
    const preset =
      GOOGLE_FIT_PRESETS.find((p) => p.id === selectedPreset) || GOOGLE_FIT_PRESETS[0];

    setSyncing(true);
    setFeedback({ type: "", text: "" });
    try {
      const endMs = Date.now();
      const startMs = endMs - preset.durationMinutes * 60000;
      const body = {
        source: "google_fit",
        sessions: [
          {
            name: preset.sport,
            sport: preset.sport,
            activityType: preset.activityType,
            startTimeMillis: startMs,
            endTimeMillis: endMs,
            distanceMeters: preset.distanceMeters,
            calories: preset.calories
          }
        ]
      };
      if (targetChallengeId) {
        body.challenge_id = Number(targetChallengeId);
      }

      const res = await apiRequest("/api/gamification/import-activity", {
        method: "POST",
        body
      });
      setSummary(res.summary);

      const chNote =
        res.challenge_updates?.length > 0
          ? ` Défi crédité : +${res.challenge_updates[0].added_score} ${res.challenge_updates[0].unit} sur « ${res.challenge_updates[0].title} ».`
          : "";
      const badgeNote =
        res.newly_unlocked_badges?.length > 0
          ? ` Nouveau(x) badge(s) : ${res.newly_unlocked_badges
              .map((b) => `${b.name} (+${b.xp_reward} XP)`)
              .join(", ")} !`
          : "";

      setFeedback({
        type: "ok",
        text: `Séance Google Fit importée (+${res.xp_gained} XP) !${chNote}${badgeNote}`
      });
      if (onActivityChanged) onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setSyncing(false);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSyncing(true);
    setFeedback({ type: "", text: "" });
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (targetChallengeId) {
        formData.append("challenge_id", String(targetChallengeId));
      }
      const res = await apiRequest("/api/gamification/import-activity", {
        method: "POST",
        body: formData,
        isFormData: true
      });
      setSummary(res.summary);
      const imported = res.imported_workouts?.[0];
      const badgeNote =
        res.newly_unlocked_badges?.length > 0
          ? ` Badge débloqué : ${res.newly_unlocked_badges.map((b) => b.name).join(", ")} !`
          : "";
      setFeedback({
        type: "ok",
        text: `Fichier « ${file.name} » analysé : ${imported?.sport} (${imported?.distance_km} km, ${imported?.duration_minutes} min) — +${res.xp_gained} XP !${badgeNote}`
      });
      if (onActivityChanged) onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setSyncing(false);
      e.target.value = "";
    }
  }

  function handleDownloadSampleGpx() {
    const blob = new Blob([SAMPLE_GPX_CONTENT], { type: "application/gpx+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "trace_campus_lyon.gpx";
    a.click();
    URL.revokeObjectURL(url);
  }

  const prog = summary?.progression;

  return (
    <div className="map-page-stack">
      {feedback.text && (
        <div className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}>
          {feedback.text}
        </div>
      )}

      <div className="grid-cards">
        <section className="card">
          <div className="topbar-row" style={{ marginBottom: "8px" }}>
            <h2 style={{ margin: 0 }}>Progression XP &amp; Récompenses Campus</h2>
            {prog?.current_tier && (
              <span className="tier-pill">
                Niveau {prog.current_tier.level} • {prog.current_tier.name}
              </span>
            )}
          </div>

          {loading || !summary ? (
            <p className="muted-text">Calcul de vos accomplissements...</p>
          ) : (
            <>
              <div className="xp-summary-boxes">
                <div className="stat-box">
                  <strong>{summary.total_xp}</strong>
                  <span>XP Total</span>
                </div>
                <div className="stat-box">
                  <strong>{summary.activity_xp}</strong>
                  <span>XP Séances</span>
                </div>
                <div className="stat-box">
                  <strong>+{summary.badges_xp}</strong>
                  <span>Bonus Badges</span>
                </div>
                <div className="stat-box">
                  <strong>
                    {summary.unlocked_count}/{summary.total_badges}
                  </strong>
                  <span>Badges acquis</span>
                </div>
              </div>

              {prog && (
                <div style={{ marginTop: "14px" }}>
                  <div className="ch-progress-meta">
                    <span>
                      Récompense active : <strong>{prog.current_tier.reward}</strong>
                    </span>
                    <strong>{prog.progress_pct} %</strong>
                  </div>
                  <div className="ch-progress-track" style={{ height: "11px" }}>
                    <div
                      className="ch-progress-fill"
                      style={{ width: `${prog.progress_pct}%` }}
                    />
                  </div>
                  <p className="muted-text" style={{ margin: "6px 0 0" }}>
                    {prog.next_tier
                      ? `Plus que ${prog.xp_to_next} XP pour atteindre « ${prog.next_tier.name} » (${prog.next_tier.reward}).`
                      : "Palier ultime atteint : vous êtes une Légende FitHub Campus !"}
                  </p>

                  <div className="tiers-ladder">
                    {prog.tiers.map((t) => (
                      <div
                        key={t.code}
                        className={`tier-row ${t.unlocked ? "unlocked" : "locked"} ${
                          t.is_current ? "current" : ""
                        }`}
                      >
                        <div>
                          <strong>
                            {t.unlocked ? "✓ " : "🔒 "}
                            {t.name} ({t.min_xp}+ XP)
                          </strong>
                          <span>{t.reward}</span>
                        </div>
                        <span className={`badge ${t.unlocked ? "badge-ok" : "badge-soon"}`}>
                          {t.is_current
                            ? "Actuel"
                            : t.unlocked
                            ? "Débloqué"
                            : "À débloquer"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        <section className="card">
          <h2>Connecteur Google Fit &amp; Import GPX / JSON</h2>
          <p className="muted-text" style={{ marginTop: 0 }}>
            Synchronisez une activité externe pour créditer automatiquement votre profil, vos badges et vos défis inter-campus actifs.
          </p>

          <form className="form-stack" onSubmit={handleGoogleFitSync}>
            <label className="field">
              <span>Défi inter-campus à créditer (optionnel — auto-détecté sinon)</span>
              <select
                value={targetChallengeId}
                onChange={(e) => setTargetChallengeId(e.target.value)}
              >
                <option value="">Auto-crédit selon la discipline sportive</option>
                {activeChallenges.map((ch) => (
                  <option key={ch.id} value={ch.id}>
                    {ch.title} ({ch.sport} • {ch.unit})
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Flux API Google Fit (simulation OAuth / REST Sessions)</span>
              <select
                value={selectedPreset}
                onChange={(e) => setSelectedPreset(e.target.value)}
              >
                {GOOGLE_FIT_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>

            <button type="submit" className="primary-btn" disabled={syncing}>
              {syncing ? "Synchronisation..." : "Synchroniser depuis Google Fit (+30 XP)"}
            </button>
          </form>

          <div className="import-divider">
            <span>OU IMPORTER UNE TRACE MONTRE GPS (.GPX / .JSON)</span>
          </div>

          <div className="quick-actions">
            <label className="upload-label" style={{ cursor: "pointer" }}>
              Importer un fichier .gpx ou .json
              <input
                type="file"
                accept=".gpx,.json,application/json,application/gpx+xml,text/xml"
                onChange={handleFileUpload}
                disabled={syncing}
                hidden
              />
            </label>
            <button
              type="button"
              className="outline-btn"
              onClick={handleDownloadSampleGpx}
            >
              Télécharger un exemple .gpx
            </button>
          </div>

          {summary?.recent_workouts?.length > 0 && (
            <div style={{ marginTop: "14px" }}>
              <h3 style={{ margin: "0 0 8px", fontSize: "14px", color: "#1E2E5C" }}>
                Dernières séances enregistrées &amp; sources
              </h3>
              <div className="workout-history-list">
                {summary.recent_workouts.slice(0, 5).map((w) => (
                  <div key={w.id} className="lb-row">
                    <div>
                      <strong style={{ color: "#1E2E5C" }}>{w.sport}</strong>
                      <span className="lb-sub">
                        {w.duration_minutes} min
                        {w.distance_km > 0 ? ` • ${w.distance_km} km` : ""} • {w.calories} kcal
                      </span>
                    </div>
                    <span className="badge badge-soon">{w.source}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>

      {summary && (
        <section className="card">
          <div className="topbar-row" style={{ marginBottom: "10px" }}>
            <h2 style={{ margin: 0 }}>
              Vitrine des Badges d&apos;Accomplissement ({summary.unlocked_count} /{" "}
              {summary.total_badges})
            </h2>
            <span className="muted-text">
              Attribution automatique sans doublon dès validation des objectifs
            </span>
          </div>

          <div className="badges-showcase-grid">
            {summary.badges.map((b) => (
              <article
                key={b.id}
                className={`badge-trophy-card ${b.unlocked ? "unlocked" : "locked"}`}
              >
                <div className="badge-icon-circle">
                  <span>{BADGE_ICONS[b.code] || "🏅"}</span>
                </div>
                <div className="badge-trophy-body">
                  <div className="topbar-row">
                    <strong>{b.name}</strong>
                    <span className={`badge ${b.unlocked ? "badge-ok" : "badge-soon"}`}>
                      +{b.xp_reward} XP
                    </span>
                  </div>
                  <p>{b.description}</p>
                  <small>
                    {b.unlocked
                      ? "✓ Badge débloqué sur votre profil étudiant"
                      : `Objectif : ${BADGE_HINTS[b.code] || b.description}`}
                  </small>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
