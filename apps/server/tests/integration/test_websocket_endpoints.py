import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import create_access_token
from app.core.websocket import ws_manager


def test_online_doctors_endpoint_requires_debug(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    response = client.get("/api/v1/ws/online-doctors")

    assert response.status_code == 403
    assert "仅在调试模式下可用" in response.text


def test_doctor_websocket_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/doctor/doctor-1?token=invalid-token"):
            pass

    assert exc_info.value.code == 4001


def test_doctor_websocket_accepts_matching_doctor_token(client):
    token = create_access_token({"sub": "doctor-1", "doctor_id": "doctor-1", "type": "doctor"})

    with client.websocket_connect(f"/api/v1/ws/doctor/doctor-1?token={token}") as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "CONNECTED"

        websocket.send_json({"type": "PING", "timestamp": 123})
        pong = websocket.receive_json()
        assert pong == {"type": "PONG", "timestamp": 123}

    assert "doctor-1" not in ws_manager.get_online_doctors()
