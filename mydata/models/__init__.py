"""
mydata/models/__init__.py

Functionality used by multiple model classes.
"""

from ..utils.exceptions import Unauthorized
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import InternalServerError
from ..utils.exceptions import BadGateway
from ..utils.exceptions import ServiceUnavailable
from ..utils.exceptions import GatewayTimeout
from ..utils.exceptions import HttpException


def HandleHttpError(response, message=None):
    """
    Raise an appropriate exception, depending on the HTTP status code.
    """
    if not message:
        message = response.text
    if response.status_code in (401, 403):
        raise Unauthorized(message, response)
    elif response.status_code == 404:
        raise DoesNotExist(message, response)
    elif response.status_code == 500:
        raise InternalServerError(message, response)
    elif response.status_code == 502:
        raise BadGateway(message, response)
    elif response.status_code == 503:
        raise ServiceUnavailable(message, response)
    elif response.status_code == 504:
        raise GatewayTimeout(message, response)
    else:
        raise HttpException(message, response)
