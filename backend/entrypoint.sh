#!/bin/bash
set -e

echo "⏳ Waiting for PostgreSQL to be ready..."
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('${DB_HOST:-db}', ${DB_PORT:-5432}))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
    echo "  PostgreSQL not ready — retrying in 2s..."
    sleep 2
done

echo "✅ PostgreSQL is ready"

echo "📦 Running migrations..."
python manage.py migrate --noinput

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "🚀 Starting Gunicorn..."
exec "$@"
