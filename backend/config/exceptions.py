"""
Custom Exception Handler — Money Manager

Provides consistent JSON error responses across all API endpoints.
Logs all errors with request context for debugging.

Response format:
    {
        "error": {
            "code": "validation_error",
            "message": "Human-readable message",
            "details": { ... }   # Field-level errors for validation
        }
    }
"""

import logging

from rest_framework.views import exception_handler
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that wraps all errors in a consistent format
    and logs them with request context.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — log it and return 500
        request = context.get('request')
        logger.exception(
            "Unhandled exception in %s %s",
            getattr(request, 'method', 'UNKNOWN'),
            getattr(request, 'path', 'UNKNOWN'),
            exc_info=exc,
        )
        return None  # Let Django handle it (returns 500)

    # ── Build consistent error response ─────────────────
    request = context.get('request')
    status_code = response.status_code

    # Determine error code
    error_code = _get_error_code(status_code)

    # Build error details
    if isinstance(response.data, dict):
        # DRF validation errors come as {field: [errors]}
        if any(isinstance(v, list) for v in response.data.values()):
            error_body = {
                'error': {
                    'code': error_code,
                    'message': 'Validation failed.',
                    'details': response.data,
                }
            }
        else:
            # Single error like {"detail": "Not found."}
            message = response.data.get('detail', str(response.data))
            error_body = {
                'error': {
                    'code': error_code,
                    'message': str(message),
                }
            }
    elif isinstance(response.data, list):
        error_body = {
            'error': {
                'code': error_code,
                'message': response.data[0] if response.data else 'An error occurred.',
            }
        }
    else:
        error_body = {
            'error': {
                'code': error_code,
                'message': str(response.data),
            }
        }

    # ── Log the error ───────────────────────────────────
    log_data = {
        'status_code': status_code,
        'method': getattr(request, 'method', 'UNKNOWN'),
        'path': getattr(request, 'path', 'UNKNOWN'),
        'user': str(getattr(request, 'user', 'anonymous')),
    }

    if status_code >= 500:
        logger.error("Server error: %s", log_data)
    elif status_code >= 400:
        logger.warning("Client error: %s", log_data)

    response.data = error_body
    return response


def _get_error_code(status_code):
    """Map HTTP status codes to human-readable error codes."""
    code_map = {
        400: 'validation_error',
        401: 'authentication_required',
        403: 'permission_denied',
        404: 'not_found',
        405: 'method_not_allowed',
        429: 'rate_limit_exceeded',
        500: 'internal_server_error',
    }
    return code_map.get(status_code, f'error_{status_code}')
