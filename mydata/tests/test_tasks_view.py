"""
Test ability to open tasks view.
"""
import unittest
import logging
import wx

from mydata.dataviewmodels.tasks import TasksModel
from mydata.views.tasks import TasksView

logger = logging.getLogger(__name__)


class TasksViewTester(unittest.TestCase):
    """
    Test ability to open tasks view.
    """
    def test_tasks_view(self):
        """
        Test ability to open tasks view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        settingsModel = None
        tasksModel = TasksModel(settingsModel)
        TasksView(frame, tasksModel=tasksModel)
        frame.Show()
        frame.Destroy()
