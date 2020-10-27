from chalicelib.user.api import blueprint


def init_app(app):
    app.register_blueprint(blueprint)
