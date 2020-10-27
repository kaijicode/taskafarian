from datetime import datetime, timedelta, timezone

from tests.conftest import timestamptz_to_str

time_entry_resource = '/time-entry'


# creating
def test_create_time_entry(app, db, user_alice):
    alice_task_id = 1
    start_time = datetime.now(timezone.utc)

    response = app.http.post(
        path=f'{time_entry_resource}/',
        json={
            'taskId': alice_task_id,
            'startDatetime': timestamptz_to_str(start_time),
            'assigneeId': 1
        },
        headers={'Authorization': f'Bearer {user_alice.token}'})
    assert response.status_code == 201

    new_time_entry = response.json_body

    db_time_entry = get_time_entry_by_id(db, new_time_entry['timeEntryId'])
    assert new_time_entry == {
        'timeEntryId': db_time_entry.time_entry_id,
        'taskId': alice_task_id,
        'assigneeId': 1,
        'startDatetime': timestamptz_to_str(db_time_entry.start_datetime),
        'endDatetime': None,
    }


def test_unauthorized_user_can_not_create_time_entry(app, db):
    # try to create a new time entry as unauthorized user
    alice_task_id = 1
    start_time = datetime.now(timezone.utc)

    response = app.http.post(
        path=f'{time_entry_resource}/',
        json={
            'taskId': alice_task_id,
            'startDatetime': timestamptz_to_str(start_time),
            'assigneeId': 1
        })
    assert response.status_code == 401
    assert response.json_body == {}

    # expect time entry not to be found in db
    db_time_entry = get_time_entry_by_start_datetime(db, start_datetime=start_time)
    assert db_time_entry is None

# reading
# -


