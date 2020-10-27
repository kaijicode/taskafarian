from chalice import Response

from chalicelib.auth.decorators import protected
from chalicelib.core.exceptions import APIError, EntityNotFound
from chalicelib.core.extensions import Blueprint
from chalicelib.core.shared import g
from chalicelib.services import task
from chalicelib.services.task import DeletionError
from chalicelib.task.schema import Task, TaskList

blueprint = Blueprint(__name__)


@blueprint.route('/', methods=['POST'])
@protected
def create_new_task():
    body = blueprint.current_request.json_body

    task_details = Task().load(body)
    task_details['created_by'] = g.current_user.user_id
    new_task = task.create_task(user=g.current_user, **task_details)
    return Response(body=Task().dump(new_task), status_code=201)


@blueprint.route('/', methods=['GET'])
@protected
def get_many_tasks():
    return Response(
        body=TaskList().dump(task.fetch_many(user=g.current_user)),
        status_code=200
    )


@blueprint.route('/{task_id}', methods=['GET'])
@protected
def get_task(task_id):
    requested_task = task.fetch(g.current_user, int(task_id))
    if requested_task:
        return Response(body=Task().dump(requested_task), status_code=200)

    raise APIError(status=404)


@blueprint.route('/{task_id}', methods=['DELETE'])
@protected
def delete_task(task_id):
    try:
        deleted_task_ids = task.delete_tasks(g.current_user, (int(task_id),))
        return Response(body={'deleted': deleted_task_ids}, status_code=200)
    except DeletionError as error:
        raise APIError(status=404, detail=f'task with id {error} can not be deleted: '
                                            'no such task id or the task does not belong to the user')


@blueprint.route('/{task_id}', methods=['PATCH'])
@protected
def update_task(task_id):
    body = blueprint.current_request.json_body

    try:
        updated_fields = Task().load(body, partial=True)
        updated_task = task.update_task(g.current_user, int(task_id), updated_fields)
        return Response(body=Task().dump(updated_task), status_code=200)
    except EntityNotFound:
        raise APIError(status=404)
