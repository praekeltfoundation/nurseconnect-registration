from django.test import TestCase
from django.urls import reverse

from registrations.forms import RegistrationDetailsForm


class RegistrationDetailsTest(TestCase):
    def test_get_form(self):
        """
        A GET request should render the registration details form
        """
        url = reverse("registrations:registration-details")
        r = self.client.get(url)
        self.assertTemplateUsed(r, "registration_details.html")
        self.assertContains(r, '<form method="post">')

    def test_msisdn_validation(self):
        """
        The phone number field should be validated, and returned in E164 format
        """
        form = RegistrationDetailsForm({"msisdn": "0820001001"})
        form.is_valid()
        self.assertNotIn("msisdn", form.errors)
        self.assertEqual(form.clean_msisdn(), "+27820001001")

        # Cannot parse
        form = RegistrationDetailsForm({"msisdn": "foo"})
        form.is_valid()
        self.assertIn("msisdn", form.errors)

        # Not possible number
        form = RegistrationDetailsForm({"msisdn": "1234"})
        form.is_valid()
        self.assertIn("msisdn", form.errors)

        # Invalid number
        form = RegistrationDetailsForm({"msisdn": "+12001230101"})
        form.is_valid()
        self.assertIn("msisdn", form.errors)

    def test_clinic_code_validation(self):
        """
        The clinic code should be digits
        """
        form = RegistrationDetailsForm({"clinic_code": "123456"})
        form.is_valid()
        self.assertNotIn("clinic_code", form.errors)
        self.assertEqual(form.clean_clinic_code(), "123456")

        # not digits
        form = RegistrationDetailsForm({"clinic_code": "foobar"})
        form.is_valid()
        self.assertIn("clinic_code", form.errors)
