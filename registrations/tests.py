from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from unittest import mock
import responses

from registrations.forms import RegistrationDetailsForm
from registrations.models import ReferralLink


class RegistrationDetailsTest(TestCase):
    def test_get_referral_link(self):
        """
        A GET request with a referral link should add the MSISDN of the referrer to the
        context
        """
        referral = ReferralLink.objects.create(msisdn="+27820001001")
        url = reverse("registrations:registration-details", args=[referral.code])
        r = self.client.get(url)
        self.assertTemplateUsed(r, "registrations/registration_details.html")
        self.assertEqual(self.client.session["registered_by"], referral.msisdn)

    def test_bad_referral_link(self):
        """
        If a bad referral code is supplied, we should not alert the user, and just act
        like no code was given
        """
        url = reverse("registrations:registration-details", args=["bad-code"])
        r = self.client.get(url)
        self.assertTemplateUsed(r, "registrations/registration_details.html")
        self.assertNotIn("registered_by", self.client.session)

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
            {
                "msisdn": "0820001001",
                "clinic_code": "123456",
                "consent": ["True"],
                "terms_and_conditions": ["True"],
            },
        )
        self.assertRedirects(r, reverse("registrations:confirm-clinic"))
        self.assertEqual(
            self.client.session["registration_details"],
            {
                "msisdn": "+27820001001",
                "clinic_code": "123456",
                "consent": ["True"],
                "terms_and_conditions": ["True"],
            },
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

    @mock.patch("registrations.views.RegistrationConfirmClinic.get_channel")
    def test_goes_to_end_on_yes(self, get_channel):
        """
        If "yes" is selected, we should set the channel and redirect to the success page
        """
        get_channel.return_value = "WhatsApp"
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {"msisdn": "+27820001001"}
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

    @responses.activate
    def test_get_channel_whatsapp(self):
        """
        If the user has a whatsapp account, the channel should be whatsapp
        """
        responses.add(
            responses.POST,
            "https://whatsapp.praekelt.org/v1/contacts",
            json={
                "contacts": [
                    {"input": "+27820001001", "status": "valid", "wa_id": "27820001001"}
                ]
            },
        )
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        self.assertEqual(self.client.session["channel"], "WhatsApp")
        self.assertRedirects(r, reverse("registrations:success"))

    @responses.activate
    def test_get_channel_sms(self):
        """
        If the user doesn't have a whatsapp account, the channel should be sms
        """
        responses.add(
            responses.POST,
            "https://whatsapp.praekelt.org/v1/contacts",
            json={"contacts": [{"input": "+27820001001", "status": "invalid"}]},
        )
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        self.assertEqual(self.client.session["channel"], "SMS")
        self.assertRedirects(r, reverse("registrations:success"))

    @responses.activate
    def test_get_channel_error(self):
        """
        If there's an error making the HTTP request, an error message should be returned
        to the user, asking them to try again.
        """
        responses.add(
            responses.POST, "https://whatsapp.praekelt.org/v1/contacts", status=500
        )
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        [message] = get_messages(r.wsgi_request)
        self.assertEqual(
            str(message),
            "There was an error creating your registration. Please try again.",
        )

    @responses.activate
    def test_get_channel_multiple_errors(self):
        """
        If there are multiple HTTP errors, then it should be logged so that we know
        about it
        """
        responses.add(
            responses.POST, "https://whatsapp.praekelt.org/v1/contacts", status=500
        )
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()
        with self.assertLogs(level="ERROR") as logs:
            self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
            self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
            self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        [error_log] = logs.output
        self.assertIn("WhatsApp API error limit reached", error_log)


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
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()

        r = self.client.get(reverse("registrations:success"))
        self.assertContains(r, "Thank you")
        self.assertEqual(r.context["channel"], "WhatsApp")
        self.assertEqual(sorted(self.client.session.keys()), [])

    def test_referral_link(self):
        """
        After a successful registration, it should display the user's referral link
        """
        session = self.client.session
        session["channel"] = "WhatsApp"
        session["foo"] = "bar"
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()

        r = self.client.get(reverse("registrations:success"))
        referral = ReferralLink.objects.get(msisdn="+27820001001")
        self.assertContains(r, referral.path)
        self.assertEqual(r.context["channel"], "WhatsApp")
        self.assertEqual(sorted(self.client.session.keys()), [])
