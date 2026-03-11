# coding=utf-8
"""Health check API."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import logging
import shutil
import os

logger = logging.getLogger(__name__)
# Add more paths if necessary
STORAGE_PATHS = {
    'logs': getattr(settings, 'LOGS_DIRECTORY', None),
    'media': getattr(settings, 'MEDIA_ROOT', None),
    'static': getattr(settings, 'STATIC_ROOT', None),
}


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_probe(request):
    """Readiness probe - checks if the application is ready.

    :param request: HTTP request
    :type request: Request
    :return: HTTP response with readiness status
    :rtype: Response
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "storage": check_storage(),
    }

    storage_info = get_storage_info()

    # Filter out None values (optional checks)
    checks = {k: v for k, v in checks.items() if v is not None}
    all_healthy = all(checks.values())

    response_data = {
        "status": "ready" if all_healthy else "not ready",
        "checks": checks,
    }
    if storage_info:
        response_data["storage_info"] = storage_info

    return Response(
        response_data,
        status=(
            status.HTTP_200_OK if all_healthy else
            status.HTTP_503_SERVICE_UNAVAILABLE
        )
    )


def check_database():
    """Check database connectivity.

    :return: True if database is reachable, False otherwise
    :rtype: bool
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


def check_redis():
    """Check Redis connectivity.

    :return: True if Redis is reachable, False otherwise
    :rtype: bool
    """
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')

        if result != 'ok':
            logger.error(
                "Redis health check failed: could not retrieve test value"
            )
            return False

        cache.delete('health_check')
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return False


def check_storage():
    """Check storage disk space - fail if usage > 90%.

    :return: True if storage usage is below threshold, False otherwise
    :rtype: bool
    """
    try:
        critical_threshold = getattr(
            settings, 'STORAGE_CRITICAL_THRESHOLD', 90
        )
        all_healthy = True

        for name, path in STORAGE_PATHS.items():
            if not path or not os.path.exists(path):
                continue

            disk_usage = shutil.disk_usage(path)
            usage_percent = round(
                (disk_usage.used / disk_usage.total) * 100, 2
            )

            if usage_percent > critical_threshold:
                logger.error(
                    f"Storage '{name}' CRITICAL: {usage_percent:.2f}% "
                    f"used at {path}"
                )
                all_healthy = False
            else:
                logger.debug(f"Storage '{name}' OK: {usage_percent:.2f}% used")

        return all_healthy
    except Exception as e:
        logger.error(f"Storage health check failed: {str(e)}")
        return False


def get_storage_info():
    """Get detailed info for all storage locations.

    :return: Dictionary with storage info or None if no paths available
    :rtype: dict or None
    """
    storage_info = {}
    for name, path in STORAGE_PATHS.items():
        if not path or not os.path.exists(path):
            continue
        try:
            disk_usage = shutil.disk_usage(path)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            storage_info[name] = {
                "path": path,
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "usage_percent": round(usage_percent, 2),
            }
        except Exception as e:
            logger.warning(f"Could not get storage info for {name}: {e}")
    return storage_info if storage_info else None
