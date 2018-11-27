from django.urls import path

from . import views

app_name = "user_preferences"

urlpatterns = [
    path("", view=views.SettingsView.as_view(), name="setting-view"),
    path("edit/", view=views.SettingsEdit.as_view(), name="setting-edit"),
    path("goodbye/", view=views.DeleteAccount.as_view(), name="account_delete"),
]
