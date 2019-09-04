import logging
from datetime import timedelta

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from . import models
from .backends import AuthenticationError, OperationError
from .utils import create_issuelink_from_remote_issue, get_backend_client

logger = logging.getLogger("helpdesk")
# Create your views here.


class IssueListView(
    LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView
):
    model = models.IssueLink
    context_object_name = "issue_list"
    paginate_by = 25
    paginate_orphans = 2
    select_related = ["creator"]
    prefetch_related = ["subscribers"]
    template_name = "helpdesk/issue_list.html"


class IssueCreateView(LoginRequiredMixin, generic.CreateView):
    model = models.IssueLink
    fields = ["title", "description"]

    def form_valid(self, form):
        il = form.save(commit=False)
        il.creator = self.request.user
        gl = get_backend_client()
        try:
            gl_issue = gl.create_issue(
                {"title": il.cached_title, "description": il.cached_description}
            )
            il.external_id = gl_issue.iid
            il.external_url = gl_issue.web_url
            il.sync_status = "sync"
        except OperationError as oe:
            logger.error(
                "Creation of issue resulted in an operation error. Message was: {}".format(
                    str(oe)
                )
            )
            messages.error(
                self.request,
                _(
                    "We weren't able to reach the helpdesk backend. We will attempt to finish creating this issue later. No futher action is required on your part."
                ),
            )
            il.sync_status = "pending"
        il.save()
        return HttpResponseRedirect(il.get_absolute_url())


class IssueDetailView(
    LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView
):
    model = models.IssueLink
    context_object_name = "issue"
    select_related = ["creator"]
    prefetch_related = ["comments"]
    template_name = "helpdesk/issue_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gl = get_backend_client()
        try:
            context["gl_issue"] = cache.get_or_set(
                "helpdesk-{}", gl.get_issue(context["issue"].external_id), 20
            )
            context["gl_issue_comments"] = cache.get_or_set(
                "helpdesk-{}-comments".format(context["gl_issue"].iid),
                gl.get_issue_comments(context["gl_issue"]),
            )
        except AuthenticationError:
            logger.error(
                "Authentication to gitlab failed! Falling back to cached values."
            )
        except OperationError as oe:
            logger.error(
                "There was an error retrieving the gitlab data. Falling back to cached values. Error message was: {}".format(
                    str(oe)
                )
            )
        return context


class IssueUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    pass


class IssueDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.DeleteView
):
    pass


class IssueSubscribeView(LoginRequiredMixin, generic.edit.UpdateView):
    pass


class IssueCloseView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    pass


class IssueReopenView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    pass


class IssueCommentCreateView(LoginRequiredMixin, generic.CreateView):
    pass


class IssueCommentUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    pass


class IssueCommentDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.DeleteView
):
    pass
