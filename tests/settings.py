"""
تنظیمات مینیمال Django برای اجرای تست‌های django-iran-ip
"""

SECRET_KEY = "test-secret-key-for-django-iran-ip"

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django_iran_ip',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'django-iran-ip-test',
    }
}

IRAN_IP_ENABLE_CACHE = True
IRAN_IP_CACHE_DURATION = 3600
IRAN_IP_VALIDATE_IP = True
IRAN_IP_CHECK_IRAN_IP = True

IRAN_IP_ENABLE_SPOOFING_DETECTION = False
IRAN_IP_ENABLE_GEOLOCATION = False

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'