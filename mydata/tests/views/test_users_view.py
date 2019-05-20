"""
Test ability to open users view.
"""
import unittest

import wx

from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...dataviewmodels.users import UsersModel
from ...models.user import UserModel
from ...views.dataview import MyDataDataView


class UsersViewTester(unittest.TestCase):
    """
    Test ability to open users view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)
        self.app.SetAppName('UsersViewTester')
        self.frame = wx.Frame(None, title='UsersViewTester')
        DATAVIEW_MODELS['users'] = UsersModel()
        self.usersView = MyDataDataView(self.frame, 'users')
        self.frame.Show()

    def test_users_view(self):
        """Test ability to open users view.
        """
        usersModel = DATAVIEW_MODELS['users']

        dataViewId = usersModel.GetMaxDataViewId() + 1
        testuser1 = UserModel(
            username="testuser1",
            fullName="Test User1",
            email="testuser1@example.com",
            dataViewId=dataViewId)
        usersModel.AddRow(testuser1)
        dataViewId = usersModel.GetMaxDataViewId() + 1
        testuser2 = UserModel(
            username="testuser2",
            fullName="Test User2",
            email="testuser2@example.com",
            dataViewId=dataViewId)
        usersModel.AddRow(testuser2)

        usersModel.Compare(testuser1, testuser2, col=1, ascending=True)

        self.assertEqual(usersModel.GetValueByRow(0, 1), "testuser1")
        self.assertEqual(usersModel.GetValueByRow(1, 1), "testuser2")
        self.assertEqual(usersModel.GetRowCount(), 2)
        self.assertEqual(usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(usersModel.GetFilteredRowCount(), 0)
        usersModel.Filter("testuser2")
        self.assertEqual(usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(usersModel.GetFilteredRowCount(), 1)
        usersModel.Filter("notfound")
        self.assertEqual(usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(usersModel.GetFilteredRowCount(), 2)
        usersModel.Filter("")
        self.assertEqual(usersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(usersModel.GetFilteredRowCount(), 0)
        usersModel.DeleteAllRows()
        self.assertEqual(usersModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(usersModel.GetFilteredRowCount(), 0)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
