import React, { useEffect, useState } from "react";
import { apiRequest } from "../api.js";

const SPORTS = [
  "Running",
  "Calisthenics",
  "Cross-Training",
  "Fitness",
  "Musculation",
  "Natation",
  "Cyclisme",
  "Boxe",
  "Escalade"
];

function BeforeAfterComparator({ beforeUrl, afterUrl, title, durationLabel }) {
  const [split, setSplit] = useState(50);
  const [sideBySide, setSideBySide] = useState(false);

  return (
    <div className="ba-wrapper">
      <div className="ba-toolbar">
        <span className="badge badge-ok">
          Avant / Après {durationLabel ? `• ${durationLabel}` : ""}
        </span>
        <button
          type="button"
          className="outline-btn"
          style={{ padding: "4px 10px", fontSize: "11.5px" }}
          onClick={() => setSideBySide(!sideBySide)}
        >
          {sideBySide ? "Mode Slider ◀▶" : "Vue Côte à côte"}
        </button>
      </div>

      {sideBySide ? (
        <div className="ba-side-grid">
          <div className="ba-side-item">
            <span className="ba-tag ba-tag-before">AVANT</span>
            <img src={beforeUrl} alt={`${title} - Avant`} />
          </div>
          <div className="ba-side-item">
            <span className="ba-tag ba-tag-after">APRÈS</span>
            <img src={afterUrl} alt={`${title} - Après`} />
          </div>
        </div>
      ) : (
        <div className="ba-slider-box">
          <img src={afterUrl} alt={`${title} - Après`} className="ba-img-base" />
          <img
            src={beforeUrl}
            alt={`${title} - Avant`}
            className="ba-img-overlay"
            style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
          />
          <span className="ba-tag ba-tag-before">AVANT</span>
          <span className="ba-tag ba-tag-after">APRÈS</span>
          <div className="ba-divider" style={{ left: `${split}%` }}>
            <span className="ba-handle">◀▶</span>
          </div>
          <input
            type="range"
            min="5"
            max="95"
            value={split}
            aria-label="Curseur comparatif Avant Après"
            className="ba-range-input"
            onChange={(e) => setSplit(Number(e.target.value))}
          />
        </div>
      )}
    </div>
  );
}

