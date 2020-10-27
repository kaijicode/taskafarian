from marshmallow import Schema, fields


class User(Schema):
    username = fields.String()
    email = fields.Email()
    first_name = fields.String()
    last_name = fields.String()
    created_at = fields.AwareDateTime()
    updated_at = fields.AwareDateTime()
