from django.conf import settings
import phonenumbers
from wabclient import Client as WABClient


def normalise_msisdn(msisdn):
    msisdn = phonenumbers.parse(msisdn, "ZA")
    return phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)


# Short timeout since we're making these requests in the HTTP request
wabclient = WABClient(url=settings.WHATSAPP_URL, timeout=2)
wabclient.connection.set_token(settings.WHATSAPP_TOKEN)
