FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/app.py .

# Run as a non-root user
RUN useradd --create-home appuser
USER appuser

# Cloud Run injects PORT; default to 8080 for local runs
ENV PORT=8080
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 app:app
