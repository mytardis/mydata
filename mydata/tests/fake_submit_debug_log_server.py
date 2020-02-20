"""
fake_submit_debug_log_server.py

A simple HTTP server to use for unit testing in MyData.
"""
import logging

from http.server import BaseHTTPRequestHandler

DEBUG = False

logger = logging.getLogger(__name__)


class FakeSubmitDebugLogHandler(BaseHTTPRequestHandler):
    """
    This class is used to handle the HTTP requests that arrive at the server.

    The handler will parse the request and the headers, then call a method
    specific to the request type. The method name is constructed from the
    request. For example, for the request method SPAM, the do_SPAM() method
    will be called with no arguments. All of the relevant information is
    stored in instance variables of the handler. Subclasses should not need
    to override or extend the __init__() method.
    """
    # pylint: disable=invalid-name
    def do_HEAD(self):
        """
        Respond to a HEAD request
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):
        """
        Respond to a POST request
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        length = int(self.headers['Content-Length'])
        _ = self.rfile.read(length)

        logger.info("Received POSTed data of length %s", length)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """
        Supressing logging of HTTP requests to STDERR.
        """
        if DEBUG:
            BaseHTTPRequestHandler.log_message(
                self, format, *args)
