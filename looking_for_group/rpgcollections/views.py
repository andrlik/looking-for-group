import urllib
import logging

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
)
from django.db.models.query_utils import Q
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin
import itertools

from . import forms, models
from ..game_catalog import models as catalog_model

# from ..game_catalog import models as db_models
from ..gamer_profiles.models import GamerProfile

# Views from here on out assume you are specifying a specific user to view. In site architechture it is a subset of the gamer profile.
# You will also need to be authenticated to view anyone's collection, and collections are only visible to people with whom you have a connection.

logger = logging.getLogger("gamer_profiles")


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
    ordering = ["created"]
    filter_present = False
    game_filter = None
    edition_filter = None
    system_filter = None
    publisher_filter = None
    copy_type_filter = None
    filter_querystring = None
    filter_form = None

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            gamerslug = kwargs.pop("gamer", None)
            self.gamer = get_object_or_404(GamerProfile, username=gamerslug)
            self.library, created = models.GameLibrary.objects.get_or_create(
                user=self.gamer.user
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.model.objects.filter(library=self.library)
        get_dict = self.request.GET.copy()
        query_string_data = {}
        if get_dict.pop("filter_present", None):
            self.game_filter = get_dict.pop("game", None)
            self.edition_filter = get_dict.pop("edition", None)
            self.system_filter = get_dict.pop("system", None)
            self.publisher_filter = get_dict.pop("publisher", None)
            self.copy_type_filter = get_dict.pop("copy_type", None)
            if self.game_filter and self.game_filter[0] != "":
                self.filter_present = True
                query_string_data["filter_present"] = 1
                query_string_data["game"] = self.game_filter[0]
                q_game_sb = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.SourceBook.objects.filter(
                                    edition__game__pk=self.game_filter[0]
                                )
                            ]
                        )
                    )
                )
                q_game_md = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.PublishedModule.objects.filter(
                                    parent_game_edition__game__pk=self.game_filter[0]
                                )
                            ]
                        )
                    )
                )
                queryset = queryset.filter(q_game_md | q_game_sb)
            if self.edition_filter and self.edition_filter[0] != "":
                self.filter_present = True
                query_string_data["filter_present"] = 1
                query_string_data["edition"] = self.edition_filter[0]
                q_edition_sb = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.SourceBook.objects.filter(
                                    edition__pk=self.edition_filter[0]
                                )
                            ]
                        )
                    )
                )
                q_edition_md = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.PublishedModule.objects.filter(
                                    parent_game_edition__pk=self.edition_filter[0]
                                )
                            ]
                        )
                    )
                )
                queryset = queryset.filter(q_edition_md | q_edition_sb)
            if self.system_filter and self.system_filter[0] != "":
                self.filter_present = True
                query_string_data["filter_present"] = 1
                query_string_data["system"] = self.system_filter[0]
                q_sys_sb = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.SourceBook.objects.filter(
                                    edition__game_system__pk=self.system_filter[0]
                                )
                            ]
                        )
                    )
                )
                q_sys_md = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.PublishedModule.objects.filter(
                                    parent_game_edition__game_system__pk=self.system_filter[
                                        0
                                    ]
                                )
                            ]
                        )
                    )
                )
                q_sys = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.GameSystem.objects.filter(
                                    id=self.system_filter[0]
                                )
                            ]
                        )
                    )
                )
                queryset = queryset.filter(q_sys | q_sys_md | q_sys_sb)
            if self.publisher_filter and self.publisher_filter[0] != "":
                self.filter_present = True
                query_string_data["filter_present"] = 1
                query_string_data["publisher"] = self.publisher_filter[0]
                q_pub_sb = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.SourceBook.objects.filter(
                                    edition__publisher__pk=self.publisher_filter[0]
                                )
                            ]
                        )
                    )
                )
                q_pub_md = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.PublishedModule.objects.filter(
                                    publisher__pk=self.publisher_filter[0]
                                )
                            ]
                        )
                    )
                )
                q_pub_sys = Q(
                    id__in=list(
                        itertools.chain.from_iterable(
                            [
                                sbc.collected_copies.filter(
                                    library=self.library
                                ).values_list("id", flat=True)
                                for sbc in catalog_model.GameSystem.objects.filter(
                                    original_publisher__pk=self.publisher_filter[0]
                                )
                            ]
                        )
                    )
                )
                queryset = queryset.filter(q_pub_sys | q_pub_md | q_pub_sb)
            if self.copy_type_filter and self.copy_type_filter[0] != "":
                self.filter_present = True
                query_string_data["filter_present"] = 1
                query_string_data["copy_type"] = self.copy_type_filter[0]
                if self.copy_type_filter[0] == "pdf":
                    queryset = queryset.filter(in_pdf=True)
                else:
                    queryset = queryset.filter(in_print=True)
            if query_string_data:
                self.filter_querystring = urllib.parse.urlencode(query_string_data)
        return queryset

    def get_permission_object(self):
        return self.gamer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.gamer
        if self.filter_present:
            context["filter_form"] = forms.CollectionFilterForm(
                initial={
                    "game": self.game_filter,
                    "edition": self.edition_filter,
                    "system": self.system_filter,
                    "publisher": self.publisher_filter,
                    "copy_type": self.copy_type_filter,
                },
                library=self.library,
            )
            context["querystring"] = self.filter_querystring
        else:
            context["filter_form"] = forms.CollectionFilterForm(library=self.library)
        context["library"] = self.library
        return context


