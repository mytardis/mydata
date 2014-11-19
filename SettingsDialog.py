import wx
import wx.aui
import re
import requests
import threading

from logger.Logger import logger

from SettingsModel import SettingsModel
from Exceptions import DuplicateKeyException


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, ID, title,
                 settingsModel,
                 size=wx.DefaultSize,
                 pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title=title, size=size, pos=pos,
                           style=style)

        self.CenterOnParent()

        self.parent = parent
        self.settingsModel = settingsModel

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.fieldsPanel = wx.Panel(self)
        self.fieldsPanelSizer = wx.FlexGridSizer(rows=9, cols=3,
                                                 vgap=5, hgap=5)
        self.fieldsPanel.SetSizer(self.fieldsPanelSizer)

        self.fieldsPanelSizer.AddGrowableCol(1)

        self.instrumentNameLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                 "Instrument Name:")
        self.fieldsPanelSizer.Add(self.instrumentNameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.instrumentNameField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        self.instrumentNameField.SetMinSize(wx.Size(250, -1))
        self.fieldsPanelSizer.Add(self.instrumentNameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(blankLine)

        self.facilityNameLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                               "Facility Name:")
        self.fieldsPanelSizer.Add(self.facilityNameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.facilityNameField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(self.facilityNameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(blankLine)

        self.contactNameLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                              "Contact Name:")
        self.fieldsPanelSizer.Add(self.contactNameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.contactNameField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY,
                                            "")
        self.fieldsPanelSizer.Add(self.contactNameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                ""))

        self.contactEmailLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                               "Contact Email:")
        self.fieldsPanelSizer.Add(self.contactEmailLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.contactEmailField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY,
                                             "")
        self.fieldsPanelSizer.Add(self.contactEmailField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                ""))

        self.dataDirectoryLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                "Data Directory:")
        self.fieldsPanelSizer.Add(self.dataDirectoryLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.dataDirectoryField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(self.dataDirectoryField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        self.browseDataDirectoryButton = wx.Button(self.fieldsPanel,
                                                   wx.ID_ANY, "Browse...")
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, self.browseDataDirectoryButton)
        self.fieldsPanelSizer.Add(self.browseDataDirectoryButton,
                                  flag=wx.EXPAND | wx.ALL, border=5)

        self.myTardisUrlLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                              "MyTardis URL:")
        self.fieldsPanelSizer.Add(self.myTardisUrlLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.myTardisUrlField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(self.myTardisUrlField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                ""))

        usernameLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                      "MyTardis Username:")
        self.fieldsPanelSizer.Add(usernameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.usernameField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(self.usernameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                ""))

        apiKeyLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                    "MyTardis API Key:")
        self.fieldsPanelSizer.Add(apiKeyLabel, flag=wx.ALIGN_RIGHT | wx.ALL,
                                  border=5)
        self.apiKeyField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "",
                                       style=wx.TE_PASSWORD)
        self.fieldsPanelSizer.Add(self.apiKeyField, flag=wx.EXPAND | wx.ALL,
                                  border=5)
        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                ""))
        self.fieldsPanel.Fit()

        sizer.Add(self.fieldsPanel, 0,
                  wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, wx.ID_ANY, size=(20, -1),
                             style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0,
                  wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        buttonSizer = wx.StdDialogButtonSizer()

        self.okButton = wx.Button(self, wx.ID_OK)
        self.okButton.SetDefault()
        buttonSizer.AddButton(self.okButton)
        self.Bind(wx.EVT_BUTTON, self.OnOK, self.okButton)

        self.cancelButton = wx.Button(self, wx.ID_CANCEL)
        buttonSizer.AddButton(self.cancelButton)
        buttonSizer.Realize()

        sizer.Add(buttonSizer, 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.UpdateFieldsFromModel(self.settingsModel)

    def GetInstrumentName(self):
        return self.instrumentNameField.GetValue()

    def SetInstrumentName(self, instrumentName):
        self.instrumentNameField.SetValue(instrumentName)

    def GetFacilityName(self):
        return self.facilityNameField.GetValue()

    def SetFacilityName(self, instrumentName):
        self.facilityNameField.SetValue(instrumentName)

    def GetMyTardisUrl(self):
        return self.myTardisUrlField.GetValue()

    def GetContactName(self):
        return self.contactNameField.GetValue()

    def SetContactName(self, contactName):
        self.contactNameField.SetValue(contactName)

    def GetContactEmail(self):
        return self.contactEmailField.GetValue()

    def SetContactEmail(self, contactEmail):
        self.contactEmailField.SetValue(contactEmail)

    def GetDataDirectory(self):
        return self.dataDirectoryField.GetValue()

    def SetDataDirectory(self, dataDirectory):
        self.dataDirectoryField.SetValue(dataDirectory)

    def SetMyTardisUrl(self, myTardisUrl):
        self.myTardisUrlField.SetValue(myTardisUrl)

    def GetUsername(self):
        return self.usernameField.GetValue()

    def SetUsername(self, username):
        self.usernameField.SetValue(username)

    def GetApiKey(self):
        return self.apiKeyField.GetValue()

    def SetApiKey(self, apiKey):
        self.apiKeyField.SetValue(apiKey)

    def OnOK(self, event):
        if self.GetInstrumentName() != \
                self.settingsModel.GetInstrumentName():
            message = "A previous instrument name of \"%s\" " \
                "has been associated with this MyData instance.\n" \
                "Please choose how you would like the new \"%s\" " \
                "instrument name to be applied." \
                % (self.settingsModel.GetInstrumentName(),
                   self.GetInstrumentName())
            renameChoice = "Rename the existing instrument record to " \
                "\"%s\"." % self.GetInstrumentName()
            discardChoice = "Discard the new instrument name and revert " \
                "to \"%s\"." % self.settingsModel.GetInstrumentName()
            createChoice = "Use a separate instrument record for \"%s\", " \
                "creating it if necessary." \
                % self.GetInstrumentName()
            dlg = wx.SingleChoiceDialog(self, message,
                                        "MyData - Instrument Name Changed",
                                        [renameChoice, discardChoice,
                                         createChoice], wx.CHOICEDLG_STYLE)
            if dlg.ShowModal() == wx.ID_OK:
                if dlg.GetStringSelection() == renameChoice:
                    logger.info("OK, we will rename the "
                                "existing instrument record.")
                    try:
                        # This should be in its own thread.
                        self.settingsModel.RenameInstrument(
                            self.GetFacilityName(),
                            self.settingsModel.GetInstrumentName(),
                            self.GetInstrumentName())
                    except DuplicateKeyException:
                        message = "Instrument name \"%s\" already exists in " \
                            "facility \"%s\"." \
                            % (self.GetInstrumentName(),
                               self.GetFacilityName())
                        dlg = wx.MessageDialog(None, message, "MyData",
                                               wx.OK | wx.ICON_ERROR)
                        dlg.ShowModal()
                        self.instrumentNameField.SetFocus()
                        self.instrumentNameField.SelectAll()
                        return

                elif dlg.GetStringSelection() == discardChoice:
                    logger.info("OK, we will discard the new instrument name.")
                    self.SetInstrumentName(
                        self.settingsModel.GetInstrumentName())
                    self.instrumentNameField.SetFocus()
                    self.instrumentNameField.SelectAll()
                elif dlg.GetStringSelection() == createChoice:
                    logger.info("OK, we will create a new instrument record.")
            else:
                return
        tempSettingsModel = SettingsModel()
        tempSettingsModel.SaveFieldsFromDialog(self)

        def validate(tempSettingsModel):
            tempSettingsModel.Validate()

        thread = threading.Thread(target=validate,
                                  args=(tempSettingsModel,))
        wx.BeginBusyCursor()
        thread.start()
        thread.join()
        wx.EndBusyCursor()

        settingsValidation = tempSettingsModel.GetValidation()
        if settingsValidation is not None and \
                not settingsValidation.GetValid():
            message = settingsValidation.GetMessage()
            logger.error(message)

            if settingsValidation.GetSuggestion():
                currentValue = ""
                if settingsValidation.GetField() == "instrument_name":
                    currentValue = self.GetInstrumentName()
                elif settingsValidation.GetField() == "facility_name":
                    currentValue = self.GetFacilityName()
                elif settingsValidation.GetField() == "mytardis_url":
                    currentValue = self.GetMyTardisUrl()
                message = message.strip()
                if currentValue != "":
                    message += "\n\nMyData suggests that you replace \"%s\" " \
                        % currentValue
                    message += "with \"%s\"." \
                        % settingsValidation.GetSuggestion()
                else:
                    message += "\n\nMyData suggests that you use \"%s\"." \
                        % settingsValidation.GetSuggestion()
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.CANCEL | wx.ICON_ERROR)
                okToUseSuggestion = dlg.ShowModal()
                if okToUseSuggestion == wx.ID_OK:
                    if settingsValidation.GetField() == "instrument_name":
                        self.SetInstrumentName(settingsValidation
                                               .GetSuggestion())
                    elif settingsValidation.GetField() == "facility_name":
                        self.SetFacilityName(settingsValidation
                                             .GetSuggestion())
                    elif settingsValidation.GetField() == "mytardis_url":
                        self.SetMyTardisUrl(settingsValidation
                                            .GetSuggestion())
            else:
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
            if settingsValidation.GetField() == "instrument_name":
                self.instrumentNameField.SetFocus()
                self.instrumentNameField.SelectAll()
            elif settingsValidation.GetField() == "facility_name":
                self.facilityNameField.SetFocus()
                self.facilityNameField.SelectAll()
            elif settingsValidation.GetField() == "data_directory":
                self.dataDirectoryField.SetFocus()
                self.dataDirectoryField.SelectAll()
            elif settingsValidation.GetField() == "mytardis_url":
                self.myTardisUrlField.SetFocus()
                self.myTardisUrlField.SelectAll()
            elif settingsValidation.GetField() == "contact_name":
                self.contactNameField.SetFocus()
                self.contactNameField.SelectAll()
            elif settingsValidation.GetField() == "contact_email":
                self.contactEmailField.SetFocus()
                self.contactEmailField.SelectAll()
            elif settingsValidation.GetField() == "username":
                self.usernameField.SetFocus()
                self.usernameField.SelectAll()
            elif settingsValidation.GetField() == "api_key":
                self.apiKeyField.SetFocus()
                self.apiKeyField.SelectAll()
            return

        self.settingsModel.SaveFieldsFromDialog(self)
        event.Skip()

    def OnBrowse(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:")
        if dlg.ShowModal() == wx.ID_OK:
            self.dataDirectoryField.SetValue(dlg.GetPath())

    def UpdateFieldsFromModel(self, settingsModel):
        self.SetInstrumentName(settingsModel.GetInstrumentName())
        self.SetFacilityName(settingsModel.GetFacilityName())
        self.SetContactName(settingsModel.GetContactName())
        self.SetContactEmail(settingsModel.GetContactEmail())
        self.SetMyTardisUrl(settingsModel.GetMyTardisUrl())
        self.SetDataDirectory(settingsModel.GetDataDirectory())
        self.SetUsername(settingsModel.GetUsername())
        self.SetApiKey(settingsModel.GetApiKey())
