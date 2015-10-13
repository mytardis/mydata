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
using a Cygwin build of scp from a Windows command prompt:

scp -vv -oNoHostAuthenticationForLocalhost=yes -P 2200 \
-i /cygdrive/C/Users/jsmith/.ssh/MyData \
/cygdrive/C/Users/jsmith/Desktop/hello.txt \
mydata@localhost:/cygdrive/C/Users/jsmith/hello2.txt

So far, I've always used the verbose options, so leave them out at
your own risk.
"""

# pylint: disable=invalid-name
# pylint: disable=missing-docstring

import socket
import sys
import threading
import traceback
import subprocess
import time

import paramiko
from paramiko.py3compat import decodebytes

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
        self.verbose = False

    def listen(self):
        # pylint: disable=too-many-branches
        try:
            backlog = 0
            self.sock.listen(backlog)
            print 'Listening for an SSH/SCP connection on port 2200...'
            self.client, _ = self.sock.accept()
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
            if self.chan is None:
                print '*** No channel.'
                # sys.exit(1)
                return
            print 'Authenticated!'

            count = 0
            while not self.server.command:
                time.sleep(0.01)
                count += 1
                if count > 100:
                    message = "\nInteractive shells are not supported.\n" \
                        "Please provide a command to be executed.\n\n"
                    sys.stderr.write(message)
                    self.chan.send_stderr(message)
                    self.chan.send_exit_status(1)
                    self.chan.close()
                    return

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
                if "-v" in self.server.command.split(" "):
                    self.verbose = True
                    print "Executing: %s" % self.server.command
                self.server.command = \
                    self.server.command.replace("scp", OpenSSH.OPENSSH.scp)
                proc = subprocess.Popen(self.server.command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True)
                # Confirm to the channel that we started the command:
                self.chan.send('\0')

                def ReadFromChannel():
                    # pylint: disable=too-many-statements
                    # The first thing we read from the client via the
                    # channel will be the file mode, size and filename
                    # (or timestamps if given, but they haven't
                    # been tested yet).
                    # We pass this info onto the remote scp process,
                    # using proc.stdin.write().
                    while not self.chan.recv_ready():
                        time.sleep(0.01)
                    try:
                        while True:
                            char = ''
                            if self.chan.recv_ready():
                                char = self.chan.recv(1)
                                if char == '\0':
                                    break
                                proc.stdin.write(char)
                                proc.stdin.flush()
                                sys.stdout.write(char.encode('utf-8'))
                                sys.stdout.flush()
                            else:
                                break
                        # end while True:
                    except socket.error:
                        print "ReadFromChannel socket error."
                        print traceback.format_exc()
                        return
                readFromChannelThread = \
                    threading.Thread(target=ReadFromChannel)
                readFromChannelThread.daemon = True
                readFromChannelThread.start()

                def WriteToChannel():
                    try:
                        while True:
                            char = proc.stdout.read(1)
                            if char == '\0':
                                return
                            sys.stdout.write(char.encode('utf-8'))
                            sys.stdout.flush()
                            self.chan.send(char)
                    except socket.error:
                        print "WriteToChannel socket error."
                        print traceback.format_exc()
                        return
                writeToChannelThread = \
                    threading.Thread(target=WriteToChannel)
                writeToChannelThread.daemon = True
                writeToChannelThread.start()

                def ReadRemoteStderr():
                    try:
                        buf = ""
                        while True:
                            char = proc.stderr.read(1)
                            buf += char
                            if char == '\n':
                                self.chan.send_stderr(buf)
                                self.chan.send('\0')
                                return
                    except socket.error:
                        print "ReadRemoteStderr socket error."
                        print traceback.format_exc()
                        return
                readRemoteStderrThread = \
                    threading.Thread(target=ReadRemoteStderr)
                readRemoteStderrThread.daemon = True
                readRemoteStderrThread.start()

                readFromChannelThread.join()
                writeToChannelThread.join()
                readRemoteStderrThread.join()

                # Stuff below should go in a thread!
                while not self.chan.recv_ready():
                    time.sleep(0.01)

                while True:
                    char = self.chan.recv(1)
                    # sys.stdout.write(char)
                    proc.stdin.write(char)
                    proc.stdin.flush()
                    if char == '\0':
                        break

                if not proc.returncode:
                    stdout, _ = proc.communicate()
                print "scp -t exit code = " + str(proc.returncode)
                self.chan.send('\0E\n\0')
                self.chan.send_exit_status(proc.returncode)
                self.chan.close()
                print ""
        except Exception as e:  # pylint: disable=broad-except
            print '*** Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            try:
                self.transport.close()
            except:  # pylint: disable=bare-except
                traceback.print_exc()
            sys.exit(1)

while True:
    ChannelListener(SOCK).listen()