class BookCreate(LoginRequiredMixin, generic.CreateView):
    """
    Add a book to a collection.
    """

    model = models.Book
    form_class = forms.BookForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method not in ["POST", "post"]:
            return HttpResponseNotAllowed(["POST"])  # Post only
        if request.GET.get("next", None):
            self.success_url = urllib.parse.quote(
                request.GET.copy().pop("next", None)[0].encode("utf-8")
            )
        self.book_type = kwargs.pop("booktype", None)
        if self.book_type not in ["sourcebook", "module", "system"]:
            return HttpResponseBadRequest()
        self.library, created = models.GameLibrary.objects.get_or_create(
            user=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        messages.error(
            self.request,
            _("You have tried to do an invalid addition to the library. Naughty!"),
        )
        return HttpResponseRedirect(self.success_url)

    def form_valid(self, form):
        obj_id = form.cleaned_data["object_id"]
        source_obj = None
        if self.book_type == "sourcebook":
            source_obj = get_object_or_404(catalog_model.SourceBook, pk=obj_id)
        elif self.book_type == "system":
            source_obj = get_object_or_404(catalog_model.GameSystem, pk=obj_id)
        else:
            source_obj = get_object_or_404(catalog_model.PublishedModule, pk=obj_id)
        if source_obj.collected_copies.filter(library=self.library).count() > 0:
            messages.error(self.request, _("This book is already in your collection."))
            return self.form_invalid(form)
        new_book = models.Book.objects.create(
            library=self.library,
            in_pdf=form.cleaned_data["in_pdf"],
            in_print=form.cleaned_data["in_print"],
            content_object=source_obj,
        )
        if not self.success_url:
            self.success_url = new_book.get_absolute_url()
        messages.success(self.request, _("Book successfully added to your library."))
        return HttpResponseRedirect(self.success_url)


class BookDetail(
    LoginRequiredMixin,
    # SelectRelatedMixin,
    # PrefetchRelatedMixin
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    View the details of a given book in someone's collection.
    """

    model = models.Book
    permission_required = "profile.view_detail"
    template_name = "rpgcollections/book_detail.html"
    # prefetch_related = ["content_object"]
    # select_related = ["library"]
    slug_url_kwarg = "book"
    slug_field = "slug"
    context_object_name = "book"

    def get_permission_object(self):
        self.object = self.get_object()
        logger.debug("Copy with slug: {}".format(self.object.slug))
        logger.debug("From library: {}".format(self.object.library))
        logger.debug("Object id is: {}".format(self.object.object_id))
        logger.debug("Object grabbed: {}".format(self.object))
        logger.debug(
            "Retrieved object successfully for title {}".format(self.object.title)
        )
        return self.object.library.user.gamerprofile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.object.library.user.gamerprofile
        return context


class BookUpdate(
    LoginRequiredMixin,
    # SelectRelatedMixin,
    # PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Update the details of the book.
    """

    model = models.Book
    form_class = forms.BookForm
    permission_required = "collections.can_delete_book"
    template_name = "rpgcollections/book_update.html"
    # select_related = ["library"]
    # prefetch_related = ["content_type", "content_object", "library__user__gamerprofile"]
    slug_url_kwarg = "book"
    context_object_name = "book"

    def form_valid(self, form):
        if form.cleaned_data["object_id"] != str(self.get_object().content_object.pk):
            messages.error(self.request, _("You tried to do something naughty!"))
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.get_object().library.user.gamerprofile
        return context


class BookDelete(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    Remove a book from your library.
    """

    model = models.Book
    permission_required = "collections.can_delete_book"
    template_name = "rpgcollections/book_delete.html"
    select_related = ["library"]
    prefetch_related = ["content_type", "content_object", "library__user__gamerprofile"]
    slug_url_kwarg = "book"
    context_object_name = "book"

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get("next", None):
            self.success_url = request.GET.get("next", None)
        if request.user.is_authenticated:
            self.library, created = models.GameLibrary.objects.get_or_create(
                user=request.user
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(
            self.request, _("Book successfully removed from your collection.")
        )
        if not self.success_url:
            return reverse_lazy(
                "gamer_profiles:book-list", kwargs={"gamer": self.request.user.username}
            )
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.get_object().library.user.gamerprofile
        return context
