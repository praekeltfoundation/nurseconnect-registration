from django.conf import settings
from django.db import models
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
        return hashids.encode(self.id)

    def __str__(self):
        return "{} <{}>".format(self.msisdn, self.code)
