import wx
import wx.aui
import re
import requests
import threading
from datetime import datetime
import sys
import os

from logger.Logger import logger
from SettingsModel import SettingsModel
from Exceptions import DuplicateKey
from Exceptions import IncompatibleMyTardisVersion
import MyDataEvents as mde
from DragAndDrop import MyDataSettingsDropTarget


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

        self.SetDropTarget(MyDataSettingsDropTarget(self))

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.dialogPanel = wx.Panel(self)

        self.settingsTabsNotebook = \
            wx.aui.AuiNotebook(self.dialogPanel, style=wx.aui.AUI_NB_TOP)
        self.generalPanel = wx.Panel(self.settingsTabsNotebook)
        self.advancedPanel = wx.Panel(self.settingsTabsNotebook)

        self.dialogPanelSizer = wx.BoxSizer()
        self.dialogPanelSizer.Add(self.settingsTabsNotebook, 0,
                                  wx.EXPAND | wx.ALL, 5)
        self.dialogPanel.SetSizer(self.dialogPanelSizer)

        sizer.Add(self.dialogPanel, 1, wx.EXPAND | wx.ALL, 5)

        self.generalPanelSizer = wx.FlexGridSizer(rows=11, cols=3,
                                                  vgap=5, hgap=5)
        self.generalPanel.SetSizer(self.generalPanelSizer)
        self.generalPanelSizer.AddGrowableCol(1)

        # Add blank space above the settings fields. Our FlexGridSizer
        # has 3 columns, so we'll add 3 units of blank space.  We don't
        # care about the width (so we use -1), but we choose a height of
        # 5px (plus the FlexGridSizer's default vgap).
        self.generalPanelSizer.Add(wx.Size(-1, 5))
        self.generalPanelSizer.Add(wx.Size(-1, 5))
        self.generalPanelSizer.Add(wx.Size(-1, 5))

        self.instrumentNameLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                 "Instrument Name:")
        self.generalPanelSizer.Add(self.instrumentNameLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.instrumentNameField = wx.TextCtrl(self.generalPanel,
                                               wx.ID_ANY, "")
        if sys.platform.startswith("darwin"):
            self.instrumentNameField.SetMinSize(wx.Size(275, -1))
        else:
            self.instrumentNameField.SetMinSize(wx.Size(250, -1))
        self.generalPanelSizer.Add(self.instrumentNameField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.generalPanel, wx.ID_ANY, "")
        self.generalPanelSizer.Add(blankLine)

        self.facilityNameLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                               "Facility Name:")
        self.generalPanelSizer.Add(self.facilityNameLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.facilityNameField = wx.TextCtrl(self.generalPanel, wx.ID_ANY, "")
        self.generalPanelSizer.Add(self.facilityNameField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.generalPanel, wx.ID_ANY, "")
        self.generalPanelSizer.Add(blankLine)

        self.contactNameLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                              "Contact Name:")
        self.generalPanelSizer.Add(self.contactNameLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.contactNameField = wx.TextCtrl(self.generalPanel, wx.ID_ANY,
                                            "")
        self.generalPanelSizer.Add(self.contactNameField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        self.generalPanelSizer.Add(wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                 ""))

        self.contactEmailLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                               "Contact Email:")
        self.generalPanelSizer.Add(self.contactEmailLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.contactEmailField = wx.TextCtrl(self.generalPanel, wx.ID_ANY,
                                             "")
        self.generalPanelSizer.Add(self.contactEmailField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        self.generalPanelSizer.Add(wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                 ""))

        self.dataDirectoryLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                "Data Directory:")
        self.generalPanelSizer.Add(self.dataDirectoryLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.dataDirectoryField = wx.TextCtrl(self.generalPanel, wx.ID_ANY, "")
        self.generalPanelSizer.Add(self.dataDirectoryField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        self.browseDataDirectoryButton = wx.Button(self.generalPanel,
                                                   wx.ID_ANY, "Browse...")
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, self.browseDataDirectoryButton)
        self.generalPanelSizer.Add(self.browseDataDirectoryButton,
                                   flag=wx.EXPAND | wx.ALL, border=5)

        self.myTardisUrlLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                              "MyTardis URL:")
        self.generalPanelSizer.Add(self.myTardisUrlLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.myTardisUrlField = wx.TextCtrl(self.generalPanel, wx.ID_ANY, "")
        self.generalPanelSizer.Add(self.myTardisUrlField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        self.generalPanelSizer.Add(wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                 ""))

        usernameLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                      "MyTardis Username:")
        self.generalPanelSizer.Add(usernameLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.usernameField = wx.TextCtrl(self.generalPanel, wx.ID_ANY, "")
        self.generalPanelSizer.Add(self.usernameField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        self.generalPanelSizer.Add(wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                 ""))

        apiKeyLabel = wx.StaticText(self.generalPanel, wx.ID_ANY,
                                    "MyTardis API Key:")
        self.generalPanelSizer.Add(apiKeyLabel, flag=wx.ALIGN_RIGHT | wx.ALL,
                                   border=5)
        self.apiKeyField = wx.TextCtrl(self.generalPanel, wx.ID_ANY, "",
                                       style=wx.TE_PASSWORD)

        # For security reasons, Mac OS X tries to disable copy/paste etc.
        # in password fields.  Copy and Cut are genuine security risks,
        # but we can re-enable paste and select all.  We make up new IDs,
        # rather than using self.apiKeyField.GetId(), so that the OS
        # doesn't try to impose its security rules on our "password" field.
        pasteId = wx.NewId()
        selectAllId = wx.NewId()
        saveId = wx.NewId()
        acceleratorList = \
            [(wx.ACCEL_CTRL, ord('V'), pasteId),
             (wx.ACCEL_CTRL, ord('A'), selectAllId),
             (wx.ACCEL_CTRL, ord('S'), saveId)]
        self.Bind(wx.EVT_MENU, self.OnPaste, id=pasteId)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=selectAllId)
        self.Bind(wx.EVT_MENU, self.OnSave, id=saveId)
        acceleratorTable = wx.AcceleratorTable(acceleratorList)
        self.SetAcceleratorTable(acceleratorTable)

        self.Bind(wx.EVT_SET_FOCUS, self.OnApiKeyFieldFocused,
                  self.apiKeyField)

        self.generalPanelSizer.Add(self.apiKeyField, flag=wx.EXPAND | wx.ALL,
                                   border=5)
        self.generalPanelSizer.Add(wx.StaticText(self.generalPanel, wx.ID_ANY,
                                                 ""))
        # Add blank space above the settings fields. Our FlexGridSizer
        # has 3 columns, so we'll add 3 units of blank space.  We don't
        # care about the width (so we use -1), but we choose a height of
        # 5px (plus the FlexGridSizer's default vgap).
        self.generalPanelSizer.Add(wx.Size(-1, 5))
        self.generalPanelSizer.Add(wx.Size(-1, 5))
        self.generalPanelSizer.Add(wx.Size(-1, 5))

        self.generalPanel.Fit()
        generalPanelSize = self.generalPanel.GetSize()
        self.settingsTabsNotebook.AddPage(self.generalPanel, "General")

        self.advancedPanelSizer = wx.FlexGridSizer(rows=5, cols=4,
                                                   vgap=5, hgap=5)
        self.advancedPanel.SetSizer(self.advancedPanelSizer)
        # self.advancedPanelSizer.AddGrowableCol(1)

        # Add blank space above the settings fields. Our FlexGridSizer
        # has 4 columns, so we'll add 4 units of blank space.  We don't
        # care about the width (so we use -1), but we choose a height of
        # 5px (plus the FlexGridSizer's default vgap).
        self.advancedPanelSizer.Add(wx.Size(-1, 5))
        self.advancedPanelSizer.Add(wx.Size(-1, 5))
        self.advancedPanelSizer.Add(wx.Size(-1, 5))
        self.advancedPanelSizer.Add(wx.Size(-1, 5))

        folderStructureLabel = wx.StaticText(self.advancedPanel, wx.ID_ANY,
                                             "Folder Structure:")
        self.advancedPanelSizer.Add(folderStructureLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.folderStructures = [
            'Username / Dataset',
            'Email / Dataset',
            'Username / Experiment / Dataset',
            'Email / Experiment / Dataset',
            'Username / "MyTardis" / Experiment / Dataset',
            'User Group / Instrument / Full Name / Dataset']
        self.folderStructureComboBox = \
            wx.ComboBox(self.advancedPanel, wx.ID_ANY,
                        choices=self.folderStructures, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectFolderStructure,
                  self.folderStructureComboBox)
        self.folderStructureComboBox.SetValue("Username / Dataset")
        self.advancedPanelSizer.Add(self.folderStructureComboBox,
                                    flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        datasetGroupingLabel = wx.StaticText(self.advancedPanel, wx.ID_ANY,
                                             "Experiment (Dataset Grouping):")
        self.advancedPanelSizer.Add(datasetGroupingLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.datasetGroupingField = wx.TextCtrl(self.advancedPanel,
                                                wx.ID_ANY, "")
        self.datasetGroupingField\
            .SetValue("Instrument Name - Data Owner's Full Name")
        self.datasetGroupingField.SetEditable(False)
        self.advancedPanelSizer.Add(self.datasetGroupingField,
                                    flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        self.groupPrefixLabel = wx.StaticText(self.advancedPanel, wx.ID_ANY,
                                              "User Group Prefix:")
        self.advancedPanelSizer.Add(self.groupPrefixLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.groupPrefixField = wx.TextCtrl(self.advancedPanel, wx.ID_ANY, "")
        self.advancedPanelSizer.Add(self.groupPrefixField,
                                    flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        self.ignoreDatasetsOlderThanCheckBox = \
            wx.CheckBox(self.advancedPanel, wx.ID_ANY,
                        "Ignore datasets older than:")
        self.Bind(wx.EVT_CHECKBOX, self.OnIgnoreOldDatasetsCheckBox,
                  self.ignoreDatasetsOlderThanCheckBox)
        self.advancedPanelSizer.Add(self.ignoreDatasetsOlderThanCheckBox,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.ignoreIntervalPanel = wx.Panel(self.advancedPanel)
        self.ignoreIntervalPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ignoreIntervalPanel.SetSizer(self.ignoreIntervalPanelSizer)

        self.ignoreDatasetsOlderThanSpinCtrl = \
            wx.SpinCtrl(self.ignoreIntervalPanel, wx.ID_ANY,
                        "999", min=0, max=999)
        self.Bind(wx.EVT_SPINCTRL, self.OnIgnoreOldDatasetsSpinCtrl,
                  self.ignoreDatasetsOlderThanSpinCtrl)
        self.ignoreDatasetsOlderThanSpinCtrl.Enable(False)
        self.ignoreIntervalPanelSizer.Add(self.ignoreDatasetsOlderThanSpinCtrl,
                                          flag=wx.EXPAND | wx.ALL, border=5)
        self.intervalUnitsPlural = ['days', 'weeks', 'months', 'years']
        self.intervalUnitsSingular = ['day', 'week', 'month', 'year']
        self.showingSingularUnits = False
        self.intervalUnitsComboBox = \
            wx.ComboBox(self.ignoreIntervalPanel, wx.ID_ANY,
                        choices=self.intervalUnitsPlural, style=wx.CB_READONLY)
        self.intervalUnitsComboBox.Enable(False)
        self.ignoreIntervalPanelSizer.Add(self.intervalUnitsComboBox,
                                          flag=wx.EXPAND | wx.ALL, border=5)

        self.advancedPanelSizer.Add(self.ignoreIntervalPanel, flag=wx.EXPAND,
                                    border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        self.advancedPanel.Fit()
        self.settingsTabsNotebook.AddPage(self.advancedPanel, "Advanced")

        self.settingsTabsNotebook.Fit()
        self.settingsTabsNotebook\
            .SetMinSize(wx.Size(generalPanelSize.GetWidth(),
                                generalPanelSize.height +
                                self.settingsTabsNotebook.GetTabCtrlHeight()))
        self.dialogPanel.Fit()

        line = wx.StaticLine(self, wx.ID_ANY, size=(20, -1),
                             style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.EXPAND | wx.RIGHT | wx.TOP, 5)

        buttonSizer = wx.StdDialogButtonSizer()

        self.okButton = wx.Button(self, wx.ID_OK, "OK")
        self.okButton.SetDefault()
        buttonSizer.AddButton(self.okButton)

        self.helpButton = wx.Button(self, wx.ID_HELP, "Help")
        buttonSizer.AddButton(self.helpButton)

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
        self.helpButton.SetId(wx.NewId())
        self.Bind(wx.EVT_BUTTON, self.OnHelp, self.helpButton)

        sizer.Add(buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizer(sizer)
        self.Fit()

        self.UpdateFieldsFromModel(self.settingsModel)

        folderStructure = self.folderStructureComboBox.GetValue()
        if folderStructure != \
                'User Group / Instrument / Full Name / Dataset':
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)

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

    def GetFolderStructure(self):
        return self.folderStructureComboBox.GetValue()

    def SetFolderStructure(self, folderStructure):
        self.folderStructureComboBox.SetValue(folderStructure)

    def GetDatasetGrouping(self):
        return self.datasetGroupingField.GetValue()

    def SetDatasetGrouping(self, datasetGrouping):
        self.datasetGroupingField.SetValue(datasetGrouping)

    def GetGroupPrefix(self):
        return self.groupPrefixField.GetValue()

    def SetGroupPrefix(self, groupPrefix):
        self.groupPrefixField.SetValue(groupPrefix)

    def IgnoreOldDatasets(self):
        return self.ignoreDatasetsOlderThanCheckBox.GetValue()

    def SetIgnoreOldDatasets(self, ignoreOldDatasets):
        self.ignoreDatasetsOlderThanCheckBox.SetValue(ignoreOldDatasets)

    def GetIgnoreOldDatasetIntervalNumber(self):
        return self.ignoreDatasetsOlderThanSpinCtrl.GetValue()

    def SetIgnoreOldDatasetIntervalNumber(self,
                                          ignoreOldDatasetIntervalNumber):
        self.ignoreDatasetsOlderThanSpinCtrl\
            .SetValue(ignoreOldDatasetIntervalNumber)

    def GetIgnoreOldDatasetIntervalUnit(self):
        return self.intervalUnitsComboBox.GetValue()

    def SetIgnoreOldDatasetIntervalUnit(self, ignoreOldDatasetIntervalUnit):
        self.intervalUnitsComboBox.SetValue(ignoreOldDatasetIntervalUnit)

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
                           defaultPath=self.GetDataDirectory()
                           .encode('ascii', 'ignore'))
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

        self.SetFolderStructure(settingsModel.GetFolderStructure())
        self.SetDatasetGrouping(settingsModel.GetDatasetGrouping())
        self.SetGroupPrefix(settingsModel.GetGroupPrefix())
        self.SetIgnoreOldDatasets(settingsModel.IgnoreOldDatasets())
        self.SetIgnoreOldDatasetIntervalNumber(
            settingsModel.GetIgnoreOldDatasetIntervalNumber())
        if settingsModel.IgnoreOldDatasets():
            self.ignoreDatasetsOlderThanSpinCtrl.Enable(True)
            self.intervalUnitsComboBox.Enable(True)
        ignoreIntervalUnit = settingsModel.GetIgnoreOldDatasetIntervalUnit()
        if ignoreIntervalUnit in self.intervalUnitsPlural and \
                self.showingSingularUnits:
            self.intervalUnitsComboBox.Clear()
            self.intervalUnitsComboBox.AppendItems(self.intervalUnitsPlural)
            self.showingSingularUnits = False
        elif ignoreIntervalUnit in self.intervalUnitsSingular and \
                not self.showingSingularUnits:
            self.intervalUnitsComboBox.Clear()
            self.intervalUnitsComboBox.AppendItems(self.intervalUnitsSingular)
            self.showingSingularUnits = True
        self.SetIgnoreOldDatasetIntervalUnit(
            settingsModel.GetIgnoreOldDatasetIntervalUnit())

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

    def OnSave(self, event):
        mydataConfigPath = self.settingsModel.GetConfigPath()
        if mydataConfigPath is not None:
            dlg = wx.FileDialog(wx.GetApp().GetMainFrame(),
                                "Save MyData configuration as...",
                                os.path.dirname(mydataConfigPath),
                                "MyData.cfg", "*.cfg",
                                wx.SAVE | wx.OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                configPath = dlg.GetPath()
                wx.GetApp().SetConfigPath(configPath)
                self.settingsModel.SetConfigPath(configPath)
                self.settingsModel\
                    .SaveFieldsFromDialog(self,
                                          configPath=configPath)
                if configPath != wx.GetApp().GetConfigPath():
                    self.settingsModel.SaveFieldsFromDialog(
                        self, configPath=wx.GetApp().GetConfigPath())

    def OnApiKeyFieldFocused(self, event):
        self.apiKeyField.SelectAll()

    def OnIgnoreOldDatasetsCheckBox(self, event):
        if event.IsChecked():
            self.ignoreDatasetsOlderThanSpinCtrl.SetValue(6)
            self.ignoreDatasetsOlderThanSpinCtrl.Enable(True)
            if self.showingSingularUnits:
                self.intervalUnitsComboBox.Clear()
                self.intervalUnitsComboBox\
                    .AppendItems(self.intervalUnitsPlural)
                self.showingSingularUnits = False
            self.intervalUnitsComboBox.SetValue("months")
            self.intervalUnitsComboBox.Enable(True)
        else:
            self.ignoreDatasetsOlderThanSpinCtrl.SetValue(1)
            self.ignoreDatasetsOlderThanSpinCtrl.Enable(False)
            if not self.showingSingularUnits:
                self.intervalUnitsComboBox.Clear()
                self.intervalUnitsComboBox\
                    .AppendItems(self.intervalUnitsSingular)
                self.showingSingularUnits = True
            self.intervalUnitsComboBox.SetValue("month")
            self.intervalUnitsComboBox.Enable(False)

    def OnIgnoreOldDatasetsSpinCtrl(self, event):
        if event.GetInt() == 1:
            if not self.showingSingularUnits:
                intervalUnitValue = self.intervalUnitsComboBox.GetValue()
                self.intervalUnitsComboBox.Clear()
                self.intervalUnitsComboBox\
                    .AppendItems(self.intervalUnitsSingular)
                self.intervalUnitsComboBox\
                    .SetValue(intervalUnitValue.replace('s', ''))
                self.showingSingularUnits = True
        else:
            if self.showingSingularUnits:
                intervalUnitValue = self.intervalUnitsComboBox.GetValue()
                self.intervalUnitsComboBox.Clear()
                self.intervalUnitsComboBox\
                    .AppendItems(self.intervalUnitsPlural)
                self.intervalUnitsComboBox.SetValue(intervalUnitValue + 's')
                self.showingSingularUnits = False

    def OnHelp(self, event):
        wx.BeginBusyCursor()
        import webbrowser
        webbrowser.open("http://mydata.readthedocs.org/en/latest/settings.html")
        wx.EndBusyCursor()
        # from help.HelpController import helpController
        # if helpController is not None and \
                # helpController.initializationSucceeded:
            # helpController.Display("Settings")
            # wx.EndBusyCursor()
        # else:
            # wx.EndBusyCursor()
            # wx.MessageBox("Unable to open: " + helpController.mydataHelpUrl,
                          # "Error", wx.OK | wx.ICON_EXCLAMATION)

    def OnSelectFolderStructure(self, event):
        folderStructure = self.folderStructureComboBox.GetValue()
        if folderStructure == 'Username / Dataset' or \
                folderStructure == 'Email / Dataset':
            self.datasetGroupingField\
                .SetValue("Instrument Name - Data Owner's Full Name")
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)
        elif folderStructure == \
                'Username / "MyTardis" / Experiment / Dataset' or \
                folderStructure == 'Username / Experiment / Dataset' or \
                folderStructure == 'Email / Experiment / Dataset':
            self.datasetGroupingField.SetValue("Experiment")
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)
        elif folderStructure == \
                'User Group / Instrument / Full Name / Dataset':
            self.datasetGroupingField.SetValue("Instrument - Full Name")
            self.groupPrefixLabel.Show(True)
            self.groupPrefixField.Show(True)

    def OnDropFiles(self, filepaths):
        self.settingsModel.SetConfigPath(filepaths[0])
        self.settingsModel.LoadSettings()
        self.UpdateFieldsFromModel(self.settingsModel)

        folderStructure = self.folderStructureComboBox.GetValue()
        if folderStructure == \
                'User Group / Instrument / Full Name / Dataset':
            self.groupPrefixLabel.Show(True)
            self.groupPrefixField.Show(True)
        else:
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)
