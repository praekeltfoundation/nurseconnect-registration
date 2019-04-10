from nurseconnect_registration.settings import *  # noqa F401

SECRET_KEY = "TEST_SECRET_KEY"

DATABASES = {"default": env.db(default="sqlite:///:memory")}  # noqa F405

CELERY_TASK_ALWAYS_EAGER = True
