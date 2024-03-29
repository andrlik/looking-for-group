"""
If the default usage of the views suits you, simply use a line like
this one in your root URLconf to set up the default URLs::

    (r'^messages/', include('postman.urls', namespace='postman', app_name='postman')),

Otherwise you may customize the behavior by passing extra parameters.

Recipients Max
--------------
Views supporting the parameter are: ``WriteView``, ``ReplyView``.
Example::
    ...View.as_view(max=3), name='write'),
See also the ``POSTMAN_DISALLOW_MULTIRECIPIENTS`` setting

User filter
-----------
Views supporting a user filter are: ``WriteView``, ``ReplyView``.
Example::
    def my_user_filter(user):
        if user.get_profile().is_absent:
            return "is away"
        return None
    ...
    ...View.as_view(user_filter=my_user_filter), name='write'),

function interface:
In: a User instance
Out: None, False, '', 'a reason', or ValidationError

Exchange filter
---------------
Views supporting an exchange filter are: ``WriteView``, ``ReplyView``.
Example::
    def my_exchange_filter(sender, recipient, recipients_list):
        if recipient.relationships.exists(sender, RelationshipStatus.objects.blocking()):
            return "has blacklisted you"
        return None
    ...
    ...View.as_view(exchange_filter=my_exchange_filter), name='write'),

function interface:
In:
    ``sender``: a User instance
    ``recipient``: a User instance
    ``recipients_list``: the full list of recipients or None
Out: None, False, '', 'a reason', or ValidationError

Auto-complete field
-------------------
Views supporting an auto-complete parameter are: ``WriteView``, ``ReplyView``.
Examples::
    ...View.as_view(autocomplete_channels=(None,'anonymous_ac')), name='write'),
    ...View.as_view(autocomplete_channels='write_ac'), name='write'),
    ...View.as_view(autocomplete_channel='reply_ac'), name='reply'),

Auto moderators
---------------
Views supporting an ``auto-moderators`` parameter are: ``WriteView``, ``ReplyView``.
Example::
    def mod1(message):
        # ...
        return None
    def mod2(message):
        # ...
        return None
    mod2.default_reason = 'mod2 default reason'
    ...
    ...View.as_view(auto_moderators=(mod1, mod2)), name='write'),
    ...View.as_view(auto_moderators=mod1), name='reply'),

function interface:
In: ``message``: a Message instance
Out: rating or (rating, "reason")
    with reting: None, 0 or False, 100 or True, 1..99

Others
------
Refer to documentation.
    ...View.as_view(form_classes=(MyCustomWriteForm, MyCustomAnonymousWriteForm)), name='write'),
    ...View.as_view(form_class=MyCustomFullReplyForm), name='reply'),
    ...View.as_view(form_class=MyCustomQuickReplyForm), name='view'),
    ...View.as_view(template_name='my_custom_view.html'), name='view'),
    ...View.as_view(success_url='postman:inbox'), name='reply'),
    ...View.as_view(formatters=(format_subject, format_body)), name='reply'),
    ...View.as_view(formatters=(format_subject, format_body)), name='view'),

"""
from __future__ import unicode_literals

from django import VERSION
from django.conf import settings
from django.conf.urls import url
from django.urls import path
from django.views.generic.base import RedirectView
from postman.views import (
    ArchivesView,
    ArchiveView,
    ConversationView,
    DeleteView,
    InboxView,
    MarkReadView,
    MarkUnreadView,
    MessageView,
    ReplyView,
    SentView,
    TrashView,
    UndeleteView,
    WriteView
)

from . import views
from .rules import user_exchange_filter

if VERSION < (1, 10):
    from django.core.urlresolvers import reverse_lazy
else:
    from django.urls import reverse_lazy
if getattr(settings, "POSTMAN_I18N_URLS", False):
    from django.utils.translation import pgettext_lazy
else:

    def pgettext_lazy(c, m):
        return m


