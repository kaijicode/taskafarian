from chalice import Response

from chalicelib.auth.decorators import protected
from chalicelib.auth.schema import (ActivationToken, LoginCredentials,
                                    PasswordChange,
                                    PasswordResetRequestDetails,
                                    RegistrationSchema, Token)
from chalicelib.core.exceptions import APIError
from chalicelib.core.extensions import Blueprint
from chalicelib.core.logger import logger
from chalicelib.core.shared import g
from chalicelib.services import auth

blueprint = Blueprint(__name__)


@blueprint.route('/register', methods=['POST'])
def register():
    body = blueprint.current_request.json_body

    try:
        registration_details = RegistrationSchema().load(body)
        new_user = auth.register_new_user(username=registration_details['username'],
                                          email=registration_details['email'],
                                          password=registration_details['password']
                                          )
    except auth.DuplicateEmail:
        raise APIError(status=422, fields={'email': ['Already exists']})
    except auth.DuplicateUsername:
        raise APIError(status=422, fields={'username': ['Already exists']})

    return Response(body=RegistrationSchema().dump(new_user), status_code=201)


@blueprint.route('/log-in', methods=['POST'])
def log_in():
    body = blueprint.current_request.json_body
    try:
        credentials = LoginCredentials().load(body)
        token, expires_at = auth.log_in(username=credentials['username'], password=credentials['password'])
        logger.info('{username} logged in'.format(username=credentials['username']))
        return Response(
            body=Token().dump({'token': token, 'expires_at': expires_at}),
            status_code=200
        )
    except auth.BadCredentials:
        raise APIError(status=404, detail='Wrong username, email or password')
    except auth.UserIsNotActive:
        raise APIError(status=403, detail='User is not activated')


@blueprint.route('/activate', methods=['POST'])
def activate():
    body = blueprint.current_request.json_body

    try:
        activation_token = ActivationToken().load(body)
        auth.activate_user_by_token(activation_token['token'])
    except auth.UserActivationFailed as error:
        raise APIError(status=422, detail=str(error))

    return Response(body={}, status_code=200)


@blueprint.route('/password/request-reset', methods=['POST'])
def request_password_reset():
    body = blueprint.current_request.json_body

    try:
        password_reset_details = PasswordResetRequestDetails().load(body)
        auth.request_password_reset(password_reset_details['email'])
        return Response(body={}, status_code=200)
    except auth.UserNotFound:
        raise APIError(status=404, detail='User not found')


@blueprint.route('/password/reset', methods=['POST'])
def reset_password():
    body = blueprint.current_request.json_body

    try:
        password_details = PasswordChange().load(body)
        auth.reset_password(password_details['token'], password_details['new_password'])
        return Response(body={}, status_code=200)
    except auth.BadCredentials:
        raise APIError(status=401, detail='Invalid token')


@blueprint.route('/log-out', methods=['DELETE'])
@protected
def log_out():
    auth.log_out(g.current_user.token)
    return Response(body={}, status_code=200)
