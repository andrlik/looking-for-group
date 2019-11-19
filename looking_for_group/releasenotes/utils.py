import logging
from collections import OrderedDict
from datetime import datetime

import docutils
import pytz
import semantic_version
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from docutils.parsers import rst
from rst_to_md.writer import Writer as MDWriter

from .models import ReleaseNote

logger = logging.getLogger("releasenotes")


def load_release_notes_from_file(filename=None):
    if not filename:
        logger.debug("No filename provided. Attempting to load from settings...")
        filename = settings.RELEASE_NOTES_FILENAME
        if not filename:
            raise ImproperlyConfigured(
                "You need to specify a release notes filename in RELEASE_NOTES_FILENAME or provide said filename to this method."
            )
        else:
            logger.debug("Found filename of {} in SETTINGS.".format(filename))
    else:
        logger.debug("Received filename override of {}".format(filename))
    parser = rst.Parser()
    docsettings = docutils.frontend.OptionParser(
        components=(rst.Parser,)
    ).get_default_values()
    document = docutils.utils.new_document("changelog", settings=docsettings)
    version_dict = OrderedDict()
    logger.debug("Attempting to open specfied file...")
    with open(filename) as f:
        parser.parse(f.read(), document)
    logger.debug("File successfully parsed into docutils tree.")
    for section in document.children[1][2:]:
        title_text_list = section[0][0].split(" ")
        version_str = title_text_list[0]
        date_released = datetime.strptime(title_text_list[-1], "(%Y-%m-%d)").replace(
            tzinfo=pytz.UTC
        )
        logger.debug("Adding version {} with notes {}".format(version_str, section[1]))
        version_dict[version_str] = {"date": date_released, "notes": section[1]}
    new_notes = 0
    updated_notes = 0
    all_notes = 0
    mdwriter = MDWriter()
    for k, v in version_dict.items():
        all_notes += 1
        node_doc = docutils.utils.new_document("soemthing", settings=docsettings)
        node_doc.append(v["notes"])
        notes_to_use = mdwriter.write(
            node_doc, docutils.io.StringOutput(encoding="utf8")
        ).decode("utf8")
        # We need to add a hack here because the mdwriter object isn't creating the sublist correctly
        # TODO: Fork and patch the rst_to_md package.
        notes_to_use = notes_to_use.replace("\n  +", "\n    +").replace(
            "\n    *", "\n        *"
        )
        logger.debug(
            "Converted {} to {} for version {}".format(v["notes"], notes_to_use, k)
        )
        date_for_record = v["date"]
        version = semantic_version.Version(k)
        release_ver, created = ReleaseNote.objects.get_or_create(
            version=version,
            defaults={"notes": notes_to_use, "release_date": date_for_record},
        )
        if created:
            logger.debug("Add a new note for version {}".format(version))
            new_notes += 1
        elif (
            release_ver.notes != str(notes_to_use)
            or release_ver.release_date != date_for_record
        ):
            logger.debug(
                "Version {} already exists, but needs to be updated...".format(version)
            )
            updated_notes += 1
            release_ver.notes = notes_to_use
            release_ver.release_date = date_for_record
            release_ver.save()
        else:
            logger.debug(
                "Version {} already exists and no changes required.".format(version)
            )
    logger.debug(
        "Evaluated {} version notes. Created {} new versions, and updated {} existing versions.".format(
            all_notes, new_notes, updated_notes
        )
    )
    return all_notes, new_notes, updated_notes
