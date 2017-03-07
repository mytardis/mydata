"""
Test ability to open tasks view.
"""
import unittest
import wx

from ...dataviewmodels.tasks import TasksModel
from ...views.dataview import MyDataDataView


class TasksViewTester(unittest.TestCase):
    """
    Test ability to open tasks view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='TasksViewTester')
        self.tasksModel = TasksModel()
        self.tasksView = MyDataDataView(self.frame, self.tasksModel)
        self.frame.Show()

    def test_tasks_view(self):
        """
        Test ability to open tasks view.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
