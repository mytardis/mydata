"""
Test ability to open users view.
"""
import unittest

import wx

from ...dataviewmodels.users import UsersModel
from ...models.user import UserModel
from ...views.users import UsersView


class UsersViewTester(unittest.TestCase):
    """
    Test ability to open users view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='UsersViewTester')
        self.settingsModel = None
        self.usersModel = UsersModel(self.settingsModel)
        self.usersView = UsersView(self.frame, usersModel=self.usersModel)
        self.frame.Show()

    def test_users_view(self):
        """
        Test ability to open users view.
        """
        dataViewId = self.usersModel.GetMaxDataViewId() + 1
        testuser1 = UserModel(
            username="testuser1",
            name="Test User1",
            email="testuser1@example.com",
            dataViewId=dataViewId)
        self.usersModel.AddRow(testuser1)
        dataViewId = self.usersModel.GetMaxDataViewId() + 1
        testuser2 = UserModel(
            username="testuser2",
            name="Test User2",
            email="testuser2@example.com",
            dataViewId=dataViewId)
        self.usersModel.AddRow(testuser2)

        self.usersModel.Compare(testuser1, testuser2, col=1, ascending=True)

        self.assertEqual(self.usersModel.GetValueByRow(0, 1), "testuser1")
        self.assertEqual(self.usersModel.GetValueByRow(1, 1), "testuser2")
        self.assertEqual(self.usersModel.GetRowCount(), 2)
        self.assertEqual(self.usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.usersModel.GetFilteredRowCount(), 0)
        self.usersModel.Filter("testuser2")
        self.assertEqual(self.usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.usersModel.GetFilteredRowCount(), 1)
        self.usersModel.Filter("notfound")
        self.assertEqual(self.usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.usersModel.GetFilteredRowCount(), 2)
        self.usersModel.Filter("")
        self.assertEqual(self.usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.usersModel.GetFilteredRowCount(), 0)
        self.usersModel.DeleteAllRows()
        self.assertEqual(self.usersModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(self.usersModel.GetFilteredRowCount(), 0)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
