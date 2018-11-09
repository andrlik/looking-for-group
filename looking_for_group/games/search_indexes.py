from haystack import indexes

from . import models


class GamePostingIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Index for a gameposting.
    """
    text = indexes.CharField(document=True, use_template=True)
    gm = indexes.CharField()
    game_edition = indexes.CharField(model_attr='published_game')
    game_system = indexes.CharField(model_attr='game_system')
    start_time = indexes.DateTimeField(model_attr='start_time')
    end_date = indexes.DateTimeField(model_attr='end_date')
    published_module = indexes.CharField(model_attr='published_module')
    status = indexes.CharField(model_attr='status')
    communities = indexes.CharField(model_attr='communities')

    def get_model(self):
        return models.GamePosting

    def prepare_gm(self, object):
        return "{}".format(object.gm)

    def prepare_game_edition(self, object):
        return "{} ({})".format(object.published_game.game.title, object.published_game.name)

    def prepare_game_system(self, object):
        return "{}".format(object.game_system.name)

    def prepare_published_module(self, object):
        return "{}".format(object.published_module.title)

    def prepare_communities(self, object):
        if object.communities.count() > 0:
            community_name_list = [comm.name for comm in object.communities.all()]
            return ", ".join(community_name_list)
        return ""

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(privacy_level='public').exclude(status__in=['closed', 'cancel'])
