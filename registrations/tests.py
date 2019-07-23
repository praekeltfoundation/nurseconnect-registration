import json
from datetime import datetime
from unittest import mock
from urllib.parse import urlencode

import responses
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from registrations.forms import RegistrationDetailsForm
from registrations.models import ReferralLink
from registrations.tasks import (
    send_registration_to_openhim,
    send_registration_to_rapidpro,
)


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
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json",
            json={"next": None, "previous": None, "results": []},
            status=200,
            headers={"Authorization": "Token some_token"},
        )
        r = self.client.get(reverse("registrations:registration-details"))

        form = RegistrationDetailsForm({"msisdn": "0820001001"}, request=r.wsgi_request)
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
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"urn": "tel:+27820001001"}),
            json={"next": None, "previous": None, "results": []},
            status=200,
            headers={"Authorization": "Token some_token"},
        )
        r = self.client.get(reverse("registrations:registration-details"))

        form = RegistrationDetailsForm({"msisdn": "0820001001"}, request=r.wsgi_request)
        form.is_valid()
        self.assertNotIn("msisdn", form.errors)
        self.assertIn("contact", r.wsgi_request.session)
        self.assertEqual(r.wsgi_request.session["contact"], {})

        contact_data = {
            "next": None,
            "previous": None,
            "results": [
                {
                    "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
                    "name": "Ben Haggerty",
                    "language": None,
                    "urns": ["tel:+27820001002"],
                    "groups": [
                        {
                            "name": "nurseconnect-sms",
                            "uuid": "5a4eb79e-1b1f-4ae3-8700-09384cca385f",
                        }
                    ],
                    "fields": {},
                    "blocked": None,
                    "stopped": None,
                    "created_on": "2015-11-11T13:05:57.457742Z",
                    "modified_on": "2015-11-11T13:05:57.576056Z",
                }
            ],
        }

        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"urn": "tel:+27820001002"}),
            json=contact_data,
            status=200,
            headers={"Authorization": "Token some_token"},
        )

        form = RegistrationDetailsForm({"msisdn": "0820001002"}, request=r.wsgi_request)
        form.is_valid()
        self.assertIn("msisdn", form.errors)
        self.assertIn("contact", r.wsgi_request.session)
        self.assertIsNotNone(r.wsgi_request.session["contact"])

    @responses.activate
    def test_get_rp_contact_error(self):
        """
        If there's an error making the HTTP request, an error message should be returned
        to the user, asking them to try again.
        """
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"urn": "tel:+27820001002"}),
            status=500,
        )

        form = RegistrationDetailsForm({"msisdn": "0820001002"})
        with self.assertLogs(level="ERROR") as logs:
            form.is_valid()
        [error_log] = logs.output
        self.assertIn("Error connecting to RapidPro", error_log)
        self.assertIn("msisdn", form.errors)
        self.assertIn(
            "There was an error checking your details. Please try again.",
            form.errors["msisdn"],
        )

    @responses.activate
    def test_opted_out_contact_redirected_to_confirmation(self):
        """
        If a contact has already opted out, then we should redirect to an optin
        confirmation page
        """
        contact_data = {
            "next": None,
            "previous": None,
            "results": [
                {
                    "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
                    "name": "Ben Haggerty",
                    "language": None,
                    "urns": ["tel:+27820001003"],
                    "groups": [
                        {
                            "name": "opted-out",
                            "uuid": "5a4eb79e-1b1f-4ae3-8700-09384cca385f",
                        }
                    ],
                    "fields": {},
                    "blocked": None,
                    "stopped": None,
                    "created_on": "2015-11-11T13:05:57.457742Z",
                    "modified_on": "2015-11-11T13:05:57.576056Z",
                }
            ],
        }
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"urn": "tel:+27820001003"}),
            json=contact_data,
            status=200,
            headers={"Authorization": "Token some_token"},
        )

        clinic_data = {
            "title": "Facility Check Nurse Connect",
            "headers": [],
            "rows": [["123457", "yGVQRg2PXNh", "Test Clinic"]],
            "width": 3,
            "height": 1,
        }
        responses.add(
            responses.GET,
            "http://testopenhim/NCfacilityCheck?"
            + urlencode({"criteria": "value:123457"}),
            json=clinic_data,
            status=200,
        )

        referral = ReferralLink.objects.create(msisdn="+27820001001")
        url = reverse("registrations:registration-details", args=[referral.code])
        r = self.client.post(
            url,
            {"msisdn": ["0820001003"], "clinic_code": ["123457"], "consent": ["True"]},
        )
        self.assertRedirects(r, reverse("registrations:confirm-optin"))
        self.assertEqual(self.client.session["clinic_name"], "Test Clinic")
        self.assertEqual(self.client.session["clinic_code"], "123457")

    @responses.activate
    def test_clinic_code_validation(self):
        """
        The clinic code should be digits and exist in DHIS2, and not be on the blacklist
        """
        clinic_data = {
            "title": "Facility Check Nurse Connect",
            "headers": [],
            "rows": [["123457", "yGVQRg2PXNh", "Test Clinic"]],
            "width": 3,
            "height": 1,
        }
        responses.add(
            responses.GET,
            "http://testopenhim/NCfacilityCheck?"
            + urlencode({"criteria": "value:123457"}),
            json=clinic_data,
            status=200,
        )
        r = self.client.get(reverse("registrations:registration-details"))

        form = RegistrationDetailsForm(
            {"clinic_code": "123457"}, request=r.wsgi_request
        )
        form.is_valid()
        self.assertNotIn("clinic_code", form.errors)
        self.assertEqual(form.clean_clinic_code(), "123457")

        # not digits
        form = RegistrationDetailsForm({"clinic_code": "foobar"})
        form.is_valid()
        self.assertIn("clinic_code", form.errors)

        # not in DHIS2
        clinic_data = {"title": "", "headers": [], "rows": [], "width": 0, "height": 0}
        responses.add(
            responses.GET,
            "http://testopenhim/NCfacilityCheck?"
            + urlencode({"criteria": "value:654321"}),
            json=clinic_data,
            status=200,
        )

        form = RegistrationDetailsForm(
            {"clinic_code": "654321"}, request=r.wsgi_request
        )
        form.is_valid()
        self.assertIn("clinic_code", form.errors)

        # in blacklist
        form = RegistrationDetailsForm(
            {"clinic_code": "123456"}, request=r.wsgi_request
        )
        form.is_valid()
        self.assertIn("clinic_code", form.errors)

    @responses.activate
    def test_check_clinic_code_error(self):
        """
        If there's an error making the HTTP request, an error message should be returned
        to the user, asking them to try again.
        """
        responses.add(responses.GET, "http://testopenhim/NCfacilityCheck", status=500)
        r = self.client.get(reverse("registrations:registration-details"))
        form = RegistrationDetailsForm(
            {"clinic_code": "123457"}, request=r.wsgi_request
        )
        form.is_valid()
        self.assertIn("clinic_code", form.errors)
        self.assertIn("jembi_api_errors", r.wsgi_request.session)
        self.assertEqual(r.wsgi_request.session["jembi_api_errors"], 1)

    @responses.activate
    def test_check_clinic_code_multiple_errors(self):
        """
        If there are multiple HTTP errors, then it should be logged so that we know
        about it
        """
        responses.add(responses.GET, "http://testopenhim/NCfacilityCheck", status=500)
        with self.assertLogs(level="ERROR") as logs:
            self.client.post(
                reverse("registrations:registration-details"), {"clinic_code": "123457"}
            )
            self.client.post(
                reverse("registrations:registration-details"), {"clinic_code": "123457"}
            )
            self.client.post(
                reverse("registrations:registration-details"), {"clinic_code": "123457"}
            )
        [error_log] = logs.output
        self.assertIn("Jembi API error limit reached", error_log)

    @responses.activate
    def test_form_success(self):
        """
        Should put the form details and clinic name in the session
        """
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json",
            json={"next": None, "previous": None, "results": []},
            status=200,
            headers={"Authorization": "Token some_token"},
        )

        clinic_data = {
            "title": "Facility Check Nurse Connect",
            "headers": [],
            "rows": [["123457", "yGVQRg2PXNh", "Test Clinic"]],
            "width": 3,
            "height": 1,
        }
        responses.add(
            responses.GET,
            "http://testopenhim/NCfacilityCheck?"
            + urlencode({"criteria": "value:123457"}),
            json=clinic_data,
            status=200,
        )

        r = self.client.post(
            reverse("registrations:registration-details"),
            {"msisdn": "0820001001", "clinic_code": "123457", "consent": ["True"]},
        )
        self.assertRedirects(r, reverse("registrations:confirm-clinic"))
        self.assertEqual(
            self.client.session["registration_details"],
            {"msisdn": "+27820001001", "clinic_code": "123457", "consent": ["True"]},
        )
        self.assertEqual(self.client.session["clinic_name"], "Test Clinic")
        self.assertEqual(self.client.session["clinic_code"], "123457")


