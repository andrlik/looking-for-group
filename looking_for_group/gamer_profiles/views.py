import logging
from rules.contrib.views import PermissionRequiredMixin
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from braces.views import SelectRelatedMixin, PrefetchRelatedMixin, LoginRequiredMixin
from . import models
from .forms import OwnershipTransferForm, BlankDistructiveForm


logger = logging.getLogger('gamer_profiles')


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
    ordering = ['-member_count', 'name']


class MyCommunitiesListView(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):
    """
    List only the current user's communities.
    """

    template_name = "gamer_profiles/my_community_list.html"
    model = models.CommunityMembership
    paginate_by = 25
    select_related = ["community"]
    ordering = ['community', 'community__name']

    def get_queryset(self):
        return models.CommunityMembership.objects.filter(
            gamer=self.request.user.gamerprofile
        )


class JoinCommunity(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    '''
    Try to join a community. Fails if community is private.
    '''
    model = models.CommunityMembership
    permission_required = "community.join"
    template_name = "gamer_profiles/community_join.html"
    form_class = BlankDistructiveForm

    def dispatch(self, request, *args, **kwargs):
        self.community = get_object_or_404(models.GamerCommunity, pk=kwargs.pop('community'))
        return super().dispatch(request, *args, **kwargs)

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
    pk_url_kwarg = "community"
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
    pk_url_kwarg = "member"
    permission_required = "community.edit_roles"
    template_name = "gamer_profiles/member_role.html"
    fields = ["community_role"]
    select_related = ["gamer", "community"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def has_permission(self):
        if self.request.user.has_perm(
            "community.edit_gamer_role", self.object.gamer, self.object.community
        ):
            return super().has_permission()
        return False


class CommunityCreateView(LoginRequiredMixin, generic.CreateView):
    """
    Creating a community.
    """

    model = models.GamerCommunity
    fields = [
        "name",
        "description",
        "url",
        "private",
        "application_approval",
        "invites_allowed",
    ]
    template_name = "gamer_profiles/community_create.html"

    def get_success_url(self):
        messages.success(
            _("Community {0} succesfully created!".format(self.object.name))
        )
        return reverse_lazy(
            "gamer_profiles:community-detail", kwargs={"community": self.object.pk}
        )


class CommunityDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
   # PrefetchRelatedMixin,
    generic.DetailView,
):
    """
    View details of a single community.
    """

    pk_url_kwarg = "community"
    permission_required = "community.list_communities"
    model = models.GamerCommunity
    template_name = "gamer_profiles/community_detail.html"
    select_related = ['owner']
    # prefetch_related = [
    #     "gamerprofile_set",
    #     "communityapplication_set",
    # ]  # TODO Add games.
    context_object_name = "community"

    def get(self, request, *args, **kwargs):
        logger.debug("Attempting to retrieve community for evaluation.")
        obj = get_object_or_404(models.GamerCommunity, pk=kwargs['community'])
        logger.debug("Found community {}".format(obj.name))
        logger.debug("Checking permissions of user...")
        if not request.user.has_perm('community.view_details', obj):
            logger.debug("User does not have permission to view.")
            view_target = 'gamer_profiles:community-join'
            message = _("You must join this community in order to view its details.")
            if obj.private:
                logger.debug("Community is private: redirecting to apply instead of join.")
                view_target = 'gamer_profiles:community-apply'
                message = _("You must be a member of this community to view its details. You can apply below.")
            messages.info(request, message)
            return HttpResponseRedirect(reverse(view_target, kwargs={'community': obj.pk}))
        logger.debug("user has permissions, proceeding with standard redirect")
        return super().get(request, *args, **kwargs)


class CommunityUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView
):
    """
    Update view for basic fields in community.
    """

    pk_url_kwarg = "community"
    permission_required = "community.edit_community"
    model = models.GamerCommunity
    template_name = "gamer_profiles/community_edit.html"
    fields = [
        "name",
        "description",
        "url",
        "private",
        "application_approval",
        "invites_allowed",
    ]

    def get_success_url(self):
        messages.success(_("{0} successfully updated.".format(self.object.name)))
        return reverse_lazy(
            "gamer_profiles/community-detail", kwargs={"community": self.object.pk}
        )


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
    ordering = ["community_role", "gamer__display_name"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
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
    permission_required = "community.approve_application"
    paginate_by = 25
    ordering = ["created", "status"]
    context_object_name = "applications"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return models.CommunityApplication.objects.filter(
            community=self.community, status__in=["new", "review", "hold"]
        )

    def get_context_data(self, **kwargs):
        all_apps = (
            models.CommunityApplication.objects.filter(community=self.community)
            .select_related("gamer")
            .order_by("created")
        )
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["approved_apps"] = all_apps.filter(status="approve")
        context["rejected_apps"] = all_apps.filter(status="reject")
        return context


class UpdateApplication(
    LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView
):
    """
    Allows the user who put in an application to update it (but not the status)
    """

    pk_url_kwarg = "application"
    model = models.CommunityApplication
    template_name = "gamer_profiles/community_apply_edit.html"
    permission_required = "community.edit_application"
    fields = ["message"]

    def dispatch(self, request, *args, **kwargs):
        comm_uk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_uk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def form_valid(self, form):
        messages.success(_("Application successfully updated."))
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
    permission_required = "community.can_apply"

    def dispatch(self, request, *args, **kwargs):
        comm_uk = kwargs['community']
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_uk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['community'] = self.community
        return context

    def get_permission_object(self):
        return self.community

    def get_success_url(self):
        return reverse_lazy("gamer_profiles:my-application-list")

    def form_valid(self, form):
        form.instance.community = self.community
        form.instance.gamer = self.user.gamerprofile
        form.instance.status = "new"
        return super().form_valid(form)


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
    template_name = "gamer_profiles/delete_application.html"
    permission_required = "community.edit_application"
    context_object_name = "application"
    select_related = ["community"]


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
    fields = ["status"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

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
                _(
                    "{0} is already a member of {1}".format(
                        application.gamer.user.display_name, self.community.name
                    )
                )
            )
        except models.CurrentlySuspended:
            messages.error(
                _(
                    "{0} is currently suspended and cannot rejoin.".format(
                        application.gamer.user.display_name
                    )
                )
            )
        return HttpResponseRedirect(self.get_success_url())


class RejectApplication(ApproveApplication):
    """
    Rejects an application.
    """

    def form_valid(self, form):
        application = self.get_object()
        application.reject_application()
        return HttpResponseRedirect(self.get_success_url())


class CommunityKickedUserList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    List of users currently kicked from community.
    """

    model = models.KickedUser
    select_related = ["kicked_user"]
    template_name = "gamer_profiles/community_kicked_list.html"
    permission_required = "community.kick_user"
    paginate_by = 25
    ordering = ["-end_date", "-created"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return self.model.objects.filter(community=self.community)


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
    ordering = ["-created"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return self.model.objects.filter(community=self.community)


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
    template_name = "gamer_profiles/delete_ban.html"
    permission_required = "community.ban_user"
    context_object_name = "ban_record"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community


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
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        self.gamer = get_object_or_404(models.GamerProfile, pk=gamer_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-banned-list",
            kwargs={"community": self.community.pk},
        )

    def has_permission(self):
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
                _(
                    "{0} is not a current member of the {1} and cannot be banned.".format(
                        self.gamer.user.display_name, self.community.name
                    )
                )
            )
            return super().form_invalid(form)
        messages.success(
            _(
                "{0} successfully banned from {1}".format(
                    self.gamer.user.display_name, self.community.name
                )
            )
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
    fields = ["reason", "end_date"]

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        gamer_pk = kwargs.pop("gamer")
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        self.gamer = get_object_or_404(models.GamerProfile, pk=gamer_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-kicked-list",
            kwargs={"community": self.community.pk},
        )

    def get_permission_object(self):
        return self.community

    def has_permission(self):
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
        return super().has_permission(self)

    def form_valid(self, form):
        try:
            self.community.kick_user(
                kicker=self.request.user.gamerprofile,
                gamer=self.gamer,
                community=self.community,
                reason=form.instance.reason,
                earliest_reapply=form.instance.end_date,
            )
        except models.NotInCommunity:
            messages.error(
                _(
                    "{0} is not a current member of the {1} and cannot be kicked.".format(
                        self.gamer.user.display_name, self.community.name
                    )
                )
            )
            return super().form_invalid(form)
        messages.success(
            _(
                "{0} successfully kicked from {1}.".format(
                    self.gamer.user.display_name, self.community.name
                )
            )
        )
        return super().form_valid(form)


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
    template_name = "gamer_profiles/kick_edit.html"
    fields = ["reason", "end_date"]
    pk_url_kwarg = "kickfile"
    permission_required = "community.kick_user"

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community", None)
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:community-kicked-list",
            kwargs={"community": self.community.pk},
        )


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
    pk_url_kwarg = "profile"
    permission_required = "profile.view_details"
    template_name = "gamer_profiles/profile_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gamer_notes"] = models.GamerNote.objects.filter(
            author=self.request.user.gamerprofile, gamer=self.object
        )
        context["your_rating"], created = models.GamerRating.objects.get_or_create(
            gamer=self.object, rater=self.request.user.gamerprofile
        )
        return context


class GamerProfileUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Update view for gamer profile.
    """

    model = models.GamerProfile
    select_related = ["user"]
    pk_url_kwarg = "profile"
    permission_required = "profile.edit_profile"
    template_name = "gamer_profiles/profile_edit.html"
    fields = [
        "rpg_experience",
        "ttgame_experience",
        "playstyle",
        "will_gm",
        "player_status",
        "adult_themes",
        "one_shots",
        "adventures",
        "campaigns",
        "online_games",
        "local_games",
        "preferred_games",
        "preferred_systems",
    ]

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:profile-detail", kwargs={"profile": self.object.pk}
        )


