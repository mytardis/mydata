from datetime import datetime


class CleanupFile(object):

    def __init__(self, dataViewId, data):
        self.dataViewId = dataViewId
        self.setDelete = False
        for key in data:
            setattr(self, key, data[key])
        dt = datetime.fromisoformat(data["verifiedAt"])
        timeString = dt.strftime("%I:%M %p")
        dateString = "{d:%A} {d.day}/{d.month}/{d.year}".format(d=dt)
        setattr(self, "verifiedAt", "{} at {}".format(dateString, timeString))


    def GetValueForKey(self, key):
        return getattr(self, key)
