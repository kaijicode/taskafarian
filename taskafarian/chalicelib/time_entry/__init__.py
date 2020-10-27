from chalicelib.time_entry.api import blueprint


def init_app(app):
    app.register_blueprint(blueprint)
