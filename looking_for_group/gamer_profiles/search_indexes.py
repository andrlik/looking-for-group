from haystack import indexes

from . import models


class CommunityIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Index for communities.
    """
    text = indexes.CharField(document=True, use_template=True)
    owner = indexes.CharField(model_attr="owner")
    member_count = indexes.IntegerField(model_attr='member_count')
    private = indexes.BooleanField(model_attr='private')
    discord = indexes.BooleanField(model_attr='linked_with_discord')

    def get_model(self):
        return models.GamerCommunity

    def prepare_owner(self, object):
        return "{}".format(object.owner)
