import rules
from django.contrib.contenttypes.models import ContentType


@rules.predicate
def is_invite_creator(user, invite):
    return user == invite.creator


@rules.predicate
def is_object_admin(user, invite):
    """
    Much more complicated. First we pull the content object and content type
    to dynamically create a permission name for the object. Then runs has_perm
    to check and return result.
    """
    object_type_name = invite.content_type.name
    new_permission = "{}.can_admin_invites".format(object_type_name)
    return user.has_perm(new_permission, invite.content_object)


@rules.predicate
def is_inviter(user, obj):
    object_type_name = ContentType.objects.get_for_model(obj).name
    new_permission = "{}.can_invite".format(object_type_name)
    return user.has_perm(new_permission, obj)


is_invite_deleter = is_invite_creator | is_object_admin


rules.add_perm("invite.can_delete", is_invite_deleter)
rules.add_perm("invite.can_create", is_inviter)
