"""
Upload data using ParallelSSH library
"""
import math
import os
import socket
from datetime import datetime
from time import sleep
import hashlib
import json
import requests
import xxhash

from ssh2 import session, sftp

from ..models.datafile import DataFileModel


def GetDataChecksum(algorithm, data):
    """
    Calculate checksum for a binary data
    """
    if algorithm == "xxh3_64":
        checksum = xxhash.xxh3_64(data).hexdigest()
    elif algorithm == "md5":
        checksum = hashlib.md5(data).hexdigest()
    else:
        checksum = None
    return checksum


def HandleResponse(rsp):
    """
    Handle API call response
    """
    data = json.loads(rsp.content)
    if "success" not in data:
        if "error_message" in data:
            raise Exception(data["error_message"])
        raise Exception("Unable to parse API call response.")
    if not data["success"]:
        raise Exception(data["error"])
    return data


def CompleteUpload(server, username, apiKey, dfoId):
    """
    Start data file assembly from chunks
    """
    headers = {
        "Authorization": "ApiKey %s:%s" % (username, apiKey),
        "Content-Type": "application/json"
    }
    return HandleResponse(requests.get(
        "%s/api/v1/mydata_upload/%s/complete/" % (server, dfoId),
        headers=headers))


def UploadChunk(server, username, apiKey, dfoId,
                algorithm, contentRange, data):
    """
    Upload single data file chunk
    """
    headers = {
        "Authorization": "ApiKey %s:%s" % (username, apiKey),
        "Checksum": GetDataChecksum(algorithm, data),
        "Content-Range": contentRange,
        "Content-Type": "application/octet-stream"
    }
    return HandleResponse(requests.post(
        "%s/api/v1/mydata_upload/%s/upload/" % (server, dfoId),
        data=data,
        headers=headers))


def GetChunks(server, username, apiKey, dfoId):
    """
    Get status of chunk upload, start or continue
    """
    headers = {
        "Authorization": "ApiKey %s:%s" % (username, apiKey),
        "Content-Type": "application/json"
    }
    return HandleResponse(requests.get(
        "%s/api/v1/mydata_upload/%s/" % (server, dfoId),
        headers=headers))


def DefaultSleepIdle():
    """
    Time to sleep after API call failed
    """
    return 5


def GetDataFileObjectId(uploadModel):
    """
    Call API to receive dfoId if required
    """
    if uploadModel.dataFileId is not None:
        try:
            dataFile = DataFileModel.GetDataFileFromId(uploadModel.dataFileId)
            return dataFile.replicas[0].dfoId
        except:
            pass

    return None

def UploadFileChunked(server, username, apiKey,
                      filePath, uploadModel, progressCallback):
    """
    Upload file using chunks API
    """

    if uploadModel.dfoId is None:
        uploadModel.dfoId = GetDataFileObjectId(uploadModel)
        if uploadModel.dfoId is None:
            return False

    status = GetChunks(server, username, apiKey, uploadModel.dfoId)

    if not status["completed"]:
        fileSize = os.stat(filePath).st_size
        totalUploaded = status["offset"]
        file = open(filePath, "rb")
        for thisChunk in range(math.ceil(fileSize/status["size"])):
            thisOffset = thisChunk*status["size"]
            if thisOffset >= totalUploaded:
                file.seek(thisOffset)
                binaryData = file.read(status["size"])
                backoffSleep = DefaultSleepIdle()
                while backoffSleep > 0 and not uploadModel.canceled:
                    upload = UploadChunk(
                        server, username, apiKey, uploadModel.dfoId,
                        status["checksum"],
                        "%s-%s/%s" % (thisOffset, thisOffset+len(binaryData), fileSize),
                        binaryData)
                    if not upload["success"]:
                        sleep(backoffSleep)
                        backoffSleep *= 2
                    else:
                        backoffSleep = 0
                        totalUploaded += len(binaryData)
                    uploadModel.SetLatestTime(datetime.now())
                    progressCallback(current=totalUploaded, total=fileSize)
                if uploadModel.canceled:
                    break
        file.close()

    if not uploadModel.canceled:
        CompleteUpload(server, username, apiKey, uploadModel.dfoId)

    return True


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


def ExecuteCommandOverSsh(sshSession, command):
    """
    Execute command over existing SSH session
    """
    channel = sshSession.open_session()
    channel.execute(command)
    message = []
    while True:
        size, data = channel.read()
        if len(data) != 0:
            message.append(data)
        if size == 0:
            break
    channel.close()
    channel.wait_closed()
    if len(message) != 0:
        raise Exception(" ".join(message))


def GetSshSession(server, auth):
    """
    Open connection and return SSH session
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server)

    sshSession = session.Session()
    sshSession.handshake(sock)

    try:
        sshSession.userauth_publickey_fromfile(auth[0], auth[1])
    except:
        raise Exception("Can't open SSH key file.")

    return sshSession


def UploadFileSsh(server, auth, filePath, remoteFilePath,
                  uploadModel, progressCallback):
    """
    Upload file using SSH, update progress status, cancel upload if requested
    """
    sess = GetSshSession(server, auth)

    try:
        ExecuteCommandOverSsh(sess, "mkdir -m 2770 -p %s" % os.path.dirname(remoteFilePath))
    except Exception as err:
        raise Exception("Can't create remote folder. %s" % str(err))

    fileInfo = os.stat(filePath)
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

    try:
        ExecuteCommandOverSsh(sess, "chmod 660 %s" % remoteFilePath)
    except Exception as err:
        raise Exception("Can't set remote file permissions. %s" % str(err))

    sess.disconnect()
