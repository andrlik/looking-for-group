from .test_views import AbstractGameSessionTest


class iCalFeedTest(AbstractGameSessionTest):
    """
    Tests to ensure that ical feeds load appropriately.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:calendar_ical"

    def test_gm(self):
        with self.assertNumQueriesLessThan(250):
            self.get(self.view_name, gamer=self.gamer1.pk)
            self.response_200()

    def test_player(self):
        with self.assertNumQueriesLessThan(250):
            self.get(self.view_name, gamer=self.gamer4.pk)
            self.response_200()
