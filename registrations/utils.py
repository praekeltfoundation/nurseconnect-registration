import phonenumbers


def normalise_msisdn(msisdn):
    msisdn = phonenumbers.parse(msisdn, "ZA")
    return phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)
