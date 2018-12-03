from . import __version__

def app_version(request):
    """
    Retrieve app version and add to template
    context.
    """
    return {"APP_VERSION": __version__}