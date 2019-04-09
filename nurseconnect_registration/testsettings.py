from nurseconnect_registration.settings import *  # noqa F401

SECRET_KEY = "TEST_SECRET_KEY"

DATABASES = {"default": env.db(default="sqlite:///:memory")}  # noqa F405

RAPIDPRO_URL = "https://test.rapidpro"
RAPIDPRO_TOKEN = "some_token"

CACHES = {
    'contacts': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'contacts',
    }
}
