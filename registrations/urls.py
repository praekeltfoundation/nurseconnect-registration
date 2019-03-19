from django.urls import path

from registrations.views import RegistrationDetailsView

urlpatterns = [path("", RegistrationDetailsView.as_view(), name="registration-details")]
