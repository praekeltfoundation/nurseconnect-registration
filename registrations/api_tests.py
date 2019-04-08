from django.contrib.auth.models import Permission, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from registrations.models import ReferralLink


class ReferralLinkApiTests(APITestCase):
    def test_authentication_required(self):
        """
        Authentication is required for this endpoint
        """
        r = self.client.post(reverse("registrations:referrallink-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_required(self):
        """
        You must have the create referral link permission for this endpoint.
        """
        user = User.objects.create_user("test")
        self.client.force_login(user)
        r = self.client.post(reverse("registrations:referrallink-list"))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_new_referral_link(self):
        """
        If a referral link for the given MSISDN doesn't exist, it should be created
        """
        self.assertEqual(ReferralLink.objects.count(), 0)
        user = User.objects.create_user("test")
        permission = Permission.objects.get(name="Can add referral link")
        user.user_permissions.add(permission)
        user.save()
        self.client.force_login(user)

        r = self.client.post(
            reverse("registrations:referrallink-list"),
            {"contact": {"urn": "tel:27820001001"}},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        [referral] = ReferralLink.objects.all()
        self.assertIn(referral.path, r.data["referral_link"])

    def test_existing_referral_link(self):
        """
        If a referral link already exists for an URN, then a new one should not be
        created
        """
        ReferralLink.objects.create(msisdn="+27820001001")
        user = User.objects.create_user("test")
        permission = Permission.objects.get(name="Can add referral link")
        user.user_permissions.add(permission)
        user.save()
        self.client.force_login(user)

        self.assertEqual(ReferralLink.objects.count(), 1)
        r = self.client.post(
            reverse("registrations:referrallink-list"),
            {"contact": {"urn": "tel:27820001001"}},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        [referral] = ReferralLink.objects.all()
        self.assertIn(referral.path, r.data["referral_link"])
