from collections import namedtuple
from enum import Enum
from typing import List, Tuple

from psycopg2.sql import SQL, Identifier, Placeholder

from chalicelib.core.database import get_db
from chalicelib.core.exceptions import DeletionError, EntityNotFound


class StatusEnum(Enum):
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'


class InvalidStartTimestamp(Exception):
    pass


class InvalidEndTimestamp(Exception):
    pass


def fetch(user: namedtuple, task_id: int):
    db = get_db()
    with db.cursor() as cursor:
        query = '''
        SELECT
            task.task_id,
            task.project_id,
            task.team_id,
            task.name,
            task.description,
            task.estimation,
            task.status,
            task.created_at,
            task.due_date,
            jsonb_build_object(
                'username', creator.username,
                'user_id', creator.user_id,
                'first_name', creator.first_name,
                'last_name', creator.last_name
            ) as creator,
            jsonb_build_object(
                'username', assignee.username,
                'user_id', assignee.user_id,
                'first_name', assignee.first_name,
                'last_name', assignee.last_name
            ) as assignee
        FROM task
        LEFT JOIN user_to_team
            ON user_to_team.team_id = task.team_id AND user_to_team.user_id = %(user_id)s
        LEFT JOIN app_user AS creator
            ON creator.user_id = task.created_by
        LEFT JOIN app_user AS assignee
            ON assignee.user_id = task.assignee_id
        WHERE task.task_id = %(task_id)s
            AND (task.created_by = %(user_id)s OR user_to_team.user_role IS NOT NULL)
        ;
        '''

        params = {
            'task_id': task_id,
            'user_id': user.user_id
        }

        cursor.execute(query, params)
        db.commit()

        return cursor.fetchone()


# TODO: BIG TODO here
# TODO: no offset
# TODO: ordering
# order_by=['-due_date', 'created_at']
# -descending
# def fetch_many(user,
#                name: str = None,
#                assignee_id: int = None,
#                status: list = None,
#                due_date: datetime = None,
#                due_date_gt: datetime = None,
#                due_date_lt: datetime = None,
#                created_at: datetime = None,
#                created_at_gt: datetime = None,
#                created_at_lt: datetime = None,
#                offset: int = 0,
#                limit: int = 20):
#
#     params = {
#         'user_id': user.user_id,
#         'name': name,
#         'assignee_id': assignee_id or user.user_id,
#         'status': status,
#         'due_date': due_date,
#         'due_date_gt': due_date_gt,
#         'due_date_lt': due_date_lt,
#         'created_at': created_at,
#         'created_at_gt': created_at_gt,
#         'created_at_lt': created_at_lt,
#         'offset': offset,
#         'limit': limit
#     }
#
#     db = get_db()
#     with db.cursor() as cursor:
#         query = SQL('''
#         WITH extended_task AS (
#             SELECT task.task_id,
#                    task.project_id,
#                    task.team_id,
#                    task.name,
#                    task.description,
#                    task.estimation,
#                    task.status,
#                    task.created_at,
#                    task.due_date,
#                    task.created_by,
#                    task.assignee_id,
#                    coalesce(jsonb_agg(time_entries) filter ( where time_entries.task_id is not null ), '[]'::jsonb) as time_entries
#             FROM task
#             LEFT JOIN LATERAL (
#                 SELECT task_time_entry.time_entry_id,
#                        task_time_entry.task_id,
#                        task_time_entry.assignee_id,
#                        task_time_entry.start_datetime,
#                        task_time_entry.end_datetime
#                 FROM task_time_entry
#                 WHERE task_time_entry.task_id = task.task_id
#                 ORDER BY task_time_entry.start_datetime DESC
#             ) AS time_entries ON true
#             WHERE task.created_by = %(user_id)s
#             --     AND {conditions}
#             GROUP BY task.task_id
#             OFFSET %(offset)s
#             LIMIT %(limit)s
#         ),
#         tasks_with_user_and_time_info AS (
#             SELECT extended_task.task_id,
#                     extended_task.project_id,
#                     extended_task.team_id,
#                     extended_task.name,
#                     extended_task.description,
#                     extended_task.estimation,
#                     extended_task.status,
#                     extended_task.created_at,
#                     extended_task.due_date,
#                     extended_task.time_entries,
#                 jsonb_build_object(
#                    'username', creator.username,
#                    'user_id', creator.user_id,
#                    'first_name', creator.first_name,
#                    'last_name', creator.last_name
#                 ) as creator,
#                 jsonb_build_object(
#                    'username', assignee.username,
#                    'user_id', assignee.user_id,
#                    'first_name', assignee.first_name,
#                    'last_name', assignee.last_name
#                 ) as assignee
#             FROM extended_task
#             LEFT JOIN app_user AS creator
#                 ON creator.user_id = extended_task.created_by
#             LEFT JOIN app_user AS assignee
#                 ON assignee.user_id = extended_task.assignee_id
#         )
#         SELECT *
#         FROM tasks_with_user_and_time_info
#         ORDER BY tasks_with_user_and_time_info.created_at DESC
#         ;
#         ''')
#
#         sql_conditions = [
#             # ANY - https://www.psycopg.org/docs/usage.html#lists-adaptation
#             SQL('task.status = ANY({})').format(Placeholder('status')) if params['status'] else None,
#             SQL('task.assignee_id = {}').format(Placeholder('assignee_id')) if params['assignee_id'] else None,
#             SQL('task.due_date > {}').format(Placeholder('due_date_gt')) if params['due_date_gt'] else None,
#             SQL('task.due_date < {}').format(Placeholder('due_date_lt')) if params['due_date_lt'] else None,
#             SQL('task.due_date = {}').format(Placeholder('due_date')) if params['due_date'] else None,
#             SQL("task.name ILIKE '%%' || {} || '%%'").format(Placeholder('name')) if params['name'] else None,
#             SQL('task.created_at > {}').format(Placeholder('created_at_gt')) if params['created_at_gt'] else None,
#             SQL('task.created_at < {}').format(Placeholder('created_at_lt')) if params['created_at_lt'] else None,
#             SQL('task.created_at = {}').format(Placeholder('created_at')) if params['created_at'] else None
#         ]
#
#         conditions = SQL(' AND ').join([condition for condition in sql_conditions if condition])
#
#         # query_count_total = query_count_total.format(conditions=conditions)
#         # cursor.execute(query_count_total, params)
#         # count_total = cursor.fetchone()
#
#         query = query.format(conditions=conditions)
#         cursor.execute(query, params)
#         tasks = cursor.fetchall()
#
#         return {
#             'entities': tasks,
#             'meta': {
#                 # 'total': count_total['count'],
#                 'count': len(tasks),
#                 'offset': offset,
#                 'limit': limit
#             }
#         }

