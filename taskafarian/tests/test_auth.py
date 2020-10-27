import os
from datetime import datetime, timedelta, timezone

import jwt

from chalicelib.services import auth
from chalicelib.services.auth import ActionType

url_registration = '/auth/register'
url_user = '/user'
url_user_me = '/user/me'
url_log_in = '/auth/log-in'
url_log_out = '/auth/log-out'
url_request_password_reset = '/auth/password/request-reset'
url_reset_password = '/auth/password/reset'
url_activate = '/auth/activate'


# registration
def test_stop_registration_if_parameters_missing(app):
    response = app.http.post(path=url_registration, json={})
    assert response.status_code == 422

    response = app.http.post(path=url_registration, json={'username': 'luna'})
    assert response.status_code == 422

    response = app.http.post(path=url_registration, json={'username': 'luna', 'email': 'luna@luna.com'})
    assert response.status_code == 422

    response = app.http.post(path=url_registration, json={'username': 'luna', 'password': '12345678'})
    assert response.status_code == 422


def test_stop_registration_if_username_or_email_is_duplicated(app, db):
    def assert_user_does_not_exist(username, email):
        with db.cursor() as cursor:
            cursor.execute('''
            SELECT user_id
            FROM app_user
            WHERE username = %s AND email = %s
            ;
            ''', (username, email))
            user = cursor.fetchone()
            db.commit()
            assert user is None

    def try_to_register(user_details):
        response = app.http.post(
            path=url_registration,
            json=user_with_duplicate_username
        )
        assert response.status_code == 422
        assert_user_does_not_exist(user_details['username'], user_details['email'])

    user_with_duplicate_username = {
        'username': 'alice',
        'email': 'bla@bla.com',
        'password': '12345678'
    }

    user_with_duplicate_email = {
        'username': 'cactus',
        'email': 'alice@alice.com',
        'password': '12345678'
    }

    try_to_register(user_with_duplicate_username)
    try_to_register(user_with_duplicate_email)


def test_successful_registration(app, db):
    new_user = {
        'username': 'luna',
        'password': '12345678',
        'email': 'luna@luna.com'
    }

    response = app.http.post(path=url_registration, json=new_user)
    assert response.status_code == 201

    with db.cursor() as cursor:
        cursor.execute('SELECT * FROM app_user WHERE username = %s', (new_user['username'],))
        user = cursor.fetchone()

    assert user is not None
    assert user.email == new_user['email']


def test_new_registered_user_can_not_log_in_until_activated(app, monkeypatch):
    auth_register_new_user = auth.register_new_user
    new_user = {
        'username': 'luna',
        'password': '12345678',
        'email': 'luna@luna.com'
    }

    # monkey patch register_new_user so that user activation is required
    def register_new_user(*args, **kwargs):
        kwargs['is_activation_required'] = True
        return auth_register_new_user(*args, **kwargs)
    monkeypatch.setattr('chalicelib.services.auth.register_new_user', register_new_user)

    response = app.http.post(path=url_registration, json=new_user)
    assert response.status_code == 201

    # user should not able to log-in before activation
    response = app.http.post(
        path=url_log_in,
        json={'username': new_user['username'], 'password': new_user['password']}
    )
    assert response.status_code == 403


def test_new_registered_user_can_log_in_if_activation_is_not_required(app, monkeypatch):
    auth_register_new_user = auth.register_new_user

    new_user = {
        'username': 'luna',
        'password': '12345678',
        'email': 'luna@luna.com'
    }

    # monkey patch register_new_user so that user activation is not required
    def patched_register_new_user(*args, **kwargs):
        kwargs['is_activation_required'] = False
        return auth_register_new_user(*args, **kwargs)
    monkeypatch.setattr('chalicelib.services.auth.register_new_user', patched_register_new_user)

    response = app.http.post(path=url_registration, json=new_user)
    assert response.status_code == 201

    response = app.http.post(
        path=url_log_in,
        json={'username': new_user['username'], 'password': new_user['password']}
    )
    assert response.status_code == 200

    token = response.json_body['token']
    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200


# log-in
def test_log_in(app):
    response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': '12345678'}
    )
    assert response.status_code == 200
    token = response.json_body['token']
    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200


def test_username_should_be_case_insensitive(app):
    response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': '12345678'}
    )
    assert response.status_code == 200

    response = app.http.post(
        path=url_log_in,
        json={'username': 'aLiCe', 'password': '12345678'}
    )
    assert response.status_code == 200


