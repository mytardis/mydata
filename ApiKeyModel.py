import requests

from logger.Logger import logger


class ApiKeyModel():

    def __init__(self, id=None, username=None, key=None,
                 apiKeyRecordJson=None):
        self.id = id
        self.username = username
        self.key = key

        self.apiKeyRecordJson = apiKeyRecordJson

        if apiKeyRecordJson is not None:
            self.key = apiKeyRecordJson['key']

    def GetId(self):
        return self.id

    def SetId(self, id):
        self.id = id

    def GetUsername(self):
        return self.username

    def GetKey(self):
        return self.key

    def GetValueForKey(self, key):
        return self.__dict__[key]

    @staticmethod
    def GetApiKeyRecord(settingsModel, username):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/apikey/?format=json" + \
            "&user__username=" + username

        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        response = requests.get(url=url, headers=headers)
        apiKeyRecordsJson = response.json()
        numApiKeyRecordsFound = apiKeyRecordsJson['meta']['total_count']

        if numApiKeyRecordsFound == 0:
            logger.debug("Didn't find an API key for username \"" +
                         username + "\".")
        else:
            logger.debug("Found API key for username \"" + username + "\".")
            apiKeyRecordJson = apiKeyRecordsJson['objects'][0]
            return ApiKeyModel(username=username,
                               apiKeyRecordJson=apiKeyRecordJson)
