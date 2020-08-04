"""
Model class for a file in cache, ready to be removed locally
"""
from datetime import datetime


class CleanupFile(object):
    """
    File to be removed locally
    """

    def __init__(self, dataViewId, data):
        self.dataViewId = dataViewId
        self.setDelete = False
        for key in data:
            setattr(self, key, data[key])
        datetimeVerified = datetime.fromisoformat(data["verifiedAt"])
        timeString = datetimeVerified.strftime("%I:%M %p")
        dateString = "{d:%A} {d.day}/{d.month}/{d.year}".format(d=datetimeVerified)
        setattr(self, "verifiedAt", "{} at {}".format(dateString, timeString))

    def GetValueForKey(self, key):
        """
        :param key:
        :return:
        """
        return getattr(self, key)
