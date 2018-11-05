import rules
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist


@rules.predicate
def is_rpgeditor(user, obj):
    if user.is_authenticated:
        if user.is_superuser:
            return True
        try:
            group = Group.objects.get(name="rpgeditors")
            if group in user.groups.all():
                return True
        except ObjectDoesNotExist:
            pass  # We'll just return False at the end.
    return False


rules.add_perm("catalog.can_edit", is_rpgeditor)
