"""
Upload data using ParallelSSH library
"""
import os
import socket
from datetime import datetime
from time import sleep

from ssh2.session import Session
from ssh2.sftp import LIBSSH2_SFTP_S_IRUSR, LIBSSH2_SFTP_S_IRGRP, LIBSSH2_SFTP_S_IWUSR, \
    LIBSSH2_SFTP_S_IROTH


def ReadFileChunks(fileObject, chunkSize):
    """
    Read data file chunk
    """
    while True:
        data = fileObject.read(chunkSize)
        if not data:
            break
        yield data


def UploadFileSSH(host, port, username, privateKeyFilePath, filePath, remoteFilePath,
               uploadModel, progressCallback):
    """
    Upload file using SSH, update progress status, cancel upload if requested
    """
    fileInfo = os.stat(filePath)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, int(port)))

    sess = Session()
    sess.handshake(sock)
    sess.userauth_publickey_fromfile(username, privateKeyFilePath)

    mode = LIBSSH2_SFTP_S_IRUSR | LIBSSH2_SFTP_S_IWUSR | LIBSSH2_SFTP_S_IRGRP | LIBSSH2_SFTP_S_IROTH
    remoteFile = sess.scp_send64(remoteFilePath, mode, fileInfo.st_size, fileInfo.st_mtime,
                                 fileInfo.st_atime)

    totalUploaded = 0
    with open(filePath, "rb") as localFile:
        for data in ReadFileChunks(localFile, 32*1024*1024):
            _, bytesWritten = remoteFile.write(data)
            totalUploaded += bytesWritten
            uploadModel.SetLatestTime(datetime.now())
            progressCallback(current=totalUploaded, total=fileInfo.st_size)
            if uploadModel.canceled:
                break

    # Without this file upload is incomplete
    sleep(0.25)

    remoteFile.flush()
    remoteFile.close()
    sess.disconnect()