app_name = "postman"

urlpatterns = [
    # Translators: keep consistency of the <option> parameter with the translation for 'm'
    url(
        pgettext_lazy("postman_url", r"^inbox/(?:(?P<option>m)/)?$"),
        InboxView.as_view(),
        name="inbox",
    ),
    # Translators: keep consistency of the <option> parameter with the translation for 'm'
    url(
        pgettext_lazy("postman_url", r"^sent/(?:(?P<option>m)/)?$"),
        SentView.as_view(),
        name="sent",
    ),
    # Translators: keep consistency of the <option> parameter with the translation for 'm'
    url(
        pgettext_lazy("postman_url", r"^archives/(?:(?P<option>m)/)?$"),
        ArchivesView.as_view(),
        name="archives",
    ),
    # Translators: keep consistency of the <option> parameter with the translation for 'm'
    url(
        pgettext_lazy("postman_url", r"^trash/(?:(?P<option>m)/)?$"),
        TrashView.as_view(),
        name="trash",
    ),
    url(
        pgettext_lazy("postman_url", r"^write/(?:(?P<recipients>[^/#]+)/)?$"),
        WriteView.as_view(exchange_filter=user_exchange_filter),
        name="write",
    ),
    url(
        pgettext_lazy("postman_url", r"^reply/(?P<message_id>[\d]+)/$"),
        ReplyView.as_view(exchange_filter=user_exchange_filter),
        name="reply",
    ),
    url(
        pgettext_lazy("postman_url", r"^view/(?P<message_id>[\d]+)/$"),
        MessageView.as_view(),
        name="view",
    ),
    # Translators: 't' stands for 'thread'
    url(
        pgettext_lazy("postman_url", r"^view/t/(?P<thread_id>[\d]+)/$"),
        ConversationView.as_view(),
        name="view_conversation",
    ),
    url(
        pgettext_lazy("postman_url", r"^archive/$"),
        ArchiveView.as_view(),
        name="archive",
    ),
    url(
        pgettext_lazy("postman_url", r"^delete/$"), DeleteView.as_view(), name="delete"
    ),
    url(
        pgettext_lazy("postman_url", r"^undelete/$"),
        UndeleteView.as_view(),
        name="undelete",
    ),
    url(
        pgettext_lazy("postman_url", r"^mark-read/$"),
        MarkReadView.as_view(),
        name="mark-read",
    ),
    url(
        pgettext_lazy("postman_url", r"^mark-unread/$"),
        MarkUnreadView.as_view(),
        name="mark-unread",
    ),
    path(
        "reports/create/<int:message>/",
        view=views.ReportCreate.as_view(),
        name="report_create",
    ),
    path(
        "reports/<slug:report>/",
        view=views.ReportDetail.as_view(),
        name="report_detail",
    ),
    path(
        "reports/<slug:report>/edit/",
        view=views.ReportUpdate.as_view(),
        name="report_update",
    ),
    path(
        "reports/<slug:report>/withdraw/",
        view=views.ReportWithdraw.as_view(),
        name="report_withdraw",
    ),
    path("reports/", view=views.ReportList.as_view(), name="report_list"),
    path(
        "reports/<slug:report>/warn/",
        view=views.ReportWarnPlaintiff.as_view(),
        name="warn_plaintiff",
    ),
    path(
        "silenced/create/<slug:report>/",
        view=views.SilencePlaintiff.as_view(),
        name="silence_plaintiff",
    ),
    path(
        "silenced/<uuid:silence>/",
        view=views.SilenceDetailview.as_view(),
        name="silence_detail",
    ),
    path(
        "silenced/<uuid:silence>/delete/",
        view=views.SilenceDelete.as_view(),
        name="silence_delete",
    ),
    path("silenced/", view=views.SilenceList.as_view(), name="silence_list"),
    url(r"^$", RedirectView.as_view(url=reverse_lazy("postman:inbox"), permanent=True)),
]
