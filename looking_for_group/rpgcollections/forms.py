from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from ..game_catalog import models as catalog_models
from ..gamer_profiles.forms import SwitchInput
from . import models
from .utils import get_distinct_editions, get_distinct_games, get_distinct_publishers, get_distinct_systems

DUMMY_CHOICES = [("", "")]

BOOK_CHOICES = [
    ("sourcebook", _("Sourcebook")),
    ("system", _("Game system reference")),
    ("module", _("Published module/adventure")),
]

COPY_TYPES = [("print", _("Print")), ("pdf", _("PDF/Ebook"))]


class BookForm(forms.ModelForm):
    """
    For for editing a book in a collection.
    """

    def clean(self):
        cleaned_data = super().clean()
        in_print = cleaned_data.get("in_print")
        in_pdf = cleaned_data.get("in_pdf")

        if not in_print and not in_pdf:
            raise forms.ValidationError(
                _("You must select one or both for Print or PDF.")
            )

    class Meta:
        model = models.Book
        fields = ["object_id", "in_print", "in_pdf"]
        widgets = {
            "object_id": forms.HiddenInput,
            "in_print": SwitchInput,
            "in_pdf": SwitchInput,
        }


def get_game_choices(library):
    games = get_distinct_games(library)
    return [("", "")] + [(g.pk, "{}".format(g.title)) for g in games]


def get_edition_choices(library):
    editions = get_distinct_editions(library)
    return [("", "")] + [
        (e.pk, "{} ({})".format(e.game.title, e.name)) for e in editions
    ]


def get_system_choices(library):
    systems = get_distinct_systems(library)
    return [("", "")] + [(s.pk, s.name) for s in systems]


def get_publisher_choices(library):
    publishers = get_distinct_publishers(library)
    return [("", "")] + [(p.pk, p.name) for p in publishers]


class CollectionFilterForm(forms.Form):
    """
    For used for filtering given collections by certain values.
    Needs to dynamically set the values based on a given game library.
    """

    filter_present = forms.HiddenInput()
    book_type = forms.ChoiceField(
        choices=[("", "")] + BOOK_CHOICES, initial="", required=False
    )
    game = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    edition = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    system = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    publisher = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    copy_type = forms.ChoiceField(
        choices=[("", "")] + COPY_TYPES, initial="", required=False
    )

    def __init__(self, *args, **kwargs):
        """
        Do some black magic to set up the form.
        """
        library = kwargs.pop("library", None)
        if not library:
            raise KeyError(
                _("You must instantiate instances of this form with a game library.")
            )
        super().__init__(*args, **kwargs)
        self.fields["filter_present"] = 1
        self.fields["game"].choices = get_game_choices(library)
        self.fields["edition"].choices = get_edition_choices(library)
        self.fields["system"].choices = get_system_choices(library)
        self.fields["publisher"].choices = get_publisher_choices(library)
