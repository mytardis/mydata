"""
fake_sftp_server.py

Local SFTP server for testing

"Uploads" to this SFTP server are just written to the local filesystem
using a temporary location for unit tests.
"""
# pylint: disable=invalid-name
from __future__ import print_function

from binascii import hexlify
import logging
import os
import select
import socket
import stat
import sys
import socketserver
import time

from six import StringIO

import paramiko
from paramiko.py3compat import u
from paramiko import SFTP_OP_UNSUPPORTED, SFTP_NO_SUCH_FILE, SFTP_OK

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - fake_ssh_server.py - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

paramiko_logger = logging.getLogger("paramiko")
# With logging.DEBUG, you can see stuff like this:
# DEB [20190514-16:22:16.996] thr=2   paramiko.transport.sftp: [chan 0] Request: open
# DEB [20190514-16:22:16.998] thr=2   paramiko.transport.sftp: [chan 0] Request: write
# DEB [20190514-16:22:16.998] thr=2   paramiko.transport.sftp: [chan 0] Request: close
# DEB [20190514-16:22:16.999] thr=2   paramiko.transport.sftp: [chan 0] Request: stat
paramiko_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter(
    '%(levelname)-.3s [%(asctime)s.%(msecs)03d] thr=%(_threadid)-3d '
    '%(name)s: %(message)s', '%Y%m%d-%H:%M:%S'))
paramiko_logger.addHandler(handler)

DEFAULT_HOST_KEY_STR = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEAqxsgBz219xjj9Y1UTA0E8nlWD8tLsnpTKCnbhVriLXThY4Aj\n"
    "QAs+AUxlgWWWn1euVHyXdKoSy6fPQ0Bv+vwy7ynphCxBoCTKqhiDyx0vF0uwwG5p\n"
    "bDPKcZuYtPzOTpzX5sf9B/4Foq8PRMn8At1lAtCi4de+/IlQhMUbPJlEsgBJuxyC\n"
    "5pUGsIQwMRg92LJDrQIgj+v1kMlXt4+HsRMKGHAGh8uJizIhdNRCtrtcdAm9HPFh\n"
    "ek9aneqIhGHXP7WGf6FTzLS+FOWKoPZw5uv/aUICwuFEZ1IW5fLkYfHy95v7lmPq\n"
    "SYjAitOvYbicy6sFMRzArpD3USV48cxbrLFtlwIDAQABAoIBAFtK+rjCVU9EqYQ/\n"
    "ZuW44JXa5W9B4d6VY77/LlAloJ3uSb+EA8rM9MVOlK4InOfhqXMMkua9Q5ADthNE\n"
    "0zqPy0FOFHjgABfI6ZT9xXve01xTlzfk8Ty5GV+qTDzs0cqh5pQMylW0VB9r1fK2\n"
    "7k49AAMTfISRTyaAwURFwnV/tWZe33EiSCXxR059fiLtbrBFL68z7GO6F/JlGPrm\n"
    "ZxVv5OMEiP2bKqkjwiXNn6BSDCxg8gCfnZHreKDK8wCmx3RFEUq1Lm2nV+LPXseF\n"
    "vZt6o1yv6t46iWpJfKv/Tt9G3uPl53aPWUKoWdJ88+rG5RLOCU3y3M/CViEZXx0c\n"
    "wvvHeyECgYEA2hlFsiCh41hWfMB3MKTpNXTARcXv7vvcrMJf22E6T7R7FLeASS/C\n"
    "6ZIalvtIv2L5rBVbxLckVFNVMJ8n1ljMtk3oJCLUC/OD7raaCYSJyNvZ33pOopIp\n"
    "t1gRyB54zp3iEZQHy1L8+rGFghQLXwTxWJX0Jjujvq60o0RBWXvfkGcCgYEAyNc/\n"
    "zJ7YGz3YfgsfvX+pwB8tf1XUjWA56xHFzS9p9MUvufHS51vKRRMGW20vxHk2jvyL\n"
    "/4sSpBj+I+zbWruMredHL9zKerj28TzFkl9qsTOtHw7fHKWZmIJvvEVsKul28c2J\n"
    "8hHKfW3H3eZYyuE2aW8t0zhe5eyDTBKXSRXLO1ECgYEAr0TeAK8+yhAEuQ6G+n2c\n"
    "uIvRtIDEN98J0YAHPqrdDI6y1sw8+RO75K64VZstNDjbAlLLw8OWG3o4nPFaN2R3\n"
    "Zw4mv1uJ4uzYmq7+DSYJAHTFm1WT+gvSIHhTGep7FThGI/A9b0WK7gBZlVZ8aOj0\n"
    "90bSxSLqjWOi4Q4KIlptKIMCgYARUI1NhLw4zQInC6p22dS2nXl8qteiQJN9spCM\n"
    "+fN2iLFupGx8SauMfPFlXGpr089iUF95bnHy97yhOEBI+DZOn8vBUpWaMuwHLCgU\n"
    "UGmQUVYxgUS24Yf2X/hmEM4cfPgmLIQh/GqqmZZLiRpKk1PvjwgyV3/G7rb7DfdA\n"
    "88ILoQKBgGGrGEXxpruK3a7DKEkzsJzNcAgCioGBrmrax5rR+qvjJfhb0NCA4VBA\n"
    "uE3OKwr2yCnxvFeaV+zfw1tszUbAqQ/67eA/DENNIqEoIZdnP4g1IPCNqOLh52f1\n"
    "IHwV0fkKk9NyOwK64zenMD0fAEBpf5brhu+1jtt45giKCixOBfqu\n"
    "-----END RSA PRIVATE KEY-----")
