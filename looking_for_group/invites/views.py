from datetime import timedelta

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from . import models
from .signals import invite_accepted

# Create your views here.


class CreateInvite(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    Creation view for a given invite.
    """

    model = models.Invite
    fields = ["label"]
    permission_required = "invite.can_create"  # Must be set for any related object
    template_name = "invites/invite_create.html"

    def dispatch(self, request, *args, **kwargs):
        ct_pk = kwargs.pop("content_type", None)
        obj_pk = kwargs.pop("object_id", None)
        self.content_type = get_object_or_404(ContentType, id=ct_pk)
        self.content_object = get_object_or_404(
            self.content_type.model_class(), pk=obj_pk
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["content_object"] = self.content_object
        context[
            self.content_type.name
        ] = self.content_object  # for a more friendly reference in template
        return context

    def get_permission_object(self):
        return self.content_object

    def form_valid(self, form):
        invite = form.save(commit=False)
        invite.creator = self.request.user
        invite.expires_at = timezone.now() + timedelta(days=30)
        invite.content_object = self.content_object
        invite.save()
        messages.success(self.request, _("Invite created!"))
        return HttpResponseRedirect(self.content_object.get_absolute_url())


class InviteDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    View for deleting an invite object.
    """

    model = models.Invite
    permission_required = "invite.can_delete"
    template_name = "invites/invite_delete.html"
    prefetch_related = ["content_object"]
    select_related = ["content_type"]
    slug_url_kwarg = "invite"
    context_object_name = "invite"

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Invite deleted."))
        return super().delete(request, *args, **kwargs)


class InviteAcceptView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.UpdateView,
):
    """
    View for accepting an invite.
    """

    model = models.Invite
    select_related = ["content_type"]
    prefetch_related = ["content_object"]
    slug_url_kwarg = "invite"
    context_object_name = "invite"
    fields = ["status"]
    template_name = "invites/invite_accept.html"

    def get_object(self):
        self.object = super().get_object()
        if self.object.status != "pending":
            if self.object.status == "expired":
                messages.error(
                    self.request, _("Sorry, this invite is already expired.")
                )
            else:
                messages.error(
                    self.request,
                    _(
                        "This invite has already been accepted and cannot be used again."
                    ),
                )
            return HttpResponseRedirect(self.object.content_object.get_absolute_url())
        return self.object

    def get_queryset(self):
        self.model.objects.filter(
            status="pending", expires_at__lte=timezone.now()
        ).update(status="expired")
        return self.model.objects.all()

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.object.status != "accepted":
            messages.error(
                self.request,
                _(
                    "It looks like someone may have been tampering with the form. Please try again, and no naughty business this time."
                ),
            )
            return self.form_invalid(form)
        self.object.accepted_by = self.request.user
        self.object.save()
        invite_accepted.send(
            models.Invite, invite=self.object, acceptor=self.request.user
        )
        return super().form_valid(form)
