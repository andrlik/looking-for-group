from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def stat_class_data(eval_number, positive_threshold=10, negative_threshold=0, positive_class='stats-list-positive', negative_class='stats-list-negative'):
    string_result = ' class="{}"'
    if eval_number <= negative_threshold:
        string_result = string_result.format(negative_class)
    elif eval_number > positive_threshold:
        string_result = string_result.format(positive_class)
    else:
        string_result = ""
    return mark_safe(string_result)
