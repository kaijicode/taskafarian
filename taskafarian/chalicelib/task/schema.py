from marshmallow import ValidationError, fields, validate

from chalicelib.core.schema import BaseSchema, EntityListMeta
from chalicelib.services.task import StatusEnum


class Status(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        possible_status = [enum_value.value for enum_value in StatusEnum]
        if value not in possible_status:
            raise ValidationError('status is not one of: ' + ', '.join(possible_status))
        return value


class User(BaseSchema):
    user_id = fields.Int()
    username = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()


class TimeEntry(BaseSchema):
    time_entry_id = fields.Int()
    task_id = fields.Int()
    assignee_id = fields.Int()
    start_datetime = fields.Str()  # comes as a string from the database
    end_datetime = fields.Str()  # same here


class Task(BaseSchema):
    task_id = fields.Int(strict=True, dump_only=True)
    project_id = fields.Int(strict=True)
    team_id = fields.Int(strict=True)
    name = fields.Str(required=True, validate=validate.Length(min=3, max=255))
    description = fields.Str()
    estimation = fields.TimeDelta()
    status = Status(required=True)
    created_at = fields.AwareDateTime(dump_only=True)
    created_by = fields.Int(dump_only=True)
    assignee_id = fields.Int(strict=True)
    due_date = fields.AwareDateTime()
    creator = fields.Nested(User, dump_only=True)
    assignee = fields.Nested(User, dump_only=True)
    time_entries = fields.Nested(TimeEntry, many=True, dump_only=True)


class TaskList(BaseSchema):
    entities = fields.Nested(Task, many=True)
    meta = fields.Nested(EntityListMeta)
