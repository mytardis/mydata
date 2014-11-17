import sqlite3


class SettingsModel():

    def __init__(self, sqlitedb):
        self.sqlitedb = sqlitedb
        self.instrument_name = ""
        self.facility_name = ""
        self.mytardis_url = ""
        self.contact_name = ""
        self.contact_email = ""
        self.username = ""
        self.api_key = ""

        self.background_mode = "False"

        self.uploadToStagingRequest = None

        conn = sqlite3.connect(self.sqlitedb)
        with conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS " +
                           "settings(id integer primary key," +
                           "field text,value text)")

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='instrument_name'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.instrument_name = rows[0]['value']
            else:
                self.instrument_name = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='facility_name'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.facility_name = rows[0]['value']
            else:
                self.facility_name = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='contact_name'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.contact_name = rows[0]['value']
            else:
                self.contact_name = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='contact_email'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.contact_email = rows[0]['value']
            else:
                self.contact_email = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='data_directory'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.data_directory = rows[0]['value']
            else:
                self.data_directory = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='mytardis_url'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.mytardis_url = rows[0]['value']
            else:
                self.mytardis_url = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='username'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.username = rows[0]['value']
            else:
                self.username = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='api_key'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.api_key = rows[0]['value']
            else:
                self.api_key = ""

            cursor.execute("SELECT value FROM settings " +
                           "WHERE field='background_mode'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.background_mode = rows[0]['value']
            else:
                self.background_mode = "False"

    def GetInstrumentName(self):
        return self.instrument_name

    def SetInstrumentName(self, instrumentName):
        self.instrument_name = instrumentName

    def GetFacilityName(self):
        return self.facility_name

    def SetFacilityName(self, facilityName):
        self.facility_name = facilityName

    def GetContactName(self):
        return self.contact_name

    def SetContactName(self, contactName):
        self.contact_name = contactName

    def GetContactEmail(self):
        return self.contact_email

    def SetContactEmail(self, contactEmail):
        self.contact_email = contactEmail

    def GetDataDirectory(self):
        return self.data_directory

    def SetDataDirectory(self, dataDirectory):
        self.data_directory = dataDirectory

    def GetMyTardisUrl(self):
        return self.mytardis_url

    def SetMyTardisUrl(self, myTardisUrl):
        self.mytardis_url = myTardisUrl

    def GetUsername(self):
        return self.username

    def SetUsername(self, username):
        self.username = username

    def GetApiKey(self):
        return self.api_key

    def SetApiKey(self, apiKey):
        self.api_key = apiKey

    def RunningInBackgroundMode(self):
        return self.background_mode == "True"

    def SetBackgroundMode(self, backgroundMode):
        if backgroundMode is True or \
                (backgroundMode is not None and backgroundMode == "True"):
            self.backgroundMode = "True"
        else:
            self.backgroundMode = "False"

    def GetUploadToStagingRequest(self):
        return self.uploadToStagingRequest

    def SetUploadToStagingRequest(self,
                                          uploadToStagingRequest):
        self.uploadToStagingRequest = uploadToStagingRequest

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def Save(self):
        conn = sqlite3.connect(self.sqlitedb)
        with conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS " +
                           "settings(id integer primary key," +
                           "field text,value text)")
            cursor.execute("DELETE FROM settings")
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('instrument_name',:instrumentName)",
                           {'instrumentName': self.GetInstrumentName()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('facility_name',:facilityName)",
                           {'facilityName': self.GetFacilityName()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('mytardis_url',:mytardisUrl)",
                           {'mytardisUrl': self.GetMyTardisUrl()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('contact_name',:contactName)",
                           {'contactName': self.GetContactName()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('contact_email',:contactEmail)",
                           {'contactEmail': self.GetContactEmail()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('data_directory',:dataDirectory)",
                           {'dataDirectory': self.GetDataDirectory()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('username',:username)",
                           {'username': self.GetUsername()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('api_key',:apiKey)",
                           {'apiKey': self.GetApiKey()})
