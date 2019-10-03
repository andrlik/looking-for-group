import logging

from django.http import JsonResponse

logger = logging.getLogger("games")


class JSONResponseMixin(object):
    def render_to_json_response(self, context, **response_kwargs):
        logger.debug("Converting to JSON...")
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        logger.debug("Received a context of size {}".format(len(context.keys())))
        return context

    def render_to_response(self, context, **response_kwargs):
        logger.debug("Sending response to JSON instead of template")
        return self.render_to_json_response(context, **response_kwargs)
