from django.template import Library
from django.urls import reverse

register = Library()


@register.simple_tag
def get_url_from_listmode(listmode, page=None):
    if "my" in listmode:
        url = reverse("helpdesk:my-issue-list")
    else:
        url = reverse("helpdesk:issue-list")
    if "close" in listmode or page:
        url = base_url + "?"
        variable_count = 0
        if "close" in listmode:
            url = url + "status=closed"
            variable_count += 1
        if page:
            if variable_count > 0:
                url = url + "&"
            url = url + "page={}".format(page)
    return url