def fetch_many(user,
               offset: int = 0,
               limit: int = 20):

    params = {
        'user_id': user.user_id,
        'limit': limit,
        'offset': offset,
    }

    db = get_db()
    with db.cursor() as cursor:
        query = SQL('''
        WITH extended_task AS (
            SELECT task.task_id,
                   task.project_id,
                   task.team_id,
                   task.name,
                   task.description,
                   task.estimation,
                   task.status,
                   task.created_at,
                   task.due_date,
                   task.created_by,
                   task.assignee_id,
                   coalesce(jsonb_agg(time_entries) filter ( where time_entries.task_id is not null ), '[]'::jsonb) as time_entries
            FROM task
            LEFT JOIN LATERAL (
                SELECT task_time_entry.time_entry_id,
                       task_time_entry.task_id,
                       task_time_entry.assignee_id,
                       task_time_entry.start_datetime,
                       task_time_entry.end_datetime
                FROM task_time_entry
                WHERE task_time_entry.task_id = task.task_id
                ORDER BY task_time_entry.start_datetime DESC
            ) AS time_entries ON true
            WHERE task.created_by = %(user_id)s
            GROUP BY task.task_id
            OFFSET %(offset)s
            LIMIT %(limit)s
        ),
        tasks_with_user_and_time_info AS (
            SELECT extended_task.task_id,
                    extended_task.project_id,
                    extended_task.team_id,
                    extended_task.name,
                    extended_task.description,
                    extended_task.estimation,
                    extended_task.status,
                    extended_task.created_at,
                    extended_task.due_date,
                    extended_task.time_entries,
                jsonb_build_object(
                   'username', creator.username,
                   'user_id', creator.user_id,
                   'first_name', creator.first_name,
                   'last_name', creator.last_name
                ) as creator,
                jsonb_build_object(
                   'username', assignee.username,
                   'user_id', assignee.user_id,
                   'first_name', assignee.first_name,
                   'last_name', assignee.last_name
                ) as assignee
            FROM extended_task
            LEFT JOIN app_user AS creator
                ON creator.user_id = extended_task.created_by
            LEFT JOIN app_user AS assignee
                ON assignee.user_id = extended_task.assignee_id
        )
        SELECT *
        FROM tasks_with_user_and_time_info
        ORDER BY tasks_with_user_and_time_info.created_at DESC
        ;
        ''')

        cursor.execute(query, params)
        tasks = cursor.fetchall()

        return {
            'entities': tasks,
            'meta': {
                'count': len(tasks),
                'offset': offset,
                'limit': limit
            }
        }


