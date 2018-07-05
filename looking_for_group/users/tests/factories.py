import factory
import factory.django
from django.db.models.signals import pre_save, post_save


@factory.django.mute_signals(pre_save, post_save)
class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password")

    class Meta:
        model = "users.User"
        django_get_or_create = ("username",)
