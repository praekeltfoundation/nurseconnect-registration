from django.conf import settings
from django.db import models
from django.urls import reverse
from hashids import Hashids

from registrations.validators import msisdn_validator

hashids = Hashids(salt=settings.SECRET_KEY, min_length=6)


class ReferralLinkManager(models.Manager):
    def get_from_referral_code(self, code):
        """
        Gets the ReferralLink object given the referral code
        """
        try:
            [id] = hashids.decode(code)
        except ValueError:
            id = None
        return self.get(id=id)


class ReferralLink(models.Model):
    objects = ReferralLinkManager()
    msisdn = models.CharField(
        max_length=12,
        unique=True,
        verbose_name="MSISDN",
        validators=[msisdn_validator],
        help_text="The MSISDN of the user who referred the current registration",
    )

    @property
    def code(self):
        """
        The code used to referece the referral in the URL
        """
        return hashids.encode(self.id)

    @property
    def path(self):
        """
        The path used in the referral link
        """
        return reverse("registrations:registration-details", args=[self.code])

    def build_uri(self, request):
        """
        Builds the absolute URI for the referral link
        """
        return request.build_absolute_uri(self.path)

    def __str__(self):
        return "{} <{}>".format(self.msisdn, self.code)