# log-out
def test_log_out(app):
    # log in
    log_in_response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': '12345678'}
    )
    assert log_in_response.status_code == 200
    token = log_in_response.json_body['token']

    # check that alice can access the api
    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200

    # log out
    response = app.http.delete(
        path=url_log_out,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200

    # check that alice can not access the api with the same token
    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 401


# password reset
def test_reset_password(app, monkeypatch):
    reset_token = ''

    # intercept the token
    def mock_send_password_reset_by_email(email, token):
        nonlocal reset_token
        reset_token = token

    monkeypatch.setattr('chalicelib.services.auth.send_password_reset_by_email', mock_send_password_reset_by_email)

    # request password reset
    response = app.http.post(
        path=url_request_password_reset,
        json={'email': 'alice@alice.com'}
    )
    assert response.status_code == 200
    assert reset_token != ''

    # reset the password
    response = app.http.post(
        path=url_reset_password,
        json={'token': reset_token, 'newPassword': 'qwertyui'}
    )
    assert response.status_code == 200
    assert response.json_body == {}

    # expect the old password stop working
    response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': '12345678'}
    )
    assert response.status_code == 404

    # expect to be able to log-in with the new password
    response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': 'qwertyui'}
    )
    assert response.status_code == 200
    token = response.json_body['token']

    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200


def test_user_can_not_use_fake_token_to_reset_password(app, user_alice):
    fake_token = jwt.encode({
        'iss': os.getenv('TASKAFARIAN_ENV'),
        'sub': user_alice.user_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=1),
        'action': ActionType.USER_ACTIVATION.value
    }, 'i-dont-know-the-secret', algorithm='HS256').decode('utf-8')

    response = app.http.post(
        path=url_reset_password,
        json={'token': fake_token, 'newPassword': 'qwertyui'}
    )
    assert response.status_code == 401

    response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': 'qwertyui'}
    )
    assert response.status_code == 404


def test_user_can_reset_password_multiple_times_before_token_is_expired(app, monkeypatch):
    """User can reset password many times using the same token until JWT token expires.
    """
    reset_token = ''

    # captures the token
    def mock_send_password_reset_by_email(email, token):
        nonlocal reset_token
        reset_token = token

    monkeypatch.setattr('chalicelib.services.auth.send_password_reset_by_email', mock_send_password_reset_by_email)

    # request password reset
    response = app.http.post(
        path=url_request_password_reset,
        json={'email': 'alice@alice.com'}
    )
    assert response.status_code == 200
    assert reset_token != ''

    # reset the password
    response = app.http.post(
        path=url_reset_password,
        json={'token': reset_token, 'newPassword': 'qwertyui'}
    )
    assert response.status_code == 200
    assert response.json_body == {}

    # reset the password again
    response = app.http.post(
        path=url_reset_password,
        json={'token': reset_token, 'newPassword': '123qwerty'}
    )
    assert response.status_code == 200
    assert response.json_body == {}

    # log-in
    response = app.http.post(
        path=url_log_in,
        json={'username': 'alice', 'password': '123qwerty'}
    )
    assert response.status_code == 200


def test_activation_token_can_not_be_used_to_reset_password(app, monkeypatch):
    """
    Scenario:
    1. user successfully registers
    2. server sends an email with activation token
    3. user decides to reset password using the activation token
    """
    auth_register_new_user = auth.register_new_user  # to avoid recursion
    new_user = {
        'username': 'luna',
        'password': '12345678',
        'email': 'luna@luna.com'
    }
    activation_token = ''

    def register_new_user(*args, **kwargs):
        kwargs['is_activation_required'] = True
        return auth_register_new_user(*args, **kwargs)
    monkeypatch.setattr('chalicelib.services.auth.register_new_user', register_new_user)

    def intercept_activation_token(email, token):
        nonlocal activation_token
        activation_token = token
    monkeypatch.setattr('chalicelib.services.auth.send_activation_link', intercept_activation_token)

    response = app.http.post(path=url_registration, json=new_user)
    assert response.status_code == 201

    # attempt to reset the password with activation token
    response = app.http.post(
        path=url_reset_password,
        json={'token': activation_token, 'newPassword': 'qwertyui'}
    )
    assert response.status_code == 401

    # try to log-in with the new password
    response = app.http.post(
        path=url_log_in,
        json={'username': new_user['username'], 'password': 'qwertyui'}
    )
    assert response.status_code == 403

    # try to log-in with the old password
    response = app.http.post(
        path=url_log_in,
        json={'username': new_user['username'], 'password': new_user['password']}
    )
    assert response.status_code == 403


