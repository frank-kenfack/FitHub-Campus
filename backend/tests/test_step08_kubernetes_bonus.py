"""Tests automatises de l'Etape 8 : Validation de l'orchestration Kubernetes (+20 % Bonus)."""

from pathlib import Path

import yaml


def _resolve_k8s_dir() -> Path:
    """Localise le dossier k8s/ dans le conteneur (/app/k8s) ou a la racine du depot."""
    candidates = [
        Path("/app/k8s"),
        Path(__file__).resolve().parents[2] / "k8s",
        Path(__file__).resolve().parents[1] / "k8s",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise AssertionError(f"Dossier k8s/ introuvable parmi {candidates}")


def _load_all_k8s_resources() -> list[dict]:
    """Charge tous les objets Kubernetes definis dans les manifests 00..08."""
    k8s_dir = _resolve_k8s_dir()
    resources: list[dict] = []
    for yaml_file in sorted(k8s_dir.glob("[0-9][0-9]-*.yaml")):
        with yaml_file.open("r", encoding="utf-8") as fh:
            for doc in yaml.safe_load_all(fh):
                if isinstance(doc, dict) and "kind" in doc:
                    resources.append(doc)
    return resources


def test_k8s_directory_and_kustomization_complete():
    """US-8.4 : Les 9 manifests numerotes et kustomization.yaml sont presents et valides."""
    k8s_dir = _resolve_k8s_dir()
    expected_files = [
        "00-namespace.yaml",
        "01-configmap.yaml",
        "02-secret.yaml",
        "03-pvc.yaml",
        "04-postgres.yaml",
        "05-redis.yaml",
        "06-backend.yaml",
        "07-frontend.yaml",
        "08-ingress.yaml",
        "kustomization.yaml",
    ]
    for fname in expected_files:
        fpath = k8s_dir / fname
        assert fpath.is_file(), f"Manifest manquant : {fname}"

    with (k8s_dir / "kustomization.yaml").open("r", encoding="utf-8") as fh:
        kust = yaml.safe_load(fh)
    assert kust["kind"] == "Kustomization"
    assert kust["namespace"] == "fithub-campus"
    assert set(kust["resources"]) == set(expected_files[:-1])


def test_k8s_namespace_configmap_and_rfc7518_secrets():
    """US-8.4 : Namespace fithub-campus, ConfigMap et Secret conforme RFC 7518 (>= 36 octets)."""
    resources = _load_all_k8s_resources()
    namespaces = [r for r in resources if r["kind"] == "Namespace"]
    assert len(namespaces) == 1
    assert namespaces[0]["metadata"]["name"] == "fithub-campus"

    cms = [r for r in resources if r["kind"] == "ConfigMap"]
    assert len(cms) == 1
    cm_data = cms[0]["data"]
    assert cm_data["REDIS_URL"] == "redis://fithub-redis:6379/0"
    assert cm_data["UPLOAD_FOLDER"] == "/app/uploads"

    secrets = [r for r in resources if r["kind"] == "Secret"]
    assert len(secrets) == 1
    sec_data = secrets[0]["stringData"]
    assert len(sec_data["SECRET_KEY"]) >= 36
    assert len(sec_data["JWT_SECRET_KEY"]) >= 36
    assert "@fithub-postgres:5432/" in sec_data["DATABASE_URL"]


def test_k8s_persistent_volume_claims_for_db_and_uploads():
    """US-8.4 : Persistance des donnees PostgreSQL et des medias via 2 PVC dedies."""
    resources = _load_all_k8s_resources()
    pvcs = {
        r["metadata"]["name"]: r
        for r in resources
        if r["kind"] == "PersistentVolumeClaim"
    }
    assert {"postgres-data-pvc", "uploads-data-pvc"} <= set(pvcs.keys())
    assert pvcs["postgres-data-pvc"]["spec"]["resources"]["requests"]["storage"] == "5Gi"
    assert pvcs["uploads-data-pvc"]["spec"]["resources"]["requests"]["storage"] == "2Gi"


def test_k8s_deployments_high_availability_probes_and_non_root():
    """US-8.4 : Les 4 Deployments definissent des probes, limites CPU/RAM, et >= 2 replicas pour web/api."""
    resources = _load_all_k8s_resources()
    deployments = {
        r["metadata"]["name"]: r
        for r in resources
        if r["kind"] == "Deployment"
    }
    assert {
        "fithub-postgres",
        "fithub-redis",
        "fithub-backend",
        "fithub-frontend",
    } <= set(deployments.keys())

    # Haute disponibilite (>= 2 replicas) et RollingUpdate sans coupure pour backend & frontend
    for ha_name in ("fithub-backend", "fithub-frontend"):
        dep = deployments[ha_name]
        assert dep["spec"]["replicas"] >= 2
        assert dep["spec"]["strategy"]["type"] == "RollingUpdate"
        assert dep["spec"]["strategy"]["rollingUpdate"]["maxUnavailable"] == 0
        pod_sec = dep["spec"]["template"]["spec"].get("securityContext", {})
        assert pod_sec.get("runAsNonRoot") is True

    # Readiness & Liveness probes + resources requests/limits sur les 4 workloads
    for name, dep in deployments.items():
        container = dep["spec"]["template"]["spec"]["containers"][0]
        assert "readinessProbe" in container, f"readinessProbe manquante sur {name}"
        assert "livenessProbe" in container, f"livenessProbe manquante sur {name}"
        res_cfg = container.get("resources", {})
        assert "requests" in res_cfg and "limits" in res_cfg, f"resources manquantes sur {name}"


def test_k8s_services_and_horizontal_pod_autoscaler():
    """US-8.4 : 4 Services ClusterIP exposent les ports internes et un HPA supervise le backend."""
    resources = _load_all_k8s_resources()
    services = {
        r["metadata"]["name"]: r
        for r in resources
        if r["kind"] == "Service"
    }
    expected_ports = {
        "fithub-postgres": 5432,
        "fithub-redis": 6379,
        "fithub-backend": 5000,
        "fithub-frontend": 80,
    }
    for svc_name, port in expected_ports.items():
        assert svc_name in services
        svc = services[svc_name]
        assert svc["spec"]["type"] == "ClusterIP"
        assert svc["spec"]["ports"][0]["port"] == port

    hpas = [r for r in resources if r["kind"] == "HorizontalPodAutoscaler"]
    assert len(hpas) == 1
    assert hpas[0]["spec"]["scaleTargetRef"]["name"] == "fithub-backend"
    assert hpas[0]["spec"]["minReplicas"] >= 2
    assert hpas[0]["spec"]["maxReplicas"] >= 4


def test_k8s_ingress_routes_http_and_websocket_socketio():
    """US-8.4 : L'Ingress NGINX route /, /api, /uploads et /socket.io avec support WebSocket."""
    resources = _load_all_k8s_resources()
    ingresses = [r for r in resources if r["kind"] == "Ingress"]
    assert len(ingresses) == 1
    ing = ingresses[0]

    annotations = ing["metadata"]["annotations"]
    assert annotations.get("nginx.ingress.kubernetes.io/websocket-services") == "fithub-backend"
    assert int(annotations.get("nginx.ingress.kubernetes.io/proxy-read-timeout", "0")) >= 1800

    paths = {
        p["path"]: p["backend"]["service"]["name"]
        for p in ing["spec"]["rules"][0]["http"]["paths"]
    }
    assert paths["/api"] == "fithub-backend"
    assert paths["/uploads"] == "fithub-backend"
    assert paths["/socket.io"] == "fithub-backend"
    assert paths["/"] == "fithub-frontend"


def test_health_endpoint_reports_step08():
    """US-8.4 : L'endpoint /api/health atteste le passage a l'Etape 8 finale."""
    from app import create_app
    from app.config import TestingConfig

    app = create_app(TestingConfig)
    with app.test_client() as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.get_json()["step"] == "step-08/kubernetes-bonus"
