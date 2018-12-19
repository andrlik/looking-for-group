import logging
import urllib
from datetime import datetime, timedelta

import pytz
from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models.query_utils import Q
from django.forms import modelform_factory
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from notifications.signals import notify
from rest_framework.renderers import JSONRenderer
from rules.contrib.views import PermissionRequiredMixin
from schedule.models import Event, Rule

from .. import models, serializers
from ...games.models import AvailableCalendar
from ..forms import BlankDistructiveForm, GamerAvailabilityForm, GamerProfileForm, KickUserForm, OwnershipTransferForm

logger = logging.getLogger("gamer_profiles")


# Create your views here.
class CommunityListView(generic.ListView):
    """
    Lists gamer communities. If user is logged in, communities that they belong to will be flagged.
    Community status is also indicated. Extra context around games is included if they are present.
    By default, all communities are shown here. Users can access their own communities via another view.
    """

    template_name = "gamer_profiles/community_list.html"
    model = models.GamerCommunity
    paginate_by = 25
    ordering = ["-member_count", "name"]


class MyCommunitiesListView(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):
    """
    List only the current user's communities.
    """

    template_name = "gamer_profiles/my_community_list.html"
    model = models.CommunityMembership
    paginate_by = 25
    select_related = ["community"]
    ordering = ["community", "community__name"]

    def get_queryset(self):
        return models.CommunityMembership.objects.filter(
            gamer=self.request.user.gamerprofile
        )


