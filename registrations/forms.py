import phonenumbers
from django import forms


class RegistrationDetailsForm(forms.Form):
    PHONE_NUMBER_ERROR_MESSAGE = (
        "Sorry we don't recognise that number. Please enter the cellphone number "
        "again, eg. 0762564722"
    )
    CLINIC_CODE_ERROR_MESSAGE = (
        "Sorry we don't recognise that code. Please enter the 6-digit facility code "
        "again, eg. 535970"
    )

    msisdn = forms.CharField(
        label="Cellphone number of the nurse being registered",
        error_messages={"required": PHONE_NUMBER_ERROR_MESSAGE},
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
        label=("I accept the Terms and Conditions"),
        error_messages={
            "required": (
                "You must agree to the terms and conditions before registering"
            )
        },
        choices=((True, "I agree"),),
        widget=forms.CheckboxSelectMultiple,
    )

    def clean_msisdn(self):
        try:
            msisdn = phonenumbers.parse(self.cleaned_data["msisdn"], "ZA")
        except phonenumbers.phonenumberutil.NumberParseException:
            raise forms.ValidationError(self.PHONE_NUMBER_ERROR_MESSAGE)
        if not phonenumbers.is_possible_number(msisdn):
            raise forms.ValidationError(self.PHONE_NUMBER_ERROR_MESSAGE)
        if not phonenumbers.is_valid_number(msisdn):
            raise forms.ValidationError(self.PHONE_NUMBER_ERROR_MESSAGE)
        return phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)

    def clean_clinic_code(self):
        code = self.cleaned_data["clinic_code"]
        if not code.isdigit():
            raise forms.ValidationError(self.CLINIC_CODE_ERROR_MESSAGE)
        return code
