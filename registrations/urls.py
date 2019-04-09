from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework import routers

from registrations.api_views import ReferralLinkViewSet
from registrations.views import (
    RegistrationConfirmClinic,
    RegistrationConfirmOptIn,
    RegistrationDetailsView,
    RegistrationSuccess,
    TermsAndConditionsView,
)

api_router = routers.DefaultRouter()
api_router.register("referral_link", ReferralLinkViewSet)

urlpatterns = [
    path("", RegistrationDetailsView.as_view(), name="registration-details"),
    path("confirm_optin", RegistrationConfirmOptIn.as_view(), name="confirm-optin"),
    path(
        "reject_optin",
        TemplateView.as_view(template_name="registrations/reject_optin.html"),
        name="reject-optin",
    ),
    path("confirm_clinic", RegistrationConfirmClinic.as_view(), name="confirm-clinic"),
    path("success", RegistrationSuccess.as_view(), name="success"),
    path(
        "terms_and_conditions/",
        TermsAndConditionsView.as_view(),
        name="terms_and_conditions",
    ),
    path("api/v1/", include(api_router.urls)),
    path("<referral>", RegistrationDetailsView.as_view(), name="registration-details"),
]