DEFAULT_HOST_KEY = paramiko.RSAKey.from_private_key(
    StringIO(DEFAULT_HOST_KEY_STR))

print("Read key: " + u(hexlify(DEFAULT_HOST_KEY.get_fingerprint())))


class SshServerInterface(paramiko.ServerInterface):
    """
    First we defined the SSH server interface,
    then we'll define the SFTP subsytem below
    """
    authorized_keys = [(
        b"AAAAB3NzaC1yc2EAAAABIwAAAIEAyO4it3fHlmGZWJaGrfeHOVY7RWO3P9M7hp"
        b"fAu7jJ2d7eothvfeuoRFtJwhUmZDluRdFyhFY/hFAh76PJKGAusIqIQKlkJxMC"
        b"KDqIexkgHAfID/6mqvmnSJf0b5W8v5h2pI/stOSwTQ+pxVhwJ9ctYDhRSlF0iT"
        b"UWT10hcuO4Ks8="
    )]

    def __init__(self):
        super(SshServerInterface, self).__init__()
        self.username = None
        self.user = None

    def check_auth_publickey(self, username, key):
        """
        Determine if a given key supplied by the client is acceptable for use
        in authentication.

        Return ``AUTH_FAILED`` if the key is not accepted,
        ``AUTH_SUCCESSFUL`` if the key is accepted and completes the
        authentication, or ``AUTH_PARTIALLY_SUCCESSFUL`` if your
        authentication is stateful, and this password is accepted for
        authentication, but more authentication is required.

        :param str username: the username of the authenticating client
        :param .PKey key: the key object provided by the client
        :return:
            ``AUTH_FAILED`` if the client can't authenticate with this key;
            ``AUTH_SUCCESSFUL`` if it can; ``AUTH_PARTIALLY_SUCCESSFUL`` if it
            can authenticate with this key but must continue with
            authentication
        :rtype: int
        """
        print("Auth attempt with key: " + u(hexlify(key.get_fingerprint())))
        if (username == "mydata") and (
                key.get_base64().encode('ascii') in
                SshServerInterface.authorized_keys):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        """
        Return a list of authentication methods supported by the server.
        This list is sent to clients attempting to authenticate, to inform them
        of authentication methods that might be successful.

        The "list" is actually a string of comma-separated names of types of
        authentication.  Possible values are ``"password"``, ``"publickey"``,
        and ``"none"``.

        The default implementation always returns ``"password"``.

        :param str username: the username requesting authentication.
        :return: a comma-separated `str` of authentication types
        """
        return "publickey"

    def check_channel_request(self, kind, chanid):
        """
        Determine if a channel request of a given type will be granted, and
        return ``OPEN_SUCCEEDED`` or an error code.  This method is
        called in server mode when the client requests a channel, after
        authentication is complete.

        The return value should either be ``OPEN_SUCCEEDED`` (or
        ``0``) to allow the channel request, or one of the following error
        codes to reject it:

            - ``OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED``
            - ``OPEN_FAILED_CONNECT_FAILED``
            - ``OPEN_FAILED_UNKNOWN_CHANNEL_TYPE``
            - ``OPEN_FAILED_RESOURCE_SHORTAGE``

        The default implementation always returns
        ``OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED``.

        :param str kind:
            the kind of channel the client would like to open (usually
            ``"session"``).
        :param int chanid: ID of the channel
        :return: an `int` success or failure code (listed above)
        """
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


