import logging
from functools import wraps
from typing import Callable, Optional

from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)

from django_iran_ip.conf import conf
from django_iran_ip.core.blacklist import IPBlacklist
from django_iran_ip.core.validators import IranIPChecker

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    استخراج IP از request.
    
    اول از attribute ای که middleware ست کرده می‌خواند،
    اگر نبود از REMOTE_ADDR استفاده می‌کند.
    """
    ip = getattr(request, 'client_ip', None)
    if ip:
        return ip

    return request.META.get('REMOTE_ADDR')


def _is_json_request(request: HttpRequest) -> bool:
    """تشخیص درخواست JSON بر اساس Accept header"""
    accept = request.META.get('HTTP_ACCEPT', '')
    return 'application/json' in accept


def _error_response(
    request: HttpRequest,
    message: str,
    status: int = 403,
) -> HttpResponse:
    """
    پاسخ خطا با فرمت مناسب (JSON یا plain) و status دلخواه.
    
    نکته: از HttpResponse مستقیم استفاده می‌کنیم چون HttpResponseForbidden
    همیشه status=403 می‌دهد و پارامتر status را نادیده می‌گیرد.
    """
    if _is_json_request(request):
        return JsonResponse({'error': message}, status=status)
    return HttpResponse(message, status=status)


# ============================================================
# Decorator 1: iran_only
# ============================================================

def iran_only(view_func: Callable) -> Callable:
    """
    فقط کاربران با IP ایرانی اجازه دسترسی دارند.
    
    Usage:
        @iran_only
        def my_view(request):
            return render(request, 'iran.html')
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        ip = _get_client_ip(request)

        if not ip:
            logger.warning("iran_only: unable to detect client IP")
            return _error_response(request, "IP قابل شناسایی نیست", status=403)

        checker = IranIPChecker()
        if not checker.is_iran_ip(ip):
            logger.info(f"iran_only: access denied for non-Iranian IP {ip}")
            return _error_response(
                request,
                "فقط کاربران ایرانی مجاز هستند",
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# Decorator 2: block_non_iran
# ============================================================

def block_non_iran(view_func: Callable) -> Callable:
    """
    مسدودسازی IP های غیر ایرانی.
    
    Usage:
        @block_non_iran
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        ip = _get_client_ip(request)

        if not ip:
            logger.warning("block_non_iran: unable to detect client IP")
            return _error_response(request, "IP قابل شناسایی نیست", status=403)

        checker = IranIPChecker()
        if not checker.is_iran_ip(ip):
            logger.info(f"block_non_iran: blocked non-Iranian IP {ip}")
            return _error_response(
                request,
                "دسترسی از خارج از ایران مسدود است",
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# Decorator 3: block_blacklisted
# ============================================================

def block_blacklisted(view_func: Callable) -> Callable:
    """
    مسدودسازی IP هایی که در لیست سیاه هستند.
    
    Usage:
        @block_blacklisted
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        ip = _get_client_ip(request)

        if ip:
            blacklist = IPBlacklist()
            if blacklist.is_blocked(ip):
                reason = blacklist.get_reason(ip)
                logger.warning(
                    f"block_blacklisted: blocked IP {ip}, reason={reason}"
                )
                message = (
                    f"دسترسی مسدود است: {reason}"
                    if reason
                    else "دسترسی مسدود است"
                )
                return _error_response(request, message, status=403)

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# Decorator 4: rate_limit_by_ip
# ============================================================

def rate_limit_by_ip(
    max_requests: Optional[int] = None,
    period: Optional[int] = None,
    key_prefix: str = "django_iran_ip:rate",
) -> Callable:
    """
    محدودیت نرخ درخواست بر اساس IP.
    
    Usage:
        @rate_limit_by_ip(max_requests=10, period=60)
        def my_view(request):
            ...
    """
    _max = max_requests if max_requests is not None else getattr(
        conf, 'SPOOFING_RATE_LIMIT', 100
    )
    _period = period if period is not None else 3600

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            ip = _get_client_ip(request)

            if ip:
                cache_key = f"{key_prefix}:{ip}"
                current = cache.get(cache_key, 0)

                if current >= _max:
                    logger.warning(
                        f"rate_limit_by_ip: IP {ip} exceeded "
                        f"{_max} requests in {_period}s"
                    )
                    return _error_response(
                        request,
                        "تعداد درخواست‌ها بیش از حد مجاز",
                        status=429,
                    )

                try:
                    cache.set(cache_key, current + 1, _period)
                except Exception as exc:
                    logger.exception(f"rate_limit_by_ip: cache error: {exc}")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# ============================================================
# Export
# ============================================================

__all__ = [
    'iran_only',
    'block_non_iran',
    'block_blacklisted',
    'rate_limit_by_ip',
]