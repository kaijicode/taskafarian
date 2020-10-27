from chalicelib.task.api import blueprint


def init_app(app):
    app.register_blueprint(blueprint, url_prefix='/task')