def create_task(user, name, status, created_by,
                assignee_id=None, due_date=None, estimation=None,
                description='', team_id=None, project_id=None):
    db = get_db()
    with db.cursor() as cursor:
        query = '''
        INSERT INTO task(name, status, created_by, assignee_id, due_date, estimation, description, team_id, project_id)
        VALUES (
            %(name)s,
            %(status)s,
            %(created_by)s,
            %(assignee_id)s,
            %(due_date)s,
            %(estimation)s,
            %(description)s,
            %(team_id)s,
            %(project_id)s
        )
        RETURNING task_id
        ;
        '''

        params = {
            'name': name,
            'status': status,
            'created_by': created_by,
            'assignee_id': assignee_id,
            'due_date': due_date,
            'estimation': estimation,
            'description': description,
            'team_id': team_id,
            'project_id': project_id
        }

        cursor.execute(query, params)

        insertion_result = cursor.fetchone()
        db.commit()

    return fetch(user, insertion_result.task_id)


def update_task(user: namedtuple, task_id: int, details: dict) -> dict:
    """
    Update task details such as name, estimation and etc.
    """
    db = get_db()
    with db.cursor() as cursor:
        changes = [
            SQL('{field} = {value}').format(
                field=Identifier(field),
                value=Placeholder(field)
            ) for field in details.keys()
        ]

        query = SQL('''
        WITH prepare_task_for_update(task_id) as (
            SELECT task.task_id
            FROM task
            INNER JOIN user_to_team
                ON user_to_team.team_id = task.team_id
                AND user_to_team.user_id = %(user_id)s
            WHERE task.task_id = %(task_id)s
        )
        UPDATE task
        SET {changes}
        FROM prepare_task_for_update
        WHERE task.task_id = prepare_task_for_update.task_id
        RETURNING task.task_id, 
            task.project_id,
            task.team_id,
            task.name,
            task.description,
            task.estimation,
            task.status,
            task.created_at,
            task.created_by,
            task.due_date,
            task.assignee_id
        ;
        ''').format(changes=SQL(', ').join(changes))

        params = {
            **details,
            'task_id': task_id,
            'user_id': user.user_id
        }
        cursor.execute(query, params)
        db.commit()

        updated_task = cursor.fetchone()
        if not updated_task:
            raise EntityNotFound()

        return updated_task


def delete_tasks(user: namedtuple, task_ids: Tuple[int, ...], all_or_nothing=True) -> List[int]:
    """Delete tasks.
    all_or_nothing=True - commit if all tasks deleted successfully otherwise abort
    all_or_nothing=False - commit even if one or more tasks could not be deleted
    """
    db = get_db()
    with db.cursor() as cursor:
        query = '''
        with prepare_for_deletion(task_id) as (
            SELECT task_id
            FROM task
            INNER JOIN user_to_team 
                ON user_to_team.team_id = task.team_id 
                AND user_to_team.user_id = %(user_id)s
            WHERE task_id IN %(task_ids)s
        )
        DELETE
        FROM task
        WHERE task.task_id IN (SELECT task_id FROM prepare_for_deletion)
        RETURNING task.task_id
        ;
        '''
        params = {
            'task_ids': tuple(task_ids),
            'user_id': user.user_id
        }

        cursor.execute(query, params)
        deleted = cursor.fetchall()
        deleted_task_ids = [task.task_id for task in deleted]

        if all_or_nothing and len(deleted_task_ids) != len(task_ids):
            # could not delete some of the tasks, aborting
            db.rollback()
            raise DeletionError(list(set(task_ids) - set(deleted_task_ids)))

        db.commit()

        return deleted_task_ids
