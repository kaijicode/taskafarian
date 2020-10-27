import os
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import psycopg2
from psycopg2.extras import NamedTupleCursor
from psycopg2.sql import SQL, Identifier

from chalicelib.core.logger import logger

_connection = None


def log(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        start_timestamp = time.perf_counter()
        try:
            value = f(self, *args, **kwargs)
            # TODO: Logging may leak credentials
            logger.debug('{date}: query={query} rows={rows}, execution_time={execution_time:.3f}ms'.format(
                date=datetime.now(timezone.utc),
                query=self.query.decode('utf-8'),
                rows=self.rowcount,
                execution_time=(time.perf_counter() - start_timestamp) * 1000
            ))
        except Exception as exception:
            logger.exception(exception)
            raise exception
        return value

    return wrapper


class Cursor(NamedTupleCursor):
    """
    NamedTupleCursor with logging capability.
    """
    @log
    def execute(self, query, vars=None):
        return super(Cursor, self).execute(query, vars)

    @log
    def callproc(self, procname, vars=None):
        return super(Cursor, self).callproc(procname, vars)


def connect(db_name=None):
    db_name = db_name if db_name else os.getenv('TASKAFARIAN_DB_NAME')
    return psycopg2.connect(
        host=os.getenv('TASKAFARIAN_DB_HOST'),
        dbname=db_name,
        user=os.getenv('TASKAFARIAN_DB_USER'),
        password=os.getenv('TASKAFARIAN_DB_PASSWORD'),
        cursor_factory=Cursor,
        port=os.getenv('TASKAFARIAN_DB_PORT')
    )


def get_db():
    global _connection
    if not _connection:
        _connection = connect()
    return _connection


def close_db():
    global _connection
    if _connection:
        _connection.close()
        _connection = None


def create_db():
    connection = connect(db_name='postgres')
    connection.set_session(autocommit=True)

    try:
        with connection.cursor() as cursor:
            sql_create_db = SQL('''CREATE DATABASE {};''').format(Identifier(os.getenv('TASKAFARIAN_DB_NAME')))
            cursor.execute(sql_create_db)
    except psycopg2.errors.DuplicateDatabase as error:
        logger.error(error.pgerror)
    finally:
        connection.close()


def drop_db():
    connection = connect(db_name='postgres')
    connection.set_session(autocommit=True)

    try:
        with connection.cursor() as cursor:
            sql_drop_db = SQL('DROP DATABASE {};').format(Identifier(os.getenv('TASKAFARIAN_DB_NAME')))
            cursor.execute(sql_drop_db)
    except (psycopg2.errors.InvalidCatalogName, psycopg2.errors.ObjectInUse) as error:
        logger.error(error.pgerror)
    finally:
        connection.close()


def create_all():
    connection = connect()

    try:
        with connection.cursor() as cursor:
            with open(Path() / 'chalicelib' / 'sql' / 'schema.sql') as f:
                cursor.execute(f.read())
                connection.commit()
    except psycopg2.Error as error:
        connection.rollback()
        logger.debug(error.pgerror)
    finally:
        connection.close()


def check_connection():
    """Test database connection
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''SELECT 1;''')
        db.commit()
