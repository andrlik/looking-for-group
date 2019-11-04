import logging

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.shortcuts import get_object_or_404

logger = logging.getLogger("rules")


class ParentObjectAutoPermissionViewSetMixin:
    """
    Applies rules permisison checking where `list` and `add` require a permisison based on a parent object.
    Based on `rules.contrib.rest_framework.AutoPermissionViewSetMixin`. Unfortunately, it isn't easy to override
    the functionality so we essentially have to rewrite it here using the new functionality.
    """

    permission_type_map = {
        "create": "add",
        "destroy": "delete",
        "list": None,  # Use your local permission in the model.
        "partial_update": "change",
        "retrieve": "view",
        "update": "change",
    }
    parent_dependent_actions = [
        "list",
        "create",
    ]  # Which keys in the permission type map require a parent object?

    parent_lookup_field = None  # Use this to check a property on the primary object.
    # These must be specified for non-detail views.
    parent_object_url_kwarg = None
    parent_object_model = None
    parent_object_lookup_field = None

    def initial(self, *args, **kwargs):
        """
        Checks permissions against object or parent object as required.
        """
        super().initial(*args, **kwargs)

        if not self.request.user:
            # No user. Don't bother checking.
            logging.debug("No user in request...")
            return

        # Get the handler for the HTTP method to use.
        try:
            if self.request.method.lower() not in self.http_method_names:
                raise AttributeError
            handler = getattr(self, self.request.method.lower())
        except AttributeError:
            # method not supported, so will be denied anyway.
            return

        try:
            perm_type = self.permission_type_map[self.action]
            logging.debug("Perm type retrieved as {}".format(perm_type))
        except KeyError:
            raise ImproperlyConfigured(
                "ParentObjectAutoPermissionViewSetMixin tried to authorize a request with the "
                "{!r} action, but permission_type_map only contains: {!r}".format(
                    self.action, self.permission_type_map
                )
            )
        if perm_type is None:
            # Skip permission checking.
            logger.debug("No permission specified, skipping checks.")
            return

        # Determine if we need to check object permissions or parent object permissions.
        obj = None
        extra_actions = self.get_extra_actions()
        # We have to access the unbound function via __func__
        if handler.__func__ in extra_actions:
            if handler.detail:
                obj = self.get_object()
            elif self.action not in ("create", "list"):
                obj = self.get_object()

        # Now check permissions. First we check to see if the parent objects are needed.
        if self.action in self.parent_dependent_actions:
            logger.debug("This action needs to check parent object permission...")
            if not obj:
                logger.debug(
                    "This isn't a detail view, so we need to fetch the parent off of the url_kwargs of the request."
                )
                # We need to pull the parent object from the url kwargs
                if (
                    not self.parent_object_model
                    or not self.parent_object_url_kwarg
                    or not self.parent_object_lookup_field
                ):
                    raise ImproperlyConfigured(
                        "You attempted to check a parent based permission on a non-detail view without specifying the parent_object_model, parent_object_url_kwarg, and parent_object_lookup_field."
                    )
                obj = get_object_or_404(
                    self.parent_object_model,
                    **{
                        self.parent_object_lookup_field: self.kwargs[
                            self.parent_object_url_kwarg
                        ]
                    }
                )
                logger.debug(
                    "Retrieved parent object of {} which is a {}".format(obj, type(obj))
                )
            elif obj and self.parent_lookup_field:
                logger.debug(
                    "This is a detail view, so we pull the parent as an attribute of the object."
                )
                try:
                    # Now we parse the lookup field, using the `__` to indicate we should delve deeper into relationship.
                    working_prop = self.get_object()
                    for prop in self.parent_lookup_field.split("__"):
                        working_prop = getattr(working_prop, prop)
                    obj = working_prop  # Set the object to the working object.
                    logger.debug(
                        "Retrieved {} from object which resolved as {}".format(
                            self.parent_lookup_field, obj
                        )
                    )
                except AttributeError:
                    raise ImproperlyConfigured(
                        "Invalid lookup field '{}' for parent object.".format(
                            self.parent_lookup_field
                        )
                    )

        # Check permissions
        perm = self.get_queryset().model.get_perm(perm_type)
        logger.debug("Testing permission {} against object {}".format(perm, obj))
        if not self.request.user.has_perm(perm, obj):
            raise PermissionDenied
