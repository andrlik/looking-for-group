from uuid import uuid4

from django.db import models

from ..models import AbstractTaggedLinkedModel


# Models to be used in tests.
class TestModelParent(AbstractTaggedLinkedModel, models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)

    class Meta:
        app_label = 'game_catalog'


class TestModelChild1(AbstractTaggedLinkedModel, models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    parent = models.ForeignKey(TestModelParent, on_delete=models.CASCADE)

    class Meta:
        app_label = 'game_catalog'


class TestModelMulti(AbstractTaggedLinkedModel, models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    parent = models.ForeignKey(TestModelParent, null=True, on_delete=models.CASCADE)
    parent2 = models.ForeignKey(TestModelChild1, null=True, on_delete=models.CASCADE)

    class Meta:
        app_label = 'game_catalog'
