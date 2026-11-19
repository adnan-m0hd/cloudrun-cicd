import io
import json
import logging
from app.app import app, ITEMS, CloudLoggingFormatter


def setup_function():
    ITEMS.clear()


def test_health():
    client = app.test_client()
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'healthy'
    assert 'X-Request-Id' in res.headers
    assert float(res.headers['X-Response-Time-Ms']) >= 0


def test_index():
    client = app.test_client()
    res = client.get('/')
    assert res.status_code == 200
    assert res.get_json()['service'] == 'cloudrun-cicd'


def test_create_and_list_items():
    client = app.test_client()
    bad = client.post('/api/items', json={})
    assert bad.status_code == 400

    created = client.post('/api/items', json={'name': 'observability-test'})
    assert created.status_code == 201
    assert created.get_json()['name'] == 'observability-test'

    listed = client.get('/api/items')
    assert listed.status_code == 200
    assert any(i['name'] == 'observability-test' for i in listed.get_json()['items'])


def test_structured_json_logging():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(CloudLoggingFormatter())
    logger = logging.getLogger('cloudrun-app')
    logger.addHandler(handler)

    try:
        client = app.test_client()
        client.get('/health')
    finally:
        logger.removeHandler(handler)

    lines = [line for line in stream.getvalue().strip().splitlines() if line.startswith('{')]
    assert len(lines) >= 1
    log_record = json.loads(lines[-1])
    assert log_record['severity'] == 'INFO'
    assert 'latency_ms' in log_record
    assert log_record['httpRequest']['path'] == '/health'
