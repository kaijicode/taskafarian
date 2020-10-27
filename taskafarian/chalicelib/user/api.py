from chalice import Blueprint, Response

from chalicelib.auth.decorators import protected
from chalicelib.core.exceptions import APIError
from chalicelib.core.shared import g
from chalicelib.user.schema import User as UserSchema

blueprint = Blueprint(__name__)


# TODO: better way of handling path parameters? (Flask does it)
@blueprint.route('/user/{user_id}')
@protected
def get_user(user_id):
    if int(user_id) != g.current_user.user_id:
        raise APIError(status=403)

    return Response(body=UserSchema().dump(g.current_user), status_code=200)


@blueprint.route('/user/me')
@protected
def get_current_user():
    return Response(body=UserSchema().dump(g.current_user), status_code=200)


