import functools
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import any_value, timestamptz_to_str

task_resource = '/task'


# creating
def test_create_task(app, db, user_alice, user_bob):
    new_task = {
        "name": "buy milk",
        "assigneeId": user_bob.user_id,
        "status": "todo"
    }

    response = app.http.post(
        path=task_resource,
        json=new_task,
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 201

    new_task = response.json_body
    task_in_db = get_task_by_id(db, new_task['taskId'])
    assert new_task == {
        'taskId': task_in_db.task_id,
        'projectId': None,
        'teamId': None,
        'name': new_task['name'],
        'description': '',
        'estimation': None,
        'status': new_task['status'],
        'createdAt': timestamptz_to_str(task_in_db.created_at),
        'dueDate': None,
        'creator': {
            'userId': user_alice.user_id,
            'username': user_alice.username,
            'firstName': user_alice.first_name,
            'lastName': user_alice.last_name
        },
        'assignee': {
            'userId': user_bob.user_id,
            'username': user_bob.username,
            'firstName': user_bob.first_name,
            'lastName': user_bob.last_name
        }
    }


def test_unauthorized_user_can_not_create_tasks(app, db, user_alice):
    new_task = {
        "name": "buy milk",
        "assigneeId": user_alice,
        "status": "todo"
    }

    response = app.http.post(path=task_resource, json=new_task)
    assert response.status_code == 401
    assert response.json_body == {}

    with db.cursor() as cursor:
        cursor.execute('''
        SELECT * 
        FROM task 
        WHERE name = %s AND created_by = %s
        ;
        ''', (new_task['name'], user_alice.user_id))
        db.commit()
        task_in_db = cursor.fetchone()
        assert task_in_db is None


def test_can_not_create_task_without_required_fields(app, db, user_alice):
    task_count = count_tasks(db)
    new_task = {
        "assigneeId": user_alice.user_id,
        "status": "todo"
    }

    response = app.http.post(
        path=task_resource,
        json=new_task,
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 422
    assert count_tasks(db) == task_count


# reading
# TODO: add search functionality (fetch_all)

def test_get_task_by_id(app, user_alice, user_bob):
    alice_task_id = 1
    response = app.http.get(
        path=f'{task_resource}/{alice_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200
    requested_task = response.json_body

    assert requested_task == {
        'taskId': any_value,
        'projectId': 1,
        'teamId': 1,
        'name': 'add header',
        'description': '',
        'estimation': None,
        'status': requested_task['status'],
        'createdAt': any_value,
        'dueDate': None,
        'creator': {
            'userId': user_alice.user_id,
            'username': user_alice.username,
            'firstName': user_alice.first_name,
            'lastName': user_alice.last_name
        },
        'assignee': {
            'userId': user_alice.user_id,
            'username': user_alice.username,
            'firstName': user_alice.first_name,
            'lastName': user_alice.last_name
        }
    }


def test_anonymous_user_can_not_access_tasks(app):
    alice_task_id = 1
    response = app.http.get(path=f'{task_resource}/{alice_task_id}')
    assert response.status_code == 401
    assert response.json_body == {}

    response = app.http.get(path=f'{task_resource}')
    assert response.status_code == 401
    assert response.json_body == {}


def test_user_can_access_his_team_tasks(app, user_alice, user_bob):
    bob_task_id = 3
    response = app.http.get(
        path=f'{task_resource}/{bob_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200
    assert response.json_body == {
        'taskId': bob_task_id,
        'projectId': 1,
        'teamId': 1,
        'name': 'write tests for the profile update feature',
        'description': '',
        'estimation': None,
        'status': 'todo',
        'createdAt': any_value,
        'dueDate': None,
        'creator': {
            'userId': user_bob.user_id,
            'username': user_bob.username,
            'firstName': user_bob.first_name,
            'lastName': user_bob.last_name
        },
        'assignee': {
            'userId': user_bob.user_id,
            'username': user_bob.username,
            'firstName': user_bob.first_name,
            'lastName': user_bob.last_name
        }
    }


def test_user_can_not_access_tasks_of_others_teams(app, user_alice):
    dave_task_id = 101

    response = app.http.get(
        path=f'{task_resource}/{dave_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 404
    assert response.json_body == {'detail': None, 'fields': None, 'status': 404}


def test_user_can_not_access_deleted_tasks(app, db, user_alice):
    """User can not tasks after deletion
    """
    alice_task_id = 1

    alice_task = get_task_by_id(db, alice_task_id)
    assert alice_task is not None

    # delete the task
    app.http.delete(
        path=f'{task_resource}/{alice_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )

    # try to read the task
    response = app.http.get(
        path=f'{task_resource}/{alice_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 404
    assert response.json_body == {'detail': None, 'fields': None, 'status': 404}


def test_get_tasks_user_created_excluding_teams(app, db, user_alice):
    delete_all_tasks(db)
    assert count_tasks(db) == 0

    with db.cursor() as cursor:
        cursor.execute('''
        INSERT INTO task (task_id, project_id, team_id, name, description, estimation, 
                            status, created_at, created_by, due_date, assignee_id)
            VALUES  (1000, NULL, NULL, 'fix header', '', NULL, 'todo', now() - '1 day'::interval, 1, NULL, 1),
                    (1001, NULL, NULL, 'fix registration', '', NULL, 'todo', now() - '2 day'::interval, 2, NULL, 2),
                    (1002, NULL, NULL, 'change color', '', NULL, 'in_progress', now(), 1, NULL, 1)
        ;
                    
        INSERT INTO task_time_entry(time_entry_id, task_id, assignee_id, start_datetime, end_datetime)
            VALUES  (2000, 1002, 1, now() - '1 day'::interval, now() - '6 hours'::interval),
                    (2001, 1002, 1, now() - '12 hours'::interval, NULL)
        ;
        ''')
        db.commit()

    tasks = [
        # recent first
        {
            'taskId': 1002,
            'projectId': None,
            'teamId': None,
            'name': 'change color',
            'description': '',
            'estimation': None,
            'status': 'in_progress',
            'createdAt': any_value,
            'dueDate': None,
            'creator': {
                'userId': user_alice.user_id,
                'username': user_alice.username,
                'firstName': user_alice.first_name,
                'lastName': user_alice.last_name
            },
            'assignee': {
                'userId': user_alice.user_id,
                'username': user_alice.username,
                'firstName': user_alice.first_name,
                'lastName': user_alice.last_name
            },
            'timeEntries': [
                # recent first
                {
                    'timeEntryId': 2001,
                    'taskId': 1002,
                    'assigneeId': user_alice.user_id,
                    'startDatetime': any_value,
                    'endDatetime': any_value
                },
                {
                    'timeEntryId': 2000,
                    'taskId': 1002,
                    'assigneeId': user_alice.user_id,
                    'startDatetime': any_value,
                    'endDatetime': any_value
                }
            ]
        },

        {
            'taskId': 1000,
            'projectId': None,
            'teamId': None,
            'name': 'fix header',
            'description': '',
            'estimation': None,
            'status': 'todo',
            'createdAt': any_value,
            'dueDate': None,
            'creator': {
                'userId': user_alice.user_id,
                'username': user_alice.username,
                'firstName': user_alice.first_name,
                'lastName': user_alice.last_name
            },
            'assignee': {
                'userId': user_alice.user_id,
                'username': user_alice.username,
                'firstName': user_alice.first_name,
                'lastName': user_alice.last_name
            },
            'timeEntries': []
        }
    ]

    response = app.http.get(
        path=f'{task_resource}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200

    assert response.json_body == {
        'entities': tasks,
        'meta': {
            # 'total': 2,
            'count': 2,
            'offset': 0,
            'limit': 20
        }
    }


@pytest.mark.skip(reason='todo')
def test_get_tasks_user_created_and_tasks_of_his_teams():
    pass


@pytest.mark.skip(reason='todo')
def test_get_tasks_belonging_to_a_requested_team():
    pass


@pytest.mark.skip(reason='todo')
def test_get_tasks_created_by_team_member():
    pass


# updating
# rewrite - update each field separately
def test_user_can_update_task_he_created(app, db, user_alice, user_bob):
    alice_task_id = 1

    update = functools.partial(request_task_update, app, user_alice.token, alice_task_id)

    task_to_update = get_task_by_id(db, alice_task_id)
    assert task_to_update is not None

    new_due_date = datetime.now(timezone.utc) + timedelta(days=2)
    new_estimation = timedelta(days=1)
    fields_to_update = {
        'name': 'add header & animation',
        'status': 'in_progress',
        'assigneeId': user_bob.user_id,
        'dueDate': timestamptz_to_str(new_due_date),
        'estimation': 60 * 60 * 24,  # day
        'description': 'do it'
    }

    # try updating each field on its own
    assert update({'name': 'add header & animation'}).status_code == 200
    assert update({'status': 'in_progress'}).status_code == 200
    assert update({'assigneeId': user_bob.user_id}).status_code == 200
    assert update({'dueDate': timestamptz_to_str(new_due_date)}).status_code == 200
    assert update({'estimation': 60 * 60 * 24}).status_code == 200
    assert update({'description': 'do it'}).status_code == 200

    # expect database to persist the changes made
    task_in_db = get_task_by_id(db, alice_task_id)
    assert task_in_db.name == fields_to_update['name']
    assert task_in_db.status == fields_to_update['status']
    assert task_in_db.assignee_id == fields_to_update['assigneeId']
    assert task_in_db.due_date == new_due_date
    assert task_in_db.estimation == new_estimation
    assert task_in_db.description == fields_to_update['description']


# TODO
@pytest.mark.skip(reason="to implement")
def test_some_fields_can_not_be_updated(app, db, user_alice, user_bob):
    alice_task_id = 1

    alice_task = get_task_by_id(db, alice_task_id)

    # check that those fields can not be updated
    update = functools.partial(request_task_update, app, user_alice.token, alice_task_id)
    response = update({'taskId': 9999})
    assert response.status_code == 422

    response = update({'projectId': 2})
    assert response.status_code == 422

    response = update({'teamId': 2})
    assert response.status_code == 422

    response = update({
        'createdAt': timestamptz_to_str(datetime.now(timezone.utc))
    })
    assert response.status_code == 422

    response = update({
        'createdBy': user_bob.user_id
    })
    assert response.status_code == 422

    # task should remain unchanged
    assert get_task_by_id(db, alice_task_id) == alice_task


def test_can_not_update_deleted_task():
    pass


def test_user_can_update_tasks_of_his_team(app, db, user_alice):
    bob_task_id = 3

    task_to_update = get_task_by_id(db, bob_task_id)
    assert task_to_update is not None

    fields_to_update = {'name': 'write tests'}

    # update
    response = app.http.patch(
        path=f'{task_resource}/{bob_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'},
        json=fields_to_update
    )
    assert response.status_code == 200
    task_in_response = response.json_body

    task_in_db = get_task_by_id(db, bob_task_id)
    assert task_in_response['name'] == fields_to_update['name']
    assert task_in_db.name == fields_to_update['name']


def test_user_can_not_update_tasks_of_other_teams(app, db, user_alice):
    dave_task_id = 101

    task_to_update = get_task_by_id(db, dave_task_id)
    assert task_to_update is not None

    fields_to_update = {'name': 'now it belongs to us'}

    # update attempt
    response = app.http.patch(
        path=f'{task_resource}/{dave_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'},
        json=fields_to_update
    )
    assert response.status_code == 404
    assert response.json_body == {'detail': None, 'fields': None, 'status': 404}

    # dave's task should remain unchanged
    assert get_task_by_id(db, dave_task_id) == task_to_update


def test_unauthorized_user_can_not_update_tasks(app, db):
    alice_task_id = 1

    task_to_update = get_task_by_id(db, alice_task_id)
    assert task_to_update is not None

    fields_to_update = {'name': 'now it belongs to anonymous user'}

    # update attempt
    response = app.http.patch(
        path=f'{task_resource}/{alice_task_id}',
        json=fields_to_update
    )
    assert response.status_code == 401
    assert response.json_body == {}

    # should remain unchanged
    assert get_task_by_id(db, alice_task_id) == task_to_update


# deleting
def test_delete_task_user_created(app, db, user_alice):
    alice_task_id = 1

    # check that the task exists
    assert get_task_by_id(db, alice_task_id) is not None

    # request to delete the task
    response = app.http.delete(
        path=f'{task_resource}/{alice_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200

    # check that the task is gone
    assert get_task_by_id(db, alice_task_id) is None


def test_handle_deletion_of_non_existent_task(app, db, user_alice):
    alice_task_id = 1

    assert get_task_by_id(db, alice_task_id) is not None

    # request to delete the task
    response = app.http.delete(
        path=f'{task_resource}/{alice_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200

    # task can be deleted twice
    response = app.http.delete(
        path=f'{task_resource}/{alice_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 404


def test_unauthorized_user_can_not_delete_my_tasks(app, db):
    alice_task_id = 1

    # check that the task exists
    original_task = get_task_by_id(db, alice_task_id)
    assert original_task is not None

    # request to delete the task
    response = app.http.delete(path=f'{task_resource}/{alice_task_id}')
    assert response.status_code == 401
    assert response.json_body == {}

    # task should still exists as is
    assert get_task_by_id(db, alice_task_id) == original_task


def test_user_can_delete_tasks_of_his_team(app, db, user_alice):
    bob_task_id = 3

    # check bob's task exists
    bob_task = get_task_by_id(db, bob_task_id)
    assert bob_task is not None

    # delete bob's task while being logged as alice
    response = app.http.delete(
        path=f'{task_resource}/{bob_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200
    assert response.json_body == {'deleted': [bob_task_id]}

    # check bob's task is marked for deletion
    bob_task_in_db = get_task_by_id(db, bob_task_id)
    assert bob_task_in_db is None


def test_user_can_not_delete_tasks_of_other_teams(app, db, user_alice):
    dave_task_id = 101

    task_to_delete = get_task_by_id(db, dave_task_id)
    assert task_to_delete is not None

    response = app.http.delete(
        path=f'{task_resource}/{dave_task_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 404
    assert response.json_body == {
        'status': 404,
        'detail': f'task with id [{dave_task_id}] can not be deleted: '
                  f'no such task id or the task does not belong to the user',
        'fields': None
    }

    # assert dave's task should remain unchanged and present
    assert get_task_by_id(db, dave_task_id) == task_to_delete


# TODO
@pytest.mark.skip(reason="to implement")
def test_user_can_delete_multiple_tasks():
    assert False


# helpers
def get_task_by_id(db, task_id):
    with db.cursor() as cursor:
        cursor.execute('SELECT * FROM task WHERE task_id = %s', (task_id,))
        db.commit()
        return cursor.fetchone()


def request_task_update(app, token, task_id, fields):
    return app.http.patch(
        path=f'{task_resource}/{task_id}',
        headers={'Authorization': f'Bearer {token}'},
        json=fields
    )


def delete_all_tasks(db):
    with db.cursor() as cursor:
        cursor.execute('''DELETE FROM task;''')
        db.commit()


def count_tasks(db):
    with db.cursor() as cursor:
        cursor.execute('''SELECT count(*) FROM task;''')
        result = cursor.fetchone()
        return result.count


# assertions
