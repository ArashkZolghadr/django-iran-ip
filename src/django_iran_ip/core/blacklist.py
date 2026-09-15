# src/django_iran_ip/core/blacklist.py
from django.core.cache import cache
from django_iran_ip.conf import settings


class IPBlacklist:
    """مدیریت لیست سیاه IP با پشتیبانی از کش"""

    CACHE_PREFIX = "django_iran_ip:blacklist:"

    def __init__(self, cache_backend=None):
        self.cache = cache_backend or cache

    def _key(self, ip: str) -> str:
        return f"{self.CACHE_PREFIX}{ip}"

    def add(self, ip: str, reason: str = "", ttl: int = 3600) -> None:
        """افزودن IP به لیست سیاه"""
        self.cache.set(self._key(ip), reason, ttl)

    def remove(self, ip: str) -> None:
        """حذف IP از لیست سیاه"""
        self.cache.delete(self._key(ip))

    def is_blocked(self, ip: str) -> bool:
        """بررسی مسدود بودن IP"""
        return self.cache.get(self._key(ip)) is not None

    def get_reason(self, ip: str) -> str:
        """دریافت دلیل مسدودسازی"""
        return self.cache.get(self._key(ip), "")