from allauth_2fa.utils import user_has_valid_totp_device

from . import __version__


def app_version(request):
    """
    Retrieve app version and add to template
    context.
    """
    return {"APP_VERSION": __version__}


def has_two_factor(request):
    """
    Check if the logged in user has 2FA enabled.
    """
    if request.user and request.user.is_authenticated:
        return {"2FA_ENABLED": user_has_valid_totp_device(request.user)}
    else:
        return {"2FA_ENABLED": False}
