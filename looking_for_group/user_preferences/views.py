import logging

from braces.views import SelectRelatedMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import generic

from . import models

# Create your views here.


logger = logging.getLogger('gamer_profiles')


class SettingsView(LoginRequiredMixin, SelectRelatedMixin, generic.DetailView):
    """
    Settings view.
    """
    model = models.Preferences
    context_object_name = 'preferences'
    template_name = 'user_preferences/setting_view.html'
    select_related = ['gamer']

    def get_object(self):
        if self.request.user.is_authenticated:
            self.object, created = models.Preferences.objects.get_or_create(gamer=self.request.user.gamerprofile)
            if created:
                logger.debug("Created new record.")
            return self.object
        else:
            return None


class SettingsEdit(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Settings edit view.
    """
    model = models.Preferences
    context_object_name = 'preferences'
    template_name = 'user_preferences/setting_edit.html'
    fields = ['news_emails', 'notification_digest', 'feedback_volunteer']
    success_url = reverse_lazy('user_preferences:setting-view')

    def get_object(self):
        self.object, created = models.Preferences.objects.get_or_create(gamer=self.request.user.gamerprofile)
        if created:
            logger.debug('Created new record.')
        return self.object
