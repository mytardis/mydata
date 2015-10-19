"""
fake_ssh_server.py

based on Paramiko's demo_server.py:

https://github.com/paramiko/paramiko/blob/master/demos/demo_server.py

It listens on port 2200, so you can connect to it as follows:

ssh -oNoHostAuthenticationForLocalhost=yes -i ~/.ssh/MyData \
        -p 2200 mydata@localhost wc -c setup.py

When running the above SSH client request, the following STDOUT appears
on the client side:

   20768 setup.py

When running the above SSH client request, the following STDOUT appears from
fake_ssh_server.py:

Listening for an SSH/SCP connection on port 2200...
Got a connection!
Client asked us to execute: wc -c setup.py
Authenticated!
Executing: wc -c setup.py

It can also be used to test SCP, for example, copying the file "hello"
using a Cygwin build of scp from a Windows command prompt:

scp -v -oNoHostAuthenticationForLocalhost=yes -P 2200 \
-i /cygdrive/C/Users/jsmith/.ssh/MyData \
/cygdrive/C/Users/jsmith/Desktop/hello.txt \
mydata@localhost:/cygdrive/C/Users/jsmith/hello2.txt
"""

# pylint: disable=invalid-name
# pylint: disable=missing-docstring

import socket
import sys
import threading
import traceback
import subprocess
import time
import re
import logging

import paramiko
from paramiko.py3compat import decodebytes
from paramiko.message import Message
from paramiko.common import cMSG_CHANNEL_WINDOW_ADJUST

import mydata.utils.openssh as OpenSSH

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - fake_ssh_server.py - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

paramiko_logger = logging.getLogger("paramiko")
paramiko_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter(
    '%(levelname)-.3s [%(asctime)s.%(msecs)03d] thr=%(_threadid)-3d ' \
    '%(name)s: %(message)s', '%Y%m%d-%H:%M:%S'))
paramiko_logger.addHandler(handler)

host_key = paramiko.RSAKey.generate(1024)


class Server(paramiko.ServerInterface):
    """
    Fake SSH Server
    """
    keyPair = OpenSSH.FindKeyPair("MyData")
    # Remove "ssh-rsa " and "MyData key":
    data = bytes(keyPair.GetPublicKey().split(" ")[1])
    mydata_pub_key = paramiko.RSAKey(data=decodebytes(data))

    def __init__(self):
        self.event = threading.Event()
        self.command = None

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
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height,
                                  pixelwidth, pixelheight, modes):
        # pylint: disable=too-many-arguments
        return True

logger.debug("Initializing socket for fake SSH server.")
try:
    SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    SOCK.bind(('127.0.0.1', 2200))
except Exception as e:  # pylint: disable=broad-except
    logger.error(traceback.format_exc())
    sys.exit(1)

logger.debug("Initialized socket for fake SSH server.")

class ChannelListener(object):
    """
    Listen for SSH/SCP connection.
    """
    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, sock):
        self.sock = sock
        self.chan = None
        self.server = None
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

    def listen(self):
        # pylint: disable=too-many-branches
        try:
            backlog = 0
            self.sock.listen(backlog)
            logger.info('Listening for an SSH/SCP connection on port 2200...')
            self.client, _ = self.sock.accept()
        except Exception as e:  # pylint: disable=broad-except
            logger.error('*** Listen/accept failed: %s', str(e))
            logger.error(traceback.format_exc())
            return

    def handle(self):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        self.transport = paramiko.Transport(self.client)
        self.transport.add_server_key(host_key)

        self.server = Server()

        try:
            self.transport.start_server(server=self.server)
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

            # Wait for the SSH/SCP client to provide a remote command.
            count = 0
            while not self.server.command:
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
                if self.server.command.startswith("/bin/rm -f"):
                    self.server.command = \
                        self.server.command.replace("/bin/rm",
                                                    OpenSSH.OPENSSH.rm)
                if self.server.command.startswith("mkdir"):
                    self.server.command = \
                        self.server.command.replace("mkdir",
                                                    OpenSSH.OPENSSH.mkdir)
                if self.server.command.startswith("cat"):
                    self.server.command = \
                        self.server.command.replace("cat",
                                                    OpenSSH.OPENSSH.cat)
                if self.server.command.startswith("scp"):
                    self.server.command = \
                        self.server.command.replace("scp",
                                                    OpenSSH.OPENSSH.scp)

            if "scp" not in self.server.command:
                # Execute a remote command other than scp.
                logger.info("Executing: %s", self.server.command)
                proc = subprocess.Popen(self.server.command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
                stdout, _ = proc.communicate()
                self.chan.send(stdout)
                logger.info("Closing channel.")
                self.chan.send_exit_status(proc.returncode)
                self.chan.close()

            if "scp" in self.server.command:
                if "-v" in self.server.command.split(" "):
                    self.verbose = True
                if self.verbose:
                    logger.info("Executing: %s", self.server.command)
                stderr_handle = subprocess.PIPE if self.verbose else None
                proc = subprocess.Popen(self.server.command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=stderr_handle,
                                        shell=True)
                # Confirm to the channel that we started the command:
                self.chan.send('\0')

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
                            # Acknowledge receipt of file modes.
                            self.chan.send('\0')
                            buf = ""
                        else:
                            raise Exception(
                                "Unknown message format: %s" % buf)
                    except socket.error:
                        logger.error("read_protocol_messages socket error.")
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
                    except socket.error:
                        logger.error("read_file_content socket error.")
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
                    except socket.error:
                        logger.error("read_remote_stderr socket error.")
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

                logger.info("Reading file content...")
                read_file_content()
                logger.info("Finished reading file content.")

                if not proc.returncode:
                    stdout, _ = proc.communicate()
                logger.info("scp -t exit code = %s", str(proc.returncode))
                self.chan.send('\0')
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

while True:
    channelListener = ChannelListener(SOCK)
    channelListener.listen()
    def handle():
        try:
            channelListener.handle()
        except EOFError, err:
            if err is not None and str(err).strip() != "":
                logger.error(str(err))
    handler = threading.Thread(target=handle)
    handler.start()
