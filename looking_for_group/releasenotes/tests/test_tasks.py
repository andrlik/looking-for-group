import pytest

from .. import tasks
from ..models import ReleaseNote

pytestmark = pytest.mark.django_db(transaction=True)


def test_update_task(rn_testdata):
    initial_count = ReleaseNote.objects.count()
    assert initial_count == 52
    tasks.check_if_release_note_update_needed(
        override_file="looking_for_group/releasenotes/tests/test_changelog_updated.rst"
    )
    assert ReleaseNote.objects.count() - initial_count == 1
