from django.urls import path

from . import views

app_name = 'invites'


urlpatterns = [
    path('create/<int:content_type>/<slug:slug>/', view=views.CreateInvite.as_view(), name='invite_create'),
    path('invite/<slug:invite>/delete/', view=views.InviteDeleteView.as_view(), name="invite_delete"),
    path('invite/<slug:invite>/accept/', view=views.InviteAcceptView.as_view(), name='invite_accept'),
]
