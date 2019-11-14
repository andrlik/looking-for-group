from collections import OrderedDict
from datetime import datetime

import semantic_version
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from docutils import utils as dutils
from docutils.parsers import rst


def get_latest_rn_version():
    """
    Parse the release notes and fetch the latest semantic version in them.

    :return: An instance of :class:`semantic_version.Version` or None
    """
    return None


def load_release_notes_from_file(filename=None):
    if not filename:
        filename = settings.RELEASE_NOTES_FILENAME
        if not filename:
            raise ImproperlyConfigured(
                "You need to specify a release notes filename in RELEASE_NOTES_FILENAME or provide said filename to this method."
            )
        parser = rst.Parser()
        document = dutils.new_document("changelog")
        version_dict = OrderedDict()
        with open(filename) as f:
            parser.parse(f, document)
        for section in document.children[1][2:]:
            title_text_list = section[0][0].split(" ")
            version_str = title_text_list[0]
            date_released = datetime.strptime(title_text_list[-1], "(%Y-%m-%d)")
            version_dict[version_str] = {
                "date": date_released,
                "version_obj": semantic_version.Version(version_str),
                "details": section[1],
            }
