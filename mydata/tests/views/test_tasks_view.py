"""
Test ability to open tasks view.
"""
import unittest
import wx

from ...dataviewmodels.tasks import TasksModel
from ...views.tasks import TasksView


class TasksViewTester(unittest.TestCase):
    """
    Test ability to open tasks view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='TasksViewTester')
        self.settingsModel = None
        self.tasksModel = TasksModel(self.settingsModel)
        self.tasksView = TasksView(self.frame, tasksModel=self.tasksModel)
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
