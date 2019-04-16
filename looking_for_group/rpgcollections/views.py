from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from ..game_catalog import models as db_models
from ..gamer_profiles.models import GamerProfile
from . import models

# Views from here on out assume you are specifying a specific user to view. In site architechture it is a subset of the gamer profile.
# You will also need to be authenticated to view anyone's collection, and collections are only visible to people with whom you have a connection.


class BookListView(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.ListView
):
    """
    For given user, get or create the library object and do a paginated list of the collection objects.
    """

    model = models.Book
    permission_required = "profile.view_detail"
    select_related = ["library"]
    prefetch_related = ["content_object"]
    paginate_by = 15
    paginate_orphans = 2
    context_object_name = "book_list"
    template_name = "rpgcollections/book_list.html"

    def dispatch(self, request, *args, **kwargs):
        gamerslug = kwargs.pop("gamer", None)
        self.gamer = get_object_or_404(GamerProfile, username=gamerslug)
        self.library, created = models.GameLibrary.objects.get_or_create(
            user=self.gamer.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(self.library)

    def get_permission_object(self):
        return self.gamer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.gamer
        context["library"] = self.library
        return context
