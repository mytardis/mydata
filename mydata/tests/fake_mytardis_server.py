"""
fake_mytardis_server.py

A simple HTTP server to use for unit testing in MyData.

Many of the responses given by this fake MyTardis server
have been copied and pasted from a real MyTardis server's
responses and hard-coded below.  In some cases, unnecessary
fields have been removed from the JSON responses.
"""
# Method names like do_GET clash with our .pylintrc's naming rules:
# pylint: disable=invalid-name
# For Python3, change this to "from http.server import BaseHTTPRequestHandler":
from BaseHTTPServer import BaseHTTPRequestHandler

from .fake_mytardis_helpers.get import FakeMyTardisGet
from .fake_mytardis_helpers.post import FakeMyTardisPost
from .fake_mytardis_helpers.put import FakeMyTardisPut

# Set this to True to log URL requests:
DEBUG = False


class FakeMyTardisHandler(BaseHTTPRequestHandler):
    """
    This class is used to handle the HTTP requests that arrive at the server.

    The handler will parse the request and the headers, then call a method
    specific to the request type. The method name is constructed from the
    request. For example, for the request method SPAM, the do_SPAM() method
    will be called with no arguments. All of the relevant information is
    stored in instance variables of the handler. Subclasses should not need
    to override or extend the __init__() method.
    """
    datafileIdAutoIncrement = 0

    def do_HEAD(self):
        """
        Respond to a HEAD request
        """
        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location",
                             self.path.replace('redirect', 'different_url'))
        else:
            self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """
        Respond to a GET request.
        """
        FakeMyTardisGet(self)

    def do_POST(self):
        """
        Respond to a POST request
        """
        FakeMyTardisPost(self)

    def do_PUT(self):
        """
        Respond to a PUT request
        """
        FakeMyTardisPut(self)

    def do_PATCH(self):
        """
        Respond to a PATCH request
        """
        self.send_response(202)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """
        Supressing logging of HTTP requests to STDERR.
        """
        if DEBUG:
            BaseHTTPRequestHandler.log_message(
                self, format, *args)
