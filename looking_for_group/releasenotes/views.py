from django.http import JsonResponse
from django.views import generic

from . import models, serializers

# Create your views here.


class ReleaseNotesView(generic.ListView):

    model = models.ReleaseNote
    template_name = "releasenotes/release_note_list.html"
    context_object_name = "rn_list"

    def get_queryset(self):
        return self.model.objects.all().order_by("-version")


class ReleaseNotesJSONView(generic.ListView):
    model = models.ReleaseNote

    def get_queryset(self):
        return self.model.objects.all().order_by("-version")

    def get_data(self):
        rn_serial = serializers.ReleaseNoteSerializer(self.get_queryset(), many=True)
        return rn_serial.data

    def render_to_response(self, context, **kwargs):
        return JsonResponse(data=self.get_data(), safe=False)
