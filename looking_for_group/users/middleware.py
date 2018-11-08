import pytz

from django.utils import timezone


class TimezoneSessionMiddleware:
    """
    Checks for a timezone in the session and activates it if needed.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.session.get('django_timezone')
        if not tzname and request.user.is_authenticated:
            tzname = request.user.timezone
        if tzname and tzname in pytz.common_timezones:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()

        response = self.get_response(request)

        return response
