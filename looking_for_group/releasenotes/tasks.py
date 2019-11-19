import semantic_version

import looking_for_group

from .models import ReleaseNote
from .utils import load_release_notes_from_file


def check_if_release_note_update_needed(override_file=None):
    curr_version = semantic_version.Version(str(looking_for_group.__version__))
    latest_note = ReleaseNote.objects.latest("release_date", "modified")
    if curr_version > latest_note.version:
        load_release_notes_from_file(filename=override_file)
