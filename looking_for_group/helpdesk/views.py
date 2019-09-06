import logging
from datetime import timedelta

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from . import models
from .backends import AuthenticationError, OperationError
from .tasks import (
    close_remote_issue,
    create_remote_comment,
    create_remote_issue,
    delete_remote_comment,
    delete_remote_issue,
    reopen_remote_issue,
    update_remote_comment,
    update_remote_issue
)
from .utils import get_backend_client

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
    status_type = "opened"

    def dispatch(self, request, *args, **kwargs):
        get_dict = request.GET.copy()
        user_info = get_dict.pop("status", None)
        if user_info and user_info in ["opened", "closed"]:
            self.status_type = user_info
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.exclude(
            sync_status__in=["delete_err", "deleted"]
        ).filter(cached_status=self.status_type)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_issues_not_deleted = self.model.objects.exclude(
            sync_status__in=["delete_err", "deleted"]
        )
        context["total_open"] = all_issues_not_deleted.filter(
            cached_status="opened"
        ).count()
        context["total_closed"] = all_issues_not_deleted.filter(
            cached_status="closed"
        ).count()
        context["your_open"] = (
            context["total_open"].filter(creator=self.request.user).count()
        )
        context["your_closed"] = (
            context["total_closed"].filter(creator=self.request.user).count()
        )
        return context


class MyIssueListView(IssueListView):

    template_name = "helpdesk/my_issue_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(creator=self.request.user)


class IssueCreateView(LoginRequiredMixin, generic.CreateView):
    model = models.IssueLink
    fields = ["cached_title", "cached_description"]

    def form_valid(self, form):
        il = form.save(commit=False)
        il.creator = self.request.user
        il.save()
        create_remote_issue(il)
        il.refresh_from_db()
        if il.sync_status != "sync":
            messages.error(
                self.request,
                _(
                    "We weren't able to reach the helpdesk backend. We will attempt to finish creating this issue later. No futher action is required on your part."
                ),
            )
        return HttpResponseRedirect(il.get_absolute_url())


