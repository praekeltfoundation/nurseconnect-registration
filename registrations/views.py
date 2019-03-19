from django.shortcuts import redirect
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django.urls import reverse_lazy

from registrations.forms import RegistrationDetailsForm


class RegistrationDetailsView(FormView):
    form_class = RegistrationDetailsForm
    template_name = "registrations/registration_details.html"
    success_url = reverse_lazy("registrations:confirm-clinic")

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
        # Clear the session, since we no longer need it.
        self.request.session.clear()
        return context
