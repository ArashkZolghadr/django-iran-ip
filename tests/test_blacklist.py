# tests/test_blacklist.py
import pytest
from django.core.cache import cache
from django_iran_ip.core.blacklist import IPBlacklist


@pytest.fixture
def blacklist():
    cache.clear()
    return IPBlacklist()


def test_add_and_check(blacklist):
    blacklist.add("1.2.3.4", reason="spam", ttl=60)
    assert blacklist.is_blocked("1.2.3.4") is True


def test_not_blocked(blacklist):
    assert blacklist.is_blocked("5.6.7.8") is False


def test_remove(blacklist):
    blacklist.add("1.2.3.4")
    blacklist.remove("1.2.3.4")
    assert blacklist.is_blocked("1.2.3.4") is False


def test_reason(blacklist):
    blacklist.add("1.2.3.4", reason="brute force")
    assert blacklist.get_reason("1.2.3.4") == "brute force"