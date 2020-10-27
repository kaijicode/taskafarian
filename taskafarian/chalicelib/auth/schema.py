from marshmallow import fields

from chalicelib.core import fields as custom_fields
from chalicelib.core.schema import BaseSchema


class RegistrationSchema(BaseSchema):
    username = custom_fields.Username(required=True)
    email = fields.Email(required=True)
    password = custom_fields.Password(write_only=True, required=True)
    first_name = fields.String()
    last_name = fields.String()
    created_at = fields.AwareDateTime(read_only=True)
    updated_at = fields.AwareDateTime(read_only=True)


class LoginCredentials(BaseSchema):
    username = custom_fields.Username(required=True)
    password = custom_fields.Password(required=True)


class Token(BaseSchema):
    token = fields.Str()
    expires_at = fields.AwareDateTime()


class ActivationToken(BaseSchema):
    token = fields.Str(required=True)


class PasswordResetRequestDetails(BaseSchema):
    email = fields.Email(required=True)


class PasswordChange(BaseSchema):
    new_password = custom_fields.Password(required=True)
    token = fields.String(required=True)
