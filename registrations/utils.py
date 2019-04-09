from django.conf import settings
from django.core.cache import caches
from temba_client.v2 import TembaClient


CACHE = caches["contacts"]
CACHE_EXPIRY_SECONDS = 600


def get_contact(msisdn):
    contact = CACHE.get(msisdn)
    if not contact:
        client = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)
        contact = client.get_contacts(urn='tel:%s' % msisdn).first()
        CACHE.set(msisdn, contact, CACHE_EXPIRY_SECONDS)

    return contact
