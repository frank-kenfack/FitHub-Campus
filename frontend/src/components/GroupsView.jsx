import React, { useEffect, useState } from "react";
import { apiRequest } from "../api.js";

const SPORT_OPTIONS = [
  "",
  "Running",
  "Calisthenics",
  "Cross-Training",
  "Fitness",
  "Musculation",
  "Natation",
  "Escalade"
];

export default function GroupsView({ user, campuses, onRequireAuth, onMembershipChanged }) {
  const [groups, setGroups] = useState([]);
  const [filters, setFilters] = useState({ campus_id: "", sport: "", q: "" });
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    sport: "Running",
    campus_id: user?.campus_id || campuses[0]?.id || 1,
    description: ""
  });
  const [expandedGroup, setExpandedGroup] = useState(null);
  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(true);

  async function fetchGroups(activeFilters = filters) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeFilters.campus_id) params.set("campus_id", activeFilters.campus_id);
      if (activeFilters.sport) params.set("sport", activeFilters.sport);
      if (activeFilters.q.trim()) params.set("q", activeFilters.q.trim());
      const qs = params.toString();
      const data = await apiRequest(`/api/groups${qs ? `?${qs}` : ""}`);
      setGroups(data.groups || []);
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchGroups(filters);
  }, [filters.campus_id, filters.sport, user?.id]);

  useEffect(() => {
    if (user?.campus_id) {
      setCreateForm((prev) => ({ ...prev, campus_id: user.campus_id }));
    } else if (campuses[0]?.id) {
      setCreateForm((prev) => ({ ...prev, campus_id: campuses[0].id }));
    }
  }, [user, campuses]);

  async function handleCreateGroup(e) {
    e.preventDefault();
    setFeedback({ type: "", text: "" });
    try {
      const data = await apiRequest("/api/groups", {
        method: "POST",
        body: {
          ...createForm,
          campus_id: Number(createForm.campus_id)
        }
      });
      setCreateForm({
        name: "",
        sport: "Running",
        campus_id: user?.campus_id || campuses[0]?.id || 1,
        description: ""
      });
      setShowCreate(false);
      setExpandedGroup(data.group);
      setFeedback({ type: "ok", text: `Groupe « ${data.group.name} » créé !` });
      await fetchGroups();
      onMembershipChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleToggleMembership(group) {
    if (!user) {
      onRequireAuth();
      return;
    }
    try {
      const action = group.is_member ? "leave" : "join";
      const data = await apiRequest(`/api/groups/${group.id}/${action}`, {
        method: "POST"
      });
      if (expandedGroup?.id === group.id) {
        setExpandedGroup(data.group);
      }
      await fetchGroups();
      onMembershipChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleInspectMembers(groupId) {
    if (expandedGroup?.id === groupId) {
      setExpandedGroup(null);
      return;
    }
    try {
      const data = await apiRequest(`/api/groups/${groupId}`);
      setExpandedGroup(data.group);
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleDeleteGroup(groupId) {
    try {
      await apiRequest(`/api/groups/${groupId}`, { method: "DELETE" });
      if (expandedGroup?.id === groupId) {
        setExpandedGroup(null);
      }
      setFeedback({ type: "ok", text: "Groupe supprimé." });
      await fetchGroups();
      onMembershipChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  return (
    <div>
      <section className="card" style={{ marginBottom: "14px" }}>
        <div className="topbar-row" style={{ marginBottom: "10px" }}>
          <h2 style={{ margin: 0 }}>Groupes Sportifs Inter-Campus ({groups.length})</h2>
          <button
            type="button"
            className="primary-btn"
            onClick={() => (user ? setShowCreate(!showCreate) : onRequireAuth())}
          >
            {showCreate ? "Fermer" : "+ Créer un groupe"}
          </button>
        </div>

        <div className="filters-bar">
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
            <option value="">Toutes les disciplines</option>
            {SPORT_OPTIONS.filter(Boolean).map((sp) => (
              <option key={sp} value={sp}>
                {sp}
              </option>
            ))}
          </select>

          <div className="search-inline">
            <input
              type="text"
              placeholder="Rechercher un club ou mot-clé..."
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && fetchGroups(filters)}
            />
            <button type="button" className="secondary-btn" onClick={() => fetchGroups(filters)}>
              Filtrer
            </button>
          </div>
        </div>

        {feedback.text && (
          <div
            className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}
            style={{ marginTop: "10px" }}
          >
            {feedback.text}
          </div>
        )}

        {showCreate && user && (
          <form className="form-stack create-panel" onSubmit={handleCreateGroup}>
            <h3 style={{ margin: "0 0 4px", color: "#1E2E5C", fontSize: "15px" }}>
              Nouveau groupe sportif étudiant
            </h3>
            <div className="form-row-2">
              <label className="field">
                <span>Nom du groupe</span>
                <input
                  type="text"
                  required
                  minLength={3}
                  placeholder="Ex : Lyon Trail & Monts d'Or"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Discipline</span>
                <select
                  value={createForm.sport}
                  onChange={(e) => setCreateForm({ ...createForm, sport: e.target.value })}
                >
                  {SPORT_OPTIONS.filter(Boolean).map((sp) => (
                    <option key={sp} value={sp}>
                      {sp}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              <span>Campus rattaché</span>
              <select
                value={createForm.campus_id}
                onChange={(e) =>
                  setCreateForm({ ...createForm, campus_id: Number(e.target.value) })
                }
              >
                {campuses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.city})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Description & créneaux d&apos;entraînement</span>
              <textarea
                rows={2}
                placeholder="Horaires habituels, lieu de rendez-vous, niveaux acceptés..."
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              />
            </label>
            <button type="submit" className="primary-btn">
              Publier le groupe
            </button>
          </form>
        )}
      </section>

      {loading ? (
        <div className="card">Chargement des groupes sportifs...</div>
      ) : (
        <div className="grid-cards">
          {groups.map((group) => {
            const isExpanded = expandedGroup?.id === group.id;
            const isCreator = user && user.id === group.created_by;
            return (
              <article key={group.id} className="card group-card">
                <div className="topbar-row">
                  <span className="badge badge-soon">{group.sport}</span>
                  <span className="muted-text" style={{ fontSize: "12px" }}>
                    {group.campus_name}
                  </span>
                </div>
                <h3 className="group-title">{group.name}</h3>
                <p className="group-desc">{group.description || "Aucune description renseignée."}</p>

                <div className="group-footer">
                  <span className="muted-text" style={{ fontSize: "12.5px" }}>
                    <strong>{group.members_count}</strong> membre{group.members_count > 1 ? "s" : ""} • par{" "}
                    <strong>{group.creator_username}</strong>
                  </span>
                  <div className="group-btns">
                    <button
                      type="button"
                      className="outline-btn"
                      onClick={() => handleInspectMembers(group.id)}
                    >
                      {isExpanded ? "Masquer" : "Membres"}
                    </button>
                    <button
                      type="button"
                      className={group.is_member ? "secondary-btn" : "primary-btn"}
                      onClick={() => handleToggleMembership(group)}
                    >
                      {group.is_member ? "Quitter" : "Rejoindre"}
                    </button>
                    {isCreator && (
                      <button
                        type="button"
                        className="danger-btn"
                        onClick={() => handleDeleteGroup(group.id)}
                      >
                        Suppr.
                      </button>
                    )}
                  </div>
                </div>

                {isExpanded && expandedGroup?.members && (
                  <div className="members-drawer">
                    <strong>Membres inscrits ({expandedGroup.members.length}) :</strong>
                    <div className="members-chips">
                      {expandedGroup.members.map((m) => (
                        <div key={m.user_id} className="member-chip">
                          {m.avatar_url ? (
                            <img src={m.avatar_url} alt={m.username} className="chip-avatar" />
                          ) : (
                            <span className="chip-initials">
                              {m.username.slice(0, 2).toUpperCase()}
                            </span>
                          )}
                          <span>
                            {m.username}{" "}
                            {m.role === "admin" && <em className="role-tag">Admin</em>}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