class CreateGamerNote(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.CreateView
):
    """
    Add a note to a gamer profile.
    """

    model = models.GamerNote
    fields = ["title", "body"]
    permission_required = "profile.view_details"
    template_name = "gamer_profiles/gamernote_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.gamer = get_object_or_404(
            models.GamerProfile, pk=self.kwargs.pop("profile")
        )
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.gamer

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:profile_detail", kwargs={"profile": self.gamer.pk}
        )

    def form_valid(self, form):
        form.instance.author = self.request.user.gamerprofile
        form.instance.gamer = self.gamer
        return super().form_valid(form)


class RateGamer(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    Update or create a rating for a given gamer.
    """

    model = models.GamerRating
    pk_url_kwarg = "rating"
    permission_required = "profile.view_details"
    http_method_names = ["post", "put"]
    fields = ["rating"]

    def dispatch(self, request, *args, **kwargs):
        self.gamer = get_object_or_404(models.GamerProfile, pk=kwargs.pop("profile"))
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.gamer

    def get_object(self):
        obj, created = models.GamerRating.objects.get_or_create(
            rater=self.request.user.gamerprofile, gamer=self.gamer
        )


class BlockGamer(LoginRequiredMixin, generic.CreateView):
    """
    Blocks another gamer. The only form is a confirmation screen.
    """

    model = models.BlockedUser
    form_class = BlankDistructiveForm
    template_name = "gamer_profiles/block_gamer.html"

    def dispatch(self, request, *args, **kwargs):
        self.gamer = get_object_or_404(models.GamerProfile, pk=kwargs.pop("profile"))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "gamer_profiles:profile-detail", kwargs={"profile": self.gamer.pk}
        )

    def form_valid(self, form):
        block_file, created = models.BlockedUser.objects.get_or_create(
            blocker=self.request.user.gamerprofile, blockee=self.gamer
        )
        if created:
            messages.success(
                _(
                    "You have successfully blocked {}".format(
                        self.gamer.user.display_name
                    )
                )
            )
        else:
            messages.error(
                _("You have already blocked {}".format(self.gamer.user.display_name))
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
    template_name = "gamer_profiles/block_delete.html"
    permission_required = "profile.remove_block"
    select_related = ["blockee"]


class MuteGamer(LoginRequiredMixin, generic.CreateView):
    """
    Mutes another gamer.
    """

    model = models.MutedUser
    form_class = BlankDistructiveForm
    template_name = "gamer_profiles/mute_gamer.html"

    def dispatch(self, request, *args, **kwargs):
        self.gamer = get_object_or_404(models.GamerProfile, pk=kwargs.pop("profile"))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.gamer.get_absolute.url()

    def form_valid(self, form):
        mute_file, created = self.model.object.get_or_create(
            muter=self.request.user.gamerprofile, mutee=self.gamer
        )
        if created:
            messages.success(
                _(
                    "You have successfully muted {}.".format(
                        self.gamer.user.display_name
                    )
                )
            )
        else:
            messages.error(
                _("You have already muted {}.".format(self.gamer.user.display_name))
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
    template_name = "gamer_profiles/mute_delete.html"
    permission_required = "profile.remove_mute"
    select_related = ["mutee"]