class SftpServerInterface(paramiko.SFTPServerInterface):
    """
    This class defines an interface for controlling the behavior of paramiko
    when using the SFTPServer subsystem to provide an SFTP server.

    Methods on this class are called from the SFTP session's thread, so you can
    block as long as necessary without affecting other sessions (even other
    SFTP sessions). However, raising an exception will usually cause the SFTP
    session to abruptly end, so you will usually want to catch exceptions and
    return an appropriate error code.

    All paths are in string form instead of unicode because not all SFTP
    clients & servers obey the requirement that paths be encoded in UTF-8.
    """
    def stat(self, path):
        """
        Return an `.SFTPAttributes` object for a path on the server, or an
        error code.  If your server supports symbolic links (also known as
        "aliases"), you should follow them.  (`lstat` is the corresponding
        call that doesn't follow symlinks/aliases.)

        :param str path:
            the requested path (relative or absolute) to fetch file statistics
            for.
        :return:
            an `.SFTPAttributes` object for the given file, or an SFTP error
            code (like ``SFTP_PERMISSION_DENIED``).
        """
        if not os.path.exists(path):
            return SFTP_NO_SUCH_FILE
        sftp_stat = paramiko.SFTPAttributes()
        sftp_stat.filename = os.path.split(path)[1]
        sftp_stat.st_size = os.path.getsize(path)
        if os.path.isdir(path):
            sftp_stat.st_mode = 0o777 | stat.S_IFDIR
        else:
            sftp_stat.st_mode = 0o777 | stat.S_IFREG
        sftp_stat.st_uid = 1000
        sftp_stat.st_gid = 1000
        sftp_stat.st_atime = time.time()
        sftp_stat.st_mtime = time.time()
        return sftp_stat

    def open(self, path, flags, attr):
        """
        Open a file on the server and create a handle for future operations
        on that file.  On success, a new object subclassed from L{SFTPHandle}
        should be returned.  This handle will be used for future operations
        on the file (read, write, etc).  On failure, an error code such as
        L{SFTP_PERMISSION_DENIED} should be returned.

        C{flags} contains the requested mode for opening (read-only,
        write-append, etc) as a bitset of flags from the C{os} module:

            - C{os.O_RDONLY}
            - C{os.O_WRONLY}
            - C{os.O_RDWR}
            - C{os.O_APPEND}
            - C{os.O_CREAT}
            - C{os.O_TRUNC}
            - C{os.O_EXCL}

        (One of C{os.O_RDONLY}, C{os.O_WRONLY}, or C{os.O_RDWR} will always
        be set.)

        The C{attr} object contains requested attributes of the file if it
        has to be created.  Some or all attribute fields may be missing if
        the client didn't specify them.

        @note: The SFTP protocol defines all files to be in "binary" mode. \
            There is no equivalent to python's "text" mode.

        :param str path: the requested file path
        :param int flags: flags or'd together from the C{os} module indicating \
            the requested mode for opening the file.
        :param SFTPAttributes attr: requested attributes of the file if it is \
            newly created.
        :returns: a new L{SFTPHandle} I{or error code}.
        :rtype: SFTPHandle
        """
        handle = MyDataSFTPHandle(path, flags)
        return handle

    def mkdir(self, path, attr):
        """
        :param str path: requested path (relative or absolute) of the new folder
        :param SFTPAttributes attr: requested attributes of the new folder
        :returns: an SFTP error code int like SFTP_OK
        """
        os.mkdir(path)
        return SFTP_OK

    def chattr(self, path, attr):
        """
        Change the attributes of a file. The attr object will contain only
        those fields provided by the client in its request, so you should
        check for the presence of fields before using them.

        :param str path: requested path (relative or absolute) of the file to
                         change.
        :param SFTPAttributes attr: requested attributes to change on the file
                                    (an SFTPAttributes object)
        :returns: an error code int like SFTP_OK.
        """
        # We don't really need to implement this for the fake SFTP server,
        # we just need the client (unit test) to think that it can change
        # file attributes like st_mode through the SFTP subsystem
        return SFTP_OK


