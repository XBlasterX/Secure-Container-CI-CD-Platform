from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from src.main import app

client = TestClient(app)


def test_health():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz():
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.0.1"}


def test_unknown():
    response = client.get("/unknown")
    assert response.status_code == 404


def test_events_invalid_severity():
    data = {
        "source": "firewall-01",
        "severity": "wrong_severity",
        "message": "SSH brute force detected",
    }
    response = client.post("/events", json=data)
    assert response.status_code == 422


def test_events_missing_message():
    data = {
        "source": "firewall-01",
        "severity": "critical",
    }
    response = client.post("/events", json=data)
    assert response.status_code == 422


def test_events_valid():
    data = {
        "source": "firewall-01",
        "severity": "critical",
        "message": "SSH brute force detected",
    }
    response = client.post("/events", json=data)
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_events_whitespace_source():
    data = {
        "source": "   ",
        "severity": "critical",
        "message": "SSH brute force detected",
    }
    response = client.post("/events", json=data)
    assert response.status_code == 422


def test_events_extra_field():
    data = {
        "source": "firewall-01",
        "severity": "critical",
        "message": "SSH brute force detected",
        "unknoen_field": "",
    }
    response = client.post("/events", json=data)
    assert response.status_code == 422


def test_events_message_too_long():
    data = {
        "source": "firewall-01",
        "severity": "critical",
        "message": "a" * 501,
    }
    response = client.post("/events", json=data)
    assert response.status_code == 422


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    before = (
        REGISTRY.get_sample_value(
            "infrastructure_events_accepted_total", {"severity": "critical"}
        )
        or 0
    )


def test_metrics_counter_increment():
    before = (
        REGISTRY.get_sample_value(
            "infrastructure_events_accepted_total", {"severity": "critical"}
        )
        or 0
    )

    data = {
        "source": "firewall-01",
        "severity": "critical",
        "message": "SSH brute force detected",
    }

    response = client.post("/events", json=data)

    after = (
        REGISTRY.get_sample_value(
            "infrastructure_events_accepted_total", {"severity": "critical"}
        )
        or 0
    )

    assert response.status_code == 200
    assert after == before + 1


def test_metrics_invalid_event():
    before = (
        REGISTRY.get_sample_value(
            "infrastructure_events_accepted_total", {"severity": "critical"}
        )
        or 0
    )

    data = {
        "source": "firewall-01",
        "severity": "banana",
        "message": "SSH brute force detected",
    }

    response = client.post("/events", json=data)

    after = (
        REGISTRY.get_sample_value(
            "infrastructure_events_accepted_total", {"severity": "critical"}
        )
        or 0
    )

    assert response.status_code == 422
    assert after == before
