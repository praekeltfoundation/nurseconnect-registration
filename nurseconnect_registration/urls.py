"""nurseconnect_registration URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django_prometheus.exports import ExportToDjangoView as metrics

from nurseconnect_registration.decorators import internal_only
from nurseconnect_registration.views import TermsAndConditionsView

urlpatterns = [
    path("", include(("registrations.urls", "registrations"))),
    path("admin/", admin.site.urls),
    path("metrics", internal_only(metrics), name="metrics"),
    path("health/", include(("watchman.urls", "health"))),
    path("terms_and_conditions/", TermsAndConditionsView.as_view()),
]
