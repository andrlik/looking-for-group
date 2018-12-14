from django.template import Library
from django.utils import timezone

register = Library()


@register.simple_tag()
def get_silence_end(user):
    if user.silence_terms.filter(ending__isnull=True).count() > 0:
        return "eternity"
    active_silences = user.silence_terms.filter(ending__gte=timezone.now())
    if active_silences.count() > 0:
        return active_silences.latest('ending')
    return None
