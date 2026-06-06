#!/bin/bash
set -e

# ── Wait for database to be ready ────────────────────────────────
# Works with both DATABASE_URL (Render/Heroku) and individual DB_* vars (Docker Compose)
MAX_ATTEMPTS=30
ATTEMPT=0

echo "⏳ Waiting for database to be ready..."

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Try Django's connection check — handles any database backend
    if python manage.py check --database default 2>/dev/null; then
        echo "✅ Database is ready"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS — database not ready, retrying in 2s..."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ Failed to connect to database after $MAX_ATTEMPTS attempts"
    exit 1
fi

echo "📦 Running migrations..."
python manage.py migrate --noinput

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "🚀 Starting Gunicorn..."
exec "$@"
