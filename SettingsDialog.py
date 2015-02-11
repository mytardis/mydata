import wx
import wx.aui
import re
import requests
import threading
from datetime import datetime
import sys

from logger.Logger import logger
from SettingsModel import SettingsModel
from Exceptions import DuplicateKey
from Exceptions import IncompatibleMyTardisVersion
import MyDataEvents as mde


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
        self.fieldsPanelSizer = wx.FlexGridSizer(rows=10, cols=3,
                                                 vgap=5, hgap=5)
        self.fieldsPanel.SetSizer(self.fieldsPanelSizer)

        self.fieldsPanelSizer.AddGrowableCol(1)

        self.instrumentNameLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                 "Instrument Name:")
        self.fieldsPanelSizer.Add(self.instrumentNameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.instrumentNameField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        if sys.platform.startswith("darwin"):
            self.instrumentNameField.SetMinSize(wx.Size(275, -1))
        else:
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

        groupPrefixLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                      "Group Prefix:")
        self.fieldsPanelSizer.Add(groupPrefixLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.groupPrefixField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY, "")
        self.fieldsPanelSizer.Add(self.groupPrefixField,
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

        # For security reasons, Mac OS X tries to disable copy/paste etc.
        # in password fields.  Copy and Cut are genuine security risks,
        # but we can re-enable paste and select all.  We make up new IDs,
        # rather than using self.apiKeyField.GetId(), so that the OS doesn't
        # try to impose it's security rules on our "password" field.
        pasteId = wx.NewId()
        selectAllId = wx.NewId()
        acceleratorList = \
            [(wx.ACCEL_CTRL, ord('V'), pasteId),
             (wx.ACCEL_CTRL, ord('A'), selectAllId)]
        self.Bind(wx.EVT_MENU, self.OnPaste, id=pasteId)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=selectAllId)
        acceleratorTable = wx.AcceleratorTable(acceleratorList)
        self.SetAcceleratorTable(acceleratorTable)

        self.Bind(wx.EVT_SET_FOCUS, self.OnApiKeyFieldFocused,
                  self.apiKeyField)

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

        self.okButton = wx.Button(self, wx.ID_OK, "OK")
        self.okButton.SetDefault()
        buttonSizer.AddButton(self.okButton)

        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "Cancel")
        buttonSizer.AddButton(self.cancelButton)
        buttonSizer.Realize()
        # Using wx.ID_CANCEL makes command-c cancel on Mac OS X,
        # but we want to use command-c for copying to the clipboard.
        # We set the ID to wx.ID_CANCEL earlier to help
        # wx.StdDialogButtonSizer to lay out the buttons correctly.
        self.cancelButton.SetId(wx.NewId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelButton)
        # As with the Cancel button, we set the OK button's ID to
        # wx.ID_OK initially to help wx.StdDialogButtonSizer to 
        # lay out the buttons.  But at least on Mac OS X, I don't
        # trust the event handling to work correctly, so I'm
        # changing the button's ID here:
        self.okButton.SetId(wx.NewId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, self.okButton)

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

    def GetGroupPrefix(self):
        return self.groupPrefixField.GetValue()

    def SetGroupPrefix(self, groupPrefix):
        self.groupPrefixField.SetValue(groupPrefix)

    def GetUsername(self):
        return self.usernameField.GetValue()

    def SetUsername(self, username):
        self.usernameField.SetValue(username)

    def GetApiKey(self):
        return self.apiKeyField.GetValue()

    def SetApiKey(self, apiKey):
        self.apiKeyField.SetValue(apiKey)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnOK(self, event):
        if self.GetInstrumentName() != \
                self.settingsModel.GetInstrumentName() and \
                self.settingsModel.GetInstrumentName() != "":
            instrumentNameMismatchEvent = mde.MyDataEvent(
                mde.EVT_INSTRUMENT_NAME_MISMATCH,
                settingsDialog=self,
                settingsModel=self.settingsModel,
                facilityName=self.GetFacilityName(),
                oldInstrumentName=self.settingsModel.GetInstrumentName(),
                newInstrumentName=self.GetInstrumentName())
            wx.PostEvent(wx.GetApp().GetMainFrame(),
                         instrumentNameMismatchEvent)
            return

        settingsDialogValidationEvent = \
            mde.MyDataEvent(mde.EVT_SETTINGS_DIALOG_VALIDATION,
                            settingsDialog=self,
                            settingsModel=self.settingsModel,
                            okEvent=event)

        intervalSinceLastConnectivityCheck = \
            datetime.now() - wx.GetApp().GetLastNetworkConnectivityCheckTime()
        # FIXME: Magic number of 30 seconds since last connectivity check.
        if intervalSinceLastConnectivityCheck.total_seconds() >= 30 or \
                not wx.GetApp().GetLastNetworkConnectivityCheckSuccess():
            checkConnectivityEvent = \
                mde.MyDataEvent(mde.EVT_CHECK_CONNECTIVITY,
                                settingsModel=self.settingsModel,
                                nextEvent=settingsDialogValidationEvent)
            wx.PostEvent(wx.GetApp().GetMainFrame(), checkConnectivityEvent)
        else:
            wx.PostEvent(wx.GetApp().GetMainFrame(),
                         settingsDialogValidationEvent)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:",
                           defaultPath=self.GetDataDirectory().encode('ascii', 'ignore'))
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
        self.SetGroupPrefix(settingsModel.GetGroupPrefix())
        self.SetApiKey(settingsModel.GetApiKey())

    def OnPaste(self, event):
        textCtrl = wx.Window.FindFocus()
        if textCtrl is not None:
            if textCtrl == self.apiKeyField:
                textCtrl.Paste()
            else:
                event.Skip()

    def OnSelectAll(self, event):
        textCtrl = wx.Window.FindFocus()
        if textCtrl is not None:
            if textCtrl == self.apiKeyField:
                textCtrl.SelectAll()
            else:
                event.Skip()

    def OnApiKeyFieldFocused(self, event):
        self.apiKeyField.SelectAll()