class IssueDetailView(
    LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView
):
    """
    Detail view for an issue.
    """

    model = models.IssueLink
    context_object_name = "issue"
    select_related = ["creator"]
    prefetch_related = ["comments"]
    template_name = "helpdesk/issue_detail.html"
    slug_url_kwarg = "ext_id"
    slug_field = "external_id"

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

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssuePendingDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.DetailView
):
    """
    Detail view for a pending issue (not yet created in backend.)
    """

    model = models.IssueLink
    pk_url_kwarg = "pk"
    context_object_name = "issue"
    template_name = "helpdesk/issue_pending_detail.html"
    select_related = ["creator"]
    permission_required = "helpdesk.edit_issue"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.sync_status == "sync" and obj.external_id:
            return HttpResponseRedirect(obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    model = models.IssueLink
    slug_field = "external_id"
    slug_url_kwarg = "ext_id"
    permission_required = "helpdesk.edit_issue"
    context_object_name = "issue"
    template_name = "helpdesk/issue_update.html"
    fields = ["cached_title", "cached_description"]

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.sync_status != "sync":
            messages.info(
                request,
                _(
                    "This item is still pending sync with our issue tracking system and cannot currently be edited."
                ),
            )
            return HttpResponseRedirect(obj.get_absolute_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        il = form.save()
        update_remote_issue(il)
        il.refresh_from_db()
        if il.sync_status != "sync":
            messages.info(
                self.request,
                _(
                    "We have updated the record, but it is still awaiting an update on the backend. No further action is required on your part."
                ),
            )
        return HttpResponseRedirect(il.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.DeleteView
):
    model = models.IssueLink
    slug_url_kwarg = "ext_id"
    slug_field = "external_id"
    permission_required = "helpdesk.delete_issue"
    context_object_name = "issue"
    template_name = "helpdesk/issue_delete.html"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        delete_remote_issue(obj)
        obj.refresh_from_db()
        if obj.sync_status == "deleted":
            obj.delete()
            messages.success(request, _("Your issue is successfully deleted."))
        else:
            messages.success(request, _("Your issue has been queued for deletion."))
        return HttpResponseRedirect(reverse_lazy("helpdesk:issue-list"))

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueSubscribeView(LoginRequiredMixin, generic.edit.UpdateView):
    model = models.IssueLink
    slug_field = "external_id"
    slug_url_kwarg = "ext_id"
    context_object_name = "issue"
    fields = ["id"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = self.get_object()
        obj.subscribers.add(self.request.user)
        messages.success(
            self.request, _("You are now subscribed to updates on this issue.")
        )
        return HttpResponseRedirect(obj.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueUnsubscribeView(IssueSubscribeView):
    def form_valid(self, form):
        obj = self.get_object()
        obj.subscribers.remove(self.request.user)
        messages.success(
            self.request, _("You are no longer subscribed to updates on this issue.")
        )
        return HttpResponseRedirect(obj.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueCloseView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    model = models.IssueLink
    slug_field = "external_id"
    slug_url_kwarg = "ext_id"
    permission_required = "helpdesk.close_issue"
    # Add a form here

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = self.get_object()
        close_comment = form.save(commit=False)
        close_comment.creator = self.reqeuest.user
        create_remote_comment(close_comment)
        close_remote_issue(obj)
        obj.status = "closed"
        obj.save()
        messages.success(self.request, _("Issue has been closed."))
        return HttpResponseRedirect(obj.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueReopenView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    model = models.IssueLink
    slug_url_kwarg = "ext_id"
    slug_field = "external_id"
    permission_required = "helpdesk.reopen_issue"
    fields = ["id"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = self.get_object()
        obj.status = "opened"
        obj.save()
        reopen_remote_issue(obj)
        messages.success(self.request, _("This issue has been reopened."))
        return HttpResponseRedirect(obj.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueCommentCreateView(LoginRequiredMixin, generic.CreateView):
    model = models.IssueCommentLink
    fields = ["cached_body"]
    template_name = "helpdesk/comment_create.html"
    master_issue = None

    def dispatch(self, request, *args, **kwargs):
        issue_id = kwargs.pop("ext_id", None)
        self.master_issue = get_object_or_404(models.IssueLink, external_id=issue_id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["issue"] = self.master_issue
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.creator = self.request.user
        obj.master_issue = self.master_issue
        obj.save()
        create_remote_comment(obj)
        obj.refresh_from_db()
        if obj.sync_status != "sync":
            messages.info(self.request, _("Your comment has been queued for creation."))
        else:
            messages.success(self.request, _("Your comment has been added."))
        return HttpResponseRedirect(obj.master_issue.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueCommentUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    model = models.IssueCommentLink
    fields = ["cached_body"]
    template_name = "helpdesk/comment_update.html"
    select_related = ["creator", "master_issue"]
    master_issue = None
    slug_field = "external_id"
    slug_url_kwarg = "cext_id"
    permission_required = "helpdesk.edit_comment"

    def dispatch(self, request, *args, **kwargs):
        issue_id = kwargs.pop("ext_id", None)
        self.master_issue = get_object_or_404(models.IssueLink, external_id=issue_id)
        if self.master_issue != self.get_object().master_issue:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save()
        update_remote_comment(obj)
        obj.refresh_from_db()
        if obj.status == "sync":
            messages.success(self.request, _("Your comment was updated."))
        else:
            messages.success(
                self.request, _("Your comment change was queued for update.")
            )
        return HttpResponseRedirect(obj.master_issue.get_absolute_url())

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])


class IssueCommentDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    model = models.IssueCommentLink
    template_name = "helpdesk/comment_delete.html"
    permission_required = "helpdesk.delete_comment"
    slug_url_kwarg = "cext_id"
    slug_field = "external_id"
    select_related = ["master_issue"]

    def dispatch(self, request, *args, **kwargs):
        issue_id = kwargs.pop("ext_id", None)
        self.master_issue = get_object_or_404(models.IssueLink, external_id=issue_id)
        if self.master_issue != self.get_object().master_issue:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.master_issue.get_absolute_url()

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        delete_remote_comment(obj)
        obj.refresh_from_db()
        if obj.status != "deleted":
            messages.success(self.request, _("Comment was queued for deletion."))
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, _("Comment was deleted."))
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.exclude(sync_status__in=["delete_err", "deleted"])
