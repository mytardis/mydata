class DuplicateKey(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(DuplicateKey, self).__init__(message)


class MultipleObjectsReturned(Exception):
    def __init__(self, message, url, response):

        # Call the base class constructor with the parameters it needs
        super(MultipleObjectsReturned, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        return self.url

    def GetResponse(self):
        return self.response


class DoesNotExist(Exception):
    def __init__(self, message, url=None, response=None):

        # Call the base class constructor with the parameters it needs
        super(DoesNotExist, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        return self.url

    def GetResponse(self):
        return self.response


class Unauthorized(Exception):
    def __init__(self, message, url=None, response=None):

        # Call the base class constructor with the parameters it needs
        super(Unauthorized, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        return self.url

    def GetResponse(self):
        return self.response


class InternalServerError(Exception):
    def __init__(self, message, url=None, response=None):

        # Call the base class constructor with the parameters it needs
        super(InternalServerError, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        return self.url

    def GetResponse(self):
        return self.response


class SshException(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(SshException, self).__init__(message)


class StagingHostRefusedSshConnection(SshException):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(StagingHostRefusedSshConnection, self).__init__(message)


class StagingHostSshPermissionDenied(SshException):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(StagingHostSshPermissionDenied, self).__init__(message)


class NoActiveNetworkInterface(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(NoActiveNetworkInterface, self).__init__(message)


class BrokenPipe(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(BrokenPipe, self).__init__(message)
