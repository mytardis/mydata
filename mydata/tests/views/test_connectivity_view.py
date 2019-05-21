"""
Test ability to open connectivity view.
"""
from .. import MyDataGuiTester
from ...utils.exceptions import NoActiveNetworkInterface
from ...views.connectivity import ReportNoActiveInterfaces


class ConnectivityViewTester(MyDataGuiTester):
    """
    Test ability to open connectivity view.
    """
    def test_connectivity_view(self):
        """Test ability to open connectivity view.
        """
        with self.assertRaises(NoActiveNetworkInterface):
            ReportNoActiveInterfaces()
