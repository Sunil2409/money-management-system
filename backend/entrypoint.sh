#!/bin/bash
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
MAX_ATTEMPTS=30
ATTEMPT=0

echo "⏳ Waiting for PostgreSQL to be ready at $DB_HOST:$DB_PORT..."
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if (echo >/dev/tcp/$DB_HOST/$DB_PORT) 2>/dev/null; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS - PostgreSQL not ready, retrying in 2s..."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ Failed to connect to PostgreSQL after $MAX_ATTEMPTS attempts"
    exit 1
fi

echo "📦 Running migrations..."
python manage.py migrate --noinput

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "🚀 Starting Gunicorn..."
exec "$@"
