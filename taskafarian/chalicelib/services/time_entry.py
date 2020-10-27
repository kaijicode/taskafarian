from collections import namedtuple
from datetime import datetime
from typing import List, Tuple

from psycopg2.sql import SQL, Identifier, Placeholder

from chalicelib.core.database import get_db
from chalicelib.core.exceptions import (DeletionError, EntityNotFound,
                                        InvalidValue)


def create(task_id: int, assignee_id: int, start_datetime: datetime, end_datetime: datetime = None):
    """Create new time entry related to a task (start task)
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        INSERT INTO task_time_entry(task_id, assignee_id, start_datetime, end_datetime)
        VALUES (%(task_id)s, %(assignee_id)s, %(start_datetime)s, %(end_datetime)s)
        RETURNING *
        ;
        ''', {
            'task_id': task_id,
            'assignee_id': assignee_id,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime
        })
        time_entry = cursor.fetchone()
        db.commit()

    return time_entry


def update(user: namedtuple, time_entry_id: int, **kwargs) -> dict:
    """Update details of time entry (e.g stop task)
    User can update only time entries he owns.
    """
    db = get_db()
    with db.cursor() as cursor:
        query = '''
        SELECT start_datetime, end_datetime
        FROM task_time_entry
        INNER JOIN task ON task.task_id = task_time_entry.task_id 
            AND task.created_by = %(user_id)s  
        WHERE time_entry_id = %(time_entry_id)s
        ;
        '''

        params = {
            'time_entry_id': time_entry_id,
            'user_id': user.user_id
        }

        cursor.execute(query, params)
        existing_time_entry = cursor.fetchone()

        if not existing_time_entry:
            raise EntityNotFound()

        if 'start_datetime' in kwargs:
            if existing_time_entry.end_datetime and kwargs['start_datetime'] >= existing_time_entry.end_datetime:
                raise InvalidValue()

        if 'end_datetime' in kwargs and \
                kwargs['end_datetime'] <= existing_time_entry.start_datetime:
            raise InvalidValue()

        fields = [
            SQL('{field} = {value}').format(
                field=Identifier(field),
                value=Placeholder(field)
            ) for field in kwargs.keys()
        ]

        query = SQL('''
        UPDATE task_time_entry
        SET {fields}
        WHERE time_entry_id = %(time_entry_id)s
        RETURNING task_time_entry.time_entry_id,
            task_time_entry.task_id,
            task_time_entry.assignee_id,
            task_time_entry.start_datetime,
            task_time_entry.end_datetime
        ;
        ''').format(fields=SQL(', ').join(fields))

        cursor.execute(query, {**kwargs, 'time_entry_id': time_entry_id})
        db.commit()

        return cursor.fetchone()


def delete(user: namedtuple, time_entry_ids: Tuple[int, ...], all_or_nothing=True) -> List[int]:
    db = get_db()
    with db.cursor() as cursor:
        query = '''
        WITH time_entries_to_delete(time_entry_id) AS (
            SELECT time_entry_id
            FROM task_time_entry
            INNER JOIN task ON task.task_id = task_time_entry.task_id
                                   AND task.created_by = %(user_id)s
            WHERE time_entry_id IN %(time_entry_ids)s
        )
        DELETE
        FROM task_time_entry
        WHERE task_time_entry.time_entry_id IN (SELECT time_entry_id FROM time_entries_to_delete)
        RETURNING time_entry_id
        ;
        '''

        params = {
            'time_entry_ids': time_entry_ids,
            'user_id': user.user_id
        }

        cursor.execute(query, params)
        deleted = cursor.fetchall()
        db.commit()

        deleted_task_entries_ids = [time_entry.time_entry_id for time_entry in deleted]

        if all_or_nothing and len(deleted) != len(time_entry_ids):
            db.rollback()
            raise DeletionError(list(set(time_entry_ids) - set(deleted_task_entries_ids)))

        db.commit()

        return deleted_task_entries_ids
