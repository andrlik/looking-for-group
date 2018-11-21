from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from . import models
from .signals import invite_accepted

# Create your views here.


def get_invite_view_name_for_object(obj):
    """
    Generates a view name from the content object.
    NOTE: Must have a corresonding view in appropriate app.
    """
    ct = ContentType.objects.get_for_model(obj)
    view_name = "{}:{}_invite_list".format(ct.app_label, ct.name.lower())
    return view_name


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
        obj_slug = kwargs.pop("slug", None)
        self.ct = get_object_or_404(ContentType, id=ct_pk)
        self.content_object = get_object_or_404(
            self.ct.model_class(), slug=obj_slug
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["content_object"] = self.content_object
        context["ct"] = self.ct.name.lower()
        context[
            self.ct.name.lower()
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
        return HttpResponseRedirect(
            reverse_lazy(
                get_invite_view_name_for_object(self.content_object),
                kwargs={"slug": self.content_object.slug},
            )
        )


class InviteDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.DeleteView
):
    """
    View for deleting an invite object.
    """

    model = models.Invite
    permission_required = "invite.can_delete"
    template_name = "invites/invite_delete.html"
    slug_url_kwarg = "invite"
    context_object_name = "invite"

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Invite deleted."))
        obj = self.get_object()
        view_name = get_invite_view_name_for_object(obj.content_object)
        self.success_url = reverse_lazy(
            view_name,
            kwargs={"slug": obj.content_object.slug},
        )
        return super().delete(request, *args, **kwargs)


class InviteAcceptView(LoginRequiredMixin, generic.edit.UpdateView):
    """
    View for accepting an invite.
    """

    model = models.Invite
    slug_url_kwarg = "invite"
    context_object_name = "invite"
    fields = ["status"]
    template_name = "invites/invite_accept.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
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
            return HttpResponseRedirect(reverse_lazy("home"))
        return super().dispatch(request, *args, **kwargs)

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
