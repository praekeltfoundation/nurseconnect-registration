import phonenumbers
from django.core.exceptions import ValidationError

PHONE_NUMBER_ERROR_MESSAGE = (
    "Sorry we don't recognise that number. Please enter the cellphone number "
    "again, eg. 0762564722"
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
