from django.urls import path

from registrations.views import (
    RegistrationDetailsView,
    RegistrationConfirmClinic,
    RegistrationSuccess,
)

urlpatterns = [
    path("", RegistrationDetailsView.as_view(), name="registration-details"),
    path("confirm_clinic", RegistrationConfirmClinic.as_view(), name="confirm-clinic"),
    path("success", RegistrationSuccess.as_view(), name="success"),
]
