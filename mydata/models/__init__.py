"""
mydata/models/__init__.py

Functionality used by multiple model classes.
"""

from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import InternalServerError
from mydata.utils.exceptions import BadGateway
from mydata.utils.exceptions import ServiceUnavailable
from mydata.utils.exceptions import GatewayTimeout
from mydata.utils.exceptions import HttpException


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
