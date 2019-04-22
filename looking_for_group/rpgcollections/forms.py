from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from ..game_catalog import models as catalog_models
from ..gamer_profiles.forms import SwitchInput
from . import models

DUMMY_CHOICES = [("", "")]

BOOK_CHOICES = [
    ("sourcebook", _("Sourcebook")),
    ("system", _("Game system reference")),
    ("module", _("Published module/adventure")),
]

COPY_TYPES = [("", ""), ("print", _("Print")), ("pdf", _("PDF/Ebook"))]


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
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sourcebook_games = catalog_models.PublishedGame.objects.filter(
        id__in=[
            sb.edition.game.pk
            for sb in catalog_models.SourceBook.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sb_ct
                    )
                ]
            ).select_related("edition", "edition__game")
        ]
    ).order_by("title")
    module_games = catalog_models.PublishedGame.objects.filter(
        id__in=[
            md.parent_game_edition.game.pk
            for md in catalog_models.PublishedModule.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=md_ct
                    )
                ]
            ).select_related("parent_game_edition", "parent_game_edition__game")
        ]
    ).order_by("title")
    games = sourcebook_games.union(module_games).order_by("title")
    return [("", "")] + [(g.pk, "{}".format(g.title)) for g in games]


def get_edition_choices(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sourcebook_editions = (
        catalog_models.GameEdition.objects.filter(
            id__in=[
                sb.edition.pk
                for sb in catalog_models.SourceBook.objects.filter(
                    id__in=[
                        b.content_object.pk
                        for b in models.Book.objects.filter(
                            library=library, content_type=sb_ct
                        )
                    ]
                ).select_related("edition")
            ]
        )
        .select_related("game")
        .order_by("game__title", "release_date")
    )
    module_editions = (
        catalog_models.GameEdition.objects.filter(
            id__in=[
                md.parent_game_edition.pk
                for md in catalog_models.PublishedModule.objects.filter(
                    id__in=[
                        b.content_object.pk
                        for b in models.Book.objects.filter(
                            library=library, content_type=md_ct
                        )
                    ]
                ).select_related("parent_game_edition")
            ]
        )
        .select_related("game")
        .order_by("game__title", "release_date")
    )
    editions = sourcebook_editions.union(module_editions).order_by(
        "game__title", "release_date"
    )
    return [("", "")] + [
        (e.pk, "{} ({})".format(e.game.title, e.name)) for e in editions
    ]


def get_system_choices(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sys_ct = ContentType.objects.get_for_model(catalog_models.GameSystem)
    sourcebook_systems = catalog_models.GameSystem.objects.filter(
        id__in=[
            sb.edition.game_system.pk
            for sb in catalog_models.SourceBook.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sb_ct
                    )
                ],
                edition__game_system__notnull=True,
            ).select_related("edition", "edition__game_system")
        ]
    ).order_by("name", "publication_date")
    module_systems = catalog_models.GameSystem.objects.filter(
        id__in=[
            md.parent_game_edition.game_system.pk
            for md in catalog_models.PublishedModule.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=md_ct
                    )
                ],
                parent_game_edition__game_system__notnull=True,
            ).select_related("parent_game_edition", "parent_game_edition__game_system")
        ]
    ).order_by("name", "publication_date")
    system_systems = catalog_models.GameSystem.objects.filter(
        id__in=[
            b.content_object.pk
            for b in models.Book.objects.filter(library=library, content_type=sys_ct)
        ]
    ).order_by("name", "publication_date")
    sb_and_md = sourcebook_systems.union(module_systems)
    systems = sb_and_md.union(system_systems).order_by("name", "publication_date")
    return [("", "")] + [(s.pk, s.name) for s in systems]


def get_publisher_choices(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sys_ct = ContentType.objects.get_for_model(catalog_models.GameSystem)
    sourcebook_publishers = catalog_models.GamePublisher.objects.filter(
        id__in=[
            sb.edition.publisher.pk
            for sb in catalog_models.SourceBook.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sb_ct
                    )
                ]
            ).select_related("edition", "edition__publisher")
        ]
    ).order_by("name")
    module_publishers = catalog_models.GamePublisher.objects.filter(
        id__in=[
            md.publisher.pk
            for md in catalog_models.PublishedModule.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=md_ct
                    )
                ]
            ).select_related("publisher")
        ]
    ).order_by("name")
    system_publishers = catalog_models.GamePublisher.objects.filter(
        id__in=[
            sys.original_publisher.pk
            for sys in catalog_models.GameSystem.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sys_ct
                    )
                ]
            ).select_related("original_publisher")
        ]
    ).order_by("name")
    sb_and_md = sourcebook_publishers.union(module_publishers)
    publishers = sb_and_md.union(system_publishers).order_by("name")
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
