"""
تنظیمات pytest برای django-iran-ip

این فایل Django را قبل از اجرای تست‌ها setup می‌کند.
"""

import os
import sys
from pathlib import Path

# اضافه کردن ریشه پروژه به sys.path (برای اطمینان)
sys.path.insert(0, str(Path(__file__).parent))

import django


def pytest_configure():
    """تنظیم Django قبل از اجرای تست‌ها"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
    django.setup()