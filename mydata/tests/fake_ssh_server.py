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

"""

# pylint: disable=invalid-name

import socket
import sys
import threading
import traceback
import subprocess

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
        print "Client asked us to execute: %s" % command
        self.command = command
        return True

    def check_auth_publickey(self, username, key):
        if (username == 'mydata') and (key == self.mydata_pub_key):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        # pylint: disable=too-many-arguments
        return True


DoGSSAPIKeyExchange = False

# now connect
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 2200))
except Exception as e:  # pylint: disable=broad-except
    print '*** Bind failed: ' + str(e)
    traceback.print_exc()
    sys.exit(1)

try:
    sock.listen(100)
    print 'Listening for connection ...'
    client, addr = sock.accept()
except Exception as e:  # pylint: disable=broad-except
    print '*** Listen/accept failed: ' + str(e)
    traceback.print_exc()
    sys.exit(1)

print 'Got a connection!'

try:
    t = paramiko.Transport(client, gss_kex=DoGSSAPIKeyExchange)
    t.set_gss_host(socket.getfqdn(""))
    try:
        t.load_server_moduli()
    except:  # pylint: disable=bare-except
        print '(Failed to load moduli -- gex will be unsupported.)'
        raise
    t.add_server_key(host_key)
    server = Server()
    try:
        t.start_server(server=server)
    except paramiko.SSHException:
        print '*** SSH negotiation failed.'
        sys.exit(1)

    # wait for auth
    chan = t.accept(20)
    if chan is None:
        print '*** No channel.'
        sys.exit(1)
    print 'Authenticated!'

    if server.command:
        print "Executing: %s" % server.command
        proc = subprocess.Popen(server.command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=True)
        stdout, _ = proc.communicate()
        chan.send(stdout)
    else:
        print "No command to execute."

    chan.close()

except Exception as e:  # pylint: disable=broad-except
    print '*** Caught exception: ' + str(e.__class__) + ': ' + str(e)
    traceback.print_exc()
    try:
        t.close()
    except:  # pylint: disable=bare-except
        pass
    sys.exit(1)