class JoinCommunity(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    Try to join a community. Fails if community is private.
    """

    model = models.CommunityMembership
    permission_required = "community.join"
    template_name = "gamer_profiles/community_join.html"
    form_class = modelform_factory(
        model=models.CommunityMembership, form=BlankDistructiveForm, fields=[]
    )

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.community = get_object_or_404(
                models.GamerCommunity, slug=kwargs.pop("community")
            )
            try:
                role = self.community.get_role(request.user.gamerprofile)
                if role:
                    messages.info(
                        request, _("You are already a member of this community.")
                    )
                    return HttpResponseRedirect(self.community.get_absolute_url())
            except models.NotInCommunity:
                pass
            if self.community.private:
                return HttpResponseRedirect(
                    reverse(
                        "gamer_profiles:community-apply",
                        kwargs={"community": self.community.pk},
                    )
                )
            # check if user is banned or kicked with a date in the future.
            bans = models.BannedUser.objects.filter(
                community=self.community, banned_user=request.user.gamerprofile
            )
            if bans:
                messages.error(
                    request, _("You are currently banned from this community.")
                )
                raise PermissionDenied(
                    _("You are currently banned from this community.")
                )
            kicks = models.KickedUser.objects.filter(
                community=self.community,
                kicked_user=request.user.gamerprofile,
                end_date__gt=timezone.now(),
            ).order_by("-end_date")
            if kicks:
                messages.error(
                    request,
                    _(
                        "You are currently under active suspension from this community until {}.".format(
                            kicks[0].end_date
                        )
                    ),
                )
                raise PermissionDenied(_("You are currently under suspension "))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def form_valid(self, form):
        self.community.add_member(self.request.user.gamerprofile)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.community.get_absolute_url()

    def get_permission_object(self):
        return self.community


class LeaveCommunity(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Leaving a community.
    """

    model = models.CommunityMembership
    pk_url_kwarg = "membership"
    permission_required = "community.leave"
    select_related = ["community", "gamer"]
    template_name = "gamer_profiles/community_leave.html"

    def form_valid(self, form):
        community = self.get_object().community
        if community.owner == self.request.user.gamerprofile:
            messages.error(
                _(
                    "You are the owner of this community. To leave it, you must transfer ownership first"
                )
            )
            return super().form_invalid(form)
        messages.success(_("You have left {0}".format(self.get_object.community.name)))
        return super().form_valid(form)


class TransferCommunityOwnership(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Allows an owner of a given community to transfer ownership to one of the other specified admins.
    """

    model = models.GamerCommunity
    slug_url_kwarg = "community"
    context_object_name = "community"
    slug_field = "slug"
    permission_required = "community.transfer_owner"
    form_class = OwnershipTransferForm
    template_name = "gamer_profiles/community_transfer.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["community"] = self.object
        return kwargs


class ChangeCommunityRole(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Allows an admin to change another user's role.
    """

    model = models.CommunityMembership
    permission_required = "community.edit_roles"
    template_name = "gamer_profiles/member_role.html"
    fields = ["community_role"]
    select_related = ["gamer", "community"]
    context_object_name = "member"

    def dispatch(self, request, *args, **kwargs):
        comm_slug = kwargs.pop("community", None)
        gamer_slug = kwargs.pop("gamer", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_slug)
        self.gamer = get_object_or_404(models.GamerProfile, username=gamer_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["gamer"] = self.gamer
        return context

    def get_object(self, queryset=None):
        if hasattr(self, "object") and self.object:
            return self.object
        try:
            self.object = models.CommunityMembership.objects.get(
                community=self.community, gamer=self.gamer
            )
        except ObjectDoesNotExist:
            raise Http404
        return self.object

    def get_permission_object(self):
        return self.community

    def has_permission(self):
        if (
            self.request.user.is_authenticated
            and self.request.user == self.get_object().gamer.user
        ):
            return False
        return super().has_permission()

    def get_success_url(self):
        messages.success(
            self.request,
            _("You have successfully edit the role of {}".format(self.gamer)),
        )
        return reverse_lazy(
            "gamer_profiles:community-member-list",
            kwargs={"community": self.community.slug},
        )


class CommunityCreateView(LoginRequiredMixin, generic.CreateView):
    """
    Creating a community.
    """

    model = models.GamerCommunity
    fields = [
        "name",
        "community_logo",
        "community_logo_cw",
        "description",
        "url",
        "private",
        "application_approval",
        "invites_allowed",
    ]
    template_name = "gamer_profiles/community_create.html"

    def form_valid(self, form):
        self.community = form.save(commit=False)
        self.community.owner = self.request.user.gamerprofile
        self.community.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        messages.success(
            self.request,
            _("Community {0} succesfully created!".format(self.community.name)),
        )
        return reverse_lazy(
            "gamer_profiles:community-detail", kwargs={"community": self.community.slug}
        )


class CommunityDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.DetailView,
):
    """
    View details of a single community.
    """

    slug_url_kwarg = "community"
    slug_field = "slug"
    permission_required = "community.list_communities"
    model = models.GamerCommunity
    template_name = "gamer_profiles/community_detail.html"
    select_related = ["owner", "discord"]
    prefetch_related = ["discord__servers", "gameposting_set"]
    # prefetch_related = [
    #     "gamerprofile_set",
    #     "communityapplication_set",
    # ]  # TODO Add games.
    context_object_name = "community"

    def get(self, request, *args, **kwargs):
        logger.debug("Attempting to retrieve community for evaluation.")
        obj = get_object_or_404(models.GamerCommunity, slug=kwargs["community"])
        logger.debug("Found community {}".format(obj.name))
        logger.debug("Checking permissions of user...")
        if not request.user.has_perm("community.view_details", obj):
            logger.debug("User does not have permission to view.")
            view_target = "gamer_profiles:community-join"
            message = _("You must join this community in order to view its details.")
            if obj.private:
                logger.debug(
                    "Community is private: redirecting to apply instead of join."
                )
                view_target = "gamer_profiles:community-apply"
                message = _(
                    "You must be a member of this community to view its details. You can apply below."
                )
            messages.info(request, message)
            return HttpResponseRedirect(
                reverse(view_target, kwargs={"community": obj.slug})
            )
        logger.debug("user has permissions, proceeding with standard redirect")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context["community"].discord:
            context["linked_discord_servers"] = context[
                "community"
            ].discord.servers.all()
        else:
            context["linked_discord_servers"] = None
        context["active_games"] = context["community"].gameposting_set.exclude(
            status__in=["closed", "cancel"]
        )
        return context


class CommunityUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView
):
    """
    Update view for basic fields in community.
    """

    slug_url_kwarg = "community"
    slug_field = "slug"
    permission_required = "community.edit_community"
    model = models.GamerCommunity
    template_name = "gamer_profiles/community_edit.html"
    fields = [
        "name",
        "community_logo",
        "community_logo_cw",
        "description",
        "url",
        "private",
        "application_approval",
        "invites_allowed",
    ]
    context_object_name = "community"

    def get_success_url(self):
        messages.success(
            self.request, _("{0} successfully updated.".format(self.object.name))
        )
        return reverse_lazy(
            "gamer_profiles:community-detail", kwargs={"community": self.object.slug}
        )


class CommunityDeleteView(
    LoginRequiredMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a community. Can only be done by the owner.
    """

    model = models.GamerCommunity
    slug_url_kwarg = "community"
    slug_field = "slug"
    context_object_name = "community"
    permission_required = "community.transfer_ownership"
    template_name = "gamer_profiles/community_delete.html"
    prefetch_related = [
        "members",
        "gameposting_set",
        "discord",
        "communityapplication_set",
    ]

    def get_success_url(self):
        messages.success(
            self.request, _("You have successfully deleted this community.")
        )
        return reverse_lazy("gamer_profiles:community-list")


class CommunityMemberList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    Pull full list of members and paginate.
    """

    model = models.CommunityMembership
    select_related = ["gamer"]
    template_name = "gamer_profiles/community_member_list.html"
    permission_required = "community.view_details"
    paginate_by = 25
    ordering = ["community_role", "gamer__user__display_name"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(community=self.community)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["user_role"] = self.community.get_role(self.request.user.gamerprofile)
        return context


class CommunityApplicantList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    List of applicants to a community. By default, only pending are shown, but the approved and denied are also provided
    via context objects.
    """

    model = models.CommunityApplication
    select_related = ["gamer"]
    template_name = "gamer_profiles/community_applicant_list.html"
    permission_required = "community.review_applications"
    ordering = ["modified", "created", "status"]
    context_object_name = "applicants"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return models.CommunityApplication.objects.filter(
            community=self.community, status__in=["review", "hold"]
        )

    def get_context_data(self, **kwargs):
        all_apps = (
            models.CommunityApplication.objects.filter(community=self.community)
            .select_related("gamer")
            .order_by("-modified")
        )
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["approved_applicants"] = all_apps.filter(status="approve").order_by(
            "-modified"
        )
        context["rejected_applicants"] = all_apps.filter(status="reject").order_by(
            "-modified"
        )
        return context


class CommunityApplicantDetail(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.DetailView
):
    """
    View for a community admin to view the details of an application.
    """

    model = models.CommunityApplication
    select_related = ["gamer", "community"]
    template_name = "gamer_profiles/community_applicant_detail.html"
    permission_required = "community.approve_application"
    pk_url_kwarg = "application"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = context["application"].community
        return context


class UpdateApplication(
    LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView
):
    """
    Allows the user who put in an application to update it (but not the status)
    """

    pk_url_kwarg = "application"
    context_object_name = "application"
    model = models.CommunityApplication
    template_name = "gamer_profiles/community_apply_edit.html"
    permission_required = "community.edit_application"
    fields = ["message"]

    def get_success_url(self):
        return reverse_lazy("gamer_profiles:my-application-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.object.community
        return context

    def form_valid(self, form):
        application = form.save(commit=False)
        if "submit_app" in self.request.POST.keys():
            try:
                if application.submit_application():
                    messages.success(
                        self.request, _("Application successfully submitted.")
                    )
                    for admin in application.community.get_admins():
                        notify.send(
                            application.gamer,
                            recipient=admin.gamer.user,
                            verb=_("submitted application"),
                            action_object=application,
                            target=application.community,
                        )
                    return HttpResponseRedirect(self.get_success_url())
            except models.AlreadyInCommunity:
                messages.error(
                    self.request, _("You are already a member of this community.")
                )
            except models.CurrentlyBanned:
                messages.error(
                    self.request, _("You are currently banned from this community.")
                )
            except models.CurrentlySuspended:
                messages.error(
                    self.request,
                    _(
                        "You are currently under an active suspension from this community."
                    ),
                )
            return self.form_invalid(form)
        messages.success(self.request, _("Application successfully updated."))
        return super().form_valid(form)


class CreateApplication(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    File an application to join a community.
    """

    model = models.CommunityApplication
    fields = ["message"]
    template_name = "gamer_profiles/community_apply.html"
    permission_required = "community.apply"

    def dispatch(self, request, *args, **kwargs):
        comm_uk = kwargs["community"]
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_uk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def get_permission_object(self):
        return self.community

    def get_success_url(self):
        return reverse_lazy("gamer_profiles:my-application-list")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.community = self.community
        self.object.gamer = self.request.user.gamerprofile
        if "submit_app" in self.request.POST.keys():
            try:
                self.object.submit_application()
                for admin in self.object.community.get_admins():
                    notify.send(
                        self.object.gamer,
                        recipient=admin.gamer.user,
                        verb=_("submitted application"),
                        action_object=self.object,
                        target=self.object.community,
                    )
                messages.success(self.request, _("Application successfully submitted."))
                return HttpResponseRedirect(self.object.community.get_absolute_url())
            except models.AlreadyInCommunity:
                messages.error(
                    self.request, _("You are already a member of this community.")
                )
            except models.CurrentlyBanned:
                messages.error(
                    self.request, _("You are currently banned from this community.")
                )
            except models.CurrentlySuspended:
                messages.error(
                    self.request, _("You are currently suspended from this community.")
                )
            return self.form_invalid(form)
        else:
            self.object.status = "new"
        self.object.save()
        messages.success(self.request, _("Application successfully saved."))
        return HttpResponseRedirect(self.get_success_url())


class MyApplicationList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    View all applications for the current user. By default, only show pending, but also include
    others as context objects.
    """

    model = models.CommunityApplication
    template_name = "gamer_profiles/my_community_applications.html"
    select_related = ["community"]
    permission_required = "community.edit_application"
    paginate_by = 25
    ordering = ["-created", "status"]
    context_object_name = "applications"

    def dispatch(self, request, *args, **kwargs):
        self.base_queryset = self.model.objects.filter(gamer=request.user.gamerprofile)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.base_queryset.filter(status__in=["new", "review", "hold"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approved_apps"] = self.base_queryset.filter(status="approve")
        context["rejected_apps"] = self.base_queryset.filter(status="reject")
        return context


class WithdrawApplication(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Withdraw and delete your application.
    """

    pk_url_kwarg = "application"
    model = models.CommunityApplication
    template_name = "gamer_profiles/application_delete.html"
    permission_required = "community.edit_application"
    context_object_name = "application"
    select_related = ["community"]
    success_url = reverse_lazy("gamer_profiles:my-application-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Application successfully deleted."))
        return super().delete(request, *args, **kwargs)


class ApproveApplication(
    LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView
):
    """
    Approve an application to a community.
    """

    model = models.CommunityApplication
    pk_url_kwarg = "application"
    permission_required = "community.approve_application"
    http_method_names = ["post"]
    fields = []

    def dispatch(self, request, *args, **kwargs):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(status__in=["review", "onhold"])

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-applicant-list",
            kwargs={"community": self.community.pk},
        )

    def form_valid(self, form):
        application = self.get_object()
        try:
            application.approve_application()
        except models.AlreadyInCommunity:
            messages.error(
                self.request,
                _(
                    "{0} is already a member of {1}".format(
                        application.gamer, self.community.name
                    )
                ),
            )
        except models.CurrentlySuspended:
            messages.error(
                self.request,
                _(
                    "{0} is currently suspended and cannot rejoin.".format(
                        application.gamer
                    )
                ),
            )
        notify.send(
            self.request.user.gamerprofile,
            recipient=application.gamer.user,
            verb="approved your application",
            action_object=application,
            target=application.community,
        )
        return HttpResponseRedirect(self.get_success_url())


class RejectApplication(ApproveApplication):
    """
    Rejects an application.
    """

    def form_valid(self, form):
        application = self.get_object()
        application.reject_application()
        messages.success(self.request, _("Application rejected."))
        notify.send(
            sender=models.CommunityApplication,
            recipient=application.gamer.user,
            verb=_("Your community application was rejected"),
            action_object=application,
            target=application.community,
        )
        return HttpResponseRedirect(self.get_success_url())


class CommunityKickedUserList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    List of users currently kicked from community.
    """

    model = models.KickedUser
    select_related = ["kicked_user", "kicker"]
    template_name = "gamer_profiles/community_kicked_list.html"
    permission_required = "community.kick_user"
    context_object_name = "kick_list"
    paginate_by = 25
    ordering = ["-end_date", "-created"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        expired_kicks = models.KickedUser.objects.filter(
            community=self.community, end_date__lt=timezone.now()
        ).select_related("kicked_user", "kicker")
        nodate_kicks = models.KickedUser.objects.filter(
            community=self.community, end_date=None
        ).select_related("kicked_user", "kicker")
        context["expired_kicks"] = expired_kicks.union(nodate_kicks).order_by(
            "-created"
        )
        return context

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return self.model.objects.filter(
            community=self.community, end_date__gte=timezone.now()
        ).order_by("-end_date", "-created")


class CommunityBannedUserList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    List of users banned from community.
    """

    model = models.BannedUser
    select_related = ["banned_user"]
    template_name = "gamer_profiles/community_banned_list.html"
    permission_required = "community.ban_user"
    paginate_by = 25
    context_object_name = "ban_list"
    ordering = ["-created"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return self.model.objects.filter(community=self.community).order_by("-created")


class CommunityDeleteBan(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Remove a ban.
    """

    model = models.BannedUser
    select_related = ["banned_user"]
    template_name = "gamer_profiles/community_ban_delete.html"
    permission_required = "community.ban_user"
    context_object_name = "ban"
    pk_url_kwarg = "ban"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-ban-list", kwargs={"community": self.community.pk}
        )

    def get_permission_object(self):
        return self.get_object().community

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Successfully deleted ban."))
        return super().delete(request, *args, **kwargs)


class CommunityUpdateBan(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Loads form for editing a ban (you can only edit the reason.)
    """

    model = models.BannedUser
    fields = ["reason"]
    permission_required = "community.ban_user"
    template_name = "gamer_profiles/community_ban_edit.html"
    pk_url_kwarg = "ban"
    select_related = ["banned_user", "banned_user__user", "community"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = self.kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-ban-list", kwargs={"community": self.community.pk}
        )

    def get_permission_object(self):
        return self.get_object().community

    def form_valid(self, form):
        messages.success(self.request, _("Ban record updated!"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below."))
        return super().form_invalid(form)


class CommunityBanUser(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    Loads form for banning a user from a specific community.
    """

    model = models.BannedUser
    permission_required = "community.ban_user"
    template_name = "gamer_profiles/community_ban_user.html"
    fields = ["reason"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = self.kwargs.pop("community", None)
        gamer_pk = self.kwargs.pop("gamer")
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        self.gamer = get_object_or_404(models.GamerProfile, username=gamer_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["gamer"] = self.gamer
        return context

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-ban-list", kwargs={"community": self.community.pk}
        )

    def has_permission(self):
        try:
            if (
                self.gamer.get_role(self.community) == "Admin"
                and self.community.owner != self.request.user.gamerprofile
            ):
                return False
            if (
                self.gamer.get_role(self.community) == "Moderator"
                and self.community.get_role(self.request.user.gamerprofile) != "Admin"
            ):
                return False
        except models.NotInCommunity:
            return False
        return super().has_permission()

    def form_valid(self, form):
        try:
            self.community.ban_user(
                banner=self.request.user.gamerprofile,
                gamer=self.gamer,
                reason=form.instance.reason,
            )
        except models.NotInCommunity:
            messages.error(
                self.request,
                _(
                    "{0} is not a current member of the {1} and cannot be banned.".format(
                        self.gamer, self.community.name
                    )
                ),
            )
            return super().form_invalid(form)
        messages.success(
            self.request,
            _(
                "{0} successfully banned from {1}".format(
                    self.gamer, self.community.name
                )
            ),
        )
        return HttpResponseRedirect(self.get_success_url())


class CommunityKickUser(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Loads form for kicking a user from a community.
    """

    model = models.KickedUser
    permission_required = "community.kick_user"
    template_name = "gamer_profiles/community_kick_user.html"
    form_class = KickUserForm

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        gamer_pk = kwargs.pop("gamer")
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        self.gamer = get_object_or_404(models.GamerProfile, username=gamer_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["gamer"] = self.gamer
        return context

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-kick-list",
            kwargs={"community": self.community.slug},
        )

    def get_permission_object(self):
        return self.community

    def has_permission(self):
        try:
            if (
                self.community.get_role(self.gamer) == "Admin"
                and self.community.owner != self.request.user.gamerprofile
            ):
                return False
            if (
                self.community.get_role(self.gamer) == "Moderator"
                and self.community.get_role(self.request.user.gamerprofile) != "Admin"
            ):
                return False
        except models.NotInCommunity:
            return False
        return super().has_permission()

    def form_valid(self, form):
        try:
            self.community.kick_user(
                kicker=self.request.user.gamerprofile,
                gamer=self.gamer,
                reason=form.instance.reason,
                earliest_reapply=form.instance.end_date,
            )
        except models.NotInCommunity:
            messages.error(
                self.request,
                _(
                    "{0} is not a current member of the {1} and cannot be kicked.".format(
                        self.gamer, self.community.name
                    )
                ),
            )
            return self.form_invalid(form)
        messages.success(
            self.request,
            _(
                "{0} successfully kicked from {1}.".format(
                    self.gamer, self.community.name
                )
            ),
        )
        return HttpResponseRedirect(self.get_success_url())


class UpdateKickRecord(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Update a kick record.
    """

    model = models.KickedUser
    select_related = ["community", "kicked_user"]
    template_name = "gamer_profiles/community_kick_edit.html"
    form_class = KickUserForm
    context_object_name = "kick"
    pk_url_kwarg = "kick"
    permission_required = "community.kick_user"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def get_object(self):
        if not hasattr(self, "object"):
            self.object = super().get_object()
            if not self.object.end_date or self.object.end_date < timezone.now():
                messages.error(
                    self.request, _("You cannot edit an expired suspension or kick.")
                )
                raise PermissionDenied
        return self.object

    def get_permission_object(self):
        return self.get_object().community

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-kick-list",
            kwargs={"community": self.community.slug},
        )


class DeleteKickRecord(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Allows an admin to delete a kick record.
    """

    model = models.KickedUser
    select_related = ["community", "kicked_user", "kicker"]
    permission_required = "community.kick_user"
    template_name = "gamer_profiles/community_kick_delete.html"
    context_object_name = "kick"
    pk_url_kwarg = "kick"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, slug=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        return context

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-kick-list",
            kwargs={"community": self.community.slug},
        )

    def get_permission_object(self):
        return self.get_object().community

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Suspension deleted."))
        return super().delete(request, *args, **kwargs)


class GamerProfileDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.DetailView,
):
    """
    View the details of a profile.
    """

    model = models.GamerProfile
    select_related = ["user"]
    prefetch_related = ["communities"]
    context_object_name = "gamer"
    slug_url_kwarg = "gamer"
    slug_field = "username"
    permission_required = "profile.view_detail"
    template_name = "gamer_profiles/profile_detail.html"

    def get_object(self, queryset=None):
        obj = cache.get_or_set(
            "profile_{}".format(self.kwargs["gamer"]), super().get_object(queryset)
        )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer_notes"] = models.GamerNote.objects.filter(
            author=self.request.user.gamerprofile, gamer=self.get_object()
        )
        avail_calendar = AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
            context["gamer"]
        )
        context["week_availability"] = avail_calendar.get_weekly_availability()
        return context

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            self.object = self.get_object()
            if self.request.user.gamerprofile.blocked_by(self.object):
                messages.error(
                    self.request,
                    _(
                        "{} has blocked you from viewing their profiles, posts, and games.".format(
                            self.object
                        )
                    ),
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy(
                        "gamer_profiles:gamer-friend",
                        kwargs={"gamer": self.get_object().username},
                    )
                )
        return super().handle_no_permission()


class GamerAvailabilityUpdate(LoginRequiredMixin, generic.FormView):
    """
    View for a user to update their playtime availability.
    """

    form_class = GamerAvailabilityForm
    template_name = "gamer_profiles/profile_set_avail.html"
    weekday_map = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    scratch_mode = False
    rule_to_use = None

    def get_success_url(self):
        return self.request.user.gamerprofile.get_absolute_url()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            no_end_q = Q(rule__isnull=False, end_recurring_period__isnull=True)
            end_future_q = Q(end_recurring_period__gt=timezone.now())
            self.avail_calendar = AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
                request.user.gamerprofile
            )
            if self.avail_calendar.events.filter(no_end_q | end_future_q).count() == 0:
                self.scratch_mode = True
            self.rule_to_use, created = Rule.objects.get_or_create(
                name="weekly",
                defaults={"description": _("Weekly"), "frequency": "WEEKLY"},
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.request.user.gamerprofile
        return context

    def get_initial(self):
        try:
            self.weekday_avail = self.avail_calendar.get_weekly_availability()
        except ValueError:
            self.weekday_avail = None
            return None
        if not self.weekday_avail:
            return None
        initial = {}
        for occ in self.weekday_avail.weekdays:
            earliest_time = None
            latest_time = None
            all_day = False
            if occ:
                if occ.seconds >= 86000:
                    initial[
                        "{}_all_day".format(self.weekday_map[occ.start.weekday()])
                    ] = occ.start.weekday()
                    all_day = True
                else:
                    if not earliest_time or occ.start < earliest_time:
                        earliest_time = occ.start
                    if not latest_time or occ.end > latest_time:
                        latest_time = occ.end
                if earliest_time and latest_time and not all_day:
                    initial[
                        "{}_earliest".format(self.weekday_map[earliest_time.weekday()])
                    ] = earliest_time.strftime("%H:%M")
                    initial[
                        "{}_latest".format(self.weekday_map[latest_time.weekday()])
                    ] = latest_time.strftime("%H:%M")
        return initial

    def form_valid(self, form):
        cdata = form.cleaned_data
        new_rules = []
        index_num = 0
        events_cancelled = 0
        events_created = 0
        user_timezone = pytz.timezone(self.request.user.timezone)
        for wday in self.weekday_map:
            day_start = None
            day_end = None
            today = timezone.now()
            if today.weekday() != index_num and today.weekday() > index_num:
                today = today - timedelta(days=today.weekday() - index_num)
            if today.weekday() != index_num and today.weekday() < index_num:
                today = today + timedelta(days=index_num - today.weekday())
            if cdata["{}_all_day".format(wday)]:
                logger.debug("Setting for all-day for {}".format(wday))
                today = timezone.now()
                if today.weekday() != index_num and today.weekday() > index_num:
                    today = today - timedelta(days=today.weekday() - index_num)
                if today.weekday() != index_num and today.weekday() < index_num:
                    today = today + timedelta(days=index_num - today.weekday())
                day_start = user_timezone.localize(
                    datetime.strptime(
                        "{} {}".format(today.strftime("%Y-%m-%d"), "00:00"),
                        "%Y-%m-%d %H:%M",
                    )
                )
                day_end = user_timezone.localize(
                    datetime.strptime(
                        "{} {}".format(today.strftime("%Y-%m-%d"), "23:59"),
                        "%Y-%m-%d %H:%M",
                    )
                )
            else:
                if cdata[
                    "{}_earliest".format(wday)
                ]:  # No need to check for both as form validation does that for us.
                    day_start = user_timezone.localize(
                        datetime.strptime(
                            "{} {}".format(
                                today.strftime("%Y-%m-%d"),
                                cdata["{}_earliest".format(wday)].strftime("%H:%M"),
                            ),
                            "%Y-%m-%d %H:%M",
                        )
                    )
                    logger.debug("Set earliest time for {} to {}".format(wday, day_start))
                    day_end = user_timezone.localize(
                        datetime.strptime(
                            "{} {}".format(
                                today.strftime("%Y-%m-%d"),
                                cdata["{}_latest".format(wday)].strftime("%H:%M"),
                            ),
                            "%Y-%m-%d %H:%M",
                        )
                    )
                    logger.debug("Set latest time for {} to {}".format(wday, day_end))
            # Check for an existing rule and cancel it.
            if not self.scratch_mode and self.weekday_avail.weekdays[index_num]:
                occ = self.weekday_avail.weekdays[index_num]
                occ.event.end_recurring_period = timezone.now() - timedelta(days=1)
                occ.event.save()
                events_cancelled += 1
            if day_start and day_end:
                e = Event.objects.create(
                    calendar=self.avail_calendar,
                    start=day_start,
                    end=day_end,
                    rule=self.rule_to_use,
                    creator=self.request.user,
                    title=_("Availability for {}".format(wday)),
                )
                events_created += 1
                logger.debug("New event created with start of {} and end of {}".format(e.start, e.end))
            index_num += 1
        logger.debug(
            "Cancelled {} pre-existing availability events and created {} new ones.".format(
                events_cancelled, events_created
            )
        )
        messages.success(self.request, _("Available times successfully updated."))
        return HttpResponseRedirect(self.get_success_url())


class GamerFriendRequestView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    For creating a friend request.
    """

    model = models.GamerFriendRequest
    permission_required = "profile.can_friend"
    template_name = "gamer_profiles/gamer_friend.html"
    fields = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.target_gamer = get_object_or_404(
                models.GamerProfile, username=kwargs.pop("gamer", None)
            )
            self.requestor = request.user.gamerprofile
            if self.requestor in self.target_gamer.friends.all():
                logger.debug(
                    "Requestor is already friends with target recipient. Redirecting..."
                )
                messages.info(
                    request,
                    _("You are already friends with {}".format(self.target_gamer)),
                )
                return HttpResponseRedirect(
                    reverse_lazy(
                        "gamer_profiles:profile-detail",
                        kwargs={"gamer": self.target_gamer.username},
                    )
                )
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.target_gamer

    def check_friend_request_for_pending(self):
        try:
            prev_request = models.GamerFriendRequest.objects.get(
                requestor=self.requestor, recipient=self.target_gamer, status="new"
            )
        except ObjectDoesNotExist:
            return False
        return prev_request

    def check_for_other_request_or_create(self):
        """
        Find out if there is already a reverse request we should simply approve.
        """
        try:
            logger.debug(
                "Checking for previous pending request from the intended recipient."
            )
            prev_request = self.model.objects.get(
                requestor=self.target_gamer,
                recipient=self.request.user.gamerprofile,
                status="new",
            )
            if prev_request:
                logger.debug("Request found, accepting it instead of making a new one.")
                prev_request.approve()
                messages.info(
                    self.request,
                    _(
                        "You already had a pending friend request from {}, which has now been accepted.".format(
                            self.target_gamer
                        )
                    ),
                )
        except ObjectDoesNotExist:
            # Create a new friend request.
            logger.debug("Creating new friend request.")
            self.model.objects.create(
                requestor=self.requestor, recipient=self.target_gamer, status="new"
            )
            messages.success(self.request, _("Friend request sent!"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_gamer"] = self.target_gamer
        context["pending_request"] = self.check_friend_request_for_pending()
        return context

    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You cannot friend this user because they have blocked you."),
        )
        return super().handle_no_permission()

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:gamer-friend", kwargs={"gamer": self.target_gamer.username}
        )

    def form_valid(self, form):
        # Verify that the user doesn't already have a friend request in queue.
        if self.check_friend_request_for_pending():
            messages.info(
                self.request,
                _("You already have a pending friend request for this user."),
            )
        else:
            self.check_for_other_request_or_create()
        return HttpResponseRedirect(self.get_success_url())


class GamerFriendRequestWithdraw(
    LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView
):
    """
    For withdrawing a friend request.
    """

    model = models.GamerFriendRequest
    pk_url_kwarg = "friend_request"
    permission_required = "profile.withdraw_friend_request"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:gamer-friend",
            kwargs={"gamer": self.object.recipient.username},
        )

    def form_valid(self, form):
        self.success_url = reverse_lazy(
            "gamer_profiles:gamer-friend",
            kwargs={"gamer": self.object.recipient.username},
        )
        messages.success(self.request, _("Friend request withdrawn."))
        return super().form_valid(form)


class GamerFriendRequestApprove(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.UpdateView
):
    """
    A POST-only view which permits the user to accept a friend request.
    """

    model = models.GamerFriendRequest
    pk_url_kwarg = "friend_request"
    permission_required = "profile.approve_friend_request"
    fields = []
    select_related = ["requestor", "requestor__user", "recipient"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("gamer_profiles:my-gamer-friend-requests")

    def form_valid(self, form):
        friend_request = self.get_object()
        if friend_request.status != "new":
            messages.error(self.request, _("This request has already been resolved."))
        else:
            friend_request.accept()
            messages.success(
                self.request,
                _("You are now friends with {}".format(friend_request.requestor)),
            )
            notify.send(
                self.request.user.gamerprofile,
                recipient=friend_request.requestor.user,
                verb=_("accepted your friend request."),
            )
        return HttpResponseRedirect(self.get_success_url())


class GamerFriendRequestReject(GamerFriendRequestApprove):
    """
    Same as approve, but in this case the form valid action is to reject.
    """

    def form_valid(self, form):
        friend_request = self.get_object()
        if friend_request.status != "new":
            messages.error(self.request, _("This request has already been resolved."))
        else:
            friend_request.deny()
            messages.success(
                self.request,
                _(
                    "You have ignored the friend request from {}".format(
                        friend_request.requestor
                    )
                ),
            )
        return HttpResponseRedirect(self.get_success_url())


class GamerFriendRequestListView(
    LoginRequiredMixin, SelectRelatedMixin, generic.ListView
):

    model = models.GamerFriendRequest
    context_object_name = "pending_requests"
    template_name = "gamer_profiles/friend_requests.html"
    select_related = ["requestor", "requestor__user", "recipient"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.request.user.gamerprofile
        context["sent_requests"] = models.GamerFriendRequest.objects.filter(
            requestor=self.request.user.gamerprofile, status="new"
        )
        return context

    def get_queryset(self):
        return models.GamerFriendRequest.objects.filter(
            recipient=self.request.user.gamerprofile, status="new"
        )


class GamerProfileUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Update view for gamer profile.
    """

    model = get_user_model()
    select_related = ["gamerprofile"]
    permission_required = "profile.edit_profile"
    template_name = "gamer_profiles/profile_update.html"
    fields = ["display_name", "bio", "homepage_url", "timezone"]

    def get_success_url(self):
        return self.get_object().gamerprofile.get_absolute_url()

    def get_object(self):
        if hasattr(self, "object"):
            return self.object
        self.object = self.request.user
        return self.object

    def get_permission_object(self):
        return self.get_object().gamerprofile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.get_object().gamerprofile
        if self.request.POST:
            profile_form = GamerProfileForm(
                self.request.POST,
                prefix="profile",
                instance=self.get_object().gamerprofile,
            )
            profile_form.is_valid()  # Just to trigger validation.
            context["profile_form"] = profile_form
        else:
            context["profile_form"] = GamerProfileForm(
                instance=self.get_object().gamerprofile, prefix="profile"
            )
        return context

    def form_invalid(self, form):
        messages.error(
            self.request,
            _("There are issues with your submission. Please review the errors below."),
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        profile_form = GamerProfileForm(
            self.request.POST, prefix="profile", instance=self.get_object().gamerprofile
        )
        if not profile_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            form.save()
            profile_form.save()
            messages.success(self.request, _("Profile updated!"))
            try:
                cache.incr_version("profile_{}".format(self.request.user.username))
            except ValueError:
                pass  # The key already expired
        return HttpResponseRedirect(self.get_success_url())


class CreateGamerNote(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    Add a note to a gamer profile.
    """

    model = models.GamerNote
    fields = ["title", "body"]
    permission_required = "profile.view_detail"
    template_name = "gamer_profiles/gamernote_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.gamer = get_object_or_404(
            models.GamerProfile, username=self.kwargs.pop("gamer")
        )
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.gamer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.gamer
        return context

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:profile-detail", kwargs={"gamer": self.gamer.username}
        )

    def form_valid(self, form):
        form.instance.author = self.request.user.gamerprofile
        form.instance.gamer = self.gamer
        return super().form_valid(form)


class UpdateGamerNote(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Updating a specific gamer note.
    """

    model = models.GamerNote
    permission_required = "profile.delete_note"
    pk_url_kwarg = "gamernote"
    context_object_name = "gamernote"
    select_related = ["gamer", "gamer__user", "author"]
    template_name = "gamer_profiles/gamernote_update.html"
    fields = ["title", "body"]

    def dispatch(self, request, *args, **kwargs):
        self.gamer = self.get_object().gamer
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:profile-detail", kwargs={"gamer": self.gamer.username}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.gamer
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Successfully updated note!"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below."))
        return super().form_invalid(form)


class RemoveGamerNote(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a gamer note.
    """

    model = models.GamerNote
    permission_required = "profile.delete_note"
    template_name = "gamer_profiles/gamernote_delete.html"
    select_related = ["author", "gamer"]
    context_object_name = "gamernote"
    pk_url_kwarg = "gamernote"

    def dispatch(self, request, *args, **kwargs):
        self.gamer = self.get_object().gamer
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:profile-detail", kwargs={"gamer": self.gamer.username}
        )

    def form_valid(self, form):
        messages.success(self.request, _("You have deleted the selected gamer note."))
        return super().form_valid(form)


class BlockGamer(LoginRequiredMixin, generic.CreateView):
    """
    Blocks another gamer. The only form is a confirmation screen.
    """

    model = models.BlockedUser
    fields = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        self.gamer = get_object_or_404(
            models.GamerProfile, username=kwargs.pop("gamer")
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        next_url = self.kwargs.pop("next", "")
        url_is_safe = is_safe_url(next_url, settings.ALLOWED_HOSTS)
        if next_url and url_is_safe:
            return next_url
        return reverse_lazy(
            "gamer_profiles:profile-detail", kwargs={"gamer": self.gamer.username}
        )

    def form_valid(self, form):
        block_file, created = models.BlockedUser.objects.get_or_create(
            blocker=self.request.user.gamerprofile, blockee=self.gamer
        )
        if created:
            messages.success(
                self.request, _("You have successfully blocked {}".format(self.gamer))
            )
        else:
            messages.error(
                self.request, _("You have already blocked {}".format(self.gamer))
            )
        return HttpResponseRedirect(self.get_success_url())


class RemoveBlock(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Remove a block.
    """

    model = models.BlockedUser
    pk_url_kwarg = "block"
    permission_required = "profile.remove_block"
    select_related = ["blockee"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_url = self.kwargs.pop("next", "")
        url_is_safe = is_safe_url(redirect_url, settings.ALLOWED_HOSTS)
        if redirect_url and url_is_safe:
            return redirect_url
        return reverse_lazy("gamer_profiles:my-block-list")

    def form_valid(self, form):
        messages.success(
            self.request,
            _("You have unblocked {}".format(self.get_object().blockee.username)),
        )
        return super().form_valid(form)


class BlockList(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):
    """
    View existing blocks.
    """

    model = models.BlockedUser
    template_name = "gamer_profiles/block_list.html"
    context_object_name = "block_list"
    select_related = ["blockee"]

    def get_queryset(self):
        return models.BlockedUser.objects.filter(
            blocker=self.request.user.gamerprofile
        ).order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer"] = self.request.user.gamerprofile
        return context


class MuteGamer(LoginRequiredMixin, generic.CreateView):
    """
    Mutes another gamer.
    """

    model = models.MutedUser
    fields = []
    # form_class = BlankDistructiveForm
    template_name = "gamer_profiles/mute_gamer.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        self.gamer = get_object_or_404(
            models.GamerProfile, username=kwargs.pop("gamer", "")
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_url = urllib.parse.unquote(self.kwargs.pop("next", ""))
        url_is_safe = is_safe_url(redirect_url, settings.ALLOWED_HOSTS)
        if redirect_url and url_is_safe:
            return urllib.request.quote(redirect_url)
        return self.gamer.get_absolute.url()

    def form_valid(self, form):
        mute_file, created = self.model.objects.get_or_create(
            muter=self.request.user.gamerprofile, mutee=self.gamer
        )
        if created:
            messages.success(
                self.request, _("You have successfully muted {}.".format(self.gamer))
            )
        else:
            messages.error(
                self.request, _("You have already muted {}.".format(self.gamer))
            )
        return HttpResponseRedirect(self.get_success_url())


class RemoveMute(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Remove a mute.
    """

    model = models.MutedUser
    pk_url_kwarg = "mute"
    permission_required = "profile.remove_mute"
    select_related = ["mutee"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_url = urllib.parse.unquote(self.kwargs.pop("next", ""))
        is_url_safe = is_safe_url(redirect_url, allowed_hosts=settings.ALLOWED_HOSTS)
        if redirect_url and is_url_safe:
            return urllib.request.quote(redirect_url)
        return reverse_lazy("gamer_profiles:my-mute-list")

    def form_valid(self, form):
        messages.success(self.request, _("You have unmuted this user."))
        return super().form_valid(form)


class MyMuteList(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):

    model = models.MutedUser
    select_related = ["mutee", "mutee__user"]
    template_name = "gamer_profiles/mute-list.html"

    def get_queryset(self):
        return models.MutedUser.objects.filter(
            muter=self.request.user.gamerprofile
        ).order_by("-created")


class CommunityInviteList(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    Provide a list of current community invites. If an admin, show all of them.
    """

    model = models.GamerCommunity
    template_name = "gamer_profiles/community_invite_list.html"
    select_related = ["owner"]
    prefetch_related = ["members"]
    permission_required = "invite.can_create"
    context_object_name = "community"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ct"] = ContentType.objects.get_for_model(context["community"])
        return context


class ExportProfileView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    Export profile data as JSON.
    """

    select_related = ["user", "preferred_games", "preferred_systems"]
    prefetch_related = ["gmed_games", "communities"]
    permission_required = "profile.edit_profile"
    model = models.GamerProfile
    slug_url_kwarg = "gamer"
    context_object_name = "gamer"
    slug_field = "username"

    def get_queryset(self):
        return models.GamerProfile.objects.all()

    def get_data(self):
        serializer = serializers.GamerProfileSerializer(self.get_object())
        return serializer.data

    def render_to_response(self, context, **response_kwargs):
        data = self.get_data()
        response = HttpResponse(
            JSONRenderer().render(data), content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="{}.json"'.format(
            context["gamer"].username
        )
        return response
