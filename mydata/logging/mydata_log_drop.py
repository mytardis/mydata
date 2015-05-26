#!/usr/bin/env python

# This file, used by MyData, lives in
# /var/www/cgi-bin/mydata_log_drop.py
# on cvl.massive.org.au

import os
import cgi
import cgitb
import string
import tempfile
import subprocess

cgitb.enable()

MAX_LOG_DIRECTORY_SIZE = 100  # size of log directory in Mb
LOG_DIRECTORY = '/opt/mydata_debug_logs/'

MAX_NR_BYTES_LOG = 50*1048576  # 50Mb


def free_root_space():
    proc = subprocess.Popen('df -B MB /',
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True,
                            universal_newlines=True)
    stdout, stderr = proc.communicate()

    return int(stdout.split('\n')[1].split('MB')[2]) > \
        1.5 * MAX_LOG_DIRECTORY_SIZE


def free_space():
    proc = subprocess.Popen('du -B MB ' + LOG_DIRECTORY,
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True,
                            universal_newlines=True)
    stdout, stderr = proc.communicate()

    return int(stdout.split('\n')[0].split('MB')[0]) < \
        MAX_LOG_DIRECTORY_SIZE

form = cgi.FieldStorage()
out = None

if 'logfile' in form:
    logfile = form['logfile']

    if logfile.file and free_space() and free_root_space():
        out = tempfile.NamedTemporaryFile(mode='w', dir=LOG_DIRECTORY,
                                          delete=False)

        BYTES_PER_READ = 1024

        bytes_read = 0

        while True:
            blob = logfile.file.read(BYTES_PER_READ)
            if not blob:
                break
            bytes_read += BYTES_PER_READ

            if bytes_read >= MAX_NR_BYTES_LOG:
                out.write("Exceeded limit of %d bytes in upload, exiting.\n"
                          % MAX_NR_BYTES_LOG)
                break
            else:
                out.write(blob)
        out.close()

print "Content-Type: text/html\r\n\r\n"

print """
<html><body>
<p>%s</p>
</body></html>
""" % ('Hello from mydata_log_drop.py',)
