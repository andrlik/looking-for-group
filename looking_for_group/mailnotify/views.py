from braces.views import SelectRelatedMixin
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from postman.models import Message
from rules.contrib.views import PermissionRequiredMixin

from . import models

# Create your views here.


class ReportCreate(LoginRequiredMixin, generic.CreateView):
    """
    Allows an end user to file a report about an offending message.
    """

    model = models.MessageReport
    template_name = "postman/report_create.html"
    fields = ["report_type", "details"]

    def get_success_url(self):
        get_dict = self.request.GET.copy()
        if "next" in get_dict.keys():
            return get_dict["next"]
        return reverse_lazy("postman:inbox")

    def dispatch(self, request, *args, **kwargs):
        message_id = kwargs.pop("message", None)
        self.offending_message = get_object_or_404(Message, pk=message_id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["message"] = self.offending_message
        context["offender"] = self.offending_message.sender
        return context

    def form_valid(self, form):
        report = form.save(commit=False)
        report.message = self.offending_message
        report.plaintiff = self.offending_message.sender
        report.status = "pending"
        report.reporter = self.request.user
        messages.success(
            self.request,
            _(
                "You have successfully filed a {} report for this message. You will be automatically notified as we review your complaint.".format(
                    report.report_type
                )
            ),
        )
        report.save()
        return HttpResponseRedirect(self.get_success_url())


class ReportDetail(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.DetailView
):
    """
    Detail view for a report. Only accessed by an administrator or the one who created the report.
    """

    model = models.MessageReport
    template_name = "postman/report_detail.html"
    context_object_name = "report"
    select_related = ["reporter", "plaintiff", "message"]
    slug_url_kwarg = "report"
    permission_required = "postman.report_view"


class ReportUpdate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.UpdateView,
):
    """
    A view for the administrator to update the report status.
    """

    model = models.MessageReport
    template_name = "postman/report_update.html"
    context_object_name = "report"
    slug_url_kwarg = "report"
    fields = ["status", "admin_response"]
    select_related = ["reporter", "plaintiff", "message"]
    permission_required = "postman.report_update"

    def get_success_url(self):
        messages.success(self.request, _("Report successfully updated."))
        return self.object.get_absolute_url()


class ReportWithdraw(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    A view for the user to delete a report they wish to withdraw.
    """

    model = models.MessageReport
    template_name = "postman/report_delete.html"
    context_object_name = "report"
    slug_url_kwarg = "report"
    select_related = ["reporter", "plaintiff", "message"]
    permission_required = "postman.report_delete"

    def get_success_url(self):
        messages.success(self.request, _("Report successfully withdrawn."))
        return reverse_lazy("postman:inbox")


class ReportList(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.ListView
):
    """
    A view for administrators to review complaints
    """

    model = models.MessageReport
    template_name = "postman/report_list.html"
    context_object_name = "report_list"
    select_related = ["reporter", "plaintiff", "message"]
    permission_required = "postman.view_report_list"
    paginate_by = 25
    paginate_orphans = 3
    ordering = ["-created"]

    def get_queryset(self):
        return self.model.objects.exclude(status="done")


class ReportWarnPlaintiff(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    A view that generates a warning for the plaintiff.
    """

    model = models.MessageReport
    permission_required = "postman.warn_plaintiff"
    slug_url_kwarg = "report"
    fields = ["slug"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        report = self.get_object()
        if report.slug == form.cleaned_data["slug"]:
            report.warn_plaintiff()
        return HttpResponseRedirect(report.get_absolute_url())


class SilencePlaintiff(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    A form for silencing a user.
    """

    model = models.SilencedUser
    template_name = "postman/silence_create.html"
    fields = ["ending"]
    permission_required = "postman.can_silence"

    def dispatch(self, request, *args, **kwargs):
        report_slug = kwargs.pop("report", None)
        self.report = get_object_or_404(models.MessageReport, slug=report_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["ending"].widget = forms.widgets.DateTimeInput(
            attrs={"class": "dtp"}, format="%Y-%m-%d %H:%M"
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.report
        return context

    def form_valid(self, form):
        silence = form.save(commit=False)
        self.report.silence_plaintiff(end_date=silence.ending)
        return HttpResponseRedirect(self.report.get_absolute_url())


class SilenceList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    """
    List of silenced users.
    """

    model = models.SilencedUser
    template_name = "postman/silence_list.html"
    context_object_name = "silence_list"
    paginate_by = 25
    paginate_orphans = 3
    ordering = ["-ending"]

    permission_required = "postman.view_silenced"


class SilenceDelete(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.DeleteView
):
    """
    A view for an admin to remove a silenced condition.
    """

    model = models.SilencedUser
    template_name = "postman/silence_delete.html"
    context_object_name = "silence"
    permission_required = "postman.silence_delete"
    pk_url_kwarg = "silence"


class SilenceDetailview(
    LoginRequiredMixin, PermissionRequiredMixin, SelectRelatedMixin, generic.DetailView
):
    """
    Detail view for a silenced user.
    """

    model = models.SilencedUser
    template_name = "postman/silence_detail.html"
    context_object_name = "silence"
    permission_required = "postman.view_silenced"
    select_related = [
        "related_report",
        "user",
        "related_report__message",
        "related_report__reporter",
    ]
