from haystack import indexes

from . import models


class EditionIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField()
    text = indexes.CharField(document=True, use_template=True)
    publisher = indexes.CharField(model_attr='publisher__name', faceted=True)
    release_date = indexes.DateField(model_attr='release_date', default=None)

    def get_model(self):
        return models.GameEdition

    def prepare_title(self, object):
        return "{} ({})".format(object.game.title, object.name)


class PublisherIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='name')
    text = indexes.CharField(document=True, model_attr='name')

    def get_model(self):
        return models.GamePublisher


class GameSystemIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='name')
    text = indexes.CharField(document=True, use_template=True)
    publisher = indexes.CharField(model_attr='original_publisher__name', faceted=True)
    release_date = indexes.DateField(model_attr='publication_date', default=None)

    def get_model(self):
        return models.GameSystem


class ModuleIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='title')
    text = indexes.CharField(document=True, use_template=True)
    publisher = indexes.CharField(model_attr='publisher__name', faceted=True)
    release_date = indexes.DateField(model_attr='publication_date', default=None)
    game_edition = indexes.CharField(model_attr='parent_game_edition', faceted=True)
    result_type = indexes.CharField(faceted=True)

    def get_model(self):
        return models.PublishedModule

    def prepare_game_edition(self, obj):
        return "{} ({})".format(obj.parent_game_edition.game.title, obj.parent_game_edition.name)

