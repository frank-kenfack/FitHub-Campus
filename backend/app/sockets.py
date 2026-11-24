"""Gestionnaires d'evenements WebSocket temps reel (Flask-SocketIO)."""

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, emit, join_room

from app.extensions import db, socketio
from app.models import User
from app.services.buddy_matching import create_and_emit_encouragement

# Association sid Socket.IO -> user_id authentifie
SOCKET_USERS: dict[str, int] = {}


def _extract_token(auth_payload: dict | None) -> str:
    if isinstance(auth_payload, dict) and auth_payload.get("token"):
        return str(auth_payload["token"]).removeprefix("Bearer ").strip()
    query_tok = request.args.get("token", "")
    if query_tok:
        return query_tok.removeprefix("Bearer ").strip()
    header_auth = request.headers.get("Authorization", "")
    if header_auth.startswith("Bearer "):
        return header_auth.removeprefix("Bearer ").strip()
    return ""


@socketio.on("connect")
def handle_socket_connect(auth: dict | None = None):
    """Authentifie la connexion WebSocket par JWT et abonne l'etudiant a sa room privee."""
    raw_token = _extract_token(auth)
    if not raw_token:
        disconnect()
        return False

    try:
        decoded = decode_token(raw_token)
        uid = int(decoded["sub"])
    except Exception:
        disconnect()
        return False

    user = db.session.get(User, uid)
    if user is None:
        disconnect()
        return False

    SOCKET_USERS[request.sid] = uid
    room_name = f"user_{uid}"
    join_room(room_name)
    emit("connected_ack", {"user_id": uid, "username": user.username, "room": room_name})
    return True


@socketio.on("disconnect")
def handle_socket_disconnect():
    """Nettoie l'association sid lors de la fermeture de la session WebSocket."""
    SOCKET_USERS.pop(request.sid, None)


@socketio.on("send_encouragement")
def handle_socket_encouragement(incoming_message: dict | None):
    sender_id = SOCKET_USERS.get(request.sid)
    if not sender_id:
        emit("encouragement_error", {"error": "Session WebSocket non authentifiee."})
        return {"ok": False, "error": "Non authentifie"}

    payload_in = incoming_message or {}
    try:
        receiver_id = int(payload_in.get("receiver_id", 0))
    except (TypeError, ValueError):
        emit("encouragement_error", {"error": "Destinataire invalide."})
        return {"ok": False, "error": "Destinataire invalide"}

    message = str(payload_in.get("message") or "")
    created, err, _status = create_and_emit_encouragement(sender_id, receiver_id, message)
    if err:
        emit("encouragement_error", {"error": err})
        return {"ok": False, "error": err}

    return {"ok": True, "encouragement": created}
