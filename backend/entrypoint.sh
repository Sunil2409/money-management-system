#!/bin/sh
set -e

echo "Waiting for PostgreSQL to accept connections..."
# Use Python instead of netcat for portability (no extra package needed)
python -c "
import socket, time, os
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))
for i in range(30):
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        break
    except (OSError, ConnectionRefusedError):
        time.sleep(1)
else:
    print('Could not connect to PostgreSQL')
    exit(1)
"
echo "PostgreSQL is online."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
