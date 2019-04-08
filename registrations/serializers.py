import re

from rest_framework import serializers

URN_REGEX = re.compile(r"^(?P<scheme>.+):(?P<path>.+)$")


class RapidProFlowWebHookSerializer(serializers.Serializer):
    class Contact(serializers.Serializer):
        urn = serializers.RegexField(
            URN_REGEX, help_text="The URN of the contact that triggered the flow"
        )

    contact = Contact(help_text="The contact that triggered the flow")
