"""
Health Check Endpoint — Money Manager

Validates database and cache connectivity for container orchestration.
Used by Docker HEALTHCHECK and load balancer health probes.

Returns:
    200: {"status": "healthy", "db": "ok", "cache": "ok"}
    503: {"status": "unhealthy", ...} with failing component details
"""

import logging

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Lightweight health probe — checks database and cache connectivity.

    This endpoint is unauthenticated by design (health probes from
    orchestrators like Docker/Kubernetes don't carry auth tokens).
    """
    health = {'status': 'healthy', 'db': 'ok', 'cache': 'ok'}
    status_code = 200

    # ── Database Check ────────────────────────────────────────
    try:
        connection.ensure_connection()
    except Exception as exc:
        health['db'] = 'unreachable'
        health['status'] = 'unhealthy'
        status_code = 503
        logger.error("Health check: database unreachable — %s", exc)

    # ── Cache Check ───────────────────────────────────────────
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise Exception('Cache read-back failed')
    except Exception as exc:
        health['cache'] = 'unreachable'
        health['status'] = 'unhealthy'
        status_code = 503
        logger.error("Health check: cache unreachable — %s", exc)

    return JsonResponse(health, status=status_code)
