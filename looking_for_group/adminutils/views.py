import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django_q.tasks import async_task
from notifications.models import Notification
from rules.contrib.views import PermissionRequiredMixin

from . import forms, tasks
from ..user_preferences.models import Preferences
from ..users.models import User

logger = logging.getLogger("gamer_profiles")


def get_filtered_user_queryset(filters_selected, filter_mode):

    pref_queryset = Preferences.objects.select_related('gamer', 'gamer__user').all()
    if filters_selected:
        filters = []
        for filter in filters_selected:
            if filter_mode != "none":
                filters.append(Q(**{filter: True}))
            else:
                filters.append(Q(**{filter: False}))
        if filter_mode != "any":
            first_filter = filters.pop()
            for item in filters:
                first_filter &= item
            pref_queryset = pref_queryset.filter(first_filter)
        else:
            first_filter = filters.pop()
            for item in filters:
                first_filter |= item
            pref_queryset = pref_queryset.filter(first_filter)
    return User.objects.filter(id__in=[p.gamer.user.pk for p in pref_queryset])


# Create your views here.
class CreateMassNotification(LoginRequiredMixin, PermissionRequiredMixin, generic.FormView):

    form_class = forms.NotificationForm
    template_name = 'adminutils/send_notification.html'
    permission_required = 'adminutils.send_notification'

    def form_valid(self, form):
        filter_selections = form.cleaned_data['filter_options']
        filter_mode = form.cleaned_data['filter_mode']
        message = "Announcement: {}".format(form.cleaned_data['message'])
        recipients = get_filtered_user_queryset(filter_selections, filter_mode)
        messages.success(self.request, _("Sending your notification to {} users.".format(recipients.count())))
        async_task(tasks.send_mass_notifcation, get_current_site(self.request), message, recipients)
        logger.debug("Sent notification async task")
        return HttpResponseRedirect(reverse_lazy('adminutils:notification'))


class SendEmailToUsers(LoginRequiredMixin, PermissionRequiredMixin, generic.FormView):

    form_class = forms.EmailForm
    template_name = 'adminutils/send_email.html'
    permission_required = "adminutils.send_email"

    def form_valid(self, form):
        filter_selections = form.cleaned_data['filter_options']
        filter_mode = form.cleaned_data['filter_mode']
        subject = form.cleaned_data['subject']
        body_plain = form.cleaned_data['body']
        recipients = get_filtered_user_queryset(filter_selections, filter_mode)
        messages.success(self.request, _('Sending your email to {} users.'.format(recipients.count())))
        async_task(tasks.send_mass_email, subject, body_plain, recipients)
        logger.debug("Sent email async task.")
        return HttpResponseRedirect(reverse_lazy('adminutils:email'))