class SftpRequestHandler(socketserver.BaseRequestHandler):
    """
    Handles a client address and creates a paramiko
    Transport object.
    """
    def __init__(self, request, client_address, server):
        try:
            socketserver.BaseRequestHandler.__init__(
                self, request, client_address, server)
        except (socket.error, select.error, EOFError) as err:
            logger.error(
                "Couldn't create SftpRequestHandler instance: %s\n", str(err))
            return
        self.timeout = 60
        self.auth_timeout = 60

        self.chan = None
        self.server = None
        self.client = None
        self.transport = None

    def setup(self):
        """
        Creates the SSH transport. Sets security options.
        """
        self.transport = paramiko.Transport(self.request)
        self.transport.add_server_key(self.server.host_key)
        self.transport.set_subsystem_handler(
            'sftp', paramiko.SFTPServer, SftpServerInterface)

    def handle(self):
        """
        Start the paramiko server, this will start a thread to handle
        the connection.
        """
        self.transport.start_server(server=SshServerInterface())

    def close_transport(self, success):
        """
        Close the transport and log any errors
        """
        try:
            SftpRequestHandler.NEED_TO_ABORT = not success
            self.transport.close()
        except Exception:
            logger.exception("Failed to close transport")

    def handle_timeout(self):
        """
        Close SSH transport in the event of a timeout.
        """
        try:
            self.transport.close()
        finally:
            self.server.handle_timeout()


class MyDataSFTPHandle(paramiko.SFTPHandle):
    '''
    SFTP File Handle
    '''

    def __init__(self, path, flags=0):
        """
        Create a new file handle

        :param str path: the requested file path
        :param int flags: optional flags as passed \
            to L{SFTPServerInterface.open}
        """
        super(MyDataSFTPHandle, self).__init__(flags=flags)
        if flags & os.O_RDONLY:
            self.readfile = open(path, 'rb')
        if flags & os.O_WRONLY:
            self.writefile = open(path, 'wb')
        if flags & os.O_RDWR:
            self.writefile = open(path, 'r+b')

    def stat(self):
        """
        Return an L{SFTPAttributes} object referring to this open file, or an
        error code.  This is equivalent to L{SFTPServerInterface.stat}, except
        it's called on an open file instead of a path.

        @return: an attributes object for the given file, or an SFTP error \
            code (like L{SFTP_PERMISSION_DENIED}).
        @rtype: L{SFTPAttributes} I{or error code}
        """
        logger.warning("MyDataSFTPHandle.stat method called!\n")
        return SFTP_OP_UNSUPPORTED


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    ThreadedTCPServer
    """


class ThreadedSftpServer(ThreadedTCPServer):
    """
    A multi-threaded test server for SFTP.

    Can be used as follows:

        server = ThreadedSftpServer((hostname, port))
        server.serve_forever()
    """
    # If the server stops/starts quickly, don't fail because of
    # "port in use" error.
    allow_reuse_address = True

    def __init__(self, address):
        self.host_key = DEFAULT_HOST_KEY
        socketserver.TCPServer.__init__(self, address, SftpRequestHandler)

    def shutdown_request(self, request):
        """
        Called to shutdown and close an individual request.

        See https://hg.python.org/cpython/file/2.7/Lib/SocketServer.py#l466

        We don't call automatically call
        socketserver.TCPServer.shutdown_request() to prevent
        TCPServer from closing the connection prematurely
        """
        # pylint: disable=unused-argument
        return

    def close_request(self, request):
        """
        Called to clean up an individual request.

        See https://hg.python.org/cpython/file/2.7/Lib/SocketServer.py#l476

        We don't call socketserver.TCPServer.close_request() to prevent
        TCPServer from closing the connection prematurely
        """
        # pylint: disable=unused-argument
        return


if __name__ == "__main__":
    SFTP_PORT = 2200
    SERVER = ThreadedSftpServer(('127.0.0.1', 2200))
    try:
        SERVER.serve_forever()
    except (SystemExit, KeyboardInterrupt):
        SERVER.server_close()
