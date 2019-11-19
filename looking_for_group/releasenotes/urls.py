from django.urls import path

from . import views

app_name = "releasenotes"

urlpatterns = [
    path("as-json/", views.ReleaseNotesJSONView.as_view(), name="note-list-json"),
    path("", views.ReleaseNotesView.as_view(), name="note-list"),
]
