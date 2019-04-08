import responses
from django.test import TestCase
from django.urls import reverse
from urllib.parse import urlencode

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

    @responses.activate
    def test_msisdn_validation(self):
        """
        The phone number field should be validated, and returned in E164 format
        """
        responses.add(responses.GET,
                      'https://test.rapidpro/api/v2/contacts.json',
                      json={"next": None, "previous": None, "results": []}, status=200,
                      headers={'Authorization': 'Token some_token'})

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

    @responses.activate
    def test_contact_exists(self):
        """
        If a contact exists in Rapidpro for this number, then we should return
        an error message
        """
        responses.add(responses.GET,
                      'https://test.rapidpro/api/v2/contacts.json?' + urlencode(
                        {'urn': 'tel:+27820001001'}),
                      json={"next": None, "previous": None, "results": []}, status=200,
                      headers={'Authorization': 'Token some_token'})

        form = RegistrationDetailsForm({"msisdn": "+27820001001"})
        form.is_valid()
        self.assertNotIn("msisdn", form.errors)

        contact_data = {
            "next": None,
            "previous": None,
            "results": [{
                "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
                "name": "Ben Haggerty",
                "language": None,
                "urns": ["tel:+27820001002"],
                "groups": [{"name": "nurseconnect-sms",
                            "uuid": "5a4eb79e-1b1f-4ae3-8700-09384cca385f"}],
                "fields": {},
                "blocked": None,
                "stopped": None,
                "created_on": "2015-11-11T13:05:57.457742Z",
                "modified_on": "2015-11-11T13:05:57.576056Z"
            }]
        }

        responses.add(responses.GET,
                      'https://test.rapidpro/api/v2/contacts.json?' + urlencode(
                        {'urn': 'tel:+27820001002'}),
                      json=contact_data, status=200,
                      headers={'Authorization': 'Token some_token'})

        form = RegistrationDetailsForm({"msisdn": "+27820001002"})
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

    @responses.activate
    def test_form_success(self):
        """
        Should put the form details and clinic name in the session
        """
        responses.add(responses.GET,
                      'https://test.rapidpro/api/v2/contacts.json',
                      json={"next": None, "previous": None, "results": []}, status=200,
                      headers={'Authorization': 'Token some_token'})
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

    def test_goes_to_end_on_yes(self):
        """
        If "yes" is selected, we should set the channel and redirect to the success page
        """
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
