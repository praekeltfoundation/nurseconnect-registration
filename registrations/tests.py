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
        self.assertTemplateUsed(r, "registrations/registration_details.html")
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

    def test_form_success(self):
        """
        Should put the form details and clinic name in the session
        """
        r = self.client.post(
            reverse("registrations:registration-details"),
            {"msisdn": "0820001001", "clinic_code": "123456", "consent": ["True"]},
        )
        self.assertRedirects(r, reverse("registrations:confirm-clinic"))
        self.assertEqual(
            self.client.session["registration_details"],
            {"msisdn": "+27820001001", "clinic_code": "123456", "consent": ["True"]},
        )
        self.assertEqual(self.client.session["clinic_name"], "Test clinic")


class ClinicConfirmTests(TestCase):
    def test_redirect_on_invalid_session(self):
        """
        If there isn't a clinic name in the session, then we should redirect to the
        registration details page, as the user went to this page without first going
        through the registration details page.
        """
        r = self.client.get(reverse("registrations:confirm-clinic"))
        self.assertRedirects(r, reverse("registrations:registration-details"))

    def test_goes_to_end_on_yes(self):
        """
        If "yes" is selected, we should set the channel and redirect to the success page
        """
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        self.assertEqual(self.client.session["channel"], "WhatsApp")
        self.assertRedirects(r, reverse("registrations:success"))

    def test_goes_to_homepage_no(self):
        """
        If "no" is selected, we should redirect to the registration details
        """
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"no": ["No"]})
        self.assertRedirects(r, reverse("registrations:registration-details"))


class RegistrationSuccessTests(TestCase):
    def test_redirect_to_clinic_confirm(self):
        """
        If there is no channel defined, we should redirect to the clinic confirmation
        """
        r = self.client.get(reverse("registrations:success"))
        # The confirm-clinic view also redirects because there is no clinic name
        self.assertRedirects(
            r, reverse("registrations:confirm-clinic"), target_status_code=302
        )

    def test_clears_session(self):
        """
        If the channel is defined, it should place the channel in the context, and clear
        the session data
        """
        session = self.client.session
        session["channel"] = "WhatsApp"
        session["foo"] = "bar"
        session.save()

        r = self.client.get(reverse("registrations:success"))
        self.assertContains(r, "Thank you")
        self.assertEqual(r.context["channel"], "WhatsApp")
        self.assertEqual(sorted(self.client.session.keys()), [])
