from django.dispatch import Signal

invite_accepted = Signal(providing_args=['invite', 'accepted_by'])  # pragma: no cover
