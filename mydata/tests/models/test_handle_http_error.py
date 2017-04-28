"""
Test method for handling HTTP error.
"""
import unittest
import wx

from ...models import HandleHttpError
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import DoesNotExist
from ...utils.exceptions import InternalServerError
from ...utils.exceptions import BadGateway
from ...utils.exceptions import ServiceUnavailable
from ...utils.exceptions import GatewayTimeout
from ...utils.exceptions import HttpException


class MockResponse(object):
    """
    Trivial class to mock the status_code attribute of the
    responses returned by the requests library.
    """
    def __init__(self, statusCode, text=""):
        """
        Initialize a mock response instance with a status code.
        """
        # The status_code attribute should be called "status_code" to be
        # consistent with the requests library, but self.status_code clashes
        # with MyData's Pylint rules, so we use self.__dict__:
        self.__dict__['status_code'] = statusCode
        self.text = text


class HttpErrorHandlerTester(unittest.TestCase):
    """
    Test method for handling HTTP error.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)
        self.app.SetAppName("HttpErrorHandlerTester")
        self.frame = wx.Frame(None, title='HttpErrorHandlerTester')
        self.frame.Show()

    def test_handle_http_error(self):
        """
        Test method for handling HTTP error.
        """
        with self.assertRaises(Unauthorized):
            HandleHttpError(MockResponse(403))
        with self.assertRaises(DoesNotExist):
            HandleHttpError(MockResponse(404))
        with self.assertRaises(InternalServerError):
            HandleHttpError(MockResponse(500))
        with self.assertRaises(BadGateway):
            HandleHttpError(MockResponse(502))
        with self.assertRaises(ServiceUnavailable):
            HandleHttpError(MockResponse(503))
        with self.assertRaises(GatewayTimeout):
            HandleHttpError(MockResponse(504))
        with self.assertRaises(HttpException):
            HandleHttpError(MockResponse(505))

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
