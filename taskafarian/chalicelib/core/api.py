from chalice import Response

from chalicelib.core.database import check_connection
from chalicelib.core.extensions import Blueprint

blueprint = Blueprint(__name__)


@blueprint.route('/health', methods=['GET'])
def health_check():
    check_connection()

    return Response(
        body={'status': 'ok'},
        status_code=200
    )
