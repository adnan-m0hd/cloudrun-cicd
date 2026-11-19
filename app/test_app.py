import io
import json
import logging
from app.app import app, ITEMS, CloudLoggingFormatter


def setup_function():
    ITEMS.clear()


def test_health():
    client = app.test_client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"
    assert "X-Request-Id" in res.headers
    assert float(res.headers["X-Response-Time-Ms"]) >= 0


def test_index():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert res.get_json()["service"] == "cloudrun-cicd"


def test_create_and_list_items():
    client = app.test_client()
    bad = client.post("/api/items", json={})
    assert bad.status_code == 400

    created = client.post("/api/items", json={"name": "observability-test"})
    assert created.status_code == 201
    assert created.get_json()["name"] == "observability-test"

    listed = client.get("/api/items")
    assert listed.status_code == 200
    assert any(i["name"] == "observability-test" for i in listed.get_json()["items"])


def test_slow_endpoint():
    client = app.test_client()
    res = client.get("/slow?ms=50")
    assert res.status_code == 200
    body = res.get_json()
    assert body["applied_ms"] == 50
    assert float(res.headers["X-Response-Time-Ms"]) >= 40

    bad = client.get("/slow?ms=invalid")
    assert bad.status_code == 400


def test_fail_endpoint_and_error_logging():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(CloudLoggingFormatter())
    logger = logging.getLogger("cloudrun-app")
    logger.addHandler(handler)

    try:
        client = app.test_client()
        res = client.get("/fail")
    finally:
        logger.removeHandler(handler)

    assert res.status_code == 500
    assert res.get_json()["error"] == "Simulated internal server error"

    lines = [json.loads(line) for line in stream.getvalue().strip().splitlines() if line.startswith("{")]
    assert len(lines) >= 2
    assert any(entry["severity"] == "ERROR" and entry.get("fault_type") == "simulated_500" for entry in lines)
    assert lines[-1]["severity"] == "ERROR"
    assert lines[-1]["httpRequest"]["status"] == 500