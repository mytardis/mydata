"""
Upload data using ParallelSSH library
"""
import os
import socket
from datetime import datetime
from time import sleep

from ssh2 import session, sftp


def ReadFileChunks(fileObject, chunkSize):
    """
    Read data file chunk
    """
    while True:
        data = fileObject.read(chunkSize)
        if not data:
            break
        yield data


def GetFileMode():
    """
    Remote file attributes
    """
    return sftp.LIBSSH2_SFTP_S_IRUSR | \
           sftp.LIBSSH2_SFTP_S_IWUSR | \
           sftp.LIBSSH2_SFTP_S_IRGRP | \
           sftp.LIBSSH2_SFTP_S_IROTH


def UploadFileSsh(server, auth, filePath, remoteFilePath,
                  uploadModel, progressCallback):
    """
    Upload file using SSH, update progress status, cancel upload if requested
    """
    fileInfo = os.stat(filePath)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server)

    sess = session.Session()
    sess.handshake(sock)
    sess.userauth_publickey_fromfile(auth[0], auth[1])

    channel = sess.scp_send64(remoteFilePath, GetFileMode(),
                              fileInfo.st_size, fileInfo.st_mtime, fileInfo.st_atime)

    totalUploaded = 0
    with open(filePath, "rb") as localFile:
        for data in ReadFileChunks(localFile, 32*1024*1024):
            _, bytesWritten = channel.write(data)
            totalUploaded += bytesWritten
            uploadModel.SetLatestTime(datetime.now())
            progressCallback(current=totalUploaded, total=fileInfo.st_size)
            if uploadModel.canceled:
                break

    channel.send_eof()
    channel.wait_eof()

    channel.close()
    channel.wait_closed()

    sess.disconnect()
