from ..models import ReleaseNote
from ..utils import load_release_notes_from_file


def test_load_release_notes_empty():
    """
    Using the test filename, load the file and attempt to populate the release note table.
    There should be exactly 50 releases within the notes, and this first run should result in all 50 being new.
    """
    assert ReleaseNote.objects.count() == 0
    all_notes, new_notes, updated_notes = load_release_notes_from_file(
        filename="looking_for_group/releasenotes/tests/test_changelog.rst"
    )
    assert ReleaseNote.objects.count() == 52
    assert all_notes == 52
    assert new_notes == all_notes
    assert updated_notes == 0
    # missing_note = ReleaseNote.objects.filter(notes_rendered__isnull=True)[0]
    # print(
    #    "{} release has no notes_rendered, with notes of {}".format(
    #        missing_note, missing_note.notes
    #    )
    # )
    assert ReleaseNote.objects.filter(notes_rendered__isnull=False).count() == all_notes
    # all_notes, new_notes, updated_notes = load_release_notes_from_file(
    #     filename="looking_for_group/releasenotes/tests/test_changelog_updated.rst"
    # )
    # assert ReleaseNote.objects.count() == 51 == all_notes
    # assert new_notes == 0
    # assert updated_notes == 2
