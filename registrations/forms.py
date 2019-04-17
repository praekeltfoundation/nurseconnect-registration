import logging
from json import JSONDecodeError
from urllib.parse import urljoin

import phonenumbers
import requests
from django import forms
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.functional import lazy
from django.utils.html import format_html
from temba_client.exceptions import TembaException

from registrations.utils import contact_in_rapidpro_groups, get_rapidpro_contact
from registrations.validators import msisdn_validator


class RegistrationDetailsForm(forms.Form):
    PHONE_NUMBER_ERROR_MESSAGE = (
        "Sorry, the number you entered is invalid. Please enter a valid 10-digit "
        "cellphone number, eg. 0762564722"
    )
    EXISTING_NUMBER_ERROR_MESSAGE = (
        "Sorry, but this phone number is already registered. Please enter a new "
        "cellphone number."
    )
    CLINIC_CODE_ERROR_MESSAGE = (
        "Sorry we don't recognise that code. Please enter the 6-digit facility code "
        "again, eg. 535970"
    )

    msisdn = forms.CharField(
        label="Cellphone number of the nurse being registered",
        error_messages={"required": PHONE_NUMBER_ERROR_MESSAGE},
        validators=[msisdn_validator],
    )
    clinic_code = forms.CharField(
        label="Clinic code of the nurse being registered",
        min_length=6,
        max_length=6,
        error_messages={
            "required": CLINIC_CODE_ERROR_MESSAGE,
            "min_length": CLINIC_CODE_ERROR_MESSAGE,
            "max_length": CLINIC_CODE_ERROR_MESSAGE,
        },
    )
    consent = forms.MultipleChoiceField(
        label=(
            "We need to store and access the information of the person signing up. "
            "They may get messages on weekends and public holidays. Do they agree?"
        ),
        error_messages={
            "required": (
                'We can\'t send NurseConnect messages to this number unless "Yes" is '
                "selected"
            )
        },
        choices=((True, "Yes"),),
        widget=forms.CheckboxSelectMultiple,
    )

    terms_and_conditions = forms.MultipleChoiceField(
        label=lazy(format_html)(
            'Please read the <a href="{}">Terms & Conditions</a>. Does the nurse '
            "signing up agree to them?",
            reverse_lazy("registrations:terms_and_conditions"),
        ),
        error_messages={
            "required": (
                "You must agree to the terms and conditions before registering"
            )
        },
        choices=((True, "I agree"),),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RegistrationDetailsForm, self).__init__(*args, **kwargs)

    def clean_msisdn(self):
        msisdn = phonenumbers.parse(self.cleaned_data["msisdn"], "ZA")
        formatted_msisdn = phonenumbers.format_number(
            msisdn, phonenumbers.PhoneNumberFormat.E164
        )

        # Check if number already registered
        try:
            contact = get_rapidpro_contact(formatted_msisdn)
        except TembaException:
            raise forms.ValidationError(
                "There was an error checking your details. Please try again."
            )
        self.request.session["contact"] = contact
        if contact_in_rapidpro_groups(
            contact, ["nurseconnect-sms", "nurseconnect-whatsapp"]
        ):
            raise forms.ValidationError(self.EXISTING_NUMBER_ERROR_MESSAGE)
        return formatted_msisdn

    def clean_clinic_code(self):
        code = self.cleaned_data["clinic_code"]
        if not code.isdigit():
            raise forms.ValidationError(self.CLINIC_CODE_ERROR_MESSAGE)

        #  Check clinic code exists
        try:
            response = requests.get(
                urljoin(settings.OPENHIM_URL, "NCfacilityCheck"),
                params={"criteria": "value:%s" % code},
                auth=settings.OPENHIM_AUTH,
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.HTTPError, JSONDecodeError):
            errors = self.request.session.get("jembi_api_errors", 0)
            self.request.session["jembi_api_errors"] = errors + 1
            if errors + 1 >= 3:
                logging.exception("Jembi API error limit reached")
            raise forms.ValidationError(
                "There was an error checking your details. Please try again."
            )

        if data["height"] != 1:
            raise forms.ValidationError(self.CLINIC_CODE_ERROR_MESSAGE)
        self.request.session["clinic_name"] = data["rows"][0][2]
        self.request.session["clinic_code"] = code

        return code
