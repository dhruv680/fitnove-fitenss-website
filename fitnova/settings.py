import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file (with pure-Python fallback if python-dotenv is not installed)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fitnova-production-2026-secret-key-for-render-deployments-9273f8e1a2b7c4d6')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Render / production deployment configuration
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)
if 'fitnove-fitenss-website-2.onrender.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('fitnove-fitenss-website-2.onrender.com')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://fitnove-fitenss-website-2.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost',
    'http://127.0.0.1',
]
if render_hostname:
    origin = f'https://{render_hostname}'
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# Always trust the X-Forwarded-Proto header from Render / load balancers for HTTPS detection
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third Party
    'rest_framework',

    # FitNova Apps
    'apps.accounts.apps.AccountsConfig',
    'apps.trainers.apps.TrainersConfig',
    'apps.members.apps.MembersConfig',
    'apps.memberships.apps.MembershipsConfig',
    'apps.attendance.apps.AttendanceConfig',
    'apps.payments.apps.PaymentsConfig',
    'apps.fitness.apps.FitnessConfig',
    'apps.classes.apps.ClassesConfig',
    'apps.crm.apps.CrmConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.facilities.apps.FacilitiesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.FaceAuthProtectionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fitnova.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.accounts.context_processors.global_fitnova_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'fitnova.wsgi.application'

# Database Configuration (PostgreSQL in production/Render, or local PostgreSQL when password is provided)
# Priority:
# 1. DATABASE_URL environment variable (Render / Cloud / Supabase / Neon PostgreSQL)
# 2. Local PostgreSQL if DB_PASSWORD is provided and USE_SQLITE is not True
# 3. Automatic fallback to SQLite if DB_PASSWORD is empty or USE_SQLITE is True
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '').strip()
USE_SQLITE = os.environ.get('USE_SQLITE', 'False').lower() in ('true', '1', 'yes')

if DATABASE_URL:
    is_cloud_db = 'render.com' in DATABASE_URL or 'neon.tech' in DATABASE_URL or 'supabase.co' in DATABASE_URL or bool(os.environ.get('RENDER_EXTERNAL_HOSTNAME'))
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=is_cloud_db
        )
    }
elif not USE_SQLITE and DB_PASSWORD:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'fitnova_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': DB_PASSWORD,
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Media files (Profile photos, QR codes, receipts)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'accounts:login'

# High-Security Biometric Authentication Configuration
FACE_BIOMETRIC_ENCRYPTION_KEY = os.environ.get(
    'FACE_BIOMETRIC_ENCRYPTION_KEY',
    'fvHuozAxdxYH5iTfbAaSpXrEw3xPOniTy8wbrQgSHE8='
)
FACE_SIMILARITY_THRESHOLD = 0.58       # Minimum cosine similarity for verified match (strictly prevents strangers < 0.50 from authenticating)
FACE_LIVENESS_VARIANCE_MIN = 20.0      # Minimum Laplacian edge variance (anti-spoof)
FACE_AUTH_MAX_FAILED_ATTEMPTS = 10     # Max failed attempts before lockout
FACE_AUTH_LOCKOUT_MINUTES = 5          # Temporary lockout window

# Enterprise Session & Cookie Security
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False          # False allows client-side JS / AJAX to read fresh CSRF token from cookie
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1209600           # 2-week secure session persistence

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
