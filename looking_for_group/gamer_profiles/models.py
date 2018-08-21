import itertools
from django.db import models, transaction, IntegrityError
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify
from django.utils.functional import cached_property
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from django.conf import settings
from ..game_catalog.models import GameSystem, PublishedGame
from ..game_catalog.utils import AbstractUUIDModel


class NotInCommunity(Exception):
    """
    Raised when a community based action is taken on a user that is not a member of the community.
    """

    pass


class AlreadyInCommunity(Exception):
    """
    Raised when you try to add a gamer to a community
    that they already belong to.
    """

    pass


class CurrentlySuspended(Exception):
    """
    Raised when you try to add a gamer to a community (either explicitly or by approving an application)
    when they are currently suspended via Kick.
    """

    pass


class CurrentlyBanned(Exception):
    """
    Raised when you try to validate an application or add a user to a community from which they are banned.
    """

    pass


# Create your models here.


PLAYER_STATUS_CHOICES = (
    ("all_full", _("All good, thanks.")),
    ("available", _("I'm available, but not looking for anything.")),
    ("searching", _("Looking for games.")),
)

APPLICATION_STATUSES = (
    ("new", _("New")),
    ("review", _("In Review")),
    ("reject", _("Rejected")),
    ("approve", _("Approved")),
    ("hold", _("On Hold")),
)


FRIEND_REQUEST_STATUSES = (
    ("new", _("Pending")),
    ("accept", _("Accepted")),
    ("reject", _("Rejected")),
)


COMMUNITY_ROLES = (
    ("member", _("Member")),
    ("moderator", _("Moderator")),
    ("admin", _("Admin")),
)


