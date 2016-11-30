"""
Test ability to create a MyData App instance.
"""
import unittest

from mydata.MyData import MyData


class MyDataAppInstanceTester(unittest.TestCase):
    """
    Test ability to create MyData App instance.
    """
    def setUp(self):
        self.mydataApp = MyData(argv=[])

    def test_mydata_app_instance(self):
        """
        Test ability to create MyData App instance.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.mydataApp.Destroy()
