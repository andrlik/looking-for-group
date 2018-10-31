from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from looking_for_group.game_catalog.utils import AbstractUUIDModel


class User(TimeStampedModel, AbstractUUIDModel, AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    display_name = models.CharField(
        _("Display Name"),
        blank=True,
        null=True,
        max_length=255,
        help_text=_("🎶 What's your name, son? ALEXANDER HAMILTON"),
    )
    bio = models.CharField(
        _("Bio"),
        blank=True,
        null=True,
        max_length=255,
        help_text=_("A few words about you."),
    )
    homepage_url = models.URLField(
        _("Homepage"), blank=True, null=True, help_text=_("Your home on the web.")
    )

    @property
    def avatar_email(self):
        if self.email:
            return self.email
        email_list = self.emailaddress_set.filter(primary=True)
        if email_list.count() > 0:
            return email_list[0]
        return None

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse("gamer_profiles:profile-detail", kwargs={"gamer": self.username})
