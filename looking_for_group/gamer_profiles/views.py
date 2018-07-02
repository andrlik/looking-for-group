from rules.contrib.views import PermissionRequiredMixin
from django.views import generic
from django.shortcuts import get_object_or_404
from braces.views import SelectRelatedMixin, PrefetchRelatedMixin, LoginRequiredMixin
from . import models


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            context["my_communities"] = self.request.user.gamerprofile.communities.all()
        return context


class MyCommunitiesListView(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):
    """
    List only the current user's communities.
    """

    template_name = "gamer_profiles/my_community_list.html"
    model = models.CommunityMembership
    paginate_by = 25
    select_related = ["community"]

    def get_queryset(self):
        return models.CommunityMembership.objects.filter(
            gamer=self.request.user.gamerprofile
        )


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

    permission_required = "community.view_details"
    model = models.GamerCommunity
    template_name = "gamer_profiles/community_detail.html"
    prefetch_related = [
        "communitymembership_set",
        "communitymembership_gamer",
        "communityapplication_set",
    ]  # TODO Add games.


class CommunityUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView
):
    """
    Update view for basic fields in community.
    """

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
        comm_pk = kwargs.pop("community")
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

    def dispatch(self, request, *args, **kwargs):
        comm_pk = kwargs.pop("community")
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
        comm_pk = kwargs.pop("community")
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
        comm_pk = kwargs.pop("community")
        self.community = get_object_or_404(models.GamerCommunity, pk=comm_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.community

    def get_queryset(self):
        return self.model.objects.filter(community=self.community)
