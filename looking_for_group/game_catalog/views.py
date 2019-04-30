from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from ..rpgcollections.forms import BookForm
from ..rpgcollections.models import Book
from . import forms
from .models import (
    GameEdition,
    GamePublisher,
    GameSystem,
    PublishedGame,
    PublishedModule,
    SourceBook,
    SuggestedAddition,
    SuggestedCorrection
)
from .utils import combined_recent

# Create your views here.
# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.


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


class RecentAdditionsView(
    LoginRequiredMixin, PermissionRequiredMixin, PrefetchRelatedMixin, generic.ListView
):
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
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.ListView,
):
    """
    List of pending corrections for editors to view.
    """

    model = SuggestedCorrection
    permission_required = "catalog.can_edit"
    template_name = "catalog/correction_list.html"
    prefetch_related = ["content_object"]
    select_related = ["submitter", "approver"]
    paginate_by = 15
    paginate_orphans = 2
    context_object_name = "correction_list"

    def queryset(self):
        return self.model.objects.filter(status="new")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approved_corrections"] = self.model.objects.filter(
            status="approved"
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        context["denied_corrections"] = self.model.objects.filter(
            status="rejected"
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
        create_type = kwargs.pop("objtype", None)
        obj_id = kwargs.pop("object_id", None)
        if not create_type and obj_id:
            raise Http404
        if create_type not in type_matching.keys():
            raise Http404
        self.source_object = get_object_or_404(type_matching[create_type], obj_id)
        if create_type == "publisher":
            self.fields = self.fields + ["new_description"]
        else:
            self.fields = self.fields + ["new_release_date"]
            if create_type not in ["module", "sourcebook"]:
                self.fields = self.fields + ["new_description"]
            else:
                self.fields = self.fields + ["new_isbn"]
            self.fields = self.fields + ["new_tags"]
        self.fields = self.fields + ["other_notes"]
        self.submitter = request.user
        return super().dispatch(request, *args, **kwargs)

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
        return HttpResponseRedirect(new_correct.content_objects.get_absolute_url())


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
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    SelectRelatedMixin,
    generic.DetailView,
):
    """
    Detail view for suggested correction, only available to editors.
    """

    model = SuggestedCorrection
    template_name = "catalog/correction_detail.html"
    select_related = ["submitter__gamerprofile", "reviewer__gamerprofile"]
    prefetch_related = ["content_object"]
    permission_required = "catalog.can_edit"
    slug_url_kwarg = "correction"
    context_object_name = "correction"


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
            obj.transfer_image()
            if obj.new_url:
                source_obj.url = obj.url
            if isinstance(source_obj, GamePublisher) or isinstance(
                source_obj, GameSystem
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
            status="approved"
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        context["rejected_additions"] = self.model.objects.filter(
            status="rejected"
        ).select_related("submitter__gamerprofile", "reviewer__gamerprofile")
        return context


class SuggestedAdditionCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    generic.CreateView,
):
    pass


class SuggestedAdditionUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    generic.edit.UpdateView,
):
    pass


class SuggestedAdditionDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
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


class SuggestedAdditionApproveDenyView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    pass