class GamerCommunity(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Represents a player community, e.g. GeeklyInc.
    """

    name = models.CharField(max_length=255, unique=True, db_index=True, help_text=_("Community Name (must be unique)"))
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    owner = models.ForeignKey("GamerProfile", on_delete=models.CASCADE)
    description = models.TextField(
        null=True,
        blank=True,
        help_text=_("Describe your community. You can use Markdown for formatting."),
    )
    description_rendered = models.TextField(
        null=True,
        blank=True,
        help_text=_("HTML generated from the makdown description."),
    )
    url = models.URLField(
        null=True,
        blank=True,
        help_text=_("Link to the community web site, if applicable."),
    )
    linked_with_discord = models.BooleanField(
        default=False, help_text=_("Is this linked with a Discord server?")
    )
    private = models.BooleanField(
        default=True,
        help_text=_(
            "Do users need to apply to join this community? If linked with Discord, users will automatically be added."
        ),
    )
    application_approval = models.CharField(
        max_length=25,
        default="admin",
        choices=COMMUNITY_ROLES,
        db_index=True,
        help_text=_(
            "What is the minimum role required to approve a membership application?"
        ),
    )
    invites_allowed = models.CharField(
        max_length=25,
        default="admin",
        choices=COMMUNITY_ROLES,
        db_index=True,
        help_text=_(
            "What is the minimum role level required to invite others to the community?"
        ),
    )
    member_count = models.PositiveIntegerField(
        default=0, help_text=_("Current total count of members.")
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            max_length = self._meta.get_field('slug').max_length
            temp_slug = slugify(self.name, allow_unicode=True)[:max_length]
            for x in itertools.count(1):
                if not type(self).objects.filter(slug=temp_slug).exists():
                    break

                temp_slug = "{}-{}".format(temp_slug[:max_length - len(str(x)) - 1], x)
            self.slug = temp_slug
        super().save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse("gamer_profiles:community-detail", kwargs={"community": self.slug})

    def get_member_count(self):
        return self.members.count()

    def get_admins(self):
        """
        Return a queryset of admins for a community.
        """
        return self.members.filter(community_role="admin")

    def get_moderators(self):
        """
        Return a queryset of community moderators.
        """
        return self.members.filter(community_role="moderator")

    def get_members(self):
        """
        Return a queryset of all members.
        """
        return self.members.all()

    def get_role(self, gamer):
        """
        Return the community role of a given member.
        """
        try:
            role_obj = CommunityMembership.objects.get(community=self, gamer=gamer)
        except ObjectDoesNotExist:
            raise NotInCommunity
        return role_obj.get_community_role_display()

    def add_member(self, gamer, role="member"):
        """
        Adds a gamer to the community directly.
        """
        try:
            with transaction.atomic():
                membership = CommunityMembership.objects.create(
                    community=self, gamer=gamer, community_role=role
                )
                self.member_count = F("member_count") + 1
                self.save()
        except IntegrityError:
            raise AlreadyInCommunity
        return membership

    def remove_member(self, gamer):
        """
        Removes a gamer from the community, but not
        from any games they already are playing.
        """
        try:
            with transaction.atomic():
                membership = CommunityMembership.objects.get(
                    community=self, gamer=gamer
                )
                membership.delete()
                self.member_count = F("member_count") - 1
                self.save()
        except ObjectDoesNotExist:
            raise NotInCommunity

    def set_role(self, gamer, role):
        """
        Set the role of a gamer to the given value.
        If gamer membership does not exist yet, it is automatically created.
        """
        role_obj, created = CommunityMembership.objects.update_or_create(
            gamer=gamer, community=self, defaults={"community_role": role}
        )

    def kick_user(self, kicker, gamer, reason, earliest_reapply=None):
        """
        Kicks a user from a community and suspends them from reapplying.
        Game membership is not affected by this.
        """
        if not kicker.user.has_perm("community.kick_user", self):
            raise PermissionDenied
        if self.owner == gamer:
            raise PermissionDenied(_("You cannot kick the owner of a community out."))
        with transaction.atomic():
            kick_file = KickedUser.objects.create(
                community=self,
                kicker=kicker,
                kicked_user=gamer,
                reason=reason,
                end_date=earliest_reapply,
            )
            self.remove_member(gamer)
        return kick_file

    def ban_user(self, banner, gamer, reason):
        """
        Bans a user from the given community.
        """
        if not banner.user.has_perm("community.ban_user", self):
            raise PermissionDenied
        if self.owner == gamer:
            raise PermissionDenied(_("You cannot ban the owner of the community."))
        with transaction.atomic():
            ban_file = BannedUser.objects.create(
                community=self, banner=banner, banned_user=gamer, reason=reason
            )
            self.remove_member(gamer)
        return ban_file

    class Meta:
        ordering = ["name"]


class GamerFriendRequest(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    An object representing a symmetrical friendship.
    """

    requestor = models.ForeignKey(
        "GamerProfile",
        on_delete=models.CASCADE,
        help_text=_("Who asked to friend?"),
        related_name="friend_requests_sent",
    )
    recipient = models.ForeignKey(
        "GamerProfile",
        on_delete=models.CASCADE,
        related_name="friend_requests_received",
        help_text=_("Will they or won't they?"),
    )
    status = models.CharField(
        max_length=25,
        choices=FRIEND_REQUEST_STATUSES,
        default="new",
        help_text=_("Current request status."),
    )

    def __str__(self):
        return "{0} friend request from {1} to {2}".format(
            self.get_status_display(), self.requestor, self.recipient
        )

    def accept(self):
        """
        Accept a friend request.
        """
        with transaction.atomic():
            self.requestor.friends.add(self.recipient)
            self.status = "accept"
            self.save()

    def deny(self):
        """
        Ignore a friend request.
        """
        self.status = "reject"
        self.save()


class GamerProfile(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A profile of game preferences and history.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    username = models.TextField(unique=True, db_index=True, help_text=_('Cached value from user.'))
    private = models.BooleanField(
        default=True,
        help_text=_("Only allow GMs and communities I belong/apply to see profile."),
    )
    friends = models.ManyToManyField("self", blank=True, help_text=_("Other friends."))
    rpg_experience = models.TextField(
        null=True,
        blank=True,
        help_text=_("A few words about your RPG experience. (Visible to GM.)"),
    )
    ttgame_experience = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "A few words about your non-RPG tabletop experience. (Visible to GM)"
        ),
    )
    playstyle = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        help_text=_(
            "A few words on the kinds of games you prefer to play, i.e. horror, silly, tactical, RP-heavy, etc."
        ),
    )
    will_gm = models.BooleanField(
        default=False, db_index=True, help_text=_("Willing to be a GM?")
    )
    player_status = models.CharField(
        max_length=25,
        default="all_full",
        choices=PLAYER_STATUS_CHOICES,
        db_index=True,
        help_text=_("Are you looking for a group right now?"),
    )
    adult_themes = models.BooleanField(
        default=False,
        help_text=_("Are you ok with 18+ themes/content/language in games?"),
        db_index=True,
    )
    one_shots = models.BooleanField(
        default=False, help_text=_("Interested in one-shots?"), db_index=True
    )

    adventures = models.BooleanField(
        default=False,
        help_text=_("Interested in short multi-session games?"),
        db_index=True,
    )
    campaigns = models.BooleanField(
        default=False, help_text=_("Interested in joining a campaign?"), db_index=True
    )
    online_games = models.BooleanField(
        default=False,
        help_text=_("Interested in online games, e.g. Roll20?"),
        db_index=True,
    )
    local_games = models.BooleanField(
        default=False, help_text=_("Intested in local games?"), db_index=True
    )
    preferred_games = models.ManyToManyField(
        PublishedGame,
        blank=True,
        help_text=_("Do you have any preferred games you like to play?"),
    )
    preferred_systems = models.ManyToManyField(
        GameSystem,
        blank=True,
        help_text=_("Do you have any preferred systems you like to play?"),
    )
    games_joined = models.PositiveIntegerField(
        default=0, help_text=_("How many time has this user joined a game?")
    )
    games_created = models.PositiveIntegerField(
        default=0, help_text=_("How many times has this user created a game?")
    )
    games_applied = models.PositiveIntegerField(
        default=0, help_text=_("How many times has this user applied to join a game?")
    )
    games_left = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "How many times has this user left a game before it was completed?"
        ),
    )
    games_finished = models.PositiveIntegerField(
        default=0, help_text=_("How many finished games has this user participated in?")
    )
    # preferred_genres = models.ManyToManyField(GameGenres, null=True, blank=True)
    # preferred_playstyles = models.ManyToManyField(PlayStyles, null=True, blank=True)
    communities = models.ManyToManyField(
        through="CommunityMembership", to=GamerCommunity, blank=True
    )
    avg_gamer_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text=_("Average overall rating from other players."),
    )
    median_gamer_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text=_("Median overall rating from other players."),
    )
    reputation_score = models.IntegerField(
        default=0, help_text=_("Calculated overall reputation score.")
    )
    attendance_record = models.DecimalField(
        null=True,
        decimal_places=4,
        max_digits=4,
        blank=True,
        help_text=_("Overall attendance record for games sessions."),
    )

    def __str__(self):
        return "Game Profile: {}".format(self.user.username)

    def get_absolute_url(self):
        return reverse("gamer_profiles:profile-detail", kwargs={"gamer": self.username})

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.user.username
        super().save(*args, **kwargs)

    @cached_property
    def display_name(self):
        return self.user.display_name

    def blocked_by(self, gamer):
        '''
        Check to see if self is blocked by indicated gamer.
        '''
        try:
            BlockedUser.objects.get(blocker=gamer, blockee=self)
        except ObjectDoesNotExist:
            return False
        return True

    def get_role(self, community):
        """
        For a given community object fetch the role the user has within that community.
        """
        try:
            role_obj = CommunityMembership.objects.get(gamer=self, community=community)
        except ObjectDoesNotExist:
            raise NotInCommunity
        return role_obj.get_community_role_display()


