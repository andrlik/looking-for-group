from rest_framework import serializers

from .models import ReleaseNote


class ReleaseNoteSerializer(serializers.ModelSerializer):
    """
    Serializes a release note object.
    """

    class Meta:
        fields = ("version", "notes", "notes_rendered")
        read_only_fields = fields
        model = ReleaseNote
