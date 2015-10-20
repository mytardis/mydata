"""
fake_ssh_server.py

Local SSH/SCP server for testing.

It listens on port 2200, so you can connect to it as follows:

ssh -oNoHostAuthenticationForLocalhost=yes -i ~/.ssh/MyData \
        -p 2200 mydata@localhost wc -c setup.py

It can also be used to test SCP, for example, copying the file "hello"
using a Cygwin build of scp from a Windows command prompt:

scp -v -oNoHostAuthenticationForLocalhost=yes -P 2200 \
-i /cygdrive/C/Users/jsmith/.ssh/MyData \
/cygdrive/C/Users/jsmith/Desktop/hello.txt \
mydata@localhost:/cygdrive/C/Users/jsmith/hello2.txt
"""

# pylint: disable=invalid-name
# pylint: disable=missing-docstring

import SocketServer
import sys
import threading
import traceback
import subprocess
import time
import re
import logging
from cStringIO import StringIO

import paramiko
from paramiko.py3compat import decodebytes
from paramiko.message import Message
from paramiko.common import cMSG_CHANNEL_WINDOW_ADJUST

import mydata.utils.openssh as OpenSSH

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - fake_ssh_server.py - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

paramiko_logger = logging.getLogger("paramiko")
paramiko_logger.setLevel(logging.WARNING)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter(
    '%(levelname)-.3s [%(asctime)s.%(msecs)03d] thr=%(_threadid)-3d ' \
    '%(name)s: %(message)s', '%Y%m%d-%H:%M:%S'))
paramiko_logger.addHandler(handler)


class SshServerInterface(paramiko.ServerInterface):
    """
    Fake SSH/SCP Server interface.
    """
    def __init__(self):
        self.command = None
        keyPair = OpenSSH.FindKeyPair("MyData")
        # Remove "ssh-rsa " and "MyData key":
        data = bytes(keyPair.GetPublicKey().split(" ")[1])
        self.mydata_pub_key = paramiko.RSAKey(data=decodebytes(data))

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        """
        Returns:
        True if this channel is now hooked up to the stdin, stdout, and stderr
        of the executing command; False if the command will not be executed.
        """
        self.command = command
        return True

    def check_auth_password(self, username, password):
        logger.warning("JUST FOR TESTING - IGNORING password.")
        if username == 'mydata':
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if (username == 'mydata') and (key == self.mydata_pub_key):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'publickey,password'

    def check_channel_shell_request(self, channel):
        return False

    def check_channel_pty_request(self, channel, term, width, height,
                                  pixelwidth, pixelheight, modes):
        # pylint: disable=too-many-arguments
        return True


