import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models.signals import post_save
from django.urls import reverse
from factory.django import mute_signals

from ...game_catalog.tests.test_accessibility import BaseAccessibilityTest
from .. import models
from ..tests.test_views import AbstractGameSessionTest


@pytest.mark.accessibility
@pytest.mark.nondestructive
class GameViewAccessibilityTestCase(
    BaseAccessibilityTest, AbstractGameSessionTest, StaticLiveServerTestCase
):
    """
    Run accessibility tests for game views.
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.gamer4.user.username
        with mute_signals(post_save):
            self.log = models.AdventureLog.objects.create(
                session=self.session2,
                initial_author=self.gamer4,
                title="Mystery in the deep",
                body="Our heroes encountered a lot of **stuff**",
            )
            self.player1 = models.Player.objects.create(
                game=self.gp1, gamer=self.gamer1
            )
            self.character1 = models.Character.objects.create(
                player=self.player1,
                name="Magic Brian",
                game=self.gp2,
                description="Elven wizard",
            )
        self.login_browser()

    def test_game_list(self):
        axe, violations = self.get_axe_violations(reverse("games:game_list"))
        assert len(violations) == 0, axe.report(violations)

    def test_my_game_list(self):
        axe, violations = self.get_axe_violations(reverse("games:my_game_list"))
        assert len(violations) == 0, axe.report(violations)

    def test_calendar_view(self):
        axe, violations = self.get_axe_violations(
            reverse("games:calendar_detail", kwargs={"gamer": self.gamer1.username})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_create(self):
        axe, violations = self.get_axe_violations(reverse("games:game_create"))
        assert len(violations) == 0, axe.report(violations)

    def test_game_detail(self):
        axe, violations = self.get_axe_violations(
            reverse("games:game_detail", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_edit(self):
        axe, violations = self.get_axe_violations(
            reverse("games:game_edit", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_delete(self):
        axe, violations = self.get_axe_violations(
            reverse("games:game_delete", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_invite_list(self):
        axe, violations = self.get_axe_violations(
            reverse("games:game_invite_list", kwargs={"slug": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_applicant_list(self):
        axe, violations = self.get_axe_violations(
            reverse("games:game_applicant_list", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_apply(self):
        axe, violations = self.get_axe_violations(
            reverse("games:game_apply", kwargs={"gameid": self.gp3.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_game_session_adhoc_create(self):
        axe, violations = self.get_axe_violations(
            reverse("games:session_adhoc_create", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_session_list(self):
        axe, violations = self.get_axe_violations(
            reverse("games:session_list", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_session_detail(self):
        axe, violations = self.get_axe_violations(
            reverse("games:session_detail", kwargs={"session": self.session1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_session_edit(self):
        axe, violations = self.get_axe_violations(
            reverse("games:session_edit", kwargs={"session": self.session1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_session_move(self):
        axe, violations = self.get_axe_violations(
            reverse("games:session_move", kwargs={"session": self.session1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_log_create(self):
        axe, violations = self.get_axe_violations(
            reverse("games:log_create", kwargs={"session": self.session1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_log_edit(self):
        axe, violations = self.get_axe_violations(
            reverse("games:log_edit", kwargs={"log": self.log.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_log_delete(self):
        axe, violations = self.get_axe_violations(
            reverse("games:log_delete", kwargs={"log": self.log.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_character_list(self):
        axe, violations = self.get_axe_violations(
            reverse("games:character_game_list", kwargs={"gameid": self.gp1.slug})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_character_detail(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "games:character_detail", kwargs={"character": self.character1.slug}
            )
        )
        assert len(violations) == 0, axe.report(violations)
