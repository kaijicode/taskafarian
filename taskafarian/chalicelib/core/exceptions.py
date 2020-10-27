import json

from chalice import Response

from chalicelib.core.database import get_db


def handle_exception(exception):
    response = exception.get_response()
    response.data = json.dumps({
        "status": exception.code,
        "detail": exception.description
    })
    response.content_type = "application/json"

    if exception.code == 500:
        db = get_db()
        if db:
            db.rollback()

    return response


class APIError(Exception):
    def __init__(self, status, detail=None, fields=None):
        self.detail = detail  # detailed error description
        self.status = status
        self.fields = fields  # field specific errors

    def to_http_response(self):
        return Response(
            body={'detail': self.detail, 'status': self.status, 'fields': self.fields},
            status_code=self.status,
            headers={'Content-Type': 'application/json'}
        )


class EntityNotFound(Exception):
    pass


class InvalidValue(Exception):
    pass


class DeletionError(Exception):
    pass
