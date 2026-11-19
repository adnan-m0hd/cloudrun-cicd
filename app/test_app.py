import pytest
from app import app, ITEMS


@pytest.fixture
def client():
    ITEMS.clear()
    return app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_index_reports_version(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "version" in r.get_json()


def test_add_and_list_items(client):
    r = client.post("/api/items", json={"name": "first"})
    assert r.status_code == 201
    r = client.get("/api/items")
    assert r.get_json()["items"] == [{"id": 1, "name": "first"}]


def test_add_item_validation(client):
    r = client.post("/api/items", json={})
    assert r.status_code == 400
