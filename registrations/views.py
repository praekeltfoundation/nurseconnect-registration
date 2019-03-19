from django.views.generic.edit import FormView

from registrations.forms import RegistrationDetailsForm


class RegistrationDetailsView(FormView):
    form_class = RegistrationDetailsForm
    template_name = "registrations/registration_details.html"
