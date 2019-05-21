"""
Test ability to open connectivity view.
"""
from .. import MyDataTester
from ...utils.exceptions import NoActiveNetworkInterface
from ...views.connectivity import ReportNoActiveInterfaces


class ConnectivityViewTester(MyDataTester):
    """
    Test ability to open connectivity view.
    """
    def test_connectivity_view(self):
        """Test ability to open connectivity view.
        """
        with self.assertRaises(NoActiveNetworkInterface):
            ReportNoActiveInterfaces()
