from marshmallow import ValidationError, fields, validates_schema

from chalicelib.core.schema import BaseSchema


class TimeEntry(BaseSchema):
    time_entry_id = fields.Int(dump_only=True)
    task_id = fields.Int(required=True)
    assignee_id = fields.Int(required=True)
    start_datetime = fields.AwareDateTime(required=True)
    end_datetime = fields.AwareDateTime()

    @validates_schema
    def validate_datetime(self, data, **kwargs):
        if 'start_datetime' in data and 'end_datetime' in data:
            if data['start_datetime'] > data['end_datetime']:
                raise ValidationError({'startDatetime': ['startDatetime is greater than endDatetime']})
