from django import forms

from .. import models
from ..forms import SuggestedAdditionForm
from .test_views import AbstractSuggestedCorrectionAdditionTest as AbstractBaseTest


class TestAdditionForm(AbstractBaseTest):
    """
    Test for validation in suggested addition form.
    """

    def test_publisher_type(self):
        """
        Test form for publisher.
        """
        form = SuggestedAdditionForm(
            {
                "title": "New Publisher",
                "url": "https://www.google.com",
                "description": "Yo ho!",
            },
            obj_type="publisher",
        )
        for x in [
            "release_date",
            "publisher",
            "ogl_license",
            "isbn",
            "game",
            "system",
            "edition",
        ]:
            print("Checking to make sure that {} is a hidden input".format(x))
            assert isinstance(form.fields[x].widget, forms.HiddenInput)
        if not form.is_valid():
            print(form.errors.as_data())
        assert form.is_valid()

    def test_game_type(self):
        """
        Test form for game type.
        """
        form = SuggestedAdditionForm(
            {
                "title": "New game",
                "description": "A new and exciting game.",
                "release_date": "2017-01-01",
            },
            obj_type="game",
        )
        for x in ["publisher", "ogl_license", "isbn", "game", "system", "edition"]:
            print("Checking to make sure that {} is a hidden input".format(x))
            assert isinstance(form.fields[x].widget, forms.HiddenInput)
        if not form.is_valid():
            print(form.errors.as_data())
        assert form.is_valid()

    def test_edition(self):
        """
        Test edition type.
        """
        form = SuggestedAdditionForm(
            {
                "title": "3E",
                "description": "New edition!",
                "release_date": "2018-01-01",
            },
            obj_type="edition",
        )
        for x in ["ogl_license", "edition", "isbn"]:
            print("Checking to make sure that {} is a hidden input".format(x))
            assert isinstance(form.fields[x].widget, forms.HiddenInput)
        assert not form.is_valid()
        form = SuggestedAdditionForm(
            {
                "title": "3E",
                "description": "New edition!",
                "release_date": "2018-01-01",
                "game": self.numensource.pk,
            },
            obj_type="edition",
        )
        assert not form.is_valid()
        form = SuggestedAdditionForm(
            {
                "title": "3E",
                "description": "New edition!",
                "release_date": "2018-01-01",
                "game": self.numensource.pk,
                "publisher": self.mcg.pk,
            },
            obj_type="edition",
        )
        if not form.is_valid():
            print(form.errors.as_data())
        assert form.is_valid()

    def test_sourcebook_type(self):
        """
        Test form for sourcebook.
        """
        form = SuggestedAdditionForm(
            {
                "title": "Numenera Discovery",
                "description": "Version 2 of the bestselling game.",
                "release_date": "2018-07-12",
            },
            obj_type="sourcebook",
        )
        for x in ["ogl_license", "game", "system"]:
            print("Checking to make sure that {} is a hidden input".format(x))
            assert isinstance(form.fields[x].widget, forms.HiddenInput)
        assert not form.is_valid()
        form = SuggestedAdditionForm(
            {
                "title": "Numenera Discovery",
                "description": "Version 2 of the bestselling game.",
                "release_date": "2018-07-12",
                "edition": self.numen.pk,
            },
            obj_type="sourcebook",
        )
        assert not form.is_valid()
        form = form = SuggestedAdditionForm(
            {
                "title": "Numenera Discovery",
                "description": "Version 2 of the bestselling game.",
                "release_date": "2018-07-12",
                "edition": self.numen.pk,
                "publisher": self.mcg.pk,
            },
            obj_type="sourcebook",
        )
        if not form.is_valid():
            print(form.errors.as_data())
        assert form.is_valid()

    def test_system_type(self):
        """
        Test form for a system.
        """
        form = SuggestedAdditionForm(
            {
                "title": "Cypher System Revised",
                "description": "New and improved",
                "ogl_license": False,
            },
            obj_type="system",
        )
        for x in ["game", "edition", "system"]:
            print("Checking to make sure that {} is a hidden input".format(x))
            assert isinstance(form.fields[x].widget, forms.HiddenInput)
        assert not form.is_valid()
        form = SuggestedAdditionForm(
            {
                "title": "Cypher System Revised",
                "description": "New and improved",
                "ogl_license": False,
                "publisher": self.mcg.pk,
            },
            obj_type="system",
        )
        if not form.is_valid():
            print(form.errors.as_data())
        assert form.is_valid()
