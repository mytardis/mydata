"""
Test ability to handle ObjectACL-related exceptions.
"""
import os
import sys
import time
import unittest
import threading
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.objectacl import ObjectAclModel
from mydata.models.experiment import ExperimentModel
from mydata.models.folder import FolderModel
from mydata.models.group import GroupModel
from mydata.models.settings import SettingsModel
from mydata.models.user import UserModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import DoesNotExist


class ObjectAclExceptionsTester(unittest.TestCase):
    """
    Test ability to handle ObjectACL-related exceptions.
    """
    def __init__(self, *args, **kwargs):
        super(ObjectAclExceptionsTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.fakeMyTardisUrl = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ObjectAclExceptionsTester')
        self.StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.WaitForFakeMyTardisServerToStart()

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_objectacl_exceptions(self):
        """
        Test ability to handle ObjectACL-related exceptions.
        """
        # pylint: disable=too-many-locals
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDataset.cfg")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.SetDataDirectory(dataDirectory)
        settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl)
        settingsValidation = settingsModel.Validate()
        self.assertTrue(settingsValidation.IsValid())

        owner = settingsModel.GetDefaultOwner()
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(dataDirectory, expFolderName)

        # Test sharing experiment with user, and ensure that no exception
        # is raised:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)

        # Test sharing experiment with group, and ensure that no exception
        # is raised:
        groupModel = GroupModel.GetGroupByName(settingsModel,
                                               "TestFacility-Group1")
        ObjectAclModel.ShareExperimentWithGroup(experimentModel, groupModel)

        # Try to create a user ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.GetApiKey()
        folderModel.settingsModel.SetApiKey("invalid")
        with self.assertRaises(Unauthorized):
            ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)
        folderModel.settingsModel.SetApiKey(apiKey)

        # Try to create a group ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.GetApiKey()
        folderModel.settingsModel.SetApiKey("invalid")
        with self.assertRaises(Unauthorized):
            ObjectAclModel.ShareExperimentWithGroup(experimentModel, groupModel)
        folderModel.settingsModel.SetApiKey(apiKey)

        # Try to create a user ObjectACL record with
        # a user without a UserProfile, which should give 404 (DoesNotExist)
        userWithoutProfile = UserModel.GetUserByUsername(settingsModel,
                                                         "userwithoutprofile")
        experimentModel.settingsModel.defaultOwner = userWithoutProfile
        experimentModel.settingsModel.SetUsername("userwithoutprofile")
        with self.assertRaises(DoesNotExist):
            ObjectAclModel.ShareExperimentWithUser(experimentModel,
                                                   userWithoutProfile)

        # Try to create a group ObjectACL record with
        # a user without a UserProfile, which should give 404 (DoesNotExist)
        with self.assertRaises(DoesNotExist):
            ObjectAclModel.ShareExperimentWithGroup(experimentModel,
                                                    groupModel)

    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        self.fakeMyTardisPort = GetEphemeralPort()
        self.httpd = HTTPServer((self.fakeMyTardisHost, self.fakeMyTardisPort),
                                FakeMyTardisHandler)

        def FakeMyTardisServer():
            """ Run fake MyTardis server """
            self.httpd.serve_forever()
        self.fakeMyTardisServerThread = \
            threading.Thread(target=FakeMyTardisServer,
                             name="FakeMyTardisServerThread")
        self.fakeMyTardisServerThread.start()

    def WaitForFakeMyTardisServerToStart(self):
        """
        Wait for fake MyTardis server to start.
        """
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.fakeMyTardisUrl +
                             "/api/v1/?format=json", timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.fakeMyTardisUrl, str(err)))
