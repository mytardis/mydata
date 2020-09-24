import os
import socket
from datetime import datetime
from time import sleep

from ssh2.session import Session
from ssh2.sftp import LIBSSH2_SFTP_S_IRUSR, LIBSSH2_SFTP_S_IRGRP, LIBSSH2_SFTP_S_IWUSR, LIBSSH2_SFTP_S_IROTH


def read_in_chunks(file_object, chunk_size):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def uploadFile(host, port, username, privateKeyFilePath, filePath, remoteFilePath,
               uploadModel, progressCallback):
    one_megabyte = 1 * 1024 * 1024
    packet = 32 * one_megabyte

    fileInfo = os.stat(filePath)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, int(port)))

    sess = Session()
    sess.handshake(sock)
    sess.userauth_publickey_fromfile(username, privateKeyFilePath)

    mode = LIBSSH2_SFTP_S_IRUSR | LIBSSH2_SFTP_S_IWUSR | LIBSSH2_SFTP_S_IRGRP | LIBSSH2_SFTP_S_IROTH
    remote_fh = sess.scp_send64(remoteFilePath, mode, fileInfo.st_size, fileInfo.st_mtime, fileInfo.st_atime)

    total_uploaded = 0
    with open(filePath, "rb") as local_fh:
        for data in read_in_chunks(local_fh, packet):
            return_code, written_bytes = remote_fh.write(data)
            total_uploaded += written_bytes
            uploadModel.SetLatestTime(datetime.now())
            progressCallback(current=total_uploaded, total=fileInfo.st_size)
            if uploadModel.canceled:
                break

    # Without this file upload is incomplete
    sleep(0.25)

    remote_fh.flush()
    remote_fh.close()
    sess.disconnect()
