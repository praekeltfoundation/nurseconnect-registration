import os

from celery import Celery
from django.conf import settings
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nurseconnect_registration.settings")

app = Celery("nurseconnect_registration")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[CeleryIntegration()])


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
