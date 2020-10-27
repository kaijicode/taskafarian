from chalicelib.core.api import blueprint
from chalicelib.core.database import close_db
from chalicelib.core.shared import g


def init_app(app):
    app.register_blueprint(blueprint)

    @app.middleware('http')
    def request_lifetime(event, get_response):
        # set shared variables
        # TODO: put database connection on g?
        g.current_request = app.current_request

        try:
            response = get_response(event)
            return response
        finally:
            # clean up
            g.clear()
            close_db()
