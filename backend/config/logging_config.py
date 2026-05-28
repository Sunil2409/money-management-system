"""
Logging Configuration — Money Manager

Provides structured logging for development (console) and production (JSON).
Log level is controlled by the LOG_LEVEL environment variable (default: INFO).

Usage in any module:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("User registered", extra={"username": user.username})
"""

from decouple import config

LOG_LEVEL = config('LOG_LEVEL', default='INFO')

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    # ── Formatters ──────────────────────────────────────────
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    # ── Handlers ────────────────────────────────────────────
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },

    # ── Loggers ─────────────────────────────────────────────
    'loggers': {
        # Django internals
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Application loggers
        'accounts': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'transactions': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'health': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },

    # ── Root Logger ─────────────────────────────────────────
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}
