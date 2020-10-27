import os
import secrets
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
import psycopg2

from chalicelib.core.database import get_db
from chalicelib.core.logger import logger
from chalicelib.core.security import check_password, hash_password


class DuplicateEmail(Exception):
    pass


class DuplicateUsername(Exception):
    pass


class BadCredentials(Exception):
    pass


class UserActivationFailed(Exception):
    pass


class UserIsNotActive(Exception):
    pass


class UserNotFound(Exception):
    pass


class ActionType(Enum):
    """Intended to be used with JWT tokens.
    Users should not be able to use token from one flow in another flow.
    e.g activation token can't be used as token to reset the password.
    """
    PASSWORD_RESET = 'password_reset'
    USER_ACTIVATION = 'user_activation'


def register_new_user(username, email, password, is_activation_required=True):
    db = get_db()
    with db.cursor() as cursor:
        try:
            password_hash = hash_password(password)
            cursor.execute('''
            INSERT INTO app_user (username, email, password_hash, is_active)
            VALUES (%(username)s, %(email)s, %(password_hash)s, %(is_active)s)
            RETURNING *;
            ''', {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'is_active': not is_activation_required
            })
            db.commit()

            new_user = cursor.fetchone()

            if is_activation_required:
                token = create_activation_token(new_user.user_id).decode('utf-8')
                send_activation_link(new_user.email, token)

            return new_user

        except psycopg2.errors.UniqueViolation as error:
            # TODO: you have to look at the database to know which constraint to catch
            # https://www.psycopg.org/docs/extensions.html#psycopg2.extensions.Diagnostics
            db.rollback()
            constraint = getattr(error.diag, 'constraint_name')
            if constraint == 'app_user_username_key':
                raise DuplicateUsername()
            elif constraint == 'app_user_email_key':
                raise DuplicateEmail()
            raise error


def log_in(username, password):
    db = get_db()
    with db.cursor() as cursor:
        query = '''
            SELECT user_id, is_active, password_hash
            FROM app_user
            WHERE username = %(username)s
            ;
        '''
        cursor.execute(query, {'username': username})

        user = cursor.fetchone()
        if user and not user.is_active:
            db.commit()
            raise UserIsNotActive()
        elif user and check_password(password, user.password_hash):
            token, expires_at = generate_auth_token_with_expiry_date()

            cursor.execute('''
            INSERT INTO token (user_id, token, expires_at)
            VALUES (%(user_id)s, %(token)s, %(expires_at)s);
            ''', {
                'user_id': user.user_id,
                'token': token,
                'expires_at': expires_at
            })
            db.commit()

            return token, expires_at

        raise BadCredentials()


def generate_auth_token_with_expiry_date():
    """
    Returns the token and the expiry date
    """
    return secrets.token_hex(32), datetime.now(timezone.utc) + timedelta(hours=1)


def is_valid_token(token):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT expires_at
        FROM token
        WHERE token = %(token)s
        ''', {'token': token})
        db.commit()

        token = cursor.fetchone()
        if token.expires_at > datetime.now(timezone.utc) + timedelta(minutes=1):
            return True
        else:
            return False


def get_user_by_id(user_id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT 
            user_id, 
            username, 
            email, 
            first_name, 
            last_name, 
            created_at, 
            updated_at, 
            is_active
        FROM app_user
        WHERE user_id = %(user_id)s
        ;
        ''', {'user_id': user_id})
        db.commit()
        return cursor.fetchone()


def get_user_by_token(token: str) -> namedtuple:
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT 
            app_user.user_id, 
            username, 
            email, 
            first_name, 
            last_name, 
            created_at, 
            updated_at, 
            is_active,
            token
        FROM app_user
        JOIN token ON token.user_id = app_user.user_id 
            AND token.token = %(token)s
            AND token.expires_at > %(expires_at)s
        ;
        ''', {
            'token': token,
            'expires_at': datetime.now(timezone.utc) + timedelta(minutes=1)
        })
        db.commit()
        user = cursor.fetchone()
        return user


def send_activation_link(email, token):
    """
    Send user an activation link containing a token.
    """
    logger.info('sending an activation link to {email}, {token}'.format(email=email, token=token))


def activate_user(user_id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        UPDATE app_user
        SET is_active = true
        WHERE user_id = %(user_id)s
        ;
        ''', {'user_id': user_id})
        db.commit()


