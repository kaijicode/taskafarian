from chalicelib.auth.api import blueprint


def init_app(app):
    app.register_blueprint(blueprint, url_prefix='/auth')
