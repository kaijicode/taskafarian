from marshmallow import Schema, fields


def camelcase(s):
    parts = iter(s.split("_"))
    return next(parts) + "".join(i.title() for i in parts)


class BaseSchema(Schema):
    """Schema that uses camel-case for its external representation
    and snake-case for its internal representation.
    https://marshmallow.readthedocs.io/en/stable/examples.html
    """

    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = camelcase(field_obj.data_key or field_name)


class EntityListMeta(BaseSchema):
    total = fields.Int()
    count = fields.Int()
    offset = fields.Int()
    limit = fields.Int()
