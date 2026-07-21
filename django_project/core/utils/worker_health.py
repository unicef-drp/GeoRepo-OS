# coding=utf-8
"""
GeoRepo.

.. note:: Helper to check celery worker health for the admin dashboard.
"""

import redis.exceptions
from celery import current_app
from django.core.cache import cache
from django.utils import timezone
from kombu.exceptions import OperationalError as KombuOperationalError

CACHE_KEY = 'worker_health_status'
CACHE_TTL = 30

# Node names for the supervisord-managed celery workers defined in
# deployment/docker/supervisord.conf (celery-tile, celery-exporter,
# celery-validator). The main celery-worker program uses the container's
# hostname as its node name, so it is detected separately below.
KNOWN_NODE_NAMES = {
    'tile': 'celery@tile',
    'exporter': 'celery@exporter',
    'validate': 'celery@validate',
}

EXPECTED_WORKER_COUNT = len(KNOWN_NODE_NAMES) + 1  # + master/celery-worker

# The celery broker and the Django cache both point at the same Redis
# instance in this project, so these exception types mean Redis itself
# is unreachable rather than "workers not responding".
BROKER_CONNECTION_ERRORS = (
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
    KombuOperationalError,
)


def _safe_cache_get(key):
    """Read from cache, treating a dead Redis as a cache miss.

    :param key: Cache key to read.
    :type key: str
    :return: Cached value, or None if missing/unreachable.
    :rtype: object
    """
    try:
        return cache.get(key)
    except BROKER_CONNECTION_ERRORS:
        return None


def _safe_cache_set(key, value, ttl):
    """Write to cache, ignoring failures when Redis is unreachable.

    :param key: Cache key to write.
    :type key: str
    :param value: Value to cache.
    :type value: object
    :param ttl: Time-to-live in seconds.
    :type ttl: int
    """
    try:
        cache.set(key, value, ttl)
    except BROKER_CONNECTION_ERRORS:
        pass


def _error_payload(message):
    """Build an unhealthy payload for a failed health check.

    :param message: Human-readable error description.
    :type message: str
    :return: Health payload with all workers reported as missing.
    :rtype: dict
    """
    return {
        'healthy': False,
        'online_count': 0,
        'expected_count': EXPECTED_WORKER_COUNT,
        'online': [],
        'missing': list(KNOWN_NODE_NAMES.keys()) + ['master'],
        'error': message,
        'checked_at': timezone.now().isoformat(),
    }


def get_worker_health(timeout=3, use_cache=True):
    """Check celery worker health via a broker ping.

    :param timeout: Seconds to wait for worker replies.
    :type timeout: int
    :param use_cache: Whether to return a cached result if available.
    :type use_cache: bool
    :return: Health payload with `healthy`, `online`, `missing`, etc.
    :rtype: dict
    """
    if use_cache:
        cached = _safe_cache_get(CACHE_KEY)
        if cached is not None:
            return cached

    try:
        replies = current_app.control.inspect(timeout=timeout).ping() or {}
    except BROKER_CONNECTION_ERRORS as e:
        data = _error_payload(f'Redis is down: {e}')
        _safe_cache_set(CACHE_KEY, data, CACHE_TTL)
        return data
    except Exception as e:
        data = _error_payload(str(e))
        _safe_cache_set(CACHE_KEY, data, CACHE_TTL)
        return data

    online = set(replies.keys())

    missing = [
        role for role, node_name in KNOWN_NODE_NAMES.items()
        if node_name not in online
    ]

    # The master celery-worker program uses the container's hostname as
    # its node name, which is dynamic. Treat it as online if any node
    # besides the known tile/exporter/validate nodes responded.
    known_node_names = set(KNOWN_NODE_NAMES.values())
    master_online = bool(online - known_node_names)
    if not master_online:
        missing.append('master')

    data = {
        'healthy': not missing,
        'online_count': len(online),
        'expected_count': EXPECTED_WORKER_COUNT,
        'online': sorted(online),
        'missing': missing,
        'checked_at': timezone.now().isoformat(),
    }
    _safe_cache_set(CACHE_KEY, data, CACHE_TTL)
    return data
