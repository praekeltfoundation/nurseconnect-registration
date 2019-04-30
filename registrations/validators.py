import phonenumbers
from django.conf import settings
from django.core.exceptions import ValidationError

PHONE_NUMBER_ERROR_MESSAGE = (
    "Sorry we don't recognise that number. Please enter the cellphone number "
    "again, eg. 0762564722"
)
CLINIC_CODE_BLOCKED_ERROR_MESSAGE = (
    "Sorry, but you can’t sign up for NurseConnect with this clinic code. It’s blocked "
    "due to fraudulent activity. You can register using a different clinic code."
)


def msisdn_validator(value):
    """
    Ensures that the value is a valid South African MSISDN
    """
    try:
        msisdn = phonenumbers.parse(value, "ZA")
    except phonenumbers.phonenumberutil.NumberParseException:
        raise ValidationError(PHONE_NUMBER_ERROR_MESSAGE)
    if not phonenumbers.is_possible_number(msisdn):
        raise ValidationError(PHONE_NUMBER_ERROR_MESSAGE)
    if not phonenumbers.is_valid_number(msisdn):
        raise ValidationError(PHONE_NUMBER_ERROR_MESSAGE)


def clinic_code_blacklist_validator(value):
    """
    Ensures that the clinic code is not in the blacklist
    """
    if value in settings.CLINIC_CODE_BLACKLIST:
        raise ValidationError(CLINIC_CODE_BLOCKED_ERROR_MESSAGE)