# Default host key used by ThreadedSshServer
#
DEFAULT_HOST_KEY = paramiko.RSAKey.from_private_key(StringIO(
    "-----BEGIN RSA PRIVATE KEY-----\n" \
    "MIIEowIBAAKCAQEAsIPRjSXd3zcgaBOeECY0jeperpN69SRXLu4wjfwCCI55fzLE\n" \
    "7GRR48uO5V57JH5a9tHdc2P8RVA+2ahSn/yYWV7NmZOJy7Rt79xsoHjKbxe9mlSL\n" \
    "DiN+GmGxCSFfxRQtyA0pa7qMDnXUKnFVViDc1r6WlzkOjmFPVRvvOO/fisumN8qM\n" \
    "72N82wFzI9cWPMg1cx60ioRFHJ56Oz1D43IEc7jLw4weIxp+1HDciVwN1FMGcpf5\n" \
    "9MkwYKqsu3zJKsrOJq59NwDwvGPZ0ZJHXOk8jvAdjH5fOyleQQCLdTmHZFR4gLMA\n" \
    "cz9puMjUJwHQ0+YZ+SI9w8pkmIo1EEXWo2MV3wIDAQABAoIBAQCJGPkrXhvkAVck\n" \
    "PwhnlqT/DOgZQ+cee+lTRCFmRjP2HWL0jqQwzwJjoXkNYcLXZ2STjBEqTKBl3ZvT\n" \
    "Rk9Wf8R8tYuPGu7NzwgMYvHj+a2Rd6kGM2AFzT9mkjYE120hDzk3xjFDwRKDMLVn\n" \
    "ebtEOCYOjN09+0z4/U+21QmK+ZRwoc283kJz4RcHI64GhzHxvvzVONHIgjWWzP15\n" \
    "Cnjnn3CjNTJYoa/oP6/XF7gcZqMmKN95YVkBlqcC23QAncRCmKNadShiggVEms9z\n" \
    "6nZu+0vHKUEjgSPTuq0G0yavCv/4jtWyKywdt2C+RZf1TZg4ng5jgIXVbPzzRGL/\n" \
    "gwzccvgRAoGBANxavLHltKGvNg4nxvI13GXlTEURhtOAOGpRu64/drQml+BhRf5H\n" \
    "IiR1esaVYJvwIWmAiccH/ATQ5x32EDOZnhBKE3eZxhOr1ms4MQqJlVWxKQgC6Ee+\n" \
    "NzXfdhrj9ryvdt5/CfXupsTAZkFDSCJdJ0aBCpQpamiq7qcqQvAxSCZdAoGBAM0R\n" \
    "nCrU4MMW+tWzGi/UvpMXTc74yKqG83GUl5zuuZmTE5gZmcx7+8XAhXRFe5piEPmV\n" \
    "XKIth6cNg3NFUdgfZeeUPeffbFUj8egSkMrqUBiLDQ9WasXg9Ju0aYfXiA9WkqJM\n" \
    "u6C6T7pLzxWOOt2jKZzQLjonlSv5/jebU47JvHFrAoGAfKnk+SxAjfyHM2jzl9I6\n" \
    "93bLOIQa6AsxX40QBhund3IiGHJP2/S4bzH7nN+jwXUQIhTzXaO5w6vAJWYxck/l\n" \
    "acfOzao0sqpT62Ll89U0pD9PPFYQvY3yxErBEaOI0uTd9jCfHQDAXq2O7Ds5Ux+q\n" \
    "eavFpV7s8XxK+k3hguwOqo0CgYBlRZYW/OxGzBlx4bJD/s9iurZ9SRVoSZ7974D0\n" \
    "Sly0QBMEIVh3yJ7s6Qe/BPVmp5l0eFO37743PJA3I/uoPNFJjUcJNKg+X7L+hfSl\n" \
    "kROfG0SG14mBUXfbUTxwjnst//YIWtaqKHhpKzkIjyX5ALPzMkgyBgxAHIR0F6wr\n" \
    "Lut2IwKBgAWa55IoR0jFBMuBW3WdADNI0NpXr7aAMfLR6Tq1Jub4+5cQ8w+Yv4Q2\n" \
    "1XrKzfkgaeCc3KWimMH8qWZYifbk4YB3RLQpLA6kGDeretVXs9qrSkznU6elGRsD\n" \
    "8AVaj+iDC5qISXWUQAsGrSk7/Agodrc8rsOYu1lPN01pNStQ86Tb\n" \
    "-----END RSA PRIVATE KEY-----\n"
))