export default function SocialFeedView({ user, campuses, onRequireAuth, onActivityChanged }) {
  const [posts, setPosts] = useState([]);
  const [myGroups, setMyGroups] = useState([]);
  const [filterMode, setFilterMode] = useState("all"); // all | 24h | before_after
  const [campusFilter, setCampusFilter] = useState("");
  const [activeStoryModal, setActiveStoryModal] = useState(null);
  const [composerType, setComposerType] = useState(""); // "" | "story" | "ba"
  const [commentInputs, setCommentInputs] = useState({});
  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [storyForm, setStoryForm] = useState({
    sport: "Running",
    duration_minutes: "45",
    distance_km: "7.5",
    calories: "420",
    title: "",
    caption: "",
    visibility: "public",
    group_id: "",
    image: null
  });

  const [baForm, setBaForm] = useState({
    title: "",
    duration_label: "8 semaines",
    caption: "",
    visibility: "public",
    group_id: "",
    before_image: null,
    after_image: null
  });

  async function loadPosts(mode = filterMode, campusId = campusFilter) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (mode === "24h") {
        params.set("kind", "workout_story");
        params.set("timeframe", "24h");
      } else if (mode === "before_after") {
        params.set("kind", "before_after");
      }
      if (campusId) {
        params.set("campus_id", campusId);
      }
      const qs = params.toString();
      const data = await apiRequest(`/api/social/posts${qs ? `?${qs}` : ""}`);
      setPosts(data.posts || []);
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function loadUserGroups() {
    if (!user) {
      setMyGroups([]);
      return;
    }
    try {
      const data = await apiRequest("/api/groups");
      setMyGroups((data.groups || []).filter((g) => g.is_member));
    } catch {
      setMyGroups([]);
    }
  }

  useEffect(() => {
    loadPosts(filterMode, campusFilter);
  }, [filterMode, campusFilter, user?.id]);

  useEffect(() => {
    loadUserGroups();
  }, [user?.id]);

  async function handlePublishStory(e) {
    e.preventDefault();
    if (!storyForm.image) {
      setFeedback({ type: "err", text: "Sélectionnez une photo de séance." });
      return;
    }
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const fd = new FormData();
      fd.append("sport", storyForm.sport);
      fd.append("duration_minutes", storyForm.duration_minutes);
      fd.append("distance_km", storyForm.distance_km || "0");
      fd.append("calories", storyForm.calories || "0");
      fd.append("title", storyForm.title);
      fd.append("caption", storyForm.caption);
      fd.append("visibility", storyForm.visibility);
      if (storyForm.group_id) fd.append("group_id", storyForm.group_id);
      fd.append("image", storyForm.image);

      await apiRequest("/api/social/stories", {
        method: "POST",
        body: fd,
        isFormData: true
      });
      setComposerType("");
      setStoryForm({
        sport: "Running",
        duration_minutes: "45",
        distance_km: "7.5",
        calories: "420",
        title: "",
        caption: "",
        visibility: "public",
        group_id: "",
        image: null
      });
      setFeedback({ type: "ok", text: "Story workout publiée (+25 XP) !" });
      await loadPosts();
      onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handlePublishBeforeAfter(e) {
    e.preventDefault();
    if (!baForm.before_image || !baForm.after_image) {
      setFeedback({ type: "err", text: "Veuillez fournir les deux photos Avant et Après." });
      return;
    }
    setBusy(true);
    setFeedback({ type: "", text: "" });
    try {
      const fd = new FormData();
      fd.append("title", baForm.title);
      fd.append("duration_label", baForm.duration_label);
      fd.append("caption", baForm.caption);
      fd.append("visibility", baForm.visibility);
      if (baForm.group_id) fd.append("group_id", baForm.group_id);
      fd.append("before_image", baForm.before_image);
      fd.append("after_image", baForm.after_image);

      await apiRequest("/api/social/before-after", {
        method: "POST",
        body: fd,
        isFormData: true
      });
      setComposerType("");
      setBaForm({
        title: "",
        duration_label: "8 semaines",
        caption: "",
        visibility: "public",
        group_id: "",
        before_image: null,
        after_image: null
      });
      setFeedback({ type: "ok", text: "Comparatif Avant/Après publié (+35 XP) !" });
      await loadPosts();
      onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleLike(postId) {
    if (!user) {
      onRequireAuth();
      return;
    }
    try {
      const data = await apiRequest(`/api/social/posts/${postId}/like`, {
        method: "POST"
      });
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? { ...p, is_liked: data.liked, likes_count: data.likes_count }
            : p
        )
      );
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleAddComment(e, postId) {
    e.preventDefault();
    if (!user) {
      onRequireAuth();
      return;
    }
    const text = (commentInputs[postId] || "").trim();
    if (!text) return;

    try {
      const data = await apiRequest(`/api/social/posts/${postId}/comments`, {
        method: "POST",
        body: { content: text }
      });
      setCommentInputs((prev) => ({ ...prev, [postId]: "" }));
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? {
                ...p,
                comments_count: data.comments_count,
                comments: [...(p.comments || []), data.comment]
              }
            : p
        )
      );
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleDeleteComment(postId, commentId) {
    try {
      const data = await apiRequest(`/api/social/comments/${commentId}`, {
        method: "DELETE"
      });
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? {
                ...p,
                comments_count: data.comments_count,
                comments: (p.comments || []).filter((c) => c.id !== commentId)
              }
            : p
        )
      );
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleDeletePost(postId) {
    try {
      await apiRequest(`/api/social/posts/${postId}`, { method: "DELETE" });
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      if (activeStoryModal?.id === postId) {
        setActiveStoryModal(null);
      }
      setFeedback({ type: "ok", text: "Publication supprimée." });
      onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  const freshStories = posts.filter((p) => p.kind === "workout_story" && p.is_fresh_24h);

  return (
    <div>
      {/* CARROUSEL STORIES 24H */}
      <section className="card" style={{ marginBottom: "14px" }}>
        <div className="topbar-row" style={{ marginBottom: "10px" }}>
          <h2 style={{ margin: 0 }}>Stories du Jour ({freshStories.length})</h2>
          <div className="quick-actions">
            <button
              type="button"
              className="primary-btn"
              onClick={() =>
                user
                  ? setComposerType(composerType === "story" ? "" : "story")
                  : onRequireAuth()
              }
            >
              {composerType === "story" ? "Fermer" : "+ Story Workout"}
            </button>
            <button
              type="button"
              className="secondary-btn"
              onClick={() =>
                user ? setComposerType(composerType === "ba" ? "" : "ba") : onRequireAuth()
              }
            >
              {composerType === "ba" ? "Fermer" : "+ Avant / Après"}
            </button>
          </div>
        </div>

        {freshStories.length === 0 ? (
          <p className="muted-text" style={{ margin: 0 }}>
            Aucune story de moins de 24h pour ce filtre. Publiez votre séance du jour !
          </p>
        ) : (
          <div className="stories-carousel">
            {freshStories.map((st) => (
              <button
                key={st.id}
                type="button"
                className={`story-bubble ${activeStoryModal?.id === st.id ? "selected" : ""}`}
                onClick={() =>
                  setActiveStoryModal(activeStoryModal?.id === st.id ? null : st)
                }
              >
                <span className="story-ring">
                  <img src={st.media_url} alt={st.username} />
                </span>
                <strong>{st.username}</strong>
                <span>{st.workout?.sport || "Workout"}</span>
              </button>
            ))}
          </div>
        )}

        {activeStoryModal && (
          <div className="story-spotlight">
            <div className="topbar-row" style={{ marginBottom: "8px" }}>
              <div>
                <strong>{activeStoryModal.username}</strong> •{" "}
                <span className="muted-text">{activeStoryModal.campus_name}</span>
              </div>
              <button
                type="button"
                className="outline-btn"
                onClick={() => setActiveStoryModal(null)}
              >
                Fermer l&apos;aperçu
              </button>
            </div>
            <img
              src={activeStoryModal.media_url}
              alt={activeStoryModal.title}
              className="spotlight-img"
            />
            <p style={{ margin: "8px 0 0", fontSize: "13px" }}>
              <strong>{activeStoryModal.title}</strong> — {activeStoryModal.caption}
            </p>
          </div>
        )}

        {/* FORMULAIRE STORY WORKOUT */}
        {composerType === "story" && user && (
          <form className="form-stack create-panel" onSubmit={handlePublishStory}>
            <h3 style={{ margin: 0, color: "#1E2E5C", fontSize: "15px" }}>
              Publier une Story de Workout (+25 XP)
            </h3>
            <div className="form-row-2">
              <label className="field">
                <span>Sport</span>
                <select
                  value={storyForm.sport}
                  onChange={(e) => setStoryForm({ ...storyForm, sport: e.target.value })}
                >
                  {SPORTS.map((sp) => (
                    <option key={sp} value={sp}>
                      {sp}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Titre de la séance</span>
                <input
                  type="text"
                  placeholder="Ex : Fractionné piste Gerland"
                  value={storyForm.title}
                  onChange={(e) => setStoryForm({ ...storyForm, title: e.target.value })}
                />
              </label>
            </div>
            <div className="metrics-inputs">
              <label className="field">
                <span>Durée (min)</span>
                <input
                  type="number"
                  min={1}
                  required
                  value={storyForm.duration_minutes}
                  onChange={(e) =>
                    setStoryForm({ ...storyForm, duration_minutes: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Distance (km)</span>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={storyForm.distance_km}
                  onChange={(e) => setStoryForm({ ...storyForm, distance_km: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Calories (kcal)</span>
                <input
                  type="number"
                  min={0}
                  value={storyForm.calories}
                  onChange={(e) => setStoryForm({ ...storyForm, calories: e.target.value })}
                />
              </label>
            </div>
            <div className="form-row-2">
              <label className="field">
                <span>Visibilité</span>
                <select
                  value={storyForm.visibility}
                  onChange={(e) => setStoryForm({ ...storyForm, visibility: e.target.value })}
                >
                  <option value="public">Publique (tous les campus)</option>
                  <option value="group">Réservée à un de mes groupes</option>
                </select>
              </label>
              <label className="field">
                <span>Groupe associé (optionnel)</span>
                <select
                  value={storyForm.group_id}
                  onChange={(e) => setStoryForm({ ...storyForm, group_id: e.target.value })}
                >
                  <option value="">Aucun groupe spécifique</option>
                  {myGroups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              <span>Photo de la séance (JPG, PNG, WEBP)</span>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                required
                onChange={(e) =>
                  setStoryForm({ ...storyForm, image: e.target.files?.[0] || null })
                }
              />
            </label>
            <label className="field">
              <span>Ressenti / Légende</span>
              <textarea
                rows={2}
                placeholder="Partage tes sensations avec ton campus..."
                value={storyForm.caption}
                onChange={(e) => setStoryForm({ ...storyForm, caption: e.target.value })}
              />
            </label>
            <button type="submit" className="primary-btn" disabled={busy}>
              {busy ? "Publication..." : "Publier ma Story"}
            </button>
          </form>
        )}

        {/* FORMULAIRE AVANT / APRÈS */}
        {composerType === "ba" && user && (
          <form className="form-stack create-panel" onSubmit={handlePublishBeforeAfter}>
            <h3 style={{ margin: 0, color: "#1E2E5C", fontSize: "15px" }}>
              Publier une Progression Avant / Après (+35 XP)
            </h3>
            <div className="form-row-2">
              <label className="field">
                <span>Titre de l&apos;évolution</span>
                <input
                  type="text"
                  required
                  minLength={3}
                  placeholder="Ex : Progression Gainage & Calisthenics"
                  value={baForm.title}
                  onChange={(e) => setBaForm({ ...baForm, title: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Durée d&apos;évolution</span>
                <input
                  type="text"
                  placeholder="Ex : 10 semaines"
                  value={baForm.duration_label}
                  onChange={(e) => setBaForm({ ...baForm, duration_label: e.target.value })}
                />
              </label>
            </div>
            <div className="form-row-2">
              <label className="field">
                <span>Photo AVANT</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  required
                  onChange={(e) =>
                    setBaForm({ ...baForm, before_image: e.target.files?.[0] || null })
                  }
                />
              </label>
              <label className="field">
                <span>Photo APRÈS</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  required
                  onChange={(e) =>
                    setBaForm({ ...baForm, after_image: e.target.files?.[0] || null })
                  }
                />
              </label>
            </div>
            <div className="form-row-2">
              <label className="field">
                <span>Visibilité</span>
                <select
                  value={baForm.visibility}
                  onChange={(e) => setBaForm({ ...baForm, visibility: e.target.value })}
                >
                  <option value="public">Publique (tous les campus)</option>
                  <option value="group">Membres d&apos;un groupe uniquement</option>
                </select>
              </label>
              <label className="field">
                <span>Groupe associé</span>
                <select
                  value={baForm.group_id}
                  onChange={(e) => setBaForm({ ...baForm, group_id: e.target.value })}
                >
                  <option value="">Aucun groupe spécifique</option>
                  {myGroups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              <span>Conseils &amp; programme suivi</span>
              <textarea
                rows={2}
                placeholder="Raconte ton parcours, ta fréquence d'entraînement..."
                value={baForm.caption}
                onChange={(e) => setBaForm({ ...baForm, caption: e.target.value })}
              />
            </label>
            <button type="submit" className="primary-btn" disabled={busy}>
              {busy ? "Publication..." : "Publier le comparatif Avant / Après"}
            </button>
          </form>
        )}
      </section>

      {/* FILTRES DU FIL COMMUNAUTAIRE */}
      <section className="card" style={{ marginBottom: "14px" }}>
        <div className="feed-filter-bar">
          <div className="quick-actions">
            {[
              { id: "all", label: "Tout le fil" },
              { id: "24h", label: "Stories du jour" },
              { id: "before_after", label: "Avant / Après" }
            ].map((item) => (
              <button
                key={item.id}
                type="button"
                className={`nav-btn ${filterMode === item.id ? "active" : ""}`}
                onClick={() => setFilterMode(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <select
            className="campus-select-inline"
            value={campusFilter}
            onChange={(e) => setCampusFilter(e.target.value)}
          >
            <option value="">Tous les campus</option>
            {campuses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {feedback.text && (
          <div
            className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}
            style={{ marginTop: "10px", marginBottom: 0 }}
          >
            {feedback.text}
          </div>
        )}
      </section>

      {/* LISTE DES PUBLICATIONS */}
      {loading ? (
        <div className="card">Chargement du fil Social Fitness...</div>
      ) : posts.length === 0 ? (
        <div className="card">Aucune publication trouvée pour ces critères.</div>
      ) : (
        <div className="social-feed-stack">
          {posts.map((post) => {
            const isAuthor = user && user.id === post.user_id;
            return (
              <article key={post.id} className="card post-card">
                <div className="post-header">
                  <div className="post-author">
                    {post.avatar_url ? (
                      <img src={post.avatar_url} alt={post.username} className="post-avatar" />
                    ) : (
                      <span className="post-initials">
                        {post.username.slice(0, 2).toUpperCase()}
                      </span>
                    )}
                    <div>
                      <strong>{post.username}</strong>
                      <span className="post-sub">
                        {post.campus_name}
                        {post.group_name ? ` • Club : ${post.group_name}` : ""}
                        {post.visibility === "group" ? " (Privé groupe)" : ""}
                      </span>
                    </div>
                  </div>
                  <div className="quick-actions">
                    <span className="badge badge-soon">
                      {post.kind === "before_after" ? "Avant / Après" : "Story Workout"}
                    </span>
                    {isAuthor && (
                      <button
                        type="button"
                        className="danger-btn"
                        onClick={() => handleDeletePost(post.id)}
                      >
                        Suppr.
                      </button>
                    )}
                  </div>
                </div>

                {post.title && <h3 className="post-title">{post.title}</h3>}
                {post.caption && <p className="post-caption">{post.caption}</p>}

                {post.kind === "workout_story" ? (
                  <div>
                    <img src={post.media_url} alt={post.title} className="story-main-img" />
                    {post.workout && (
                      <div className="workout-chips">
                        <span className="metric-chip">{post.workout.sport}</span>
                        <span className="metric-chip">{post.workout.duration_minutes} min</span>
                        {post.workout.distance_km > 0 && (
                          <span className="metric-chip">{post.workout.distance_km} km</span>
                        )}
                        {post.workout.calories > 0 && (
                          <span className="metric-chip">{post.workout.calories} kcal</span>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <BeforeAfterComparator
                    beforeUrl={post.before_media_url}
                    afterUrl={post.after_media_url}
                    title={post.title}
                    durationLabel={post.duration_label}
                  />
                )}

                <div className="social-actions-row">
                  <button
                    type="button"
                    className={`like-btn ${post.is_liked ? "liked" : ""}`}
                    onClick={() => handleToggleLike(post.id)}
                  >
                    {post.is_liked ? "👏 Applaudi" : "👏 Applaudir"} ({post.likes_count})
                  </button>
                  <span className="muted-text" style={{ fontWeight: 600 }}>
                    💬 {post.comments_count} commentaire{post.comments_count > 1 ? "s" : ""}
                  </span>
                </div>

                <div className="comments-box">
                  {(post.comments || []).map((c) => {
                    const canDelete = user && (user.id === c.user_id || user.id === post.user_id);
                    return (
                      <div key={c.id} className="comment-row">
                        <div>
                          <strong>{c.username} :</strong> <span>{c.content}</span>
                        </div>
                        {canDelete && (
                          <button
                            type="button"
                            className="comment-del-btn"
                            title="Supprimer ce commentaire"
                            onClick={() => handleDeleteComment(post.id, c.id)}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    );
                  })}

                  <form
                    className="comment-form"
                    onSubmit={(e) => handleAddComment(e, post.id)}
                  >
                    <input
                      type="text"
                      placeholder={
                        user
                          ? "Encourager ou commenter cette publication..."
                          : "Connectez-vous pour commenter..."
                      }
                      value={commentInputs[post.id] || ""}
                      onChange={(e) =>
                        setCommentInputs({ ...commentInputs, [post.id]: e.target.value })
                      }
                    />
                    <button type="submit" className="secondary-btn">
                      Envoyer
                    </button>
                  </form>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
