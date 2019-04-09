from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from registrations.forms import RegistrationDetailsForm
from registrations.models import ReferralLink
from registrations.utils import contact_in_groups


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

        if contact_in_groups(form.cleaned_data['msisdn'], ['opted-out']):
            return redirect(reverse_lazy("registrations:confirm-optin"))
        return super().form_valid(form)

    def get_initial(self):
        if "registration_details" in self.request.session:
            return self.request.session["registration_details"]
        return super().get_initial()


class RegistrationConfirmOptIn(TemplateView):
    template_name = "registrations/confirm_optin.html"

    def dispatch(self, request, *args, **kwargs):
        if "registration_details" not in request.session or 'msisdn' not in \
                request.session.get('registration_details', {}):
            return redirect(reverse_lazy("registrations:registration-details"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["msisdn"] = self.request.session["registration_details"]["msisdn"]
        return context

    def post(self, request, *args, **kwargs):
        if "yes" in request.POST:
            request.session["channel"] = "WhatsApp"
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

    def post(self, request, *args, **kwargs):
        if "yes" in request.POST:
            # TODO: WhatsApp check
            # TODO: Create registration
            request.session["channel"] = "WhatsApp"
            return redirect(reverse_lazy("registrations:success"))
        return redirect(reverse_lazy("registrations:registration-details"))


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
