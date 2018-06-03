from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel


class User(TimeStampedModel, AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
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

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})
