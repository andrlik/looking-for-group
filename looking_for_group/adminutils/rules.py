import rules


@rules.predicate
def is_admin(user, obj=None):
    return user.is_superuser


@rules.predicate
def is_staff(user, obj=None):
    return user.is_staff


rules.add_perm("adminutils.send_notification", is_admin)
rules.add_perm("adminutils.send_email", is_admin)
rules.add_perm("adminutils.create_oauth2_app", is_staff)