# activation
def test_user_activation(app, monkeypatch):
    auth_register_new_user = auth.register_new_user
    activation_token = ''
    new_user = {
        'username': 'luna',
        'password': '12345678',
        'email': 'luna@luna.com'
    }

    # monkey patch register_new_user so that user activation is required
    def register_new_user(*args, **kwargs):
        kwargs['is_activation_required'] = True
        return auth_register_new_user(*args, **kwargs)
    monkeypatch.setattr('chalicelib.services.auth.register_new_user', register_new_user)

    def intercept_activation_token(email, token):
        nonlocal activation_token
        activation_token = token
    monkeypatch.setattr('chalicelib.services.auth.send_activation_link', intercept_activation_token)

    response = app.http.post(path=url_registration, json=new_user)
    assert response.status_code == 201

    # user should not able to log-in before activation
    response = app.http.post(
        path=url_log_in,
        json={'username': new_user['username'], 'password': new_user['password']}
    )
    assert response.status_code == 403

    # activate
    response = app.http.post(
        path=url_activate,
        json={'token': activation_token}
    )
    assert response.status_code == 200

    # user should be able to log-in after activation
    response = app.http.post(
        path=url_log_in,
        json={'username': new_user['username'], 'password': new_user['password']}
    )
    assert response.status_code == 200


def test_password_reset_token_can_not_be_used_to_activate_account(app, monkeypatch):
    """
    Scenario:
    1. registered user alice requests password reset
    2. server sends alice token for password reset
    3. alice shares the token with bob
    4. bob tries to activate his account by sending the token to /activate endpoint
    """
    auth_register_new_user = auth.register_new_user
    reset_token = ''

    # captures the token
    def mock_send_password_reset_by_email(email, token):
        nonlocal reset_token
        reset_token = token

    monkeypatch.setattr('chalicelib.services.auth.send_password_reset_by_email', mock_send_password_reset_by_email)

    # request password reset
    response = app.http.post(
        path=url_request_password_reset,
        json={'email': 'alice@alice.com'}
    )
    assert response.status_code == 200
    assert reset_token != ''

    # register new user
    def patched_register_new_user(*args, **kwargs):
        kwargs['is_activation_required'] = True
        return auth_register_new_user(*args, **kwargs)
    monkeypatch.setattr('chalicelib.services.auth.register_new_user', patched_register_new_user)

    new_user = {
        'username': 'luna',
        'password': '12345678',
        'email': 'luna@luna.com'
    }

    response = app.http.post(path=url_registration, json=new_user)
    assert response.status_code == 201

    # try to activate user with token for password reset from alice
    response = app.http.post(path=url_activate, json={'token': reset_token})
    assert response.status_code == 422

    # no access
    response = app.http.post(path=url_log_in, json={
        'username': new_user['username'],
        'password': new_user['password']
    })
    assert response.status_code == 403


# deactivation
def test_deactivated_user_can_not_use_the_api(app, db, user_alice):
    """Remove any active user tokens when is_active flag on the user_app becomes false.
    """
    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200

    auth.deactivate_user(user_alice.user_id)

    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 401
    assert response.json_body == {}

    with db.cursor() as cursor:
        cursor.execute('''
        SELECT user_id
        FROM token
        WHERE user_id = %s
        ''', (user_alice.user_id,))
        assert len(cursor.fetchall()) == 0


# invalid token
def test_can_not_use_the_api_with_expired_token(app, user_eve):
    response = app.http.get(
        path=f'{url_user}/me',
        headers={'Authorization': f'Bearer {user_eve.token}'}
    )
    assert response.status_code == 401
    assert response.json_body == {}


def test_can_not_use_the_api_with_fake_token(app, user_alice):
    response = app.http.get(
        path=f'{url_user}/{user_alice.user_id}',
        headers={'Authorization': 'Bearer myfaketoken'}
    )
    assert response.status_code == 401
    assert response.json_body == {}

    response = app.http.get(
        path=url_user_me,
        headers={'Authorization': 'Bearer myfaketoken'}
    )

    assert response.status_code == 401
    assert response.json_body == {}

