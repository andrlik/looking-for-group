import pytest

from ...gamer_profiles.tests import factories
from ..models import ReleaseNote, ReleaseNotice
from ..utils import load_release_notes_from_file


@pytest.fixture
def release_notes_filename():
    return "looking_for_group/releasenotes/tests/test_changelog.rst"


class ReleaseNoteTestDataObject(object):
    """
    Class containing release note testdata.
    """

    def __init__(self, release_notes_filename, *args, **kwargs):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gn1, created = ReleaseNotice.objects.get_or_create(user=self.gamer1.user)
        self.gn2, created = ReleaseNotice.objects.get_or_create(user=self.gamer2.user)
        load_release_notes_from_file(release_notes_filename)
        self.release_notes = ReleaseNote.objects.all().order_by("-release_date")
        self.gn1.latest_version_shown = self.release_notes[0]
        self.gn1.save()
        self.gn2.latest_version_shown = self.release_notes[3]
        self.gn2.save()


@pytest.fixture
def rn_testdata(release_notes_filename):
    yield ReleaseNoteTestDataObject(release_notes_filename)
