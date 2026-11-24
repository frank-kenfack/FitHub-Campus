import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { apiRequest } from "../api.js";

const KIND_META = {
  gym: { label: "Salle partenaire", short: "SALLE", color: "#E61A5F", bg: "#FFF1F2" },
  spot: { label: "Aire extérieure", short: "PARC", color: "#1B8A3D", bg: "#DCFCE7" },
  event: { label: "Séance étudiante", short: "RDV", color: "#1E2E5C", bg: "#EEF2FF" }
};

function defaultTomorrowIsoLocal() {
  const d = new Date(Date.now() + 24 * 3600 * 1000);
  d.setMinutes(0, 0, 0);
  const tzOffset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tzOffset).toISOString().slice(0, 16);
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function makePlaceIcon(kind, isSelected) {
  const meta = KIND_META[kind] || KIND_META.gym;
  const scale = isSelected ? "transform: scale(1.14);" : "";
  return L.divIcon({
    className: "fithub-div-marker",
    html: `<div class="map-pin map-pin-${kind}" style="background:${meta.color};${scale}">
      <span>${meta.short}</span>
    </div>`,
    iconSize: [52, 28],
    iconAnchor: [26, 28],
    popupAnchor: [0, -26]
  });
}

function makeRefIcon() {
  return L.divIcon({
    className: "fithub-div-marker",
    html: `<div class="map-pin-gps" title="Position de référence">GPS</div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19]
  });
}

export default function MapEventsView({
  user,
  campuses,
  onRequireAuth,
  onActivityChanged
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);
  const markersByIdRef = useRef({});
  const showFormRef = useRef(false);

  const [places, setPlaces] = useState([]);
  const [referencePoint, setReferencePoint] = useState(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const [gpsStatus, setGpsStatus] = useState("");

  // Filtres combinables (US-6.3)
  const [kindFilter, setKindFilter] = useState("all");
  const [campusFilter, setCampusFilter] = useState("");
  const [radiusFilter, setRadiusFilter] = useState("");
  const [sportFilter, setSportFilter] = useState("");
  const [gpsCoords, setGpsCoords] = useState(null);

  // Création d'événement géolocalisé (US-6.2)
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [eventForm, setEventForm] = useState({
    title: "",
    sport: "Running",
    campus_id: user?.campus_id || campuses[0]?.id || 1,
    starts_at: defaultTomorrowIsoLocal(),
    max_participants: 12,
    address: "",
    description: "",
    latitude: campuses[0]?.latitude || 45.7299,
    longitude: campuses[0]?.longitude || 4.8273
  });

  useEffect(() => {
    showFormRef.current = showCreateForm;
  }, [showCreateForm]);

  useEffect(() => {
    const defaultCid = user?.campus_id || campuses[0]?.id;
    const found = campuses.find((c) => c.id === Number(defaultCid)) || campuses[0];
    if (found) {
      setEventForm((prev) => ({
        ...prev,
        campus_id: found.id,
        latitude: prev.title ? prev.latitude : found.latitude,
        longitude: prev.title ? prev.longitude : found.longitude
      }));
    }
  }, [user, campuses]);

  // Initialisation unique de la carte Leaflet + OpenStreetMap
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return undefined;

    const initialCampus =
      campuses.find((c) => c.id === user?.campus_id) || campuses[0] || {
        latitude: 46.6033,
        longitude: 2.3522
      };

    const map = L.map(mapContainerRef.current, {
      center: [initialCampus.latitude, initialCampus.longitude],
      zoom: user?.campus_id ? 13 : 6,
      scrollWheelZoom: true
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    markersLayerRef.current = layerGroup;

    map.on("click", (evt) => {
      if (!showFormRef.current) return;
      const lat = Number(evt.latlng.lat.toFixed(5));
      const lon = Number(evt.latlng.lng.toFixed(5));
      setEventForm((prev) => ({
        ...prev,
        latitude: lat,
        longitude: lon
      }));
      setFeedback({
        type: "ok",
        text: `Coordonnées sélectionnées sur la carte : ${lat}, ${lon}`
      });
    });

    setTimeout(() => map.invalidateSize(), 120);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markersLayerRef.current = null;
    };
  }, []);

  async function fetchPlaces(override = {}) {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      const k = override.kind ?? kindFilter;
      const cid = override.campus_id ?? campusFilter;
      const rad = override.radius_km ?? radiusFilter;
      const sp = override.sport ?? sportFilter;
      const coords = override.gpsCoords !== undefined ? override.gpsCoords : gpsCoords;

      if (k && k !== "all") params.set("kind", k);
      if (cid) params.set("campus_id", String(cid));
      if (sp.trim()) params.set("sport", sp.trim());
      if (coords) {
        params.set("lat", String(coords.latitude));
        params.set("lon", String(coords.longitude));
      }
      if (rad) {
        if (!coords && !cid && !user) {
          const fallbackCampus = campuses[0];
          if (fallbackCampus) {
            params.set("lat", String(fallbackCampus.latitude));
            params.set("lon", String(fallbackCampus.longitude));
          }
        }
        params.set("radius_km", String(rad));
      }

      const qs = params.toString();
      const placesPayload = await apiRequest(`/api/places${qs ? `?${qs}` : ""}`);
      setPlaces(placesPayload.places || []);
      setReferencePoint(placesPayload.reference_point || null);
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPlaces();
  }, [kindFilter, campusFilter, radiusFilter, gpsCoords, user]);

  // Mise à jour des marqueurs Leaflet et du cercle de rayon Haversine
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = markersLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    markersByIdRef.current = {};

    const boundsPoints = [];

    if (referencePoint?.latitude != null && referencePoint?.longitude != null) {
      const refLatLng = [referencePoint.latitude, referencePoint.longitude];
      const refMarker = L.marker(refLatLng, { icon: makeRefIcon() });
      refMarker.bindPopup(
        `<strong>Point de référence (${
          referencePoint.source === "gps" ? "GPS actif" : "Campus"
        })</strong><br/>Lat ${referencePoint.latitude.toFixed(4)}, Lon ${referencePoint.longitude.toFixed(4)}`
      );
      layer.addLayer(refMarker);
      boundsPoints.push(refLatLng);

      if (referencePoint.radius_km) {
        const circle = L.circle(refLatLng, {
          radius: Number(referencePoint.radius_km) * 1000,
          color: "#E61A5F",
          fillColor: "#E61A5F",
          fillOpacity: 0.08,
          weight: 2,
          dashArray: "6 4"
        });
        layer.addLayer(circle);
      }
    }

    places.forEach((p) => {
      const latlng = [p.latitude, p.longitude];
      boundsPoints.push(latlng);
      const meta = KIND_META[p.kind] || KIND_META.gym;
      const marker = L.marker(latlng, {
        icon: makePlaceIcon(p.kind, p.id === selectedPlaceId)
      });

      const distHtml =
        p.distance_km != null ? ` • <strong>${p.distance_km} km</strong>` : "";
      const capHtml =
        p.kind === "event" && p.max_participants != null
          ? `<div style="margin-top:4px;font-size:12px;">Inscrits : <strong>${p.rsvp_count}/${p.max_participants}</strong> ${
              p.is_full ? '<span style="color:#BE123C;font-weight:700;">(Complet)</span>' : ""
            }</div>`
          : "";

      marker.bindPopup(
        `<div style="min-width:190px;">
          <div style="font-size:11px;font-weight:800;color:${meta.color};text-transform:uppercase;">
            ${escapeHtml(meta.label)}${distHtml}
          </div>
          <strong style="font-size:13.5px;color:#1E2E5C;">${escapeHtml(p.title)}</strong>
          <div style="font-size:12px;color:#475569;margin-top:2px;">
            ${escapeHtml(p.sport)} : ${escapeHtml(p.address || p.campus_name)}
          </div>
          ${capHtml}
        </div>`
      );

      marker.on("click", () => {
        setSelectedPlaceId(p.id);
      });

      layer.addLayer(marker);
      markersByIdRef.current[p.id] = marker;
    });

    if (boundsPoints.length === 1) {
      map.setView(boundsPoints[0], 14);
    } else if (boundsPoints.length > 1) {
      map.fitBounds(boundsPoints, { padding: [36, 36], maxZoom: 14 });
    }
  }, [places, referencePoint, selectedPlaceId]);

  function activateFallbackCampus() {
    const fallback =
      campuses.find((c) => c.id === Number(campusFilter || user?.campus_id)) ||
      campuses[0];
    if (!fallback) return;
    const coords = { latitude: fallback.latitude, longitude: fallback.longitude };
    setGpsCoords(coords);
    if (!radiusFilter) {
      setRadiusFilter("5");
    }
    setGpsStatus(`Carte centrée autour de ${fallback.name} (${fallback.city}).`);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([fallback.latitude, fallback.longitude], 14, {
        duration: 0.6
      });
    }
  }

  function handleLocateMe() {
    setFeedback({ type: "", text: "" });
    if (!navigator.geolocation) {
      activateFallbackCampus("Géolocalisation HTML5 non disponible.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = {
          latitude: Number(pos.coords.latitude.toFixed(5)),
          longitude: Number(pos.coords.longitude.toFixed(5))
        };
        setGpsCoords(coords);
        if (!radiusFilter) setRadiusFilter("5");
        setGpsStatus(
          `GPS navigateur actif (${coords.latitude}, ${coords.longitude}).`
        );
        if (mapInstanceRef.current) {
          mapInstanceRef.current.flyTo([coords.latitude, coords.longitude], 14, {
            duration: 0.6
          });
        }
      },
      () => {
        activateFallbackCampus("Permission GPS refusée ou indisponible.");
      },
      { timeout: 3500 }
    );
  }

  function handleFocusCampus(campus) {
    setCampusFilter(String(campus.id));
    setGpsCoords({ latitude: campus.latitude, longitude: campus.longitude });
    setGpsStatus(`Centré sur ${campus.name} (${campus.city}).`);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([campus.latitude, campus.longitude], 14, {
        duration: 0.5
      });
    }
  }

  function handleResetFilters() {
    setKindFilter("all");
    setCampusFilter("");
    setRadiusFilter("");
    setSportFilter("");
    setGpsCoords(null);
    setGpsStatus("");
    fetchPlaces({
      kind: "all",
      campus_id: "",
      radius_km: "",
      sport: "",
      gpsCoords: null
    });
  }

  function focusPlaceOnMap(place) {
    setSelectedPlaceId(place.id);
    const map = mapInstanceRef.current;
    const marker = markersByIdRef.current[place.id];
    if (map) {
      map.flyTo([place.latitude, place.longitude], 15, { duration: 0.5 });
    }
    if (marker) {
      setTimeout(() => marker.openPopup(), 250);
    }
  }

  async function handleCreateEvent(e) {
    e.preventDefault();
    if (!user) {
      onRequireAuth();
      return;
    }
    setSubmitting(true);
    setFeedback({ type: "", text: "" });
    try {
      const isoStarts = new Date(eventForm.starts_at).toISOString();
      const res = await apiRequest("/api/places/events", {
        method: "POST",
        body: {
          title: eventForm.title,
          sport: eventForm.sport,
          campus_id: Number(eventForm.campus_id),
          starts_at: isoStarts,
          max_participants: Number(eventForm.max_participants),
          address: eventForm.address,
          description: eventForm.description,
          latitude: Number(eventForm.latitude),
          longitude: Number(eventForm.longitude)
        }
      });

      const badgeNote =
        res.newly_unlocked_badges?.length > 0
          ? ` Badge débloqué : ${res.newly_unlocked_badges.map((b) => b.name).join(", ")} !`
          : "";

      setFeedback({
        type: "ok",
        text: `Événement « ${res.place.title} » publié sur la carte (+20 XP) !${badgeNote}`
      });
      setShowCreateForm(false);
      setEventForm((prev) => ({ ...prev, title: "", description: "", address: "" }));
      await fetchPlaces();
      setSelectedPlaceId(res.place.id);
      if (onActivityChanged) onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRsvp(place) {
    if (!user) {
      onRequireAuth();
      return;
    }
    setFeedback({ type: "", text: "" });
    try {
      const action = place.is_going ? "leave" : "join";
      const res = await apiRequest(`/api/places/${place.id}/rsvp`, {
        method: "POST",
        body: { action }
      });
      const badgeNote =
        res.newly_unlocked_badges?.length > 0
          ? ` Nouveau badge débloqué : ${res.newly_unlocked_badges
              .map((b) => `${b.name} (+${b.xp_reward} XP)`)
              .join(", ")} !`
          : "";
      setFeedback({
        type: "ok",
        text: res.is_going
          ? `Inscription confirmée à « ${place.title} » !${badgeNote}`
          : `Participation annulée pour « ${place.title} ».`
      });
      await fetchPlaces();
      if (onActivityChanged) onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  async function handleDeleteEvent(placeId) {
    try {
      await apiRequest(`/api/places/${placeId}`, { method: "DELETE" });
      setFeedback({ type: "ok", text: "Événement supprimé." });
      await fetchPlaces();
      if (onActivityChanged) onActivityChanged();
    } catch (err) {
      setFeedback({ type: "err", text: err.message });
    }
  }

  return (
    <div className="map-page-stack">
      <section className="card">
        <div className="topbar-row" style={{ marginBottom: "10px" }}>
          <div>
            <h2 style={{ margin: 0 }}>
              CARTE DES SALLES, PARCS ET SÉANCES COLLECTIVES
            </h2>
            <p className="muted-text" style={{ margin: "3px 0 0" }}>
              Découvrez les salles partenaires, aires extérieures et entraînements étudiants autour de votre campus.
            </p>
          </div>
          <div className="quick-actions">
            <button type="button" className="secondary-btn" onClick={handleLocateMe}>
              Autour de moi (GPS)
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                if (!user) {
                  onRequireAuth();
                  return;
                }
                setShowCreateForm((prev) => !prev);
              }}
            >
              {showCreateForm ? "Fermer le formulaire" : "+ Créer un événement"}
            </button>
          </div>
        </div>

        {gpsStatus && <div className="gps-banner">{gpsStatus}</div>}

        {feedback.text && (
          <div
            className={`alert ${feedback.type === "ok" ? "alert-ok" : "alert-err"}`}
            style={{ marginBottom: "12px" }}
          >
            {feedback.text}
          </div>
        )}

        <div className="campus-shortcuts">
          <span className="muted-text" style={{ fontWeight: 700 }}>
            Accès rapide campus :
          </span>
          {campuses.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`chip-filter-btn ${
                Number(campusFilter) === c.id ? "active" : ""
              }`}
              onClick={() => handleFocusCampus(c)}
            >
              {c.city}
            </button>
          ))}
          <button type="button" className="chip-filter-btn" onClick={handleResetFilters}>
            Réinitialiser (France entière)
          </button>
        </div>

        <div className="map-filters-grid">
          <label className="field">
            <span>Type de lieu</span>
            <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
              <option value="all">Tous (Salles, Spots &amp; Événements)</option>
              <option value="gym">Salles partenaires (Gym)</option>
              <option value="spot">Spots Street-Workout / Plein air</option>
              <option value="event">Événements étudiants</option>
            </select>
          </label>

          <label className="field">
            <span>Rayon autour du point GPS / campus</span>
            <select value={radiusFilter} onChange={(e) => setRadiusFilter(e.target.value)}>
              <option value="">Sans limite de distance</option>
              <option value="1">Moins de 1 km</option>
              <option value="3">Moins de 3 km</option>
              <option value="5">Moins de 5 km</option>
              <option value="15">Moins de 15 km</option>
            </select>
          </label>

          <label className="field">
            <span>Campus de rattachement</span>
            <select value={campusFilter} onChange={(e) => setCampusFilter(e.target.value)}>
              <option value="">Tous les campus</option>
              {campuses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Discipline sportive</span>
            <div style={{ display: "flex", gap: "6px" }}>
              <input
                type="text"
                placeholder="Running, Calisthenics..."
                value={sportFilter}
                onChange={(e) => setSportFilter(e.target.value)}
              />
              <button
                type="button"
                className="outline-btn"
                onClick={() => fetchPlaces()}
              >
                Filtrer
              </button>
            </div>
          </label>
        </div>

        {showCreateForm && (
          <form className="event-create-panel" onSubmit={handleCreateEvent}>
            <div className="topbar-row" style={{ marginBottom: "8px" }}>
              <h3 style={{ margin: 0, color: "#1E2E5C" }}>
                Organiser un événement sportif géolocalisé
              </h3>
              <span className="badge badge-soon">
                Astuce : cliquez sur la carte ci-dessous pour placer le point GPS !
              </span>
            </div>

            <div className="form-row-2">
              <label className="field">
                <span>Titre de l&apos;événement</span>
                <input
                  type="text"
                  required
                  minLength={3}
                  placeholder="Ex : Footing Nocturne Parc de la Tête d'Or"
                  value={eventForm.title}
                  onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Discipline</span>
                <input
                  type="text"
                  required
                  value={eventForm.sport}
                  onChange={(e) => setEventForm({ ...eventForm, sport: e.target.value })}
                />
              </label>
            </div>

            <div className="form-row-3">
              <label className="field">
                <span>Campus</span>
                <select
                  value={eventForm.campus_id}
                  onChange={(e) => {
                    const cid = Number(e.target.value);
                    const cmp = campuses.find((c) => c.id === cid);
                    setEventForm({
                      ...eventForm,
                      campus_id: cid,
                      latitude: cmp ? cmp.latitude : eventForm.latitude,
                      longitude: cmp ? cmp.longitude : eventForm.longitude
                    });
                  }}
                >
                  {campuses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Date &amp; heure de rendez-vous</span>
                <input
                  type="datetime-local"
                  required
                  value={eventForm.starts_at}
                  onChange={(e) =>
                    setEventForm({ ...eventForm, starts_at: e.target.value })
                  }
                />
              </label>

              <label className="field">
                <span>Nombre de places max</span>
                <input
                  type="number"
                  min={1}
                  max={500}
                  required
                  value={eventForm.max_participants}
                  onChange={(e) =>
                    setEventForm({ ...eventForm, max_participants: e.target.value })
                  }
                />
              </label>
            </div>

            <div className="form-row-3">
              <label className="field">
                <span>Adresse / Point de RDV</span>
                <input
                  type="text"
                  placeholder="Ex : Entrée Sud Halle Tony Garnier"
                  value={eventForm.address}
                  onChange={(e) => setEventForm({ ...eventForm, address: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Latitude GPS</span>
                <input
                  type="number"
                  step="0.00001"
                  required
                  value={eventForm.latitude}
                  onChange={(e) =>
                    setEventForm({ ...eventForm, latitude: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Longitude GPS</span>
                <input
                  type="number"
                  step="0.00001"
                  required
                  value={eventForm.longitude}
                  onChange={(e) =>
                    setEventForm({ ...eventForm, longitude: e.target.value })
                  }
                />
              </label>
            </div>

            <label className="field" style={{ marginTop: "8px" }}>
              <span>Description &amp; niveau conseillé</span>
              <input
                type="text"
                placeholder="Allure conviviale, ouvert à tous les étudiants du campus !"
                value={eventForm.description}
                onChange={(e) =>
                  setEventForm({ ...eventForm, description: e.target.value })
                }
              />
            </label>

            <div className="quick-actions" style={{ marginTop: "10px" }}>
              <button type="submit" className="primary-btn" disabled={submitting}>
                {submitting ? "Publication..." : "Publier l'événement (+20 XP)"}
              </button>
            </div>
          </form>
        )}

        <div className="map-legend-bar">
          <span>
            <i className="legend-dot" style={{ background: "#E61A5F" }} /> Salle partenaire
          </span>
          <span>
            <i className="legend-dot" style={{ background: "#1B8A3D" }} /> Spot extérieur
          </span>
          <span>
            <i className="legend-dot" style={{ background: "#1E2E5C" }} /> Événement étudiant
          </span>
          <span>
            <i className="legend-dot" style={{ background: "#0284C7" }} /> Point GPS de référence
          </span>
          <strong style={{ marginLeft: "auto", color: "#1E2E5C" }}>
            {places.length} résultat{places.length > 1 ? "s" : ""} affiché
            {places.length > 1 ? "s" : ""}
          </strong>
        </div>

        <div className="map-canvas-wrap">
          <div ref={mapContainerRef} className="leaflet-map-box" />
        </div>
      </section>

      <section className="card">
        <h2>
          LIEUX ET ÉVÉNEMENTS À PROXIMITÉ ({places.length})
        </h2>
        {loading ? (
          <p className="muted-text">Chargement des coordonnées géographiques...</p>
        ) : places.length === 0 ? (
          <p className="muted-text">
            Aucun lieu ou événement trouvé dans ce périmètre. Élargissez le rayon kilométrique ou créez un événement !
          </p>
        ) : (
          <div className="grid-cards" style={{ marginBottom: 0 }}>
            {places.map((p) => {
              const meta = KIND_META[p.kind] || KIND_META.gym;
              const isEvent = p.kind === "event";
              return (
                <article
                  key={p.id}
                  className={`place-card ${selectedPlaceId === p.id ? "selected" : ""}`}
                >
                  <div>
                    <div className="topbar-row" style={{ marginBottom: "6px" }}>
                      <span
                        className="badge"
                        style={{ background: meta.bg, color: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        {p.distance_km != null && (
                          <span className="distance-pill">{p.distance_km} km</span>
                        )}
                        <span className="badge badge-soon">{p.sport}</span>
                      </div>
                    </div>

                    <h3 className="place-title">{p.title}</h3>
                    <p className="muted-text" style={{ margin: "2px 0 6px" }}>
                      {p.address} • <strong>{p.campus_city}</strong>
                    </p>
                    {p.description && (
                      <p style={{ margin: "0 0 8px", fontSize: "13px" }}>{p.description}</p>
                    )}

                    {isEvent && (
                      <div className="event-meta-box">
                        <div className="topbar-row">
                          <span>
                            RDV :{" "}
                            <strong>
                              {p.starts_at
                                ? new Date(p.starts_at).toLocaleString("fr-FR", {
                                    day: "2-digit",
                                    month: "short",
                                    hour: "2-digit",
                                    minute: "2-digit"
                                  })
                                : "À venir"}
                            </strong>
                          </span>
                          <span>
                            Places :{" "}
                            <strong>
                              {p.rsvp_count} / {p.max_participants ?? "∞"}
                            </strong>{" "}
                            {p.is_full && (
                              <em style={{ color: "#BE123C", fontWeight: 800, fontStyle: "normal" }}>
                                (COMPLET)
                              </em>
                            )}
                          </span>
                        </div>
                        {p.participants?.length > 0 && (
                          <div className="members-chips" style={{ marginTop: "6px" }}>
                            {p.participants.map((part) => (
                              <span key={part.user_id} className="member-chip">
                                <span className="chip-initials">
                                  {part.username.slice(0, 2).toUpperCase()}
                                </span>
                                <span>{part.username}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="group-actions-row" style={{ marginTop: "10px" }}>
                    <button
                      type="button"
                      className="outline-btn"
                      onClick={() => focusPlaceOnMap(p)}
                    >
                      Voir sur la carte
                    </button>

                    <div className="group-btns">
                      <button
                        type="button"
                        className={p.is_going ? "outline-btn" : "primary-btn"}
                        disabled={!p.is_going && p.is_full}
                        onClick={() => handleRsvp(p)}
                      >
                        {p.is_going
                          ? "Inscrit (annuler)"
                          : p.is_full
                          ? "Complet"
                          : isEvent
                          ? "Je participe"
                          : `Je m'y entraîne (${p.rsvp_count})`}
                      </button>

                      {user && p.created_by === user.id && (
                        <button
                          type="button"
                          className="danger-btn"
                          onClick={() => handleDeleteEvent(p.id)}
                        >
                          Supprimer
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
