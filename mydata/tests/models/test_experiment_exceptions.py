"""
Test ability to handle experiment-related exceptions.
"""
import os
import sys
import time
import unittest
import threading
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.experiment import ExperimentModel
from mydata.models.folder import FolderModel
from mydata.models.schema import SchemaModel
from mydata.models.settings import SettingsModel
from mydata.models.user import UserProfileModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import MultipleObjectsReturned
from mydata.utils.exceptions import Unauthorized

class ExperimentExceptionsTester(unittest.TestCase):
    """
    Test ability to handle experiment-related exceptions.
    """
    def __init__(self, *args, **kwargs):
        super(ExperimentExceptionsTester, self).__init__(*args, **kwargs)
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
                              title='ExperimentExceptionsTester')
        self.StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.WaitForFakeMyTardisServerToStart()

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_experiment_exceptions(self):
        """
        Test ability to handle experiment-related exceptions.
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
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

        # LOOKING UP EXPERIMENTS

        # LOOKING UP EXPERIMENTS WITH TITLE SET MANUALLY

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle(expFolderName)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (instrument, userFolderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Look up one of many existing experiment records with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle("Multiple Existing Experiments")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment1")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle(expFolderName)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (instrument, groupFolderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a user folder
        # name, and a group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle(expFolderName)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s', '%s'"
            % (instrument, userFolderName, expFolderName,
               groupFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a group folder
        # name, and a user folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        folderModel.SetExperimentTitle(expFolderName)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', '%s'"
            % (instrument, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Try to look up experiment record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.GetApiKey()
        folderModel.settingsModel.SetApiKey("invalid")
        with self.assertRaises(Unauthorized):
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        folderModel.settingsModel.SetApiKey(apiKey)

        # Try to look up experiment record with a missing UserProfile
        # for the authorizing user, which can result in a 404 from the
        # MyTardis API:
        folderModel.SetExperimentTitle("Missing UserProfile")
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), UserProfileModel)

        # Try to look up experiment record with a missing Schema,
        # which can result in a 404 from the MyTardis API:
        folderModel.SetExperimentTitle("Missing Schema")
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), SchemaModel)

        # Try to look up experiment record and handle a 404 of
        # unknown origin from the MyTardis API:
        folderModel.SetExperimentTitle("Unknown 404")
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), None)

        # LOOKING UP EXPERIMENTS WITH TITLE SET AUTOMATICALLY

        folderModel.SetExperimentTitle("")
        folderModel.experimentTitleSetManually = False

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s" % (instrument, userFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.GetUploaderModel().SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.GetUploaderModel().SetUuid(uploaderUuid)

        # Look up one of many existing experiment records with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        folderModel.settingsModel.GetUploaderModel().SetUuid("Multiple Existing Experiments")
        with self.assertRaises(MultipleObjectsReturned) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        folderModel.settingsModel.GetUploaderModel().SetUuid(uploaderUuid)

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s"
            % (instrument, groupFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.GetUploaderModel().SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.GetUploaderModel().SetUuid(uploaderUuid)

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a user folder
        # name and a group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (instrument, userFolderName, groupFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a user folder
        # name and a group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.GetUploaderModel().SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.GetUploaderModel().SetUuid(uploaderUuid)

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.GetInstrument().GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message, "Experiment not found for '%s'." % instrument)

        # Look up existing experiment record with
        # experiment title set automatically, and with neither a user folder
        # name nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.GetUploaderModel().SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.GetUploaderModel().SetUuid(uploaderUuid)

        # CREATING EXPERIMENTS

        # Try to create an experiment with a title specified manually
        # and check that the title is correct:
        testRun = False
        folderModel.SetExperimentTitle(expFolderName)
        experimentModel = \
            ExperimentModel.CreateExperimentForFolder(folderModel, testRun)
        self.assertEqual(experimentModel.GetTitle(), expFolderName)

        # Try to create an experiment with a title specified manually,
        # and with testRun activated:
        testRun = True
        folderModel.SetExperimentTitle(expFolderName)
        experimentModel = \
            ExperimentModel.GetOrCreateExperimentForFolder(folderModel, testRun)
        self.assertEqual(experimentModel, None)
        testRun = False

        # Get or create an experiment with a title specified manually,
        # which already exists and with testRun activated:
        testRun = True
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = \
            ExperimentModel.GetOrCreateExperimentForFolder(folderModel, testRun)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.SetExperimentTitle(expFolderName)
        testRun = False

        # Try to create an experiment record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.GetApiKey()
        folderModel.settingsModel.SetApiKey("invalid")
        with self.assertRaises(Unauthorized):
            _ = ExperimentModel.CreateExperimentForFolder(folderModel, testRun)
        folderModel.settingsModel.SetApiKey(apiKey)

        # Now let's test experiment creation with the experiment's
        # title determined automatically (from the instrument's name
        # and user folder name or group folder name):
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)

        # Test case where MyTardis API returns a 404, e.g. because a
        # requested Experiment Schema can't be found.
        folderModel.SetExperimentTitle(
            "Request 404 from Fake MyTardis Server")
        with self.assertRaises(DoesNotExist):
            _ = ExperimentModel.CreateExperimentForFolder(folderModel, testRun)


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
