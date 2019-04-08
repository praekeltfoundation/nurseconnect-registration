from rest_framework import permissions, viewsets
from rest_framework.response import Response

from registrations.models import ReferralLink
from registrations.serializers import URN_REGEX, RapidProFlowWebHookSerializer
from registrations.utils import normalise_msisdn


class ReferralLinkViewSet(viewsets.GenericViewSet):
    """
    Allows the creating of referral links
    """

    serializer_class = RapidProFlowWebHookSerializer
    queryset = ReferralLink.objects.all()
    permission_classes = (permissions.DjangoModelPermissions,)

    def create(self, request):
        """
        Returns the full referral URI for the given MSISDN
        """
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        urn = serializer.validated_data["contact"]["urn"]
        msisdn = URN_REGEX.match(urn).group("path")
        msisdn = normalise_msisdn(msisdn)
        referral, _ = ReferralLink.objects.get_or_create(msisdn=msisdn)
        return Response({"referral_link": referral.build_uri(request)})
