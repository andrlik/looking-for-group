import pytest
from notifications.models import Notification
from notifications.signals import notify

from .. import tasks
from ..models import Preferences

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def up_task_testdata(game_testdata):
    Preferences.objects.create(gamer=game_testdata.gamer1)
    Preferences.objects.create(gamer=game_testdata.gamer2)
    Preferences.objects.create(gamer=game_testdata.gamer3)
    notify.send(
        game_testdata.gamer2,
        recipient=game_testdata.gamer1.user,
        verb="sent you a friend request.",
    )
    notify.send(
        game_testdata.gamer2,
        recipient=game_testdata.gamer1.user,
        verb="banned community user",
        action_object=game_testdata.gamer3,
        target=game_testdata.comm1,
    )
    notify.send(
        game_testdata.gamer1,
        recipient=game_testdata.gamer3.user,
        verb="sent you a friend request.",
    )
    notify.send(
        game_testdata.gamer3,
        recipient=game_testdata.gamer2.user,
        verb="sent you a friend request.",
    )
    game_testdata.gamer1.preferences.notification_digest = True
    game_testdata.gamer1.preferences.save()
    game_testdata.gamer3.preferences.notification_digest = True
    game_testdata.gamer3.preferences.save()
    return game_testdata


def test_collect_users(up_task_testdata):
    user_list = tasks.get_users_with_digests()
    assert len(user_list) == 2


def test_generate_single_email_body(up_task_testdata):
    user = up_task_testdata.gamer1.user
    notifications = Notification.objects.filter(
        recipient=user, unread=True, emailed=False
    )
    assert notifications.count() == 3
    txt_body, html_body = tasks.form_email_body(user, notifications)


def test_email_sending(up_task_testdata):
    user = up_task_testdata.gamer1.user
    notifications = Notification.objects.filter(
        recipient=user, unread=True, emailed=False
    )
    tasks.send_digest_email(user, notifications)


def test_full_process(up_task_testdata):
    tasks.perform_daily_digests()
