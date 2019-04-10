import logging

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
from registrations.utils import wabclient

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

    def form_valid(self, form):
        self.request.session["registration_details"] = form.cleaned_data
        # TODO: Replace with result of clinic code check
        self.request.session["clinic_name"] = "Test clinic"
        return super().form_valid(form)

    def get_initial(self):
        if "registration_details" in self.request.session:
            return self.request.session["registration_details"]
        return super().get_initial()


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
        if "yes" not in request.POST:
            return redirect(reverse_lazy("registrations:registration-details"))

        # TODO: Create registration

        try:
            request.session["channel"] = self.get_channel(
                request.session["registration_details"]["msisdn"]
            )
        except RequestException:
            WHATSAPP_API_FAILURES.inc()

            # Ensure that we know of repeating errors
            try:
                request.session["whatsapp_api_errors"] += 1
            except KeyError:
                request.session["whatsapp_api_errors"] = 1
            if request.session.get("whatsapp_api_errors", 0) >= 3:
                logging.exception("WhatsApp API error limit reached")

            messages.error(
                request,
                "There was an error creating your registration. Please try again.",
            )
            return redirect(reverse_lazy("registrations:confirm-clinic"))

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