class OptinConfirmTests(TestCase):
    def test_redirect_on_invalid_session(self):
        """
        If there isn't a msisdn in the session, then we should redirect to the
        registration details page, as the user went to this page without first going
        through the registration details page.
        """
        r = self.client.get(reverse("registrations:confirm-optin"))
        self.assertRedirects(r, reverse("registrations:registration-details"))

    def test_goes_to_clinic_confirm_on_yes(self):
        """
        If "yes" is selected, we should redirect to the clinic confirmation page
        """
        session = self.client.session
        session["registration_details"] = {"msisdn": "+27820001001"}
        session["clinic_name"] = "Test clinic"
        session.save()
        r = self.client.post(reverse("registrations:confirm-optin"), {"yes": ["Yes"]})
        self.assertRedirects(r, reverse("registrations:confirm-clinic"))

    def test_goes_to_farewell_page_on_no(self):
        """
        If "no" is selected, we should redirect to a farewell page
        """
        session = self.client.session
        session["registration_details"] = {"msisdn": "+27820001001"}
        session.save()
        r = self.client.post(reverse("registrations:confirm-optin"), {"no": ["No"]})
        self.assertRedirects(r, reverse("registrations:reject-optin"))


class ClinicConfirmTests(TestCase):
    def test_redirect_on_invalid_session(self):
        """
        If there isn't a clinic name in the session, then we should redirect to the
        registration details page, as the user went to this page without first going
        through the registration details page.
        """
        r = self.client.get(reverse("registrations:confirm-clinic"))
        self.assertRedirects(r, reverse("registrations:registration-details"))

    @mock.patch("registrations.views.send_registration_to_openhim")
    @mock.patch("registrations.views.send_registration_to_rapidpro")
    @mock.patch("registrations.views.RegistrationConfirmClinic.get_channel")
    def test_goes_to_end_on_yes(self, get_channel, _, _2):
        """
        If "yes" is selected, we should set the channel and redirect to the success page
        """
        get_channel.return_value = "WhatsApp"
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {
            "msisdn": "+27820001001",
            "clinic_code": "123457",
        }
        session["contact"] = {}
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        self.assertEqual(self.client.session["channel"], "WhatsApp")
        self.assertRedirects(r, reverse("registrations:success"))

    def test_goes_to_homepage_no(self):
        """
        If "no" is selected, we should redirect to the registration details page, set
        the clinic code error message, and remove the clinic code from the initial
        form values
        """
        session = self.client.session
        session["clinic_name"] = "Test clinic"
        session["registration_details"] = {
            "msisdn": "+27820001001",
            "clinic_code": "123457",
        }
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"no": ["No"]})
        self.assertEqual(
            self.client.session["clinic_code_error"],
            "Please re-enter your 6-digit clinic code.",
        )
        self.assertNotIn("clinic_code", self.client.session["registration_details"])
        self.assertRedirects(r, reverse("registrations:registration-details"))

    @responses.activate
    @mock.patch("registrations.views.send_registration_to_openhim")
    @mock.patch("registrations.views.send_registration_to_rapidpro")
    def test_get_channel_whatsapp(self, _, _2):
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
        session["registration_details"] = {
            "msisdn": "+27820001001",
            "clinic_code": "123457",
        }
        session["contact"] = {}
        session.save()
        r = self.client.post(reverse("registrations:confirm-clinic"), {"yes": ["Yes"]})
        self.assertEqual(self.client.session["channel"], "WhatsApp")
        self.assertRedirects(r, reverse("registrations:success"))

    @responses.activate
    @mock.patch("registrations.views.send_registration_to_openhim")
    @mock.patch("registrations.views.send_registration_to_rapidpro")
    def test_get_channel_sms(self, _, _2):
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
        session["registration_details"] = {
            "msisdn": "+27820001001",
            "clinic_code": "123457",
        }
        session["contact"] = {}
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

    @responses.activate
    def test_correct_info_sent_to_openhim(self):
        """
        Check that the correct values for the registration are being sent to the OpenHIM
        API.
        """
        responses.add(responses.POST, "http://testopenhim/nc/subscription")
        timestamp = datetime(2019, 1, 1).timestamp()
        channel = "WhatsApp"
        msisdn = "+27820001001"
        clinic_code = "123457"
        contact_persal = "testpersal"
        contact_sanc = "testsanc"
        registered_by = "+27820001002"

        send_registration_to_openhim(
            msisdn,
            registered_by,
            channel,
            clinic_code,
            contact_persal,
            contact_sanc,
            timestamp,
        )
        [call] = responses.calls
        self.assertEqual(
            json.loads(call.request.body),
            {
                "mha": 1,
                "swt": 7,
                "type": 7,
                "cmsisdn": "+27820001001",
                "dmsisdn": "+27820001002",
                "rmsisdn": None,
                "faccode": "123457",
                "id": "27820001001^^^ZAF^TEL",
                "dob": None,
                "persal": "testpersal",
                "sanc": "testsanc",
                "encdate": "20190101000000",
            },
        )
        self.assertEqual(
            call.request.headers["Authorization"], "Basic UkVQTEFDRU1FOlJFUExBQ0VNRQ=="
        )

    def get_rp_responses_data(self):
        """
        Returns data to be used for resposes to RapidPro requests in multiple tests.
        """
        contact_data = {
            "uuid": "89341938-7c98-4c8e-bc9d-7cd8c9cfc468",
            "name": "Test User",
            "language": None,
            "urns": ["tel:+27820001001", "whatsapp:27820001001"],
            "groups": [],
            "fields": {
                "persal": None,
                "opt_out_date": None,
                "registered_by": "+27820001002",
                "facility_code": "123457",
                "registration_date": "2019-01-01T00:00:00.000000Z",
                "preferred_channel": "whatsapp",
                "sanc": None,
            },
            "blocked": None,
            "stopped": None,
            "created_on": "2019-01-01T00:00:00.000000Z",
            "modified_on": "2019-01-01T00:00:00.000000Z",
        }
        flows_data = {
            "next": None,
            "previous": None,
            "results": [
                {
                    "uuid": "9766a4c2-12c3-4eeb-9e39-912662918a9c",
                    "name": "Post Registration",
                    "type": "message",
                    "archived": False,
                    "labels": [],
                    "expires": 10080,
                    "runs": {
                        "active": 0,
                        "completed": 1,
                        "interrupted": 0,
                        "expired": 0,
                    },
                    "created_on": "2019-04-09T09:25:01.532016Z",
                    "modified_on": "2019-04-09T09:32:12.657544Z",
                }
            ],
        }
        flow_start_data = {
            "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
            "flow": {
                "uuid": "9766a4c2-12c3-4eeb-9e39-912662918a9c",
                "name": "Post Registration",
            },
            "groups": [],
            "contacts": [{"uuid": "89341938-7c98-4c8e-bc9d-7cd8c9cfc468", "name": ""}],
            "restart_participants": False,
            "status": "complete",
            "extra": {},
            "created_on": "2013-08-19T19:11:21.082Z",
            "modified_on": "2013-08-19T19:11:21.082Z",
        }
        return {
            "contact_data": contact_data,
            "flows_data": flows_data,
            "flow_start_data": flow_start_data,
        }

    @responses.activate
    def test_registration_created_for_existing_contact(self):
        """
        Check that the correct information is being sent to RapidPro to create
        the registration.
        """
        contact_list_data = {
            "next": None,
            "previous": None,
            "results": [
                {
                    "uuid": "89341938-7c98-4c8e-bc9d-7cd8c9cfc468",
                    "name": "Test User",
                    "language": None,
                    "urns": ["tel:+27820001001", "whatsapp:27820001001"],
                    "groups": [],
                    "fields": {
                        "persal": None,
                        "opt_out_date": None,
                        "registered_by": "+27820001002",
                        "facility_code": "123457",
                        "registration_date": "2019-01-01T00:00:00.000000Z",
                        "preferred_channel": "whatsapp",
                        "sanc": None,
                    },
                    "blocked": None,
                    "stopped": None,
                    "created_on": "2019-01-01T00:00:00.000000Z",
                    "modified_on": "2019-01-01T00:00:00.000000Z",
                }
            ],
        }
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"urn": "tel:+27820001001"}),
            json=contact_list_data,
        )

        response_data = self.get_rp_responses_data()
        responses.add(
            responses.POST,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"uuid": "89341938-7c98-4c8e-bc9d-7cd8c9cfc468"}),
            json=response_data["contact_data"],
        )

        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/flows.json?",
            json=response_data["flows_data"],
        )

        responses.add(
            responses.POST,
            "https://test.rapidpro/api/v2/flow_starts.json",
            json=response_data["flow_start_data"],
        )

        timestamp = datetime(2019, 1, 1).timestamp()
        channel = "WhatsApp"
        msisdn = "+27820001001"
        clinic_code = "123457"
        registered_by = "+27820001002"
        contact = {
            "uuid": "89341938-7c98-4c8e-bc9d-7cd8c9cfc468",
            "fields": {"persal": "testpersal", "sanc": "testsanc"},
        }

        send_registration_to_rapidpro(
            contact, msisdn, registered_by, channel, clinic_code, timestamp
        )
        [rp_call_1, rp_contact_call, rp_call_3, rp_flow_start_call] = responses.calls

        self.assertEqual(
            json.loads(rp_contact_call.request.body),
            {
                "fields": {
                    "preferred_channel": "whatsapp",
                    "registered_by": "+27820001002",
                    "facility_code": "123457",
                    "registration_date": "2019-01-01T00:00:00.000000Z",
                    "reg_source": "mobi-site",
                }
            },
        )
        self.assertEqual(
            json.loads(rp_flow_start_call.request.body),
            {
                "flow": "9766a4c2-12c3-4eeb-9e39-912662918a9c",
                "contacts": ["89341938-7c98-4c8e-bc9d-7cd8c9cfc468"],
            },
        )

    @responses.activate
    def test_registration_created_for_new_contact(self):
        """
        Check that the correct information is being sent to RapidPro to create
        the registration.
        """
        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/contacts.json?"
            + urlencode({"urn": "tel:+27820001001"}),
            json={"next": None, "previous": None, "results": []},
        )

        response_data = self.get_rp_responses_data()
        responses.add(
            responses.POST,
            "https://test.rapidpro/api/v2/contacts.json?",
            json=response_data["contact_data"],
        )

        responses.add(
            responses.GET,
            "https://test.rapidpro/api/v2/flows.json?",
            json=response_data["flows_data"],
        )

        responses.add(
            responses.POST,
            "https://test.rapidpro/api/v2/flow_starts.json",
            json=response_data["flow_start_data"],
        )
        responses.add(responses.POST, "http://testopenhim/nc/subscription")

        timestamp = datetime(2019, 1, 1).timestamp()
        channel = "WhatsApp"
        msisdn = "+27820001001"
        clinic_code = "123457"
        registered_by = "+27820001002"
        contact = {}

        send_registration_to_rapidpro(
            contact, msisdn, registered_by, channel, clinic_code, timestamp
        )
        [rp_call_1, rp_contact_call, rp_call_3, rp_flow_start_call] = responses.calls

        self.assertEqual(
            json.loads(rp_contact_call.request.body),
            {
                "urns": ["tel:+27820001001", "whatsapp:27820001001"],
                "fields": {
                    "preferred_channel": "whatsapp",
                    "registered_by": "+27820001002",
                    "facility_code": "123457",
                    "registration_date": "2019-01-01T00:00:00.000000Z",
                    "reg_source": "mobi-site",
                },
            },
        )
        self.assertEqual(
            json.loads(rp_flow_start_call.request.body),
            {
                "flow": "9766a4c2-12c3-4eeb-9e39-912662918a9c",
                "contacts": ["89341938-7c98-4c8e-bc9d-7cd8c9cfc468"],
            },
        )


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