def activate_user_by_token(activation_token):
    try:
        token_details = jwt.decode(
            activation_token,
            os.getenv('TASKAFARIAN_SECRET_KEY'),
            algorithms=['HS256'],
            issuer=os.getenv('TASKAFARIAN_ENV')
        )

        if 'sub' not in token_details:
            raise UserActivationFailed('Bad token')
        elif 'action' not in token_details or token_details['action'] != ActionType.USER_ACTIVATION.value:
            raise UserActivationFailed('Bad Token')
        activate_user(token_details['sub'])

    except jwt.exceptions.ExpiredSignatureError:
        raise UserActivationFailed('Expired')
    except jwt.exceptions.PyJWTError:
        # handle any other pyjwt exceptions in a same way
        # e.g token created in one environment and attempted to be used in another
        raise UserActivationFailed('Invalid token')


def create_activation_token(user_id, token_life=timedelta(minutes=15)):
    return jwt.encode({
        'iss': os.getenv('TASKAFARIAN_ENV'),
        'sub': user_id,
        'exp': datetime.now(timezone.utc) + token_life,
        'action': ActionType.USER_ACTIVATION.value
    }, os.getenv('TASKAFARIAN_SECRET_KEY'), algorithm='HS256')


def send_password_reset_by_email(email: str, token: str):
    """TODO
    """
    logger.info(f'Sending password reset email:\n\temail: {email}\n\ttoken: {token}')


def request_password_reset(email: str):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT email
        FROM app_user
        WHERE email = %(email)s
        ;
        ''', {'email': email})
        db.commit()
        user = cursor.fetchone()

        if not user:
            # no user with such email
            raise UserNotFound()

    token = create_token_for_password_reset(email).decode('utf-8')
    send_password_reset_by_email(email, token)


def create_token_for_password_reset(email, token_life=timedelta(minutes=10)):
    return jwt.encode({
        'iss': os.getenv('TASKAFARIAN_ENV'),
        'exp': datetime.now(timezone.utc) + token_life,
        'email': email,
        'action': ActionType.PASSWORD_RESET.value
    }, os.getenv('TASKAFARIAN_SECRET_KEY'), algorithm='HS256')


def reset_password(token, new_password):
    try:
        decoded = jwt.decode(
            token,
            os.getenv('TASKAFARIAN_SECRET_KEY'),
            algorithms=['HS256'],
            issuer=os.getenv('TASKAFARIAN_ENV')
        )

        if 'action' not in decoded or decoded['action'] != ActionType.PASSWORD_RESET.value:
            # unexpected action. maybe user tried to reuse token from other flow
            raise BadCredentials()

        password_hash = hash_password(new_password)

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute('''
            UPDATE app_user
            SET password_hash = %(password_hash)s
            WHERE email = %(email)s
            ;
            ''', {'password_hash': password_hash, 'email': decoded['email']})
            db.commit()
    except jwt.exceptions.PyJWTError:
        raise BadCredentials()


def log_out(token):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        DELETE
        FROM token
        WHERE token = %(token)s
        ''', {'token': token})
        db.commit()


def deactivate_user(user_id):
    """Deactivates user by setting the is_active flag to false and removing all tokens."""
    db = get_db()

    with db.cursor() as cursor:
        query = '''
        UPDATE app_user 
        SET is_active = true
        WHERE user_id = %(user_id)s
        ;
        
        DELETE
        FROM token
        WHERE user_id = %(user_id)s
        ; 
        '''
        params = {'user_id': user_id}
        cursor.execute(query, params)
        db.commit()
