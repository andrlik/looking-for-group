from django.urls import path

from . import views

app_name = "adminutils"

urlpatterns = [
    path("email/", view=views.SendEmailToUsers.as_view(), name='email'),
    path("notify/", view=views.CreateMassNotification.as_view(), name='notification'),
]
