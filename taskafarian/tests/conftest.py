import json as jsonlib
import os
from datetime import datetime
from pathlib import Path

import pytest
from chalice.test import Client, TestHTTPClient
from marshmallow.fields import AwareDateTime

from app import app as application
from chalicelib.core.database import close_db, create_all, create_db, drop_db


class JSONEncoder(jsonlib.JSONEncoder):
    """JSON encoder with datetime support
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class TestClient(Client):
    @property
    def http(self):
        if self._http_client is None:
            self._http_client = CustomHTTPClient(self._app, self._chalice_config)
        return self._http_client


class CustomHTTPClient(TestHTTPClient):
    def request(self, method, path, headers=None, body=None, json=None):
        if headers and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        else:
            headers = {'Content-Type': 'application/json'}

        return super().request(method, path, headers, jsonlib.dumps(json, cls=JSONEncoder))


@pytest.fixture
def app():
    with TestClient(application, stage_name='test') as client:
        # TODO
        # looks like chalice loads environment variables later (when http request is sent)
        # but we need the correct environment variables right now to prepare the database.
        load_env_variables()

        # safety check
        assert os.getenv('TASKAFARIAN_DB_NAME') == 'test_taskafarian'

        # TODO: consider reusing the database connection
        # TODO: consider doing rollback instead of dropping the database
        # TODO: ^ or try TRUNCATE
        drop_db()
        create_db()
        create_all()
        load_fixture('base.sql')

        yield client

        close_db()


def get_user(username):
    from chalicelib.core.database import get_db
    db = get_db()
    with db.cursor() as cursor:
        query = '''
        SELECT * 
        FROM app_user
        LEFT JOIN token using (user_id)
        WHERE username = %(username)s
        ;
        '''
        params = {'username': username}
        cursor.execute(query, params)
        db.commit()

        return cursor.fetchone()


@pytest.fixture
def user_alice(app):
    return get_user('alice')


@pytest.fixture
def user_bob(app):
    return get_user('bob')


@pytest.fixture
def user_charlie():
    return get_user('charlie')


@pytest.fixture
def user_dave():
    return get_user('dave')


@pytest.fixture
def user_eve():
    return get_user('eve')


@pytest.fixture
def user_fiona():
    return get_user('fiona')


class EqualAny:
    def __eq__(self, other):
        return True


any_value = EqualAny()


def timestamptz_to_str(value):
    return AwareDateTime().serialize('timestamp', {'timestamp': value})


def load_fixture(name):
    from chalicelib.core.database import get_db
    db = get_db()
    with db.cursor() as cursor:
        with (Path() / 'tests/fixtures' / name).open() as f:
            cursor.execute(f.read())
            db.commit()
    close_db()


def load_env_variables():
    with open(Path() / '.chalice' / 'config.json') as f:
        config = jsonlib.load(f)
        env_vars = config['stages']['test']['environment_variables']
        for key, value in env_vars.items():
            os.environ[key] = value


@pytest.fixture
def db():
    from chalicelib.core.database import connect
    connection = connect()
    yield connection
    connection.close()
