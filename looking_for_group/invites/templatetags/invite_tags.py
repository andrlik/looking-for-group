from django.contrib.contenttypes.models import ContentType
from django.template import Library
from django.utils import timezone

from ..models import Invite

register = Library()


@register.simple_tag()
def get_active_invites_for_object(obj):
    invite_root = Invite.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.id
    )
    invite_root.filter(status="pending", expires_at__lte=timezone.now()).update(
        status="expired"
    )  # Set any past due invites to expired.
    return invite_root.filter(status="pending", expires_at__gt=timezone.now())


@register.simple_tag()
def get_active_invites_for_object_by_creator(obj, user):
    return get_active_invites_for_object(obj).filter(creator=user)


@register.simple_tag()
def get_expired_invites_for_object(obj):
    invite_root = Invite.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.id
    )
    invite_root.filter(status="pending", expires_at__lte=timezone.now()).update(
        status="expired"
    )
    return invite_root.filter(status="expired")


@register.simple_tag()
def get_expired_invites_for_object_by_creator(obj, user):
    return get_expired_invites_for_object(obj).filter(creator=user)


@register.simple_tag()
def get_accepted_invites_for_object(obj):
    invite_root = Invite.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.id
    )
    invite_root.filter(status="pending", expires_at__lte=timezone.now()).update(
        status="expired"
    )
    return invite_root.filter(status="accepted")


@register.simple_tag()
def get_accepted_invites_for_object_by_creator(obj, user):
    return get_accepted_invites_for_object(obj).filter(creator=user)
