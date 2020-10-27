from chalice import Response

from chalicelib.auth.decorators import protected
from chalicelib.core.exceptions import APIError, DeletionError, EntityNotFound
from chalicelib.core.extensions import Blueprint
from chalicelib.core.shared import g
from chalicelib.services import time_entry
from chalicelib.time_entry.schema import TimeEntry

blueprint = Blueprint(__name__)


@blueprint.route('/time-entry', methods=['POST'])
@protected
def create_time_entry():
    body = blueprint.current_request.json_body
    new_time_entry = time_entry.create(**TimeEntry().load(body))
    return Response(body=TimeEntry().dump(new_time_entry), status_code=201)


@blueprint.route('/time-entry/{time_entry_id}', methods=['PATCH'])
@protected
def update_time_entry(time_entry_id):
    body = blueprint.current_request.json_body

    try:
        updated_time_entry = time_entry.update(
            user=g.current_user,
            time_entry_id=int(time_entry_id),
            **TimeEntry().load(body, partial=True)
        )
        return Response(body=TimeEntry().dump(updated_time_entry), status_code=200)
    except EntityNotFound:
        raise APIError(status=404)


@blueprint.route('/time-entry/{time_entry_id}', methods=['DELETE'])
@protected
def delete_time_entry(time_entry_id):
    try:
        deleted_ids = time_entry.delete(user=g.current_user, time_entry_ids=(int(time_entry_id),))
    except DeletionError as error:
        raise APIError(status=404, detail=f'time entry with id {error} can not be deleted: '
                                            'no such time entry id or the time entry does not belong to the user')
    return Response(body={'deleted': deleted_ids}, status_code=200)

