from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpResponseRedirect,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

# from ..game_catalog import models as db_models
from ..gamer_profiles.models import GamerProfile
from ..game_catalog import models as catalog_model
from . import models, forms

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
        if request.user.is_authenticated:
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


class BookCreate(LoginRequiredMixin, generic.CreateView):
    """
    Add a book to a collection.
    """

    model = models.Book
    form_class = forms.BookForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method not in ["post"]:
            return HttpResponseNotAllowed(["POST"])  # Post only
        self.success_url = request.GET.copy().pop("next", None)
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
        if source_obj.collected_copies.filter(library=self.library).count > 0:
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
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    View the details of a given book in someone's collection.
    """

    model = models.Book
    permission_required = "profile.view_detail"
    template_name = "rpgcollections/book_detail.html"
    prefetch_related = [
        "content_type",
        "content_object",
        "library__user",
        "library__user__gamerprofile",
    ]
    select_related = ["library"]
    slug_url_kwarg = "book"

    def get_permission_object(self):
        return self.get_object().library.user.gamerprofile


class BookUpdate(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Update the details of the book.
    """

    model = models.Book
    form_class = forms.BookForm
    permission_required = "collection.can_delete_book"
    template_name = "rpgcollections/book_update.html"
    select_related = ["library"]
    prefetch_related = ["content_type", "content_object", "library__user__gamerprofile"]
    slug_url_kwarg = "book"

    def form_valid(self, form):
        if form.cleaned_data["object_id"] != str(self.get_object().content_object.pk):
            messages.error(self.request, _("You tried to do something naughty!"))
            return self.form_invalid(form)
        return super().form_valid(form)


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
    permission_required = "collection.can_delete_book"
    template_name = "rpgcollections/book_delete.html"
    select_related = ["library"]
    prefetch_related = ["content_type", "content_object", "library__user__gamerprofile"]
    slug_url_kwarg = "book"

    def dispatch(self, request, *args, **kwargs):
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
