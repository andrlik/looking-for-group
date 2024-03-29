import notifications.urls
from ajax_select import urls as ajax_select_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from keybase_proofs.views import KeybaseProofView

from looking_for_group.gamer_profiles.views import KeybaseProofListOverrideView, KeybaseProofProfileOverridenView
from looking_for_group.user_preferences.views import (
    Dashboard,
    HomeView,
    PrivacyView,
    SiteCatalogStatsView,
    SiteSocialStatsView,
    TermsView
)

# from star_ratings import urls as rating_urls
from . import api_routers, rating_url_override


def trigger_error(request):
    divide_by_zero = 1 / 0  # noqa


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", view=Dashboard.as_view(), name="dashboard"),
    path(
        "dashboard/stats/social/",
        SiteSocialStatsView.as_view(),
        name="site-social-stats",
    ),
    path(
        "keybase-proofs/api/<slug:username>/",
        KeybaseProofListOverrideView.as_view(),
        name="keybase-proofs-api",
    ),
    path(
        "keybase-proofs/profile/<slug:username>/",
        KeybaseProofProfileOverridenView.as_view(),
        name="keybase-profile",
    ),
    path(
        "keybase-proofs/new-proof",  # Here we don't have the trailing slash because of how the app works.
        KeybaseProofView.as_view(),
        name="keybase-new-proof",
    ),
    path("releasenotes/", include("looking_for_group.releasenotes.urls")),
    path(
        "dashboard/stats/catalog/",
        SiteCatalogStatsView.as_view(),
        name="site-catalog-stats",
    ),
    path("sentry-debug", view=trigger_error),
    path("health/", view=TemplateView.as_view(template_name="health.html")),
    path("privacy/", view=PrivacyView.as_view(), name="privacy"),
    path("terms/", view=TermsView.as_view(), name="terms"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    path("{}doc/".format(settings.ADMIN_URL), include("django.contrib.admindocs.urls")),
    # User management
    path("users/", include("looking_for_group.users.urls", namespace="users")),
    path("accounts/", include("allauth_2fa.urls")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("catalog/", include("looking_for_group.game_catalog.urls")),
    path("collections/", include("looking_for_group.rpgcollections.urls")),
    path(
        "inbox/notifications/", include(notifications.urls, namespace="notifications")
    ),
    path("social/", include("looking_for_group.gamer_profiles.urls")),
    path("social/avatar/", include("avatar.urls")),
    path("games/", include("looking_for_group.games.urls")),
    path("invites/", include("looking_for_group.invites.urls")),
    path("search/", include("haystack.urls")),
    path("ratings/", include(rating_url_override)),
    path("settings/", include("looking_for_group.user_preferences.urls")),
    path("utils/", include("looking_for_group.adminutils.urls")),
    # path("ratings/", include(rating_urls, namespace="ratings")),
    path("api-auth/", include("rest_framework.urls")),
    path("api/", include(api_routers)),
    path("o/", include("oauth2_provider.urls")),
    path(
        "messages/", include("looking_for_group.mailnotify.urls", namespace="postman")
    ),
    path("ajax_select/", include(ajax_select_urls)),
    path("helpdesk/", include("looking_for_group.helpdesk.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
