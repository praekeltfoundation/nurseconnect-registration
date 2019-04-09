from django.conf import settings
from temba_client.v2 import TembaClient


def get_contact(msisdn):
    client = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)
    contact = client.get_contacts(urn='tel:%s' % msisdn).first()
    return contact
