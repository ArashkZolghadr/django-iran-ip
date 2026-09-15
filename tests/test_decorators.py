"""
تست‌های دکوراتورهای django-iran-ip
"""

import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory

from django_iran_ip.contrib.django.decorators import (
    block_blacklisted,
    block_non_iran,
    iran_only,
    rate_limit_by_ip,
)
from django_iran_ip.core.blacklist import IPBlacklist


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def rf():
    """RequestFactory برای ساخت request های تست"""
    return RequestFactory()


@pytest.fixture(autouse=True)
def clear_cache():
    """پاکسازی کش قبل و بعد از هر تست"""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def dummy_view():
    """view ساده برای تست"""
    def _view(request):
        return HttpResponse("OK")
    return _view


@pytest.fixture
def make_request(rf):
    """ساخت request با client_ip مشخص"""
    def _make(ip):
        request = rf.get("/")
        request.client_ip = ip
        return request
    return _make


# ============================================================
# Iran Only
# ============================================================

class TestIranOnly:
    def test_iranian_ip_allowed(self, make_request, dummy_view):
        """IP ایرانی باید اجازه دسترسی بگیرد"""
        request = make_request("5.22.10.20")

        decorated = iran_only(dummy_view)
        response = decorated(request)

        assert response.status_code == 200
        assert response.content == b"OK"

    def test_non_iranian_ip_blocked(self, make_request, dummy_view):
        """IP غیر ایرانی باید مسدود شود"""
        request = make_request("8.8.8.8")

        decorated = iran_only(dummy_view)
        response = decorated(request)

        assert response.status_code == 403

    def test_missing_ip_blocked(self, make_request, dummy_view):
        """اگر IP قابل شناسایی نباشد، باید مسدود شود"""
        request = make_request(None)

        decorated = iran_only(dummy_view)
        response = decorated(request)

        assert response.status_code == 403


# ============================================================
# Block Non Iran
# ============================================================

class TestBlockNonIran:
    def test_iranian_ip_allowed(self, make_request, dummy_view):
        request = make_request("5.22.10.20")

        decorated = block_non_iran(dummy_view)
        response = decorated(request)

        assert response.status_code == 200

    def test_non_iranian_ip_blocked(self, make_request, dummy_view):
        request = make_request("8.8.8.8")

        decorated = block_non_iran(dummy_view)
        response = decorated(request)

        assert response.status_code == 403


# ============================================================
# Block Blacklisted
# ============================================================

class TestBlockBlacklisted:
    def test_non_blacklisted_allowed(self, make_request, dummy_view):
        request = make_request("5.22.10.20")

        decorated = block_blacklisted(dummy_view)
        response = decorated(request)

        assert response.status_code == 200

    def test_blacklisted_blocked(self, make_request, dummy_view):
        # اضافه کردن IP به لیست سیاه
        blacklist = IPBlacklist()
        blacklist.add("1.2.3.4", reason="spam", ttl=60)

        request = make_request("1.2.3.4")

        decorated = block_blacklisted(dummy_view)
        response = decorated(request)

        assert response.status_code == 403

    def test_reason_in_response(self, make_request, dummy_view):
        blacklist = IPBlacklist()
        blacklist.add("1.2.3.4", reason="brute force", ttl=60)

        request = make_request("1.2.3.4")

        decorated = block_blacklisted(dummy_view)
        response = decorated(request)

        assert b"brute force" in response.content


# ============================================================
# Rate Limit By IP
# ============================================================

class TestRateLimitByIP:
    def test_under_limit_allowed(self, make_request, dummy_view):
        request = make_request("5.22.10.20")

        decorated = rate_limit_by_ip(max_requests=5, period=60)(dummy_view)

        # 5 درخواست اول باید پاس شوند
        for i in range(5):
            response = decorated(request)
            assert response.status_code == 200, f"request {i+1} failed"

    def test_over_limit_blocked(self, make_request, dummy_view):
        request = make_request("5.22.10.20")

        decorated = rate_limit_by_ip(max_requests=3, period=60)(dummy_view)

        # 3 درخواست اول OK
        for _ in range(3):
            response = decorated(request)
            assert response.status_code == 200

        # درخواست چهارم باید 429 باشد
        response = decorated(request)
        assert response.status_code == 429

    def test_different_ips_separate_counters(self, make_request, dummy_view):
        """IP های مختلف باید شمارنده جدا داشته باشند"""
        decorated = rate_limit_by_ip(max_requests=2, period=60)(dummy_view)

        request1 = make_request("5.22.10.20")
        request2 = make_request("5.22.10.21")

        # IP اول 2 درخواست
        for _ in range(2):
            assert decorated(request1).status_code == 200
        assert decorated(request1).status_code == 429

        # IP دوم باید هنوز OK باشد
        assert decorated(request2).status_code == 200