from django.urls import path

from registrations.views import (
    RegistrationConfirmClinic,
    RegistrationDetailsView,
    RegistrationSuccess,
    TermsAndConditionsView,
)

urlpatterns = [
    path("", RegistrationDetailsView.as_view(), name="registration-details"),
    path("confirm_clinic", RegistrationConfirmClinic.as_view(), name="confirm-clinic"),
    path("success", RegistrationSuccess.as_view(), name="success"),
    path(
        "terms_and_conditions/",
        TermsAndConditionsView.as_view(),
        name="terms_and_conditions",
    ),
    path("<referral>", RegistrationDetailsView.as_view(), name="registration-details"),
]