class SshRequestHandler(SocketServer.BaseRequestHandler):
    """
    Handles a client address and creates a paramiko
    Transport object.
    """
    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, request, client_address, server):
        SocketServer.BaseRequestHandler.__init__(self, request, client_address,
                                                 server)
        self.timeout = 60
        self.auth_timeout = 60

        self.chan = None
        self.server_instance = None
        self.client = None
        self.transport = None

        # These are used for SCP only:
        self.verbose = False
        # modified: Only populated if scp client uses "-p".
        self.modified = None
        # accessed: Only populated if scp client uses "-p".
        self.accessed = None
        # transfer_type: C for single file copy or
        #                D for recursive directory copy.
        self.transfer_type = None
        # file_mode: POSIX permissions, e.g. 0644
        self.file_mode = None
        # file_size: File size in bytes
        self.file_size = None
        # file_name: File name
        self.file_name = None

    def setup(self):
        """
        Creates the SSH transport. Sets security options.
        """
        self.transport = paramiko.Transport(self.request)
        self.transport.add_server_key(self.server.host_key)

    def handle(self):
        """
        Start the paramiko server, this will start a thread to handle
        the connection.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches

        try:
            self.server_instance = SshServerInterface()
            self.transport.start_server(server=self.server_instance)
        except paramiko.SSHException:
            logger.error('*** SSH negotiation failed.')
            return

        logger.debug('Got a connection!')

        try:
            # wait for auth
            self.chan = self.transport.accept(20)
            if self.chan is None:
                logger.error('*** No channel.')
                try:
                    self.transport.close()
                except:  # pylint: disable=bare-except
                    logger.error(traceback.format_exc())
                return
            logger.info('Authenticated!')

            # Wait for the SSH/SCP client to provide a "remote" command.
            # (to be run locally when running a test server on 127.0.0.1).
            count = 0
            while not self.server_instance.command:
                time.sleep(0.01)
                count += 1
                if count > 100:
                    message = "\nInteractive shells are not supported.\n" \
                        "Please provide a command to be executed.\n\n"
                    logger.error(message)
                    self.chan.send_stderr(message)
                    self.chan.send_exit_status(1)
                    self.chan.close()
                    try:
                        self.transport.close()
                    except:  # pylint: disable=bare-except
                        logger.error(traceback.format_exc())
                    return

            if sys.platform.startswith("win"):
                # Use bundled Cygwin binaries for these commands:
                if self.server_instance.command.startswith("/bin/rm -f"):
                    self.server_instance.command = \
                        self.server_instance.command.replace("/bin/rm",
                                                             OpenSSH.OPENSSH.rm)
                if self.server_instance.command.startswith("mkdir"):
                    self.server_instance.command = \
                        self.server_instance.command.replace("mkdir",
                                                             OpenSSH.OPENSSH.mkdir)
                if self.server_instance.command.startswith("cat"):
                    self.server_instance.command = \
                        self.server_instance.command.replace("cat",
                                                             OpenSSH.OPENSSH.cat)
                if self.server_instance.command.startswith("scp"):
                    self.server_instance.command = \
                        self.server_instance.command.replace("scp",
                                                             OpenSSH.OPENSSH.scp)

            if "scp" not in self.server_instance.command:
                # Execute a "remote" command other than scp.
                logger.info("Executing: %s", self.server_instance.command)
                proc = subprocess.Popen(self.server_instance.command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
                stdout, _ = proc.communicate()
                self.chan.send(stdout)
                logger.info("Closing channel.")
                self.chan.send_exit_status(proc.returncode)
                self.chan.close()

            if "scp" in self.server_instance.command:
                self.verbose = ("-v" in self.server_instance.command.split(" "))
                if self.verbose:
                    logger.info("Executing: %s", self.server_instance.command)
                stderr_handle = subprocess.PIPE if self.verbose else None
                proc = subprocess.Popen(self.server_instance.command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=stderr_handle,
                                        shell=True)
                # Confirm to the channel that we started the command:
                logger.info("Waiting for the 'scp -t' process to "
                            "acknowledge that it has started up OK.")
                response = proc.stdout.read(1)
                assert response == '\0'
                self.chan.send(response)

                def read_protocol_messages():
                    """
                    The SCP protocol messages don't appear to be
                    officially documented anywhere, but they are
                    unofficially described here:
                    https://blogs.oracle.com/janp/entry/how_the_scp_protocol_works

                    The first thing we read from the client via the
                    channel will usually be the file mode, size and
                    filename (e.g. "C0644 128 hello.txt"). Or, if
                    scp has been run with the -p option, then we
                    should receive timestamps first, followed by
                    the file mode/size/filename string.

                    We pass this info onto the "remote" scp process,
                    using proc.stdin.write().
                    """
                    # pylint: disable=too-many-statements
                    while not self.chan.recv_ready():
                        time.sleep(0.01)
                    try:
                        buf = ""
                        while self.chan.recv_ready():
                            char = self.chan.recv(1)
                            proc.stdin.write(char)
                            proc.stdin.flush()
                            if char == '\n':
                                break
                            buf += char
                        match1 = re.match(
                            r"^T([0-9]+)\s+0\s+([0-9]+)\s0$", buf)
                        if match1:
                            logger.info("Received timestamps string: %s", buf)
                            # Acknowledge receipt of timestamps.
                            self.chan.send('\0')
                            self.modified = match1.group(1)
                            self.accessed = match1.group(2)
                            buf = ""
                            while self.chan.recv_ready():
                                char = self.chan.recv(1)
                                proc.stdin.write(char)
                                proc.stdin.flush()
                                if char == '\n':
                                    break
                                buf += char
                        match2 = re.match(
                            r"^([C,D])([0-7][0-7][0-7][0-7])\s+" \
                            r"([0-9]+)\s+(\S+)$", buf)
                        if match2:
                            logger.info("Received file mode/size/filename "
                                        "string: %s", buf)
                            self.transfer_type = match2.group(1)
                            self.file_mode = match2.group(2)
                            self.file_size = int(match2.group(3))
                            self.file_name = match2.group(4)
                        else:
                            raise Exception(
                                "Unknown message format: %s" % buf)
                        logger.info("Waiting for the 'scp -t' process "
                                    "to acknowledge protocol messages.")
                        response = proc.stdout.read(1)
                        assert response == '\0'
                        self.chan.send(response)
                    except:  # pylint: disable=bare-except
                        logger.error("read_protocol_messages error.")
                        logger.error(traceback.format_exc())
                        try:
                            self.transport.close()
                        except:  # pylint: disable=bare-except
                            logger.error(traceback.format_exc())
                        return

                def adjust_window_size():
                    """
                    Increasing window size (used by SSH's
                    flow control) can speed up transfers
                    of large files.


                    The message below should result in
                    a "recvd adjust" message in the client's
                    debug2 log (if using "scp -vv").
                    """
                    m = Message()
                    m.add_byte(cMSG_CHANNEL_WINDOW_ADJUST)
                    m.add_int(self.chan.get_id())
                    # This is a bit arbitrary:
                    window_size = min(2*self.file_size, 10000000)
                    m.add_int(window_size)
                    # pylint: disable=protected-access
                    self.transport._send_user_message(m)


                def read_file_content():
                    try:
                        while not self.chan.recv_ready():
                            time.sleep(0.01)

                        # Read the file content from the SSH channel,
                        # and write it into the "scp -t" subprocess:
                        chunk_size = 1024
                        while True:
                            chunk = self.chan.recv(chunk_size)
                            proc.stdin.write(chunk)
                            proc.stdin.flush()
                            if len(chunk) < chunk_size:
                                break
                    except:  # pylint: disable=bare-except
                        logger.error("read_file_content error.")
                        logger.error(traceback.format_exc())
                        try:
                            self.transport.close()
                        except:  # pylint: disable=bare-except
                            logger.error(traceback.format_exc())
                        return

                def read_remote_stderr():
                    try:
                        buf = ""
                        while True:
                            char = proc.stderr.read(1)
                            buf += char
                            if char == '\n' and self.verbose:
                                self.chan.send_stderr(buf)
                                self.chan.send('\0')
                                break
                            if char == '\0':
                                self.chan.send('\0')
                                break
                    except:  # pylint: disable=bare-except
                        logger.error("read_remote_stderr error.")
                        logger.error(traceback.format_exc())
                        try:
                            self.transport.close()
                        except:  # pylint: disable=bare-except
                            logger.error(traceback.format_exc())
                        return
                stderr_thread = \
                    threading.Thread(target=read_remote_stderr)
                stderr_thread.daemon = True
                if self.verbose:
                    stderr_thread.start()

                logger.info("Reading protocol messages...")
                read_protocol_messages()
                logger.info("Finished reading protocol messages.")
                logger.info("Adjusting window size...")
                adjust_window_size()
                logger.info("Finished adjusting window size.")
                if self.verbose:
                    logger.info("Joining stderr")
                    stderr_thread.join()
                    logger.info("Joined stderr.")

                logger.info("Reading file content and writing to scp -t...")
                read_file_content()
                logger.info(
                    "Finished reading file content and writing to scp -t.")

                logger.info("Waiting for 'scp -t' to acknowledge that it "
                            "has received all of the file content.")
                response = proc.stdout.read(1)
                assert response == '\0'
                self.chan.send(response)

                if not proc.returncode:
                    stdout, _ = proc.communicate()
                logger.info("scp -t exit code = %s", str(proc.returncode))
                # 'E' means 'end' in the SCP protocol:
                self.chan.send('E\n\0')
                self.chan.send_exit_status(proc.returncode)
                self.chan.close()
                logger.info("")
                try:
                    self.transport.close()
                except:  # pylint: disable=bare-except
                    logger.error(traceback.format_exc())
        except Exception as e:  # pylint: disable=broad-except
            logger.error('*** Caught exception: ' + str(e.__class__) + ': ' + str(e))
            logger.error(traceback.format_exc())
            try:
                self.transport.close()
            except:  # pylint: disable=bare-except
                logger.error(traceback.format_exc())
            return

    def handle_timeout(self):
        try:
            self.transport.close()
        finally:
            SocketServer.BaseRequestHandler.handle_timeout(self)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """
    ThreadedTCPServer
    """
    pass


class ThreadedSshServer(ThreadedTCPServer):
    """
    A multi-threaded test server for SSH/SCP.

    Can be used as follows:

        server = ThreadedSshServer((hostname, port))
        server.serve_forever()
    """
    # If the server stops/starts quickly, don't fail because of
    # "port in use" error.
    allow_reuse_address = True

    def __init__(self, address):
        self.host_key = DEFAULT_HOST_KEY
        SocketServer.TCPServer.__init__(self, address, SshRequestHandler)

    def shutdown_request(self, request):
        # Prevent TCPServer from closing the connection prematurely
        return

    def close_request(self, request):
        # Prevent TCPServer from closing the connection prematurely
        return


if __name__ == "__main__":
    SERVER = ThreadedSshServer(("127.0.0.1", 2200))
    try:
        logger.info("Listening on port 2200...")
        SERVER.serve_forever()
    except (SystemExit, KeyboardInterrupt):
        SERVER.server_close()
