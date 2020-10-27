import psycopg2
from marshmallow import Schema, fields
from psycopg2.extras import NamedTupleCursor

db = psycopg2.connect(
    host='0.0.0.0',
    port='5555',
    dbname='taskafarian',
    user='taskafarian',
    password='taskafarian',
    cursor_factory=NamedTupleCursor
)


class User(Schema):
    username = fields.String()
    email = fields.Email()
    first_name = fields.String()
    last_name = fields.String()
    created_at = fields.AwareDateTime()
    updated_at = fields.AwareDateTime()


try:
    with db.cursor() as cursor:
        query = '''
        SELECT *
        FROM app_user
        WHERE user_id = 1
        ;
        '''
        cursor.execute(query)
        user = cursor.fetchone()

        print(User().dump(user))
finally:
    db.close()
