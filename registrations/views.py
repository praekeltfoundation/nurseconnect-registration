import logging
from datetime import datetime

from celery import chain
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from prometheus_client import Counter
from requests.exceptions import RequestException
from wabclient.exceptions import AddressException

from registrations.forms import RegistrationDetailsForm
from registrations.models import ReferralLink
from registrations.tasks import (
    send_registration_to_openhim,
    send_registration_to_rapidpro,
)
from registrations.utils import contact_in_rapidpro_groups, wabclient

WHATSAPP_API_FAILURES = Counter("whatsapp_api_failures", "WhatsApp API failures")


class RegistrationDetailsView(FormView):
    form_class = RegistrationDetailsForm
    template_name = "registrations/registration_details.html"
    success_url = reverse_lazy("registrations:confirm-clinic")

    def dispatch(self, request, *args, **kwargs):
        try:
            code = kwargs["referral"]
            referral = ReferralLink.objects.get_from_referral_code(code)
            request.session["registered_by"] = referral.msisdn
        except (ReferralLink.DoesNotExist, KeyError):
            # Don't alert the user, just act like no referral code was given
            pass
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "clinic_code_error" in self.request.session:
            context["clinic_code_error"] = self.request.session.pop("clinic_code_error")
        return context

    def get_form_kwargs(self):
        kwargs = super(RegistrationDetailsView, self).get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.request.session["registration_details"] = form.cleaned_data

        contact = self.request.session["contact"]
        if contact_in_rapidpro_groups(contact, ["opted-out"]):
            return redirect(reverse_lazy("registrations:confirm-optin"))
        return super().form_valid(form)

    def get_initial(self):
        if "registration_details" in self.request.session:
            return self.request.session["registration_details"]
        return super().get_initial()


class RegistrationConfirmOptIn(TemplateView):
    template_name = "registrations/confirm_optin.html"

    def dispatch(self, request, *args, **kwargs):
        if (
            "registration_details" not in request.session
            or "msisdn" not in request.session.get("registration_details", {})
        ):
            return redirect(reverse_lazy("registrations:registration-details"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if "yes" in request.POST:
            return redirect(reverse_lazy("registrations:confirm-clinic"))
        return redirect(reverse_lazy("registrations:reject-optin"))


class RegistrationConfirmClinic(TemplateView):
    template_name = "registrations/confirm_clinic.html"

    def dispatch(self, request, *args, **kwargs):
        if "clinic_name" not in request.session:
            return redirect(reverse_lazy("registrations:registration-details"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["clinic_name"] = self.request.session["clinic_name"]
        return context

    def get_channel(self, msisdn):
        """
        Returns "WhatsApp" or "SMS" depending on whether the MSISDN is
        whatsappable.

        Args:
            msisdn (str): The MSISDN to query
        """
        try:
            wabclient.get_address(msisdn)
            return "WhatsApp"
        except AddressException:
            return "SMS"

    def post(self, request, *args, **kwargs):
        session = request.session

        if "yes" not in request.POST:
            session["registration_details"].pop("clinic_code")
            session["clinic_code_error"] = "Please re-enter your 6-digit clinic code."
            return redirect(reverse_lazy("registrations:registration-details"))

        try:
            session["channel"] = self.get_channel(
                request.session["registration_details"]["msisdn"]
            )
        except RequestException:
            WHATSAPP_API_FAILURES.inc()

            # Ensure that we know of repeating errors
            try:
                session["whatsapp_api_errors"] += 1
            except KeyError:
                session["whatsapp_api_errors"] = 1
            if session.get("whatsapp_api_errors", 0) >= 3:
                logging.exception("WhatsApp API error limit reached")

            messages.error(
                request,
                "There was an error creating your registration. Please try again.",
            )
            return redirect(reverse_lazy("registrations:confirm-clinic"))

        chain(
            send_registration_to_rapidpro.s(
                contact=session["contact"],
                msisdn=session["registration_details"]["msisdn"],
                referral_msisdn=session.get("registered_by"),
                channel=session["channel"],
                clinic_code=session["registration_details"]["clinic_code"],
                timestamp=datetime.utcnow().timestamp(),
            ),
            send_registration_to_openhim.s(
                referral_msisdn=session.get("registered_by"),
                channel=session["channel"],
                clinic_code=session["registration_details"]["clinic_code"],
                persal=session.get("contact", {}).get("fields", {}).get("persal", None),
                sanc=session.get("contact", {}).get("fields", {}).get("sanc", None),
                timestamp=datetime.utcnow().timestamp(),
            ),
        ).apply_async()

        return redirect(reverse_lazy("registrations:success"))


class RegistrationSuccess(TemplateView):
    template_name = "registrations/success.html"

    def dispatch(self, request, *args, **kwargs):
        if "channel" not in self.request.session:
            return redirect(reverse_lazy("registrations:confirm-clinic"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = self.request.session.pop("channel")

        msisdn = self.request.session["registration_details"]["msisdn"]
        referral, _ = ReferralLink.objects.get_or_create(msisdn=msisdn)
        context["referral_link"] = referral.build_uri(self.request)

        # Clear the session, since we no longer need it.
        self.request.session.clear()
        return context


class TermsAndConditionsView(TemplateView):
    template_name = "terms_and_conditions.html"
