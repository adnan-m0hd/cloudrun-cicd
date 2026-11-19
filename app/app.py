import os
from flask import Flask, jsonify, request

app = Flask(__name__)

VERSION = os.environ.get("APP_VERSION", "dev")
ITEMS = []  # in-memory only; resets on restart (fine for a CI/CD demo)


@app.get("/")
def index():
    return jsonify(service="cloudrun-cicd-demo", version=VERSION)


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


@app.get("/api/items")
def list_items():
    return jsonify(items=ITEMS)


@app.post("/api/items")
def add_item():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name or not isinstance(name, str):
        return jsonify(error="'name' (string) is required"), 400
    item = {"id": len(ITEMS) + 1, "name": name}
    ITEMS.append(item)
    return jsonify(item), 201
