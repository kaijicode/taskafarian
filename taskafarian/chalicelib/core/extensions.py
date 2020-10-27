from typing import Callable
from functools import wraps

from chalice import Blueprint as ChaliceBlueprint
from chalice import Response
from marshmallow import ValidationError

from chalicelib.core.exceptions import APIError


class Blueprint(ChaliceBlueprint):
    """Blueprint with error handling capability
    TODO: In an upcoming version of chalice, it can be rewritten as a middleware:
            related: https://github.com/aws/chalice/pull/1549
    """
    def route(self, *args, **kwargs) -> Callable:
        register_route = super(Blueprint, self).route(*args, **kwargs)

        def wrapped_view(view) -> Callable:
            @wraps(view)
            def inner(*view_args, **view_kwargs) -> Response:
                try:
                    return view(*view_args, **view_kwargs)
                except ValidationError as exception:
                    return APIError(status=422, fields=exception.messages).to_http_response()
                except APIError as exception:
                    return exception.to_http_response()

            return register_route(inner)
        return wrapped_view
