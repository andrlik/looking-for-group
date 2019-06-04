import factory
import factory.django
from allauth.account.models import EmailAddress
from django.db.models.signals import post_save, pre_save


def set_email_as_confirmed(user, email):
    email, created = EmailAddress.objects.get_or_create(user=user, email=user.email)
    email.verfied = True
    email.primary = True
    email.save()
    return email.email


class EmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailAddress
    user = None
    email = None
    verified = True
    primary = True


@factory.django.mute_signals(pre_save, post_save)
class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    display_name = factory.Sequence(lambda n: f"User {n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password")

    primary_email = factory.RelatedFactory(EmailFactory, "user", email=email)

    class Meta:
        model = "users.User"
        django_get_or_create = ("username",)
