"""
Base class for deriving a model class for the settings
displayed in each tab of the settings dialog
"""


class BaseSettingsModel(object):
    """
    Base class for deriving a model class for the settings
    displayed in each tab of the settings dialog
    """
    def __init__(self):
        # Saved in MyData.cfg:
        self.mydataConfig = dict()

        self.fields = []

        self.default = dict()

    def SetDefaultForField(self, field):
        """
        Set default value for one field.
        """
        self.mydataConfig[field] = self.default[field]

    def SetDefaults(self):
        """
        Set default values for configuration parameters
        that will appear in MyData.cfg for fields in the
        Settings Dialog's Filter tab
        """
        for field in self.fields:
            self.SetDefaultForField(field)
