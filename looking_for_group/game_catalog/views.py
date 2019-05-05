import logging
from datetime import timedelta

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from ..rpgcollections.forms import BookForm
from . import forms
from .models import (
    GameEdition,
    GamePublisher,
    GameSystem,
    PublishedGame,
    PublishedModule,
    SourceBook,
    SuggestedAddition,
    SuggestedCorrection,
)
from .utils import combined_recent

# Create your views here.
# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.

logger = logging.getLogger("games")

type_matching = {
    "publisher": GamePublisher,
    "game": PublishedGame,
    "system": GameSystem,
    "edition": GameEdition,
    "module": PublishedModule,
    "sourcebook": SourceBook,
}


class GamePublisherListView(PrefetchRelatedMixin, generic.ListView):
    """
    List view of game publishers. We prefetch so we can list number of games, modules, etc.
    """

    model = GamePublisher
    prefetch_related = ["gamesystem_set", "gameedition_set", "publishedmodule_set"]
    template_name = "catalog/pub_list.html"
    ordering = ["name"]
    paginate_by = 30
    paginate_orphans = 4


class GamePublisherDetailView(PrefetchRelatedMixin, generic.DetailView):
    model = GamePublisher
    prefetch_related = ["gamesystem_set", "gameedition_set", "publishedmodule_set"]
    pk_url_kwarg = "publisher"
    context_object_name = "publisher"
    template_name = "catalog/pub_detail.html"


class GamePublisherUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update a game publisher view.
    """

    model = GamePublisher
    pk_url_kwarg = "publisher"
    context_object_name = "publisher"
    template_name = "catalog/pub_edit.html"
    fields = ["name", "logo", "url", "description"]
    permission_required = "catalog.can_edit"

    def get_success_url(self):
        return self.object.get_absolute_url()


class GamePublisherCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a new game publisher.
    """

    model = GamePublisher
    fields = ["name", "logo", "url", "description"]
    permission_required = "catalog.can_edit"
    template_name = "catalog/pub_create.html"

    def get_permission_object(self):
        return self.model


class GamePublisherDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete a game publisher.
    """

    model = GamePublisher
    permission_required = "catalog.can_edit"
    prefetch_related = ["gameedition_set", "gamesystem_set", "publishedmodule_set"]
    template_name = "catalog/pub_delete.html"
    context_object_name = "publisher"
    pk_url_kwarg = "publisher"

    def get_success_url(self):
        return reverse_lazy("game_catalog:pub-list")


class GameSystemCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a game system.
    """

    model = GameSystem
    permission_required = "catalog.can_edit"
    template_name = "catalog/system_create.html"
    form_class = forms.SystemForm

    def get_permission_object(self):
        return self.model

    def get_success_url(self):
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.object.original_publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key did not exist yet
        return self.object.get_absolute_url()

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())


class GameSystemListView(SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView):
    model = GameSystem
    select_related = ["original_publisher"]
    prefetch_related = ["game_editions"]
    template_name = "catalog/system_list.html"
    ordering = ["name"]
    paginate_by = 30
    paginate_orphans = 4


class GameSystemDetailView(
    SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView
):
    model = GameSystem
    select_related = ["original_publisher"]
    prefetch_related = ["game_editions"]
    pk_url_kwarg = "system"
    context_object_name = "system"
    template_name = "catalog/system_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["collect_form"] = BookForm(initial={"object_id": context["system"].pk})
        return context


class GameSystemUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for game system.
    """

    model = GameSystem
    context_object_name = "system"
    pk_url_kwarg = "system"
    permission_required = "catalog.can_edit"
    form_class = forms.SystemForm
    template_name = "catalog/system_edit.html"

    def get_success_url(self):
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.get_object().original_publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key did not exist yet
        return self.object.get_absolute_url()


class GameSystemDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for game system.
    """

    model = GameSystem
    context_object_name = "system"
    select_related = ["original_publisher"]
    prefetch_related = ["game_editions", "gameposting_set", "gamerprofile_set"]
    pk_url_kwarg = "system"
    permission_required = "catalog.can_edit"
    template_name = "catalog/system_delete.html"
    success_url = reverse_lazy("game_catalog:system-list")

    def delete(self, request, *args, **kwargs):
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.get_object().original_publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key did not exist yet
        return super().delete(request, *args, **kwargs)


class PublishedGameCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a published game.
    """

    model = PublishedGame
    permission_required = "catalog.can_edit"
    template_name = "catalog/game_create.html"
    form_class = forms.GameForm

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_permission_object(self):
        return self.model


class PublishedGameListView(PrefetchRelatedMixin, generic.ListView):
    model = PublishedGame
    prefetch_related = ["editions"]
    template_name = "catalog/game_list.html"
    ordering = ["title", "-publication_date"]
    paginate_by = 30
    paginate_orphans = 4


class PublishedGameUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a game
    """

    model = PublishedGame
    permission_required = "catalog.can_edit"
    form_class = forms.GameForm
    pk_url_kwarg = "game"
    context_object_name = "game"
    template_name = "catalog/game_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class PublishedGameDetailView(PrefetchRelatedMixin, generic.DetailView):
    model = PublishedGame
    prefetch_related = ["editions"]
    pk_url_kwarg = "game"
    context_object_name = "game"
    template_name = "catalog/game_detail.html"


class PublishedGameDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for published game.
    """

    model = PublishedGame
    permission_required = "catalog.can_edit"
    context_object_name = "game"
    prefetch_related = ["editions"]
    pk_url_kwarg = "game"
    template_name = "catalog/game_delete.html"
    success_url = reverse_lazy("game_catalog:game-list")


class EditionCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create view for a new edition.
    """

    model = GameEdition
    permission_required = "catalog.can_edit"
    form_class = forms.EditionForm
    template_name = "catalog/edition_create.html"

    def get_permission_object(self):
        return self.model

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop("game", None)
        self.game = get_object_or_404(PublishedGame, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def form_valid(self, form):
        edition = form.save(commit=False)
        edition.game = self.game
        edition.save()
        try:
            # Now attempt to invalidate the publisher cache.
            pub_key = make_template_fragment_key(
                "publisher_publications", [edition.publisher.pk]
            )
            cache.incr_version(pub_key)
        except ValueError:
            # pub_key is not active
            pass
        return HttpResponseRedirect(edition.get_absolute_url())


class EditionUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a game edition.
    """

    model = GameEdition
    permission_required = "catalog.can_edit"
    form_class = forms.EditionForm
    context_object_name = "edition"
    slug_url_kwarg = "edition"
    template_name = "catalog/edition_edit.html"

    def form_valid(self, form):
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.get_object().publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key didn't exist
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class EditionDetailView(SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView):
    model = GameEdition
    select_related = ["game_system", "publisher", "game"]
    prefetch_related = ["publishedmodule_set", "sourcebooks"]
    slug_url_kwarg = "edition"
    slug_field = "slug"
    context_object_name = "edition"
    template_name = "catalog/edition_detail.html"


class EditionDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a game edition.
    """

    model = GameEdition
    slug_url_kwarg = "edition"
    select_related = ["publisher", "game_system", "game"]
    prefetch_related = ["publishedmodule_set", "sourcebooks", "gameposting_set"]
    context_object_name = "edition"
    permission_required = "catalog.can_edit"
    template_name = "catalog/edition_delete.html"

    def delete(self, request, *args, **kwargs):
        self.game = self.get_object().game
        self.success_url = self.game.get_absolute_url()
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.get_object().publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key did not exist
        return super().delete(request, *args, **kwargs)


class SourceBookCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create view for a new sourcebook.
    """

    model = SourceBook
    form_class = forms.SourceBookForm
    permission_required = "catalog.can_edit"
    template_name = "catalog/sourcebook_create.html"

    def dispatch(self, request, *args, **kwargs):
        edition_slug = kwargs.pop("edition", None)
        self.edition = get_object_or_404(GameEdition, slug=edition_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.model

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edition"] = self.edition
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["initial"]["publisher"] = self.edition.publisher.pk
        return form_kwargs

    def form_valid(self, form):
        self.book = form.save(commit=False)
        self.book.edition = self.edition
        if not self.book.publisher:
            self.book.publisher = self.edition.publisher
        self.book.save()
        return HttpResponseRedirect(self.book.get_absolute_url())


class SourceBookDetailView(SelectRelatedMixin, generic.DetailView):
    model = SourceBook
    select_related = ["edition", "edition__game"]
    context_object_name = "book"
    template_name = "catalog/sourcebook_detail.html"
    slug_url_kwarg = "book"
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["collect_form"] = BookForm(initial={"object_id": context["book"].pk})
        return context


class SourceBookUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Edit view for a source book.
    """

    model = SourceBook
    form_class = forms.SourceBookForm
    permission_required = "catalog.can_edit"
    context_object_name = "book"
    slug_url_kwarg = "book"
    template_name = "catalog/sourcebook_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class SourceBookDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a sourcebook.
    """

    model = SourceBook
    permission_required = "catalog.can_edit"
    context_object_name = "book"
    slug_url_kwarg = "book"
    template_name = "catalog/sourcebook_delete.html"
    select_related = [
        "edition",
        "edition__game",
        "edition__publisher",
        "edition__game_system",
    ]

    def delete(self, request, *args, **kwargs):
        self.success_url = self.get_object().edition.get_absolute_url()
        return super().delete(request, *args, **kwargs)


class PublishedModuleCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a published module.
    """

    model = PublishedModule
    permission_required = "catalog.can_edit"
    template_name = "catalog/module_create.html"
    form_class = forms.ModuleForm

    def get_permission_object(self):
        return self.model

    def dispatch(self, request, *args, **kwargs):
        edition_slug = kwargs.pop("edition", None)
        self.edition = get_object_or_404(GameEdition, slug=edition_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edition"] = self.edition
        return context

    def form_valid(self, form):
        self.module = form.save(commit=False)
        self.module.parent_game_edition = self.edition
        self.module.save()
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.module.publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key did not exist yet
        return HttpResponseRedirect(self.module.get_absolute_url())


class PublishedModuleListView(SelectRelatedMixin, generic.ListView):
    model = PublishedModule
    select_related = [
        "parent_game_edition",
        "publisher",
        "parent_game_edition__game_system",
    ]
    template_name = "catalog/module_list.html"
    ordering = [
        "title",
        "parent_game_edition__game__title",
        "parent_game_edition__name",
    ]
    paginate_by = 30
    paginate_orphans = 4


class PublishedModuleUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update a published module.
    """

    model = PublishedModule
    context_object_name = "module"
    pk_url_kwarg = "module"
    form_class = forms.ModuleForm
    permission_required = "catalog.can_edit"
    template_name = "catalog/module_edit.html"

    def get_success_url(self):
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.get_object().publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key did not exist yet
        return self.object.get_absolute_url()


class PublishedModuleDetailView(SelectRelatedMixin, generic.DetailView):
    model = PublishedModule
    select_related = [
        "parent_game_edition",
        "parent_game_edition__game_system",
        "publisher",
    ]
    pk_url_kwarg = "module"
    context_object_name = "module"
    template_name = "catalog/module_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["collect_form"] = BookForm(initial={"object_id": context["module"].pk})
        return context


class PublishedModuleDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a module.
    """

    model = PublishedModule
    context_object_name = "module"
    pk_url_kwarg = "module"
    permission_required = "catalog.can_edit"
    template_name = "catalog/module_delete.html"
    select_related = ["parent_game_edition", "publisher"]
    prefetch_related = ["gameposting_set"]

    def delete(self, request, *args, **kwargs):
        pub_key = make_template_fragment_key(
            "publisher_publications", [self.get_object().publisher.pk]
        )
        try:
            cache.incr_version(pub_key)
        except ValueError:
            pass  # Key didn't exist yet.
        self.success_url = self.get_object().parent_game_edition.get_absolute_url()
        return super().delete(request, *args, **kwargs)


class RecentAdditionsView(generic.ListView):
    """
    Retrieve a list of recently added objects to the catalog and display as a list.
    """

    template_name = "catalog/recent_addition_list.html"
    model = GameEdition
    context_object_name = "recent_addition_list"

    def get_queryset(self):
        return cache.get_or_set(
            "recent_rpg_additions",
            combined_recent(
                30,
                Edition=GameEdition.objects.all()
                .select_related("game")
                .prefetch_related("tags"),
                Sourcebook=SourceBook.objects.all()
                .select_related("edition")
                .prefetch_related("tags"),
                Publisher=GamePublisher.objects.all(),
                System=GameSystem.objects.all(),
                Module=PublishedModule.objects.all().select_related(
                    "parent_game_edition"
                ),
            ),
        )


class SuggestedCorrectionListView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.ListView
):
    """
    List of pending corrections for editors to view.
    """

    model = SuggestedCorrection
    permission_required = "catalog.can_edit"
    template_name = "catalog/correction_list.html"
    paginate_by = 15
    paginate_orphans = 2
    context_object_name = "correction_list"

    def get_queryset(self):
        return self.model.objects.filter(status="new")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approved_corrections"] = self.model.objects.filter(
            status="approved", modified__gte=timezone.now() - timedelta(days=30)
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        context["denied_corrections"] = self.model.objects.filter(
            status="rejected", modified__gte=timezone.now() - timedelta(days=30)
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        return context


class SuggestedCorrectionCreateView(LoginRequiredMixin, generic.CreateView):
    """
    Create view for suggested corrections.
    """

    model = SuggestedCorrection
    template_name = "catalog/correction_create.html"
    fields = ["new_title", "new_url", "new_image"]

    def dispatch(self, request, *args, **kwargs):
        self.create_type = kwargs.pop("objtype", None)
        obj_id = kwargs.pop("object_id", None)
        if not self.create_type and obj_id:
            raise Http404
        if self.create_type not in type_matching.keys():
            raise Http404
        self.source_object = get_object_or_404(
            type_matching[self.create_type], pk=obj_id
        )
        if self.create_type == "publisher":
            self.fields = self.fields + ["new_description"]
        else:
            self.fields = self.fields + ["new_release_date"]
            if self.create_type not in ["module", "sourcebook"]:
                self.fields = self.fields + ["new_description"]
            else:
                self.fields = self.fields + ["new_isbn"]
            self.fields = self.fields + ["new_tags"]
        self.fields = self.fields + ["other_notes"]
        self.submitter = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        initial = {}
        if (
            self.create_type == "publisher"
            or self.create_type == "system"
            or self.create_type == "edition"
        ):
            initial["new_title"] = self.source_object.name
        else:
            initial["new_title"] = self.source_object.title
        if self.create_type == "edition" or self.create_type == "sourcebook":
            initial["new_release_date"] = self.source_object.release_date
        else:
            if self.create_type != "publisher":
                initial["new_release_date"] = self.source_object.publication_date
        if self.create_type != "sourcebook" and self.create_type != "module":
            initial["new_description"] = self.source_object.description
        else:
            initial["new_isbn"] = self.source_object.isbn
        if self.create_type == "system":
            initial["new_url"] = self.source_object.system_url
        else:
            if self.create_type != "sourcebook":
                initial["new_url"] = self.source_object.url
        kwargs["initial"] = initial
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_object"] = self.source_object
        context["obj_type"] = self.create_type
        return context

    def form_valid(self, form):
        new_correct = form.save(commit=False)
        new_correct.submitter = self.submitter
        new_correct.status = "new"
        new_correct.content_object = self.source_object
        new_correct.save()
        messages.success(
            self.request,
            _(
                "Thank you for your submitted correction! You will receive a notification when we make the changes."
            ),
        )
        return HttpResponseRedirect(new_correct.content_object.get_absolute_url())


class SuggestedCorrectionUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a suggested correction.
    """

    model = SuggestedCorrection
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "correction"
    fields = ["new_title", "new_url", "new_image"]
    template_name = "catalog/correction_update.html"
    context_object_name = "correction"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object().content_object
        if isinstance(obj, GamePublisher):
            self.fields = self.fields + ["new_description"]
        else:
            self.fields = self.fields + ["new_release_date"]
            if not isinstance(obj, SourceBook) and not isinstance(obj, PublishedModule):
                self.fields = self.fields + ["new_description"]
            else:
                self.fields = self.fields + ["new_isbn"]
            self.fields = self.fields + ["new_tags"]
        self.fields = self.fields + ["other_notes"]
        return super().dispatch(request, *args, **kwargs)


class SuggestedCorrectionDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.DetailView
):
    """
    Detail view for suggested correction, only available to editors.
    """

    model = SuggestedCorrection
    template_name = "catalog/correction_detail.html"
    select_related = ["submitter__gamerprofile", "reviewer__gamerprofile"]
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "correction"
    context_object_name = "correction"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_object"] = context["correction"].content_object
        return context


class SuggestedCorrectionDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView
):
    """
    Delete a suggested correction.
    """

    model = SuggestedCorrection
    template_name = "catalog/correction_delete.html"
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "correction"
    context_object_name = "correction"

    def get_success_url(self):
        return reverse_lazy("game_catalog:correction_list")


class SuggestedCorrectionApproveDenyView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Approve or deny view for Suggested Corrections.
    """

    model = SuggestedCorrection
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "correction"
    context_object_name = "correction"
    fields = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method not in ["post", "POST"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        messages.error(
            self.request,
            _(
                "There was an issue with your submitted form and so your change has not been processed."
            ),
        )
        return HttpResponseRedirect(self.get_object().get_absolute_url())

    def form_valid(self, form):
        obj = self.get_object()
        source_obj = obj.content_object
        obj.reviewer = self.request.user
        if "approve" in self.request.POST:
            if obj.new_image.name:
                if hasattr(source_obj, "logo"):
                    obj.transfer_image("logo")
                else:
                    obj.transfer_image()
            if obj.new_url:
                source_obj.url = obj.new_url
            if (
                isinstance(source_obj, GamePublisher)
                or isinstance(source_obj, GameSystem)
                or isinstance(source_obj, GameEdition)
            ):
                if obj.new_title:
                    source_obj.name = obj.new_title
            else:
                if obj.new_title:
                    source_obj.title = obj.new_title
            if not isinstance(source_obj, GamePublisher):
                if isinstance(source_obj, GameEdition) or isinstance(
                    source_obj, SourceBook
                ):
                    if obj.new_release_date:
                        source_obj.release_date = obj.new_release_date
                if not isinstance(source_obj, PublishedGame):
                    if obj.new_release_date:
                        source_obj.publication_date = obj.new_release_date
                if not isinstance(source_obj, SourceBook) and not isinstance(
                    source_obj, PublishedModule
                ):
                    if obj.new_description:
                        source_obj.description = obj.new_description
                else:
                    if obj.new_isbn:
                        source_obj.isbn = obj.new_isbn
                if obj.new_tags:
                    tag_list = None
                    if "," in obj.new_tags:
                        tag_list = obj.new_tags.split(",")
                    else:
                        tag_list = obj.new_tags
                    source_obj.tags.add(*tag_list)
            source_obj.save()
            obj.status = "approved"
            obj.save()
            messages.success(
                self.request,
                _(
                    "You have successfully approved this correction and the source object has been updated."
                ),
            )
        else:
            obj.status = "rejected"
            obj.save()
            messages.success(
                self.request, _("You have successfully rejected this correction.")
            )
        return HttpResponseRedirect(obj.get_absolute_url())


class SuggestedAdditionListView(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    List for Suggested Addition list
    """

    model = SuggestedAddition
    template_name = "catalog/addition_list.html"
    select_related = ["submitter__gamerprofile", "reviewer__gamerprofile"]
    permission_required = "catalog.can_edit"
    context_object_name = "addition_list"

    def get_queryset(self):
        return self.model.objects.filter(status="new")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approved_additions"] = self.model.objects.filter(
            status="approved", modified__gte=timezone.now() - timedelta(days=30)
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        context["rejected_additions"] = self.model.objects.filter(
            status="rejected", modified__gte=timezone.now() - timedelta(days=30)
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        return context


class SuggestedAdditionCreateView(LoginRequiredMixin, generic.CreateView):
    form_class = forms.SuggestedAdditionForm
    model = SuggestedAddition
    template_name = "catalog/addition_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.obj_type = kwargs.pop("obj_type", None)
        allowed_object_types = [
            "publisher",
            "system",
            "game",
            "edition",
            "module",
            "sourcebook",
        ]
        logger.debug("Found obj_type of {}".format(self.obj_type))
        if not self.obj_type or self.obj_type not in allowed_object_types:
            logger.debug(
                "Object type of {} is not in {}".format(
                    self.obj_type, allowed_object_types
                )
            )
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """
        Must generate the success url based on the object type to send them back to the right place.
        """
        game_list = reverse_lazy("game_catalog:game-list")
        urls_to_send = {
            "publisher": reverse_lazy("game_catalog:pub-list"),
            "game": game_list,
            "edition": game_list,
            "sourcebook": game_list,
            "module": reverse_lazy("game_catalog:module-list"),
            "system": reverse_lazy("game_catalog:system-list"),
        }
        return urls_to_send[self.obj_type]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["obj_type"] = self.obj_type
        return kwargs

    def form_valid(self, form):
        new_obj = form.save(commit=False)
        new_obj.content_type = ContentType.objects.get_for_model(
            type_matching[self.obj_type]
        )
        new_obj.submitter = self.request.user
        new_obj.save()
        messages.success(
            self.request,
            _(
                "Thank you for submitting your suggested addition. You will receive a notification when it is added to the library."
            ),
        )
        return HttpResponseRedirect(self.get_success_url())


class SuggestedAdditionUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    form_class = forms.SuggestedAdditionForm
    model = SuggestedAddition
    template_name = "catalog/addition_update.html"
    slug_url_kwarg = "addition"
    context_object_name = "addition"
    permission_required = "catalog.can_edit"
    model_map = {
        "gamepublisher": "publisher",
        "publishedgame": "game",
        "gameedition": "edition",
        "sourcebook": "sourcebook",
        "gamesystem": "system",
        "publishedmodule": "module",
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        obj = self.get_object()
        kwargs["obj_type"] = self.model_map[obj.content_type.model]
        return kwargs


class SuggestedAdditionDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.DetailView
):
    model = SuggestedAddition
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "addition"
    context_object_name = "addition"
    template_name = "catalog/addition_detail.html"
    select_related = ["submitter__gamerprofile", "reviewer__gamerprofile"]


class SuggestedAdditionDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    model = SuggestedAddition
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "addition"
    context_object_name = "addition"
    template_name = "catalog/addition_delete.html"
    select_related = ["submitter__gamerprofile", "reviewer__gamerprofile"]

    def get_success_url(self):
        return reverse_lazy("game_catalog:addition_list")


class SuggestedAdditionApproveDenyView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    model = SuggestedAddition
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "addition"
    context_object_name = "addition"
    model_map = {
        "gamepublisher": "publisher",
        "publishedgame": "game",
        "gameedition": "edition",
        "sourcebook": "sourcebook",
        "gamesystem": "system",
        "publishedmodule": "module",
    }
    fields = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method not in ["post", "POST"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.reviewer = self.request.user
        new_obj = None
        if "approve" in self.request.POST:
            if self.model_map[obj.content_type.model] == "publisher":
                new_obj = GamePublisher.objects.create(
                    name=obj.title, description=obj.description, url=obj.url
                )
                if obj.image.name:
                    obj.transfer_image(new_obj, "logo")
            elif self.model_map[obj.content_type.model] == "game":
                new_obj = PublishedGame.objects.create(
                    title=obj.title,
                    url=obj.title,
                    description=obj.description,
                    publication_date=obj.release_date,
                )
                if obj.image.name:
                    obj.transfer_image(new_obj)
                if obj.suggested_tags:
                    if "," in obj.suggested_tags:
                        new_obj.tags.add(*obj.suggested_tags.split(","))
                    else:
                        new_obj.tags.add(obj.suggested_tags)
            elif self.model_map[obj.content_type.model] == "edition":
                if not obj.publisher:
                    messages.error(
                        self.request,
                        _("You need to specify a publisher for this edition."),
                    )
                    return self.form_valid(form)
                new_obj = GameEdition(
                    name=obj.title,
                    description=obj.description,
                    url=obj.url,
                    release_date=obj.release_date,
                    game_system=obj.system,
                    game=obj.game,
                    publisher=obj.publisher,
                )
                new_obj.save()
                if obj.suggested_tags:
                    if "," in obj.suggested_tags:
                        new_obj.tags.add(*obj.suggested_tags.split(","))
                    else:
                        new_obj.tags.add(obj.suggested_tags)
            elif self.model_map[obj.content_type.model] == "sourcebook":
                if not obj.edition:
                    messages.error(
                        self.request,
                        _(
                            "You need to specify an edition to which this sourcebook belongs."
                        ),
                    )
                    return self.form_invalid(form)
                new_obj = SourceBook(
                    title=obj.title,
                    corebook=obj.corebook,
                    edition=obj.edition,
                    release_date=obj.release_date,
                    isbn=obj.isbn,
                )
                if not obj.publisher:
                    new_obj.publisher = obj.edition.publisher
                new_obj.save()
                obj.transfer_image(new_obj)
                if obj.suggested_tags:
                    if "," in obj.suggested_tags:
                        new_obj.tags.add(*obj.suggested_tags.split(","))
                    else:
                        new_obj.tags.add(obj.suggested_tags)
            elif self.model_map[obj.content_type.model] == "system":
                if not obj.publisher:
                    messages.error(
                        self.request,
                        _("You need to specify an original publisher for the system!"),
                    )
                    return self.form_invalid(form)
                new_obj = GameSystem.objects.create(
                    name=obj.title,
                    original_publisher=obj.publisher,
                    system_url=obj.url,
                    description=obj.description,
                    isbn=obj.isbn,
                    publication_date=obj.release_date,
                    ogl_license=obj.ogl_license,
                )
                if obj.image.name:
                    obj.transfer_image(new_obj)
                if obj.suggested_tags:
                    if "," in obj.suggested_tags:
                        new_obj.tags.add(*obj.suggested_tags.split(","))
                    else:
                        new_obj.tags.add(obj.suggested_tags)
            elif self.model_map[obj.content_type.model] == "module":
                if not obj.edition or not obj.publisher:
                    messages.error(
                        self.request,
                        _(
                            "You must specify both a game edition and a publisher to create a module."
                        ),
                    )
                    return self.form_invalid(form)
                new_obj = PublishedModule.objects.create(
                    title=obj.title,
                    url=obj.url,
                    publisher=obj.publisher,
                    parent_game_edition=obj.edition,
                    publication_date=obj.release_date,
                    isbn=obj.isbn,
                )
                if obj.image.name:
                    obj.transfer_image(new_obj)
                if obj.suggested_tags:
                    if "," in obj.suggested_tags:
                        new_obj.tags.add(*obj.suggested_tags.split(","))
                    else:
                        new_obj.tags.add(obj.suggested_tags)
            else:
                messages.error(
                    self.request,
                    _("This suggested addition is missing a valid content type."),
                )
                return self.form_invalid(form)
            messages.success(
                self.request, _("You have successfully approved this addition.")
            )
            obj.status = "approved"
        else:
            obj.status = "rejected"
            obj.reviewer = self.request.user
            obj.save()
            messages.success(
                self.request, _("You have successfully rejected this addition.")
            )
            return HttpResponseRedirect(obj.get_absolute_url())
        obj.save()
        return HttpResponseRedirect(new_obj.get_absolute_url())
