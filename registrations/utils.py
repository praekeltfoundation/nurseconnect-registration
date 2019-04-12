import logging

import phonenumbers
from django.conf import settings
from temba_client.exceptions import TembaException
from temba_client.v2 import TembaClient
from wabclient import Client as WABClient


def normalise_msisdn(msisdn):
    msisdn = phonenumbers.parse(msisdn, "ZA")
    return phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)


def get_rapidpro_contact(msisdn):
    try:
        contact = tembaclient.get_contacts(urn="tel:%s" % msisdn).first()
    except TembaException as e:
        logging.exception("Error connecting to RapidPro (msisdn: %s)" % msisdn)
        raise e
    if contact:
        return contact.serialize()
    return {}


def contact_in_rapidpro_groups(contact, groups):
    if contact:
        for group in contact.get("groups", []):
            if group["name"] in groups:
                return True
    return False


def get_rapidpro_flow_by_name(name):
    flows = tembaclient.get_flows().iterfetches()
    for flow_batch in flows:
        for flow in flow_batch:
            if flow.name.lower() == name:
                return flow
    return None


tembaclient = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)

# Short timeout since we're making these requests in the HTTP request
wabclient = WABClient(url=settings.WHATSAPP_URL, timeout=2)
wabclient.connection.set_token(settings.WHATSAPP_TOKEN)
