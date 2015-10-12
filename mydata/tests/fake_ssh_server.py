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

Listening for connection ...
Got a connection!
Client asked us to execute: wc -c setup.py
Authenticated!
Executing: wc -c setup.py

It can also be used to test SCP, for example, copying the file "hello"
as follows:

"/usr/bin/scp" -qvvv -P 2200 -i /Users/wettenhj/.ssh/MyData -c arcfour128 \
    -oIdentitiesOnly=yes -oPasswordAuthentication=no \
    -oNoHostAuthenticationForLocalhost=yes -oStrictHostKeyChecking=no \
    ./hello mydata@localhost:~

"""

# pylint: disable=invalid-name
# pylint: disable=missing-docstring

import socket
import sys
import threading
import traceback
import subprocess

import paramiko
from paramiko.py3compat import decodebytes
from paramiko.message import Message
from paramiko.common import cMSG_CHANNEL_WINDOW_ADJUST

import mydata.utils.openssh as OpenSSH


# setup logging
paramiko.util.log_to_file('fake_ssh_server.log')

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
        print "JUST FOR TESTING - IGNORING password."
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

# now connect
try:
    SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    SOCK.bind(('', 2200))
except Exception as e:  # pylint: disable=broad-except
    print '*** Bind failed: ' + str(e)
    traceback.print_exc()
    sys.exit(1)


class ChannelListener(object):
    """
    Listen for SSH/SCP connection.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, sock):
        self.sock = sock
        self.modeSizeFilename = "Sink: "
        self.chan = None
        self.server = None
        self.client = None
        self.transport = None

    def listen(self):
        # pylint: disable=too-many-branches
        print "listen for self = " + str(self)
        try:
            self.sock.listen(100)
            print 'Listening for connection ...'
            self.client, _ = self.sock.accept()
            print 'Got connection.'
        except Exception as e:  # pylint: disable=broad-except
            print '*** Listen/accept failed: ' + str(e)
            traceback.print_exc()
            sys.exit(1)

        self.transport = paramiko.Transport(self.client, gss_kex=False)
        self.transport.set_gss_host(socket.getfqdn(""))
        try:
            self.transport.load_server_moduli()
        except:  # pylint: disable=bare-except
            print '(Failed to load moduli -- gex will be unsupported.)'
            raise
        self.transport.add_server_key(host_key)

        self.server = Server()

        try:
            self.transport.start_server(server=self.server)
        except paramiko.SSHException:
            print '*** SSH negotiation failed.'
            sys.exit(1)

        print 'Got a connection!'

        try:
            # wait for auth
            self.chan = self.transport.accept(20)
            print "self.chan = " + str(self.chan)
            if self.chan is None:
                print '*** No channel.'
                # sys.exit(1)
                return
            print 'Authenticated!'

            if self.server.command:
                print "Client asked us to execute: %s" % self.server.command
                print "Executing: %s" % self.server.command
                if "scp" not in self.server.command:
                    proc = subprocess.Popen(self.server.command,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            shell=True)
                    stdout, _ = proc.communicate()
                    self.chan.send(stdout)
                    print "Closing channel."
                    self.chan.send_exit_status(proc.returncode)
                    self.chan.close()
                if "scp" in self.server.command:
                    proc = subprocess.Popen(self.server.command,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            shell=True)

                    def ReadFromChannel():
                        # pylint: disable=too-many-statements
                        finishedReadingModeSizeFilename = False
                        try:
                            while True:
                                char = ''
                                if self.chan.recv_ready():
                                    char = self.chan.recv(1)
                                    if char == '\0':
                                        print r"ReadFromChannel: '\0' received from channel."
                                        print "Breaking!!!"
                                        break
                                    if not finishedReadingModeSizeFilename:
                                        self.modeSizeFilename += char
                                    proc.stdin.write(char)
                                    proc.stdin.flush()
                                    sys.stdout.write(char)
                                    sys.stdout.flush()
                                else:
                                    break
                                if char == '\n':
                                    print "Newline found while reading " \
                                        "from channel."

                                    if not finishedReadingModeSizeFilename:
                                        # send_stderr below results in:
                                        # "rcvd ext data [len]"
                                        # appearing in the scp client's debug2 log.
                                        # where [len] is the length of
                                        # "Sink: C0600 131072 tmpt1q6jx"
                                        # including one extra character
                                        # (which must be the newline or '\0' ?)
                                        # "C0600" is the file mode (read only),
                                        # 131072 is the file size, and tmpt1q6jx
                                        # is the filename.
                                        self.chan.send_stderr(
                                            self.modeSizeFilename)
                                        finishedReadingModeSizeFilename = True

                                        # Sending the message below results in:
                                        # "rcvd adjust [window_size]"
                                        # appearing in the scp client's debug2 log.
                                        components = \
                                            self.modeSizeFilename.split(" ")
                                        print "components = " + str(components)
                                        fileSize = int(components[-2])
                                        m = Message()
                                        m.add_byte(cMSG_CHANNEL_WINDOW_ADJUST)
                                        m.add_int(self.chan.get_id())
                                        # Using filename size for window size for
                                        # now, which is wrong. I'm not sure how
                                        # the window size is supposed to be
                                        # calculated.
                                        windowSize = fileSize
                                        m.add_int(windowSize)
                                        self.transport._send_user_message(m)  # pylint: disable=protected-access
                                        while True:
                                            char = proc.stdout.read(1)
                                            # This will just be the mode, size and
                                            # filename echoed back.
                                            self.chan.send(char)
                                            if proc.returncode is not None:
                                                print "proc has finished."
                                                break
                                            if char == '\0':
                                                print r"ReadFromChannel: '\0' found in output of " \
                                                    r"scp -t"
                                                break
                                    # End: if not finishedReadingModeSizeFilename:

                                    while True:
                                        char = ''
                                        if self.chan.recv_ready():
                                            char = self.chan.recv(1)
                                            proc.stdin.write(char)
                                            proc.stdin.flush()
                                            sys.stdout.write(char)
                                            sys.stdout.flush()
                                        else:
                                            print "Breaking because chan recv not ready. (2)"
                                            break
                                    if not self.chan.recv_ready():
                                        print "Breaking because chan recv not ready. (3)"
                                        break
                                # End if char == '\n':
                            # end while True:
                        except socket.error:
                            print "ReadFromChannel socket error."
                            print traceback.format_exc()
                            return
                    readFromChannelThread = \
                        threading.Thread(target=ReadFromChannel)
                    readFromChannelThread.start()

                    def WriteToChannel():
                        try:
                            while True:
                                char = proc.stdout.read(1)
                                if char == '\0':
                                    print r"WriteToChannel: '\0' found in output of scp -t"
                                    return
                                sys.stdout.write(char)
                                sys.stdout.flush()
                                self.chan.send(char)
                        except socket.error:
                            print "WriteToChannel socket error."
                            print traceback.format_exc()
                            return
                    writeToChannelThread = \
                        threading.Thread(target=WriteToChannel)
                    writeToChannelThread.start()

                    print "Waiting for readFromChannelThread to finish..."
                    readFromChannelThread.join()
                    print "readFromChannelThread joined."
                    print "Waiting for writeToChannelThread to finish..."
                    writeToChannelThread.join()
                    print "writeToChannelThread joined."
                    if proc.returncode is not None:
                        print "Sending return code %d over channel and " \
                            "closing channel." % proc.returncode
                        self.chan.send_exit_status(proc.returncode)
                        print "Closing channel."
                        self.chan.close()
                    else:
                        # print "No return code to send over channel."
                        # print "Not closing channel."
                        print "Waiting for scp -t to finish."
                        stdout, _ = proc.communicate('E\n')
                        print "scp -t process completed!"
                        print "STDOUT from scp -t: " + stdout
                        print "scp -t exit code = " + str(proc.returncode)
                        self.chan.send_exit_status(proc.returncode)
                        print "Closing channel."
                        self.chan.close()
                # End: if "scp" in self.server.command:
            else:  # if self.server.command
                print "Closing channel."
                self.chan.close()

            # try:
                # self.transport.close()
            # except:  # pylint: disable=bare-except
                # traceback.print_exc()

        except Exception as e:  # pylint: disable=broad-except
            print '*** Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            try:
                self.transport.close()
            except:  # pylint: disable=bare-except
                traceback.print_exc()
            sys.exit(1)

while True:
    print "Waiting for a connection..."
    ChannelListener(SOCK).listen()
