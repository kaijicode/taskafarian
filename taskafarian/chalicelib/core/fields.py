from marshmallow import fields, validate


class Username(fields.Str):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(validate.Regexp(regex='^[a-zA-Z0-9_]+$'))

    def _deserialize(self, value, attr, data, **kwargs):
        deserialized = super()._deserialize(value, attr, data, **kwargs)
        return deserialized.lower()


class Password(fields.Str):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(validate.Length(min=8, max=32))
