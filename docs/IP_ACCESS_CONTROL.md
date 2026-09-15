# کنترل دسترسی بر اساس IP در django-iran-ip

راهنمای کامل استفاده از **دکوراتورها** و **سیستم Blacklist** در `django-iran-ip`
برای کنترل دسترسی کاربران بر اساس آدرس IP.

---

## فهرست

- [معرفی](#معرفی)
- [نصب و راه‌اندازی](#نصب-و-راه‌اندازی)
- [بخش اول: دکوراتورها](#بخش-اول-دکوراتورها)
  - [iran_only](#دکوراتور-iran_only)
  - [block_non_iran](#دکوراتور-block_non_iran)
  - [block_blacklisted](#دکوراتور-block_blacklisted)
  - [rate_limit_by_ip](#دکوراتور-rate_limit_by_ip)
  - [ترکیب دکوراتورها](#ترکیب-دکوراتورها)
  - [پاسخ‌های JSON و HTML](#پاسخهای-json-و-html)
- [بخش دوم: سیستم Blacklist](#بخش-دوم-سیستم-blacklist)
  - [API مرجع](#api-مرجع)
  - [مثال‌های کاربردی](#مثالهای-کاربردی)
  - [یکپارچگی با Spoofing Detection](#یکپارچگی-با-spoofing-detection)
- [تنظیمات](#تنظیمات)
- [بهترین شیوه‌ها](#بهترین-شیوه‌ها)
- [سوالات متداول](#سوالات-متداول)
- [مشارکت](#مشارکت)
- [لایسنس](#لایسنس)

---

## معرفی

`django-iran-ip` دو ابزار اصلی برای کنترل دسترسی بر اساس IP فراهم می‌کند:

| ابزار | کاربرد |
|-------|--------|
| **دکوراتورها** | محدودسازی سریع view ها بر اساس IP، لیست سیاه، و نرخ درخواست |
| **IPBlacklist** | مدیریت پویا و متمرکز لیست IP های مسدود |

این دو مکمل یکدیگرند: دکوراتورها **اعمال** می‌کنند، و Blacklist **داده** فراهم می‌کند.

---

## نصب و راه‌اندازی

### ۱. نصب

```bash
pip install django-iran-ip
```

یا با Poetry:

```bash
poetry add django-iran-ip
```

### ۲. اضافه کردن به INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'django_iran_ip',
]
```

### ۳. اضافه کردن Middleware

برای اینکه `request.client_ip` و `request.is_iran_ip` ست شوند:

```python
# settings.py
MIDDLEWARE = [
    # ...
    'django_iran_ip.contrib.django.middleware.IranIPMiddleware',
]
```

### ۴. تنظیم Cache

برای Blacklist و Rate Limit نیاز به cache داری.

**Redis (توصیه‌شده برای production):**

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

**Memcached:**

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
```

**حافظه محلی (فقط development):**

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

---

## بخش اول: دکوراتورها

### دکوراتور iran_only

فقط کاربران با IP ایرانی اجازه دسترسی دارند.

**امضا**

```python
iran_only(view_func)
```

**مثال**

```python
from django_iran_ip.contrib.django.decorators import iran_only
from django.shortcuts import render

@iran_only
def iranian_dashboard(request):
    return render(request, 'dashboard.html')
```

**رفتار**

| وضعیت | نتیجه |
|-------|-------|
| IP ایرانی | view اجرا می‌شود |
| IP غیر ایرانی | 403 Forbidden |
| IP قابل شناسایی نیست | 403 Forbidden |

**کاربرد**

- سرویس‌های پرداخت ایرانی
- محتوای محدود به ایران
- API های داخلی

### دکوراتور block_non_iran

مشابه `iran_only` ولی با پیام متفاوت. مناسب برای مسدودسازی صریح.

**امضا**

```python
block_non_iran(view_func)
```

**مثال**

```python
from django_iran_ip.contrib.django.decorators import block_non_iran
from django.http import JsonResponse

@block_non_iran
def internal_api(request):
    return JsonResponse({'status': 'ok'})
```

**تفاوت با iran_only**

| ویژگی | iran_only | block_non_iran |
|-------|-----------|-----------------|
| پیام خطا | «فقط کاربران ایرانی مجاز هستند» | «دسترسی از خارج از ایران مسدود است» |
| بار معنایی | محدودسازی مثبت | مسدودسازی منفی |
| کاربرد | سرویس مخصوص ایران | مسدودسازی فعال |

### دکوراتور block_blacklisted

اگر IP در blacklist باشد، مسدود می‌شود.

**امضا**

```python
block_blacklisted(view_func)
```

**مثال**

```python
from django_iran_ip.contrib.django.decorators import block_blacklisted
from django.shortcuts import render

@block_blacklisted
def login_view(request):
    return render(request, 'login.html')
```

**رفتار**

| وضعیت | نتیجه |
|-------|-------|
| IP در blacklist | 403 با نمایش دلیل |
| IP در blacklist نیست | view اجرا می‌شود |

**کاربرد**

- خط دفاعی اول در view های حساس
- همکاری با سیستم تشخیص خودکار (spoofing detection)
- مسدودسازی دستی توسط ادمین

### دکوراتور rate_limit_by_ip

محدودیت نرخ درخواست بر اساس IP.

**امضا**

```python
rate_limit_by_ip(max_requests=None, period=None, key_prefix="django_iran_ip:rate")
```

**پارامترها**

| پارامتر | نوع | پیش‌فرض | توضیح |
|---------|-----|----------|--------|
| max_requests | int | از conf.SPOOFING_RATE_LIMIT یا 100 | حداکثر درخواست در بازه |
| period | int | 3600 | بازه به ثانیه |
| key_prefix | str | "django_iran_ip:rate" | پیشوند کلید cache |

**مثال**

```python
from django_iran_ip.contrib.django.decorators import rate_limit_by_ip

# حداکثر ۵ درخواست در ۶۰ ثانیه
@rate_limit_by_ip(max_requests=5, period=60)
def login_view(request):
    return render(request, 'login.html')

# استفاده از پیش‌فرض‌های conf
@rate_limit_by_ip()
def api_view(request):
    return JsonResponse({'status': 'ok'})
```

**رفتار**

| وضعیت | نتیجه |
|-------|-------|
| زیر حد مجاز | view اجرا می‌شود |
| عبور از حد مجاز | 429 Too Many Requests |

**کاربرد**

- جلوگیری از brute force روی login
- محدودسازی API
- ضد scraping و spam

### ترکیب دکوراتورها

دکوراتورها را می‌توان ترکیب کرد. ترتیب مهم است!

**مثال ۱: اول blacklist، بعد iran_only**

```python
@iran_only
@block_blacklisted
def sensitive_view(request):
    return HttpResponse("ok")
```

ترتیب اجرا: `block_blacklisted` اول چک می‌شود، بعد `iran_only`.

**مثال ۲: rate limit روی login ایرانی**

```python
@iran_only
@rate_limit_by_ip(max_requests=10, period=60)
def iranian_login(request):
    return render(request, 'login.html')
```

**قاعده ترتیب**

1. blacklist — همیشه اول (سریع‌ترین، کم‌هزینه‌ترین)
2. rate limit — دوم (جلوگیری از حمله)
3. iran_only — سوم (تشخیص جغرافیایی، ممکن است کند باشد)

### پاسخ‌های JSON و HTML

همه دکوراتورها بر اساس هدر `Accept` تصمیم می‌گیرند:

| درخواست | هدر | پاسخ |
|---------|-----|------|
| مرورگر | `Accept: text/html` | `HttpResponse(message, status=code)` |
| API | `Accept: application/json` | `JsonResponse({'error': message}, status=code)` |

**مثال با curl**

```bash
# HTML
curl http://localhost:8000/iran/

# JSON
curl -H "Accept: application/json" http://localhost:8000/iran/
```

---

## بخش دوم: سیستم Blacklist

### معرفی

`IPBlacklist` یک کلاس سبک برای مدیریت لیست سیاه IP است که از cache جنگو
استفاده می‌کند:

- ✅ سرعت بالا (cache در حافظه یا Redis)
- ✅ TTL خودکار (IP بعد از مدت مشخص خودکار حذف می‌شود)
- ✅ ثبت دلیل مسدودسازی
- ✅ مقیاس‌پذیری (چند سرور می‌توانند از یک cache مشترک استفاده کنند)
- ✅ بدون نیاز به دیتابیس

### چه زمانی استفاده کنیم؟

| سناریو | مناسب است؟ |
|--------|-------------|
| مسدودسازی موقت IP مهاجم | ✅ |
| مسدودسازی خودکار بعد از تشخیص spoofing | ✅ |
| مسدودسازی دستی توسط ادمین | ✅ |
| مسدودسازی دائمی هزاران IP | ⚠️ (cache محدود است) |
| لیست سیاه بزرگ (میلیونی) | ❌ (از threat intelligence استفاده کن) |

### API مرجع

**کلاس IPBlacklist**

```python
class IPBlacklist:
    CACHE_PREFIX = "django_iran_ip:blacklist:"

    def __init__(self, cache_backend=None):
        """
        Args:
            cache_backend: اختیاری. اگر ندهی، از cache پیش‌فرض جنگو استفاده می‌کند.
        """
        ...

    def add(self, ip: str, reason: str = "", ttl: int = 3600) -> None:
        """
        افزودن IP به لیست سیاه.

        Args:
            ip: آدرس IP (فرمت IPv4)
            reason: دلیل مسدودسازی (اختیاری)
            ttl: مدت زمان به ثانیه (پیش‌فرض: 1 ساعت)
        """
        ...

    def remove(self, ip: str) -> None:
        """حذف IP از لیست سیاه."""
        ...

    def is_blocked(self, ip: str) -> bool:
        """بررسی مسدود بودن IP."""
        ...

    def get_reason(self, ip: str) -> str:
        """دریافت دلیل مسدودسازی."""
        ...
```

**مثال پایه**

```python
from django_iran_ip.core.blacklist import IPBlacklist

bl = IPBlacklist()

# افزودن با TTL پیش‌فرض (1 ساعت)
bl.add("10.0.0.1", reason="suspicious activity")

# افزودن با TTL سفارشی (24 ساعت)
bl.add("10.0.0.2", reason="brute force attack", ttl=86400)

# بررسی
if bl.is_blocked("10.0.0.1"):
    reason = bl.get_reason("10.0.0.1")
    print(f"IP مسدود است. دلیل: {reason}")

# حذف دستی
bl.remove("10.0.0.1")
```

### مثال‌های کاربردی

**۱. مسدودسازی بعد از چند تلاش ناموفق ورود**

```python
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django_iran_ip.core.blacklist import IPBlacklist


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is None:
            cache_key = f"login_fail:{request.client_ip}"
            fails = cache.get(cache_key, 0) + 1
            cache.set(cache_key, fails, 300)  # 5 دقیقه

            if fails >= 5:
                IPBlacklist().add(
                    request.client_ip,
                    reason=f"{fails} failed login attempts",
                    ttl=3600,
                )
                return HttpResponseForbidden("IP شما مسدود شد")
        else:
            cache.delete(f"login_fail:{request.client_ip}")
            login(request, user)

    return render(request, 'login.html')
```

**۲. API مدیریتی برای مسدودسازی**

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@staff_member_required
@require_POST
def block_ip_api(request, ip):
    reason = request.POST.get('reason', 'manual block')
    ttl = int(request.POST.get('ttl', 3600))

    IPBlacklist().add(ip, reason=reason, ttl=ttl)

    return JsonResponse({
        'status': 'blocked',
        'ip': ip,
        'reason': reason,
        'ttl': ttl,
    })


@staff_member_required
@require_POST
def unblock_ip_api(request, ip):
    IPBlacklist().remove(ip)
    return JsonResponse({'status': 'unblocked', 'ip': ip})
```

**۳. مسدودسازی دسته‌ای**

```python
from django_iran_ip.core.blacklist import IPBlacklist


def bulk_add(ips_and_reasons: dict, ttl: int = 3600):
    """
    افزودن دسته‌ای IP ها.

    Args:
        ips_and_reasons: {'1.2.3.4': 'reason1', '5.6.7.8': 'reason2'}
        ttl: مدت زمان به ثانیه
    """
    bl = IPBlacklist()
    for ip, reason in ips_and_reasons.items():
        bl.add(ip, reason=reason, ttl=ttl)


# استفاده
bulk_add({
    '1.2.3.4': 'brute force',
    '5.6.7.8': 'spam',
    '10.20.30.40': 'scanner',
}, ttl=7200)
```

**۴. صفحه ورود امن با سه لایه**

```python
from django_iran_ip.contrib.django.decorators import (
    iran_only,
    rate_limit_by_ip,
    block_blacklisted,
)


@iran_only
@rate_limit_by_ip(max_requests=5, period=300)
@block_blacklisted
def login_view(request):
    """
    صفحه ورود با سه لایه امنیتی:
    1. فقط IP ایرانی
    2. حداکثر ۵ درخواست در ۵ دقیقه
    3. IP های blacklist شده مسدود
    """
    if request.method == 'POST':
        # منطق ورود
        ...
    return render(request, 'login.html')
```

### یکپارچگی با Spoofing Detection

اگر `IRAN_IP_SPOOFING_AUTO_BLOCK = True` باشد، IP هایی که به‌عنوان
spoofing تشخیص داده می‌شوند، خودکار در blacklist قرار می‌گیرند:

```python
# settings.py
IRAN_IP_ENABLE_SPOOFING_DETECTION = True
IRAN_IP_SPOOFING_AUTO_BLOCK = True
IRAN_IP_SPOOFING_THRESHOLD = 70.0
```

بعد از این، هر IP با risk score بالای 70، به مدت پیش‌فرض در blacklist
قرار می‌گیرد و درخواست‌های بعدی‌اش مسدود می‌شوند.

---

## تنظیمات

| تنظیم | پیش‌فرض | توضیح |
|-------|----------|--------|
| IRAN_IP_ENABLE_CACHE | True | فعال‌سازی cache |
| IRAN_IP_CACHE_DURATION | 3600 | مدت cache به ثانیه |
| IRAN_IP_CHECK_IRAN_IP | False | بررسی خودکار ایرانی بودن IP |
| IRAN_IP_BLOCK_NON_IRAN_IP | False | مسدودسازی خودکار غیرایرانی‌ها |
| IRAN_IP_SPOOFING_RATE_LIMIT | 1000 | حد نرخ پیش‌فرض |

---

## بهترین شیوه‌ها

**۱. همیشه TTL بده**

```python
# خوب ✅
bl.add("1.2.3.4", reason="brute force", ttl=3600)

# بد ❌ (تا ابد مسدود می‌ماند)
bl.add("1.2.3.4")
```

**۲. دلیل معنادار بنویس**

```python
# خوب ✅
bl.add("1.2.3.4", reason="5 failed logins from same IP")

# بد ❌
bl.add("1.2.3.4", reason="bad")
```

**۳. IP های خصوصی را مسدود نکن**

```python
bl.add("192.168.1.1")    # ❌
bl.add("10.0.0.1")       # ❌
bl.add("127.0.0.1")      # ❌
```

**۴. برای production از Redis استفاده کن**

cache حافظه‌ای در production:

- ❌ بین سرورها مشترک نیست
- ❌ با ری‌استارت پاک می‌شود

**۵. ترتیب دکوراتورها را رعایت کن**

```python
@iran_only
@rate_limit_by_ip(max_requests=10, period=60)
@block_blacklisted          # ← همیشه پایین‌ترین (اول اجرا می‌شود)
def view(request): ...
```

**۶. قبل از مسدودسازی، IP را اعتبارسنجی کن**

```python
from django_iran_ip.core.validators import IPValidator

validator = IPValidator()

if validator.is_valid_ipv4(ip) and not validator.is_private_ip(ip):
    bl.add(ip, reason=reason, ttl=ttl)
```

---

## سوالات متداول

**آیا دکوراتورها بدون Middleware کار می‌کنند؟**

بله. اگر Middleware نصب نباشد، `_get_client_ip` از `REMOTE_ADDR` استفاده می‌کند. ولی برای پشتیبانی از CDNها (ابرآروان، کلودفلر) Middleware توصیه می‌شود.

**تفاوت iran_only و block_non_iran چیست؟**

از نظر فنی یکسان هستند، فقط پیام خطا متفاوت است:

- `iran_only` → «فقط ایرانی‌ها»
- `block_non_iran` → «مسدودسازی غیرایرانی‌ها»

**آیا می‌توانم rate limit را per-user کنم؟**

در نسخه فعلی نه. برای این کار باید `key_prefix` را تغییر دهی یا دکوراتور سفارشی بنویسی.

**آیا blacklist بین سرورها مشترک است؟**

بله، اگر از cache مشترک (Redis، Memcached) استفاده کنی.

**حداکثر تعداد IP در blacklist چقدر است؟**

بستگی به backend دارد:

- Redis: میلیون‌ها
- Memcached: میلیون‌ها
- LocMemCache: محدود به حافظه سرور

**TTL منقضی شده ولی IP هنوز مسدود است — چرا؟**

cache backend برای TTL دقت کاملاً دقیق ندارد. این طبیعی است.

**آیا می‌توانم بین دو blacklist مختلف تفکیک کنم؟**

بله، با prefix سفارشی:

```python
class TempBlacklist(IPBlacklist):
    CACHE_PREFIX = "django_iran_ip:temp:"

class PermanentBlacklist(IPBlacklist):
    CACHE_PREFIX = "django_iran_ip:perm:"
```

**آیا blacklist با restart سرور پاک می‌شود؟**

اگر از Redis یا Memcached استفاده کنی، نه. اگر از LocMemCache استفاده کنی، بله.

---

## مشارکت

اگر باگ پیدا کردی یا پیشنهاد داری، لطفاً Issue باز کن:

https://github.com/ArashkZolghadr/django-iran-ip/issues

---

## لایسنس

MIT License — برای جزئیات بیشتر فایل LICENSE را ببینید.