import sqlite3


class SettingsModel():

    def __init__(self, sqlitedb):
        self.sqlitedb = sqlitedb
        self.mytardis_url = ""
        self.institution_name = ""
        self.username = ""
        self.api_key = ""

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
                           "WHERE field='institution_name'")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.institution_name = rows[0]['value']
            else:
                self.institution_name = ""

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

    def GetInstrumentName(self):
        return self.instrument_name

    def SetInstrumentName(self, instrumentName):
        self.instrument_name = instrumentName

    def GetInstitutionName(self):
        return self.institution_name

    def SetInstitutionName(self, institutionName):
        self.institution_name = institutionName

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
                           "('mytardis_url',:mytardisUrl)",
                           {'mytardisUrl': self.GetMyTardisUrl()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('institution_name',:institutionName)",
                           {'institutionName': self.GetInstitutionName()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('data_directory',:dataDirectory)",
                           {'dataDirectory': self.GetDataDirectory()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('username',:username)",
                           {'username': self.GetUsername()})
            cursor.execute("INSERT INTO settings(field,value) VALUES " +
                           "('api_key',:apiKey)",
                           {'apiKey': self.GetApiKey()})
