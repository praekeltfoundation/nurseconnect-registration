import phonenumbers
from django.conf import settings
from temba_client.v2 import TembaClient
from wabclient import Client as WABClient


def normalise_msisdn(msisdn):
    msisdn = phonenumbers.parse(msisdn, "ZA")
    return phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)


def get_rapidpro_contact(msisdn):
    contact = tembaclient.get_contacts(urn="tel:%s" % msisdn).first()
    if contact:
        return contact.serialize()
    return None


def contact_in_rapidpro_groups(contact, groups):
    if contact:
        for group in contact.get("groups", []):
            if group["name"] in groups:
                return True
    return False


tembaclient = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)

# Short timeout since we're making these requests in the HTTP request
wabclient = WABClient(url=settings.WHATSAPP_URL, timeout=2)
wabclient.connection.set_token(settings.WHATSAPP_TOKEN)