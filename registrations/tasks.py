from datetime import datetime
from urllib.parse import urljoin

import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from requests.exceptions import RequestException

from nurseconnect_registration.celery import app
from registrations.utils import get_rapidpro_flow_by_name, tembaclient

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


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def send_registration_to_rapidpro(
    contact, msisdn, referral_msisdn, channel, clinic_code, timestamp
):
    # Create/Update contact
    contact_data = {
        "preferred_channel": channel.lower(),
        "registered_by": referral_msisdn,
        "facility_code": clinic_code,
        "registration_date": datetime.fromtimestamp(timestamp).isoformat(),
    }
    if contact:
        uuid = contact.get("uuid")
        contact = tembaclient.update_contact(uuid, fields=contact_data)
    else:
        urns = ["tel:%s" % msisdn]
        if channel == "WhatsApp":
            urns.append("whatsapp:%s" % msisdn.replace("+", ""))
        contact = tembaclient.create_contact(
            urns=urns, fields=contact_data)

    # Start the contact on the registration flow
    flow = get_rapidpro_flow_by_name("post registration")
    tembaclient.create_flow_start(flow.uuid, contacts=[contact.uuid])

    return contact