class GamerRating(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A rating another gamer gives another.
    """

    rater = models.ForeignKey(
        GamerProfile,
        related_name="raters",
        help_text=_("Who is rating this user?"),
        on_delete=models.CASCADE,
    )
    gamer = models.ForeignKey(
        GamerProfile,
        help_text=_("Which gamer is being rated?"),
        on_delete=models.CASCADE,
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text=_("How are they rated?"),
    )

    def __str__(self):
        return "[{0}] {1} rated {2} {3} stars".format(
            self.created, self.rater, self.gamer, self.rating
        )


class GamerNote(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Private gamer notes about other gamers.
    """

    author = models.ForeignKey(
        GamerProfile,
        related_name="authored_notes",
        help_text=_("Who wrote this note?"),
        on_delete=models.CASCADE,
    )
    gamer = models.ForeignKey(
        GamerProfile, help_text=_("Whom is this note about?"), on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255, help_text=_("Some helpful title for you."))
    body = models.TextField(
        help_text=_("Your note (markdown ok, but html is naughty.)")
    )
    body_rendered = models.TextField(
        help_text=_("The actual rendered text derived from source markdown.")
    )

    def __str__(self):
        return "[{0}] {1} by {2} about {3}".format(
            self.title, self.title, self.author, self.gamer
        )

    def get_absolute_url(self):
        return reverse("gamer_profiles:note_detail", kwargs={"note": self.pk})


class CommunityMembership(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Represents the community and role that a gamer profile has.
    """

    gamer = models.ForeignKey(GamerProfile, on_delete=models.CASCADE)
    community = models.ForeignKey(
        GamerCommunity, related_name="members", on_delete=models.CASCADE
    )
    community_role = models.CharField(
        max_length=25, default="member", choices=COMMUNITY_ROLES, db_index=True
    )
    avg_comm_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text=_("Average rating from other community members."),
    )
    median_comm_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text=_("Median rating from other community members."),
    )
    comm_reputation_score = models.IntegerField(
        default=0, help_text="Calculated reputation score within community."
    )
    comm_games_joined = models.PositiveIntegerField(
        default=0, help_text=_("How many time has this user joined a game?")
    )
    comm_games_created = models.PositiveIntegerField(
        default=0, help_text=_("How many times has this user created a game?")
    )
    comm_games_applied = models.PositiveIntegerField(
        default=0, help_text=_("How many times has this user applied to join a game?")
    )
    comm_games_left = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "How many times has this user left a game before it was completed?"
        ),
    )
    comm_games_finished = models.PositiveIntegerField(
        default=0, help_text=_("How many finished games has this user participated in?")
    )
    comm_game_attendance_record = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=4,
        max_digits=4,
        help_text=_("Attendance percentage for sessions within community."),
    )

    def __str__(self):
        return "{0} with role of {1} in {2}".format(
            self.gamer.user.username, self.community_role, self.community.name
        )

    class Meta:
        unique_together = ["gamer", "community"]
        order_with_respect_to = "community"


class CommunityApplication(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Application to join a community.
    """

    gamer = models.ForeignKey(GamerProfile, on_delete=models.CASCADE)
    community = models.ForeignKey(GamerCommunity, on_delete=models.CASCADE)
    message = models.TextField(
        null=True,
        blank=True,
        help_text=_("Any message to pass along with your application?"),
    )
    status = models.CharField(
        max_length=30,
        choices=APPLICATION_STATUSES,
        help_text=_("Application Status"),
        db_index=True,
    )

    def __str__(self):
        return "{0} {1} {2}".format(self.created, self.gamer.user.username, self.status)

    def get_absolute_url(self):
        return reverse(
            "gamer_profiles:community-application-detail",
            kwargs={"application": self.pk},
        )

    def validate_application(self):
        """
        Checks if the user is banned, suspended, or already a member.
        """
        memberships = CommunityMembership.objects.filter(
            community=self.community, gamer=self.gamer
        )
        if memberships:
            raise AlreadyInCommunity
        bans = BannedUser.objects.filter(community=self.community, banned_user=self.gamer)
        if bans:
            raise CurrentlyBanned
        kicks = KickedUser.objects.filter(
            community=self.community, kicked_user=self.gamer, end_date__gt=timezone.now()
        )
        if kicks:
            raise CurrentlySuspended
        return True

    def submit_application(self):
        """
        Submit an application.
        """
        if self.validate_application():
            self.status = "review"
            self.save()
            return True
        return False  # Really an exception gets passed up to us.

    def approve_application(self):
        """
        Approves an application and adds gamer to community.
        """

        if self.validate_application():
            with transaction.atomic():
                self.community.add_member(self.gamer)
                self.status = "approve"
                self.save()
            return True
        return False  # Actually an exception gets passed up.

    def reject_application(self):
        """
        Rejects an application.
        """
        self.status = "reject"
        self.save()

    class Meta:
        ordering = ['community__name', 'modified']


class BlockedUser(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Captures user-initiated blocks, as opposed to by community.
    """

    blocker = models.ForeignKey(
        GamerProfile,
        related_name="blocked_by_users",
        help_text=_("User who initiated block."),
        on_delete=models.CASCADE,
    )
    blockee = models.ForeignKey(
        GamerProfile,
        help_text=_("User who has been blocked."),
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return "{0} blocked {2}".format(self.blockee.username, self.blockee.username)


class MutedUser(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Captures mute moderations from users as opposed to by community.
    """

    muter = models.ForeignKey(
        GamerProfile,
        related_name="muted_by_users",
        help_text=_("User who initiated mute."),
        on_delete=models.CASCADE,
    )
    mutee = models.ForeignKey(
        GamerProfile, help_text=_("User who has been muted."), on_delete=models.CASCADE
    )

    def __str__(self):
        return "{0} muted {1}".format(self.muter.username, self.mutee.username)


class KickedUser(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Capture users kicked/suspended from a community.
    """

    community = models.ForeignKey(GamerCommunity, on_delete=models.CASCADE)
    kicker = models.ForeignKey(
        GamerProfile,
        related_name="kicked_by_users",
        help_text=_("User who initated kick."),
        on_delete=models.CASCADE,
    )
    kicked_user = models.ForeignKey(
        GamerProfile, help_text=_("User who was kicked."), on_delete=models.CASCADE
    )
    end_date = models.DateTimeField(
        null=True, blank=True, help_text=_("Earliest date that user can reapply.")
    )
    reason = models.TextField(
        help_text=_("Why is the user kicked from this community?")
    )

    def __str__(self):
        return "{0} kicked {1} from {2} until {3}".format(
            self.kicker.username,
            self.kicked_user.username,
            self.community.name,
            self.end_date,
        )


class BannedUser(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Capture users kicked/suspended from a community.
    """

    community = models.ForeignKey(GamerCommunity, on_delete=models.CASCADE)
    banner = models.ForeignKey(
        GamerProfile,
        related_name="banned_by_users",
        help_text=_("User who initated ban."),
        on_delete=models.CASCADE,
    )
    banned_user = models.ForeignKey(
        GamerProfile, help_text=_("User who was banned."), on_delete=models.CASCADE
    )
    reason = models.TextField(help_text=_("Why is this user being banned?"))

    def __str__(self):
        return "{0} banned {1} from {2} on {3}".format(
            self.banner.username,
            self.banned_user.username,
            self.community.name,
            self.created,
        )
