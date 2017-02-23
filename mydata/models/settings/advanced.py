"""
Model class for the settings displayed in the Advanced tab
of the settings dialog and saved to disk in MyData.cfg
"""
class AdvancedSettingsModel(object):
    """
    Model class for the settings displayed in the Advanced tab
    of the settings dialog and saved to disk in MyData.cfg
    """
    def __init__(self):
        # Saved in MyData.cfg:
        self.mydataConfig = dict()

        self.fields = [
            'folder_structure',
            'dataset_grouping',
            'group_prefix',
            'validate_folder_structure',
            'max_upload_threads',
            'max_upload_retries',
            'start_automatically_on_login',
            'upload_invalid_user_folders'
        ]

    @property
    def folderStructure(self):
        """
        Get folder structure
        """
        return self.mydataConfig['folder_structure']

    @folderStructure.setter
    def folderStructure(self, folderStructure):
        """
        Set folder structure
        """
        self.mydataConfig['folder_structure'] = folderStructure

    @property
    def validateFolderStructure(self):
        """
        Returns True if folder structure should be validated
        """
        return self.mydataConfig['validate_folder_structure']

    @validateFolderStructure.setter
    def validateFolderStructure(self, validateFolderStructure):
        """
        Set this to True if folder structure should be validated
        """
        self.mydataConfig['validate_folder_structure'] = validateFolderStructure

    @property
    def startAutomaticallyOnLogin(self):
        """
        Returns True if MyData should start automatically on login
        """
        return self.mydataConfig['start_automatically_on_login']

    @startAutomaticallyOnLogin.setter
    def startAutomaticallyOnLogin(self, startAutomaticallyOnLogin):
        """
        Set this to True if MyData should start automatically on login
        """
        self.mydataConfig['start_automatically_on_login'] = startAutomaticallyOnLogin

    @property
    def uploadInvalidUserOrGroupFolders(self):
        """
        Returns True if data folders should be scanned and uploaded even if
        MyData can't find a MyTardis user (or group) record corresponding to
        the the user (or group) folder.
        """
        return self.mydataConfig['upload_invalid_user_folders']

    @uploadInvalidUserOrGroupFolders.setter
    def uploadInvalidUserOrGroupFolders(self, uploadInvalidUserOrGroupFolders):
        """
        Set this to True if data folders should be scanned and uploaded even if
        MyData can't find a MyTardis user (or group) record corresponding to
        the the user (or group) folder.
        """
        self.mydataConfig['upload_invalid_user_folders'] = \
            uploadInvalidUserOrGroupFolders

    @property
    def datasetGrouping(self):
        """
        Return dataset grouping (how datasets are collected into experiments).
        """
        return self.mydataConfig['dataset_grouping']

    @datasetGrouping.setter
    def datasetGrouping(self, datasetGrouping):
        """
        Set dataset grouping (how datasets are collected into experiments).
        """
        self.mydataConfig['dataset_grouping'] = datasetGrouping

    @property
    def groupPrefix(self):
        """
        Return prefix prepended to group folder name to match MyTardis group
        """
        return self.mydataConfig['group_prefix']

    @groupPrefix.setter
    def groupPrefix(self, groupPrefix):
        """
        Set prefix prepended to group folder name to match MyTardis group
        """
        self.mydataConfig['group_prefix'] = groupPrefix

    @property
    def maxUploadThreads(self):
        """
        Return the maximum number of concurrent uploads
        """
        return self.mydataConfig['max_upload_threads']

    @maxUploadThreads.setter
    def maxUploadThreads(self, maxUploadThreads):
        """
        Set the maximum number of concurrent uploads
        """
        self.mydataConfig['max_upload_threads'] = maxUploadThreads

    @property
    def maxUploadRetries(self):
        """
        Get the maximum number of retries per upload
        """
        return self.mydataConfig['max_upload_retries']

    @maxUploadRetries.setter
    def maxUploadRetries(self, maxUploadRetries):
        """
        Set the maximum number of retries per upload
        """
        self.mydataConfig['max_upload_retries'] = maxUploadRetries

    def SetDefaults(self):
        """
        Set default values for configuration parameters
        that will appear in MyData.cfg for fields in the
        Settings Dialog's Filter tab
        """
        self.mydataConfig['folder_structure'] = "Username / Dataset"
        self.mydataConfig['dataset_grouping'] = \
            "Instrument Name - Dataset Owner's Full Name"
        self.mydataConfig['group_prefix'] = ""
        self.mydataConfig['validate_folder_structure'] = True
        self.mydataConfig['max_upload_threads'] = 5
        self.mydataConfig['max_upload_retries'] = 1
        self.mydataConfig['start_automatically_on_login'] = True
        self.mydataConfig['upload_invalid_user_folders'] = True
