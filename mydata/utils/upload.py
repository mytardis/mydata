"""
Upload data using ParallelSSH library
"""
import math
import os
import socket
import requests
from datetime import datetime
import json
import hashlib
import xxhash
from time import sleep

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


def handle_response(rsp):
    data = json.loads(rsp.content)
    if "success" not in data:
        if "error_message" in data:
            raise Exception(data["error_message"])
        raise Exception("Unable to parse API call response.")
    if not data["success"]:
        raise Exception(data["error"])
    return data


def CompleteUpload(server, username, api_key, dfo_id):
    headers = {
        "Authorization": "ApiKey %s:%s" % (username, api_key),
        "Content-Type": "application/json"
    }
    return handle_response(requests.get(
        "%s/api/v1/mydata_upload/%s/complete/" % (server, dfo_id),
        headers=headers))


def UploadChunk(server, username, api_key, dfo_id,
                algorithm, content_range, data):
    headers = {
        "Authorization": "ApiKey %s:%s" % (username, api_key),
        "Checksum": GetDataChecksum(algorithm, data),
        "Content-Range": content_range,
        "Content-Type": "application/octet-stream"
    }
    return handle_response(requests.post(
        "%s/api/v1/mydata_upload/%s/upload/" % (server, dfo_id),
        data=data,
        headers=headers))


def GetChunks(server, username, api_key, dfo_id):
    headers = {
        "Authorization": "ApiKey %s:%s" % (username, api_key),
        "Content-Type": "application/json"
    }
    return handle_response(requests.get(
        "%s/api/v1/mydata_upload/%s/" % (server, dfo_id),
        headers=headers))


def UploadFileChunked(server, username, api_key,
                      filePath, uploadModel, progressCallback):
    """
    Upload file using chunks API
    """
    if uploadModel.dfoId is None:
        if uploadModel.dataFileId is not None:
            try:
                dataFile = DataFileModel.GetDataFileFromId(uploadModel.dataFileId)
                uploadModel.dfoId = dataFile.replicas[0].dfoId
            except:
                pass
    dfo_id = uploadModel.dfoId
    if dfo_id is None:
        return False

    status = GetChunks(server, username, api_key, dfo_id)

    if not status["completed"]:
        backoffIdle = 5
        backoffSleep = backoffIdle
        fileInfo = os.stat(filePath)
        totalUploaded = status["offset"]
        file = open(filePath, "rb")
        for thisChunk in range(math.ceil(fileInfo.st_size/status["size"])):
            thisOffset = thisChunk*status["size"]
            if thisOffset >= totalUploaded:
                file.seek(thisOffset)
                binaryData = file.read(status["size"])
                bytesRead = len(binaryData)
                content_range = "%s-%s/%s" % (thisOffset, thisOffset+bytesRead, fileInfo.st_size)
                keep_uploading = True
                while keep_uploading and not uploadModel.canceled:
                    upload = UploadChunk(
                        server, username, api_key, dfo_id,
                        status["checksum"], content_range,
                        binaryData)
                    if not upload["success"]:
                        sleep(backoffSleep)
                        backoffSleep *= 2
                    else:
                        keep_uploading = False
                        backoffSleep = backoffIdle
                        totalUploaded += bytesRead
                    uploadModel.SetLatestTime(datetime.now())
                    progressCallback(current=totalUploaded, total=fileInfo.st_size)
                if uploadModel.canceled:
                    break
        file.close()

    if not uploadModel.canceled:
        CompleteUpload(server, username, api_key, dfo_id)

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