# updating
def test_update_time_entry_date_time(app, db, user_alice):
    time_entry_id = 1
    start_datetime = datetime.now(tz=timezone.utc)
    end_datetime = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    response = app.http.patch(
        path=f'{time_entry_resource}/{time_entry_id}',
        json={
            'startDatetime': timestamptz_to_str(start_datetime),
            'endDatetime': timestamptz_to_str(end_datetime)
        },
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200

    response_time_entry = response.json_body
    assert response_time_entry == {
        'timeEntryId': time_entry_id,
        'taskId': 1,
        'assigneeId': 1,
        'startDatetime': timestamptz_to_str(start_datetime),
        'endDatetime': timestamptz_to_str(end_datetime)
    }

    time_entry_in_db = get_time_entry_by_id(db, time_entry_id)
    assert time_entry_in_db._asdict() == {
        'time_entry_id': time_entry_id,
        'task_id': 1,
        'assignee_id': 1,
        'start_datetime': start_datetime,
        'end_datetime': end_datetime
    }


def test_unauthorized_user_can_not_update_time_entry(app, db):
    alice_time_entry_id = 1
    end_datetime = datetime.now(timezone.utc)

    # get time entry to compare
    db_previous_time_entry = get_time_entry_by_id(db, alice_time_entry_id)

    # try to make a change as anonymous user
    response = app.http.patch(
        path=f'{time_entry_resource}/{alice_time_entry_id}',
        json={'endDatetime': timestamptz_to_str(end_datetime)})
    assert response.status_code == 401

    # get current time entry after attempted change
    db_current_time_entry = get_time_entry_by_id(db, alice_time_entry_id)

    # should remain unchanged
    assert db_previous_time_entry == db_current_time_entry


def test_user_can_not_update_time_entries_of_his_team(app, db, user_alice):
    bob_time_entry_id = 2
    db_previous_time_entry = get_time_entry_by_id(db, bob_time_entry_id)
    end_datetime = datetime.now(timezone.utc)

    # alice attempts to modify bob's time entry
    response = app.http.patch(
        path=f'{time_entry_resource}/{bob_time_entry_id}',
        json={'endDatetime': timestamptz_to_str(end_datetime)},
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 404
    assert response.json_body == {'detail': None, 'fields': None, 'status': 404}

    # check bob's time entry to be unchanged
    db_current_time_entry = get_time_entry_by_id(db, bob_time_entry_id)
    assert db_previous_time_entry == db_current_time_entry


def test_user_can_not_update_time_entries_of_other_teams(app, db, user_alice):
    dave_time_entry_id = 102
    start_datetime = datetime.now(timezone.utc)

    original_time_entry = get_time_entry_by_id(db, dave_time_entry_id)
    assert original_time_entry is not None

    # alice attempts to change dave's time entry
    response = app.http.patch(
        path=f'{time_entry_resource}/{dave_time_entry_id}',
        json={'startDatetime': timestamptz_to_str(start_datetime)},
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 404
    assert response.json_body == {'detail': None, 'fields': None, 'status': 404}

    # time entry remains unchanged
    assert get_time_entry_by_id(db, dave_time_entry_id) == original_time_entry


# deleting
def test_delete_time_entry(app, db, user_alice):
    alice_time_entry_id = 1

    time_entry = get_time_entry_by_id(db, alice_time_entry_id)
    count_task_time_entries = count_time_entries_for_task(db, time_entry.task_id)
    assert time_entry is not None

    response = app.http.delete(
        path=f'{time_entry_resource}/{alice_time_entry_id}',
        headers={'Authorization': f'Bearer {user_alice.token}'}
    )
    assert response.status_code == 200

    deleted_ids = response.json_body['deleted']
    assert deleted_ids == [1]
    assert get_time_entry_by_id(db, alice_time_entry_id) is None
    assert count_time_entries_for_task(db, time_entry.task_id) == count_task_time_entries - 1


def test_unauthorized_user_can_not_delete_time_entry(app, db):
    alice_time_entry_id = 1

    db_previous_time_entry = get_time_entry_by_id(db, alice_time_entry_id)
    count_time_entries = count_time_entries_for_task(db, db_previous_time_entry.task_id)
    assert db_previous_time_entry is not None

    response = app.http.delete(path=f'{time_entry_resource}/{alice_time_entry_id}')
    assert response.status_code == 401
    assert response.json_body == {}

    assert get_time_entry_by_id(db, alice_time_entry_id) == db_previous_time_entry
    assert count_time_entries_for_task(db, db_previous_time_entry.task_id) == count_time_entries


def test_user_can_not_delete_time_entries_of_team_members(app, db, user_alice):
    dave_time_entry_id = 4  # dave's time entry that belongs to the Web Team (same as alice)
    assert_can_not_delete_time_entry(app, db, user_alice, dave_time_entry_id)


def test_user_can_not_delete_time_entries_of_other_teams(app, db, user_alice):
    dave_time_entry_id = 102  # dave's time entry that belongs to Dev Ops Team (different from alice)
    assert_can_not_delete_time_entry(app, db, user_alice, dave_time_entry_id)


# helpers
def assert_can_not_delete_time_entry(app, db, user, time_entry_id):
    # expect the time entry to exist
    original_time_entry = get_time_entry_by_id(db, time_entry_id)
    assert original_time_entry is not None
    count_time_entries = count_time_entries_for_task(db, original_time_entry.task_id)

    # user tries to delete time entry not belonging to him
    response = app.http.delete(
        path=f'{time_entry_resource}/{time_entry_id}',
        headers={'Authorization': f'Bearer {user.token}'}
    )
    assert response.status_code == 404
    assert response.json_body == {'detail': f'time entry with id {[time_entry_id]} can not be deleted: '
                                            'no such time entry id or the time entry does not belong to the user',
                                  'fields': None,
                                  'status': 404}

    # the time entry should remain and be unchanged
    assert get_time_entry_by_id(db, time_entry_id) == original_time_entry
    assert count_time_entries_for_task(db, original_time_entry.task_id) == count_time_entries


def get_time_entry_by_id(db, time_entry_id):
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT *
        FROM task_time_entry
        WHERE time_entry_id = %s
        ;
        ''', (time_entry_id, ))
        db.commit()
        return cursor.fetchone()


def get_time_entry_by_start_datetime(db, start_datetime):
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT *
        FROM task_time_entry
        WHERE start_datetime = %s
        ;
        ''', (start_datetime, ))
        db.commit()
        return cursor.fetchone()


def count_time_entries_for_task(db, task_id):
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT count(*)
        FROM task_time_entry
        WHERE task_id = %s
        ;
        ''', (task_id, ))
        db.commit()
        return cursor.fetchone().count
