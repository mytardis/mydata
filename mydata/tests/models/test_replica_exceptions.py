"""
Test ability to handle replica-related exceptions.

'replica' is the name of the MyTardis API resource
endpoint for DataFileObjects (DFOs).
"""
from .. import MyDataTester
from ...settings import SETTINGS
from ...models.datafile import DataFileModel
from ...models.replica import ReplicaModel
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import MissingMyDataReplicaApiEndpoint


class ReplicaExceptionsTester(MyDataTester):
    """
    Test ability to handle replica-related exceptions.

    'replica' is the name of the MyTardis API resource
    endpoint for DataFileObjects (DFOs).
    """
    def test_replica_exceptions(self):
        """
        Test ability to handle replica-related exceptions.
        """
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        # Fake MyTardis server's authentication will succeed as long
        # as we provide a non-empty username and API key and as long
        # as the API key is not "invalid"
        SETTINGS.general.username = "testuser1"
        SETTINGS.general.apiKey = "valid"

        # Fake MyTardis server will return a fake DataFile for any ID:
        datafile = DataFileModel.GetDataFileFromId(12345)
        replica = datafile.replicas[0]

        bytesOnStaging = ReplicaModel.CountBytesUploadedToStaging(replica.dfoId)
        # Fake MyTardis server will return 1024 by default
        # for replica size queries:
        self.assertEqual(bytesOnStaging, 1024)

        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = ReplicaModel.CountBytesUploadedToStaging(replica.dfoId)
        SETTINGS.general.apiKey = apiKey

        # This special DFO ID tells the Fake MyTardis server to respond
        # with a 404 error:
        replica.dfoId = 444894
        with self.assertRaises(MissingMyDataReplicaApiEndpoint):
            _ = ReplicaModel.CountBytesUploadedToStaging(replica.dfoId)
