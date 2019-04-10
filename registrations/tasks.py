from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from datetime import datetime
from urllib.parse import urljoin
from requests.exceptions import RequestException
import requests

from nurseconnect_registration.celery import app


openhim_session = requests.Session()
openhim_session.auth = settings.OPENHIM_AUTH
openhim_session.headers.update({"User-Agent": "NurseConnectRegistration"})


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def send_registration_to_openhim(
    msisdn, referral_msisdn, channel, clinic_code, persal, sanc, timestamp
):
    response = openhim_session.post(
        url=urljoin(settings.OPENHIM_URL, "nc/subscription"),
        json={
            "mha": 1,
            "swt": 7 if channel == "WhatsApp" else 1,
            "type": 7,
            "dmsisdn": referral_msisdn or msisdn,
            "cmsisdn": msisdn,
            "rmsisdn": None,
            "faccode": clinic_code,
            "id": "{}^^^ZAF^TEL".format(msisdn.lstrip("+")),
            "dob": None,
            "persal": persal,
            "sanc": sanc,
            "encdate": datetime.utcfromtimestamp(timestamp).strftime("%Y%m%d%H%M%S"),
        },
    )
    response.raise_for_status()
    return (response.status_code, response.headers, response.content)
