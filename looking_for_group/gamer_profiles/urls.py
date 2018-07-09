from django.urls import path

from . import views

app_name = "gamer_profiles"
urlpatterns = [
    path("communities/", view=views.CommunityListView.as_view(), name='community-list'),
    path("communities/<uuid:community>/", view=views.CommunityDetailView.as_view(), name='community-detail'),
    path("communities/<uuid:community>/apply/", view=views.CreateApplication.as_view(), name='community-apply'),
    path("communities/<uuid:community>/join/", view=views.JoinCommunity.as_view(), name='community-join'),
]
