from functools import wraps

from chalice import Response

from chalicelib.core.shared import g
from chalicelib.services.auth import get_user_by_token


def protected(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # extract token from header value: 'Bearer <token>'
            authorization_header = g.current_request.headers['Authorization']
            token = authorization_header.split(' ')[1]

            g.current_user = get_user_by_token(token)
            # TODO: lazy load team roles that the user belongs to?
            if g.current_user:
                return func(*args, **kwargs)
        except (KeyError, IndexError):
            return Response(body={}, status_code=401)

        return Response(body={}, status_code=401)

    return wrapper
