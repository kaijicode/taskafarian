import os

from chalice import Chalice, CORSConfig

from chalicelib import auth, core, task, time_entry, user

app = Chalice(app_name='chalicarian')
app.api.cors = CORSConfig(
    allow_origin=os.environ.get('TASKAFARIAN_ALLOWED_ORIGIN')
)

core.init_app(app)
auth.init_app(app)
user.init_app(app)
task.init_app(app)
time_entry.init_app(app)
