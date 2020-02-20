"""
Utility methods for tests.
"""
import select
import socket
import sys
import time
import threading
from socketserver import ThreadingMixIn

from http.Server import HTTPServer

import requests

from .fake_mytardis_server import FakeMyTardisHandler
from ..logs import logger


def GetEphemeralPort():
    """
    Return an unused ephemeral port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def StartFakeMyTardisServer(host="127.0.0.1"):
    """
    Start fake MyTardis server.
    """
    port = GetEphemeralPort()
    httpd = ThreadedHTTPServer((host, port), FakeMyTardisHandler)

    def FakeMyTardisServer():
        """ Run fake MyTardis server """
        try:
            httpd.serve_forever()
        except (socket.error, select.error, EOFError) as err:
            sys.stderr.write(
                "FakeMyTardisServer aborted with error: %s\n" % str(err))

    thread = threading.Thread(target=FakeMyTardisServer,
                              name="FakeMyTardisServerThread")
    thread.start()

    return host, port, httpd, thread


def WaitForFakeMyTardisServerToStart(url):
    """
    Wait for fake MyTardis server to start.
    """
    logger.debug("Waiting for fake MyTardis server to start...\n")
    attempts = 0
    while True:
        try:
            attempts += 1
            requests.get(url + "/api/v1/?format=json", timeout=1)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.25)
            if attempts > 10:
                raise


def Subtract(str1, str2):
    """
    Subtract strings, e.g. "foobar" - "foo" = "bar"
    to isolate recently added logs from total log history.
    """
    return "".join(str1.rsplit(str2))
