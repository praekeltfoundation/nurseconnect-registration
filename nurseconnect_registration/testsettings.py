from nurseconnect_registration.settings import *  # noqa F401

SECRET_KEY = "TEST_SECRET_KEY"

DATABASES = {"default": env.db(default="sqlite:///:memory")}  # noqa F405

RAPIDPRO_URL = "https://test.rapidpro"
RAPIDPRO_TOKEN = "some_token"

CELERY_TASK_ALWAYS_EAGER = True

OPENHIM_URL = "http://testopenhim"
OPENHIM_USERNAME = "REPLACEME"
OPENHIM_PASSWORD = "REPLACEME"
OPENHIM_AUTH = (OPENHIM_USERNAME, OPENHIM_PASSWORD)
