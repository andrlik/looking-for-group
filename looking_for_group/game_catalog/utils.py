import logging
from uuid import uuid4
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TaggedItemBase


logger = logging.getLogger('util_models')


class UUIDTaggedItem(GenericUUIDTaggedItemBase, TaggedItemBase):
    """
    UUID compatible tagged item management model.
    """

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class AbstractUUIDModel(models.Model):
    '''
    An abstract model that handles the default UUID primary key data.
    '''
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)

    class Meta:
        abstract = True


class AbstractTaggedLinkedModel(models.Model):
    """
    Helper functions for collecting tags from linked objects.
    """

    tags = TaggableManager(through=UUIDTaggedItem)

    @classmethod
    def get_all_parent_objects(cls):
        """
        Fetch all releated objects to this for tag examination.
        """
        return [
            f for f in cls._meta.get_fields()
            if f.many_to_one and not f.auto_created and f.related_model
        ]

    @cached_property
    def inherited_tags(self):
        return self.get_inherited_tags()

    def get_inherited_tags(self):
        """
        Fetches tags for itself and all other linked model instances.
        """
        related_objects = self.get_all_parent_objects()
        logger.debug("Found {} related objects.".format(len(related_objects)))
        parent_tags = None
        for field in related_objects:
            obj = getattr(self, field.name)
            logger.debug("Parsing instance of class {}".format(obj.__class__))
            for prop in ["tags", "inherited_tags"]:
                if hasattr(obj, prop):
                    logger.debug("Found property: {}".format(prop))
                    tags_qs = getattr(obj, prop)
                    if tags_qs:
                        logger.debug("Tags found")
                        if not parent_tags:
                            logger.debug('First tag queryset')
                            parent_tags = tags_qs.all()
                        else:
                            logger.debug('Merging tags into existing queryset')
                            parent_tags = parent_tags.union(tags_qs.all())
        return parent_tags

    @cached_property
    def inherited_tag_names(self):
        '''
        Fetches just the tag names.
        '''
        tag_list = self.get_inherited_tags()
        tag_names = []
        if tag_list:
            for tag in tag_list:
                tag_names.append(tag.name)
        return tag_names

    class Meta:
        abstract = True
