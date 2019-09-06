from django.urls import path

from . import views

app_name = "helpdesk"
urlpatterns = [
    path("issues/", view=views.IssueListView.as_view(), name="issue-list"),
    path("issues/my/", view=views.MyIssueListView.as_view(), name="my-issue-list"),
    path("issues/create/", view=views.IssueCreateView.as_view(), name="issue-create"),
    path(
        "issues/issue/<ext_id>/",
        view=views.IssueDetailView.as_view(),
        name="issue-detail",
    ),
    path(
        "issues/issue/<ext_id>/edit/",
        view=views.IssueUpdateView.as_view(),
        name="issue-update",
    ),
    path(
        "issues/issue/<ext_id>/subscribe/",
        view=views.IssueSubscribeView.as_view(),
        name="issue-subscribe",
    ),
    path(
        "issues/issue/<ext_id>/unsubscribe/",
        view=views.IssueUnsubscribeView.as_view(),
        name="issue-unsubscribe",
    ),
    path(
        "issues/issue/<ext_id>/close/",
        view=views.IssueCloseView.as_view(),
        name="issue-close",
    ),
    path(
        "issues/issue/<ext_id>/reopen/",
        view=views.IssueReopenView.as_view(),
        name="issue-reopen",
    ),
    path(
        "issues/issue/<ext_id>/delete/",
        view=views.IssueDeleteView.as_view(),
        name="issue-delete",
    ),
    path(
        "issues/issue/<ext_id>/comment/create/",
        view=views.IssueCommentCreateView.as_view(),
        name="issue-add-comment",
    ),
    path(
        "issues/issue/<ext_id>/comment/<cext_id>/edit/",
        view=views.IssueCommentUpdateView.as_view(),
        name="issue-edit-comment",
    ),
    path(
        "issues/issue/<ext_id>/comment/<cext_id>/delete/",
        view=views.IssueCommentDeleteView.as_view(),
        name="issue-delete-comment",
    ),
]
