import json
import logging
import os
import sys
import time
import uuid
from flask import Flask, g, jsonify, request


class CloudLoggingFormatter(logging.Formatter):
    """Formats log records as single-line JSON compatible with Google Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "app_version": os.getenv("APP_VERSION", "dev"),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        if hasattr(record, "json_fields") and isinstance(record.json_fields, dict):
            log_entry.update(record.json_fields)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("cloudrun-app")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudLoggingFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logging()
app = Flask(__name__)

ITEMS = []


@app.before_request
def start_timer():
    g.start_time = time.perf_counter()
    g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))


@app.after_request
def log_request(response):
    latency_ms = round((time.perf_counter() - g.start_time) * 1000, 2)
    response.headers["X-Request-Id"] = g.request_id
    response.headers["X-Response-Time-Ms"] = str(latency_ms)

    if response.status_code >= 500:
        level = logging.ERROR
    elif response.status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO

    logger.log(
        level,
        f"{request.method} {request.path} -> {response.status_code} ({latency_ms}ms)",
        extra={
            "json_fields": {
                "request_id": g.request_id,
                "latency_ms": latency_ms,
                "httpRequest": {
                    "requestMethod": request.method,
                    "requestUrl": request.url,
                    "path": request.path,
                    "status": response.status_code,
                    "userAgent": request.headers.get("User-Agent", ""),
                },
            }
        },
    )
    return response


@app.get("/")
def index():
    return jsonify(
        {
            "service": "cloudrun-cicd",
            "status": "ok",
            "version": os.getenv("APP_VERSION", "dev"),
        }
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "version": os.getenv("APP_VERSION", "dev"),
        }
    ), 200


@app.get("/api/items")
def list_items():
    return jsonify({"items": ITEMS, "count": len(ITEMS)}), 200


@app.post("/api/items")
def create_item():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        logger.warning(
            "Validation failed on create_item",
            extra={"json_fields": {"request_id": g.request_id, "reason": "missing_name"}},
        )
        return jsonify({"error": "Field 'name' is required"}), 400

    item = {"id": len(ITEMS) + 1, "name": name}
    ITEMS.append(item)
    return jsonify(item), 201


@app.get("/slow")
def slow():
    """Simulates configurable latency (clamped between 0 and 5000ms) for SLO testing."""
    try:
        delay_ms = int(request.args.get("ms", "500"))
    except ValueError:
        return jsonify({"error": "Parameter 'ms' must be an integer"}), 400

    clamped_ms = max(0, min(delay_ms, 5000))
    time.sleep(clamped_ms / 1000.0)
    return jsonify(
        {
            "status": "delayed",
            "requested_ms": delay_ms,
            "applied_ms": clamped_ms,
        }
    ), 200


@app.get("/fail")
def fail():
    """Simulates a controlled 500 server error to test Cloud Logging ERROR severity and alerts."""
    logger.error(
        "Simulated internal server failure triggered on /fail",
        extra={"json_fields": {"request_id": g.request_id, "fault_type": "simulated_500"}},
    )
    return jsonify(
        {
            "error": "Simulated internal server error",
            "request_id": g.request_id,
        }
    ), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)