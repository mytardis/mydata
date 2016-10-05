"""
Classes for MyData's settings dialog.
"""

# Disabling some Pylint checks for now...
# pylint: disable=missing-docstring
# pylint: disable=too-many-lines
# pylint: disable=too-many-statements
# pylint: disable=no-member
# pylint: disable=wrong-import-position

from datetime import datetime
from datetime import timedelta
import sys
import os
import traceback

import wx
if wx.version().startswith("3.0.3.dev"):
    import wx.lib.masked
    from wx.lib.agw.aui import AuiNotebook
    from wx.lib.agw.aui import AUI_NB_TOP
else:
    import wx.lib.masked
    from wx.aui import AuiNotebook
    from wx.aui import AUI_NB_TOP

from mydata.utils import BeginBusyCursorIfRequired
from mydata.utils import EndBusyCursorIfRequired
from mydata.logs import logger
import mydata.events as mde


class SettingsDropTarget(wx.FileDropTarget):
    """
    Handles drag and drop of a MyData.cfg file
    onto the settings dialog.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.parent = parent

    def OnDropFiles(self, x, y, filenames):
        # pylint: disable=invalid-name
        # pylint: disable=arguments-differ
        # pylint: disable=unused-argument
        """
        Handles drag and drop of a MyData.cfg file
        onto the settings dialog.
        """
        return self.parent.OnDropFiles(filenames)


class SettingsDialog(wx.Dialog):
    """
    MyData's settings dialog.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, parent,
                 settingsModel,
                 size=wx.DefaultSize,
                 pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE,
                 validationMessage=None):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title="Settings",
                           size=size, pos=pos, style=style)

        self.CenterOnParent()

        self.parent = parent
        self.settingsModel = settingsModel

        self.SetDropTarget(SettingsDropTarget(self))

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.dialogPanel = wx.Panel(self)

        if wx.version().startswith("3.0.3.dev"):
            self.settingsTabsNotebook = \
                AuiNotebook(self.dialogPanel, agwStyle=AUI_NB_TOP)
        else:
            self.settingsTabsNotebook = \
                AuiNotebook(self.dialogPanel, style=AUI_NB_TOP)
        # Without the following line, the tab font looks
        # too small on Mac OS X:
        self.settingsTabsNotebook.SetFont(self.dialogPanel.GetFont())
        self.generalPanel = wx.Panel(self.settingsTabsNotebook)
        self.schedulePanel = wx.Panel(self.settingsTabsNotebook)
        self.filtersPanel = wx.Panel(self.settingsTabsNotebook)
        self.advancedPanel = wx.Panel(self.settingsTabsNotebook)

        self.dialogPanelSizer = wx.BoxSizer()
        self.dialogPanelSizer.Add(self.settingsTabsNotebook, 0,
                                  wx.EXPAND | wx.ALL, 5)
        self.dialogPanel.SetSizer(self.dialogPanelSizer)

        sizer.Add(self.dialogPanel, 1, wx.EXPAND | wx.ALL, 5)

        if sys.platform.startswith("linux"):
            self.SetMinSize(wx.Size(-1, 490))

        # General tab

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
            self.instrumentNameField.SetMinSize(wx.Size(290, -1))
        elif sys.platform.startswith("linux"):
            self.instrumentNameField.SetMinSize(wx.Size(290, -1))
        else:
            self.instrumentNameField.SetMinSize(wx.Size(265, -1))
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

        # Schedule tab

        self.innerSchedulePanel = wx.Panel(self.schedulePanel)
        self.innerSchedulePanelSizer = wx.BoxSizer(wx.VERTICAL)

        self.scheduleTypePanel = wx.Panel(self.innerSchedulePanel)
        self.scheduleTypePanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.scheduleTypePanelSizer.Add(wx.StaticText(self.innerSchedulePanel,
                                                      wx.ID_ANY,
                                                      "Schedule type"))

        choices = ["On Startup", "On Settings Saved", "Manually",
                   "Once", "Daily", "Weekly", "Timer"]
        self.scheduleTypeComboBox = wx.ComboBox(self.scheduleTypePanel,
                                                choices=choices,
                                                style=wx.CB_READONLY)
        self.scheduleTypeComboBox.SetMinSize((150, -1))
        self.scheduleTypeComboBox.SetSelection(0)
        self.scheduleTypePanelSizer.Add(self.scheduleTypeComboBox)
        self.Bind(wx.EVT_COMBOBOX, self.OnScheduleTypeChange,
                  self.scheduleTypeComboBox)
        self.scheduleTypePanel.SetSizerAndFit(self.scheduleTypePanelSizer)
        self.innerSchedulePanelSizer.Add(self.scheduleTypePanel)
        self.innerSchedulePanelSizer.AddSpacer(10)

        self.dateTimePanel = wx.Panel(self.innerSchedulePanel, wx.ID_ANY)
        self.innerSchedulePanelSizer.Add(self.dateTimePanel, flag=wx.EXPAND)
        self.dateTimeGroupBox = wx.StaticBox(self.dateTimePanel, wx.ID_ANY,
                                             label="Date/Time")
        # self.dateTimeGroupBox.SetFont(self.smallFont)
        self.dateTimeGroupBoxSizer = wx.StaticBoxSizer(self.dateTimeGroupBox,
                                                       wx.VERTICAL)
        self.dateTimePanel.SetSizer(self.dateTimeGroupBoxSizer)
        self.innerDateTimePanel = wx.Panel(self.dateTimePanel, wx.ID_ANY)
        self.innerDateTimePanelSizer = wx.FlexGridSizer(rows=2, cols=2,
                                                        hgap=10, vgap=10)
        self.innerDateTimePanel.SetSizer(self.innerDateTimePanelSizer)

        self.innerDateTimePanel.Fit()
        self.dateTimeGroupBoxSizer.Add(self.innerDateTimePanel, flag=wx.EXPAND)
        self.dateTimePanel.Fit()
        self.datePanel = wx.Panel(self.innerDateTimePanel, wx.ID_ANY)
        self.datePanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.dateLabel = wx.StaticText(self.datePanel, label="Date")
        self.datePanelSizer.Add(self.dateLabel)
        # self.dateLabel.SetFont(self.smallFont)
        self.dateEntryPanel = wx.Panel(self.datePanel, wx.ID_ANY)
        self.dateEntryPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.dateCtrl = wx.lib.masked.Ctrl(self.dateEntryPanel,
                                           autoformat='EUDATEDDMMYYYY/',
                                           size=(120, -1))
        self.dateEntryPanelSizer.Add(self.dateCtrl)
        height = self.dateCtrl.GetSize().height
        self.dateSpin = wx.SpinButton(self.dateEntryPanel, wx.ID_ANY,
                                      size=(-1, height), style=wx.SP_VERTICAL)
        self.dateSpin.SetRange(-999, 999)
        self.Bind(wx.EVT_SPIN_UP, self.OnIncrementDate, self.dateSpin)
        self.Bind(wx.EVT_SPIN_DOWN, self.OnDecrementDate, self.dateSpin)
        self.dateEntryPanelSizer.Add(self.dateSpin)
        self.dateEntryPanel.SetSizerAndFit(self.dateEntryPanelSizer)
        self.datePanelSizer.Add(self.dateEntryPanel)
        self.datePanel.SetSizerAndFit(self.datePanelSizer)
        self.innerDateTimePanelSizer.Add(self.datePanel)

        self.timePanel = wx.Panel(self.innerDateTimePanel, wx.ID_ANY)
        self.timePanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.timeLabel = wx.StaticText(self.timePanel, label="Time")
        self.timePanelSizer.Add(self.timeLabel)
        # self.timeLabel.SetFont(self.smallFont)
        self.timeEntryPanel = wx.Panel(self.timePanel, wx.ID_ANY)
        self.timeEntryPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.timeCtrl = wx.lib.masked.TimeCtrl(self.timeEntryPanel,
                                               displaySeconds=False,
                                               size=(120, -1))
        self.timeEntryPanelSizer.Add(self.timeCtrl)
        height = self.timeCtrl.GetSize().height
        self.timeSpin = wx.SpinButton(self.timeEntryPanel, wx.ID_ANY,
                                      size=(-1, height), style=wx.SP_VERTICAL)
        self.timeSpin.SetRange(-999, 999)
        self.Bind(wx.EVT_SPIN_UP, self.OnIncrementTime, self.timeSpin)
        self.Bind(wx.EVT_SPIN_DOWN, self.OnDecrementTime, self.timeSpin)
        self.timeEntryPanelSizer.Add(self.timeSpin)
        self.timeEntryPanel.SetSizerAndFit(self.timeEntryPanelSizer)
        self.timePanelSizer.Add(self.timeEntryPanel)
        self.timePanel.SetSizerAndFit(self.timePanelSizer)
        self.innerDateTimePanelSizer.Add(self.timePanel)

        self.timerPanel = wx.Panel(self.innerDateTimePanel, wx.ID_ANY)
        self.timerPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.timerLabel = wx.StaticText(self.timerPanel,
                                        label="Timer (minutes)")
        self.timerPanelSizer.Add(self.timerLabel)
        # self.timerLabel.SetFont(self.smallFont)
        self.timerEntryPanel = wx.Panel(self.timerPanel, wx.ID_ANY)
        self.timerEntryPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.timerNumCtrl = wx.lib.masked.NumCtrl(self.timerEntryPanel,
                                                  size=(120, -1))
        self.timerNumCtrl.SetMax(999)
        self.timerNumCtrl.SetValue(15)
        self.timerEntryPanelSizer.Add(self.timerNumCtrl)
        height = self.timerNumCtrl.GetSize().height
        self.timerSpin = wx.SpinButton(self.timerEntryPanel, wx.ID_ANY,
                                       size=(-1, height), style=wx.SP_VERTICAL)
        self.timerSpin.SetMax(999)
        self.timerSpin.SetValue(15)
        self.Bind(wx.EVT_SPIN, self.OnSpinTimer, self.timerSpin)
        self.timerEntryPanelSizer.Add(self.timerSpin)
        self.timerEntryPanel.SetSizerAndFit(self.timerEntryPanelSizer)
        self.timerPanelSizer.Add(self.timerEntryPanel)
        self.timerPanel.SetSizerAndFit(self.timerPanelSizer)
        self.innerDateTimePanelSizer.Add(self.timerPanel)

        self.fromToPanel = wx.Panel(self.innerDateTimePanel, wx.ID_ANY)
        self.fromToPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fromPanel = wx.Panel(self.fromToPanel, wx.ID_ANY)
        self.fromPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.fromLabel = wx.StaticText(self.fromPanel, label="From:")
        self.fromPanelSizer.Add(self.fromLabel)
        # self.fromLabel.SetFont(self.smallFont)
        self.fromTimeEntryPanel = wx.Panel(self.fromPanel, wx.ID_ANY)
        self.fromTimeEntryPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fromTimeCtrl = wx.lib.masked.TimeCtrl(self.fromTimeEntryPanel,
                                                   displaySeconds=False,
                                                   size=(120, -1))
        self.fromTimeEntryPanelSizer.Add(self.fromTimeCtrl)
        height = self.fromTimeCtrl.GetSize().height
        self.fromTimeSpin = wx.SpinButton(self.fromTimeEntryPanel, wx.ID_ANY,
                                          size=(-1, height),
                                          style=wx.SP_VERTICAL)
        self.fromTimeSpin.SetRange(-999, 999)
        self.Bind(wx.EVT_SPIN_UP, self.OnIncrementFromTime, self.fromTimeSpin)
        self.Bind(wx.EVT_SPIN_DOWN, self.OnDecrementFromTime,
                  self.fromTimeSpin)
        self.fromTimeEntryPanelSizer.Add(self.fromTimeSpin)
        self.fromTimeEntryPanel.SetSizerAndFit(self.fromTimeEntryPanelSizer)
        self.fromPanelSizer.Add(self.fromTimeEntryPanel)
        self.fromPanel.SetSizerAndFit(self.fromPanelSizer)
        self.fromToPanelSizer.Add(self.fromPanel)
        self.fromToPanelSizer.AddSpacer(10)
        self.toPanel = wx.Panel(self.fromToPanel, wx.ID_ANY)
        self.toPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.toLabel = wx.StaticText(self.toPanel, label="To:")
        self.toPanelSizer.Add(self.toLabel)
        # self.toLabel.SetFont(self.smallFont)
        self.toTimeEntryPanel = wx.Panel(self.toPanel, wx.ID_ANY)
        self.toTimeEntryPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.toTimeCtrl = wx.lib.masked.TimeCtrl(self.toTimeEntryPanel,
                                                 displaySeconds=False,
                                                 value='23:59:59',
                                                 size=(120, -1))
        self.toTimeEntryPanelSizer.Add(self.toTimeCtrl)
        height = self.toTimeCtrl.GetSize().height
        self.toTimeSpin = wx.SpinButton(self.toTimeEntryPanel, wx.ID_ANY,
                                        size=(-1, height),
                                        style=wx.SP_VERTICAL)
        self.toTimeSpin.SetRange(-999, 999)
        self.Bind(wx.EVT_SPIN_UP, self.OnIncrementToTime, self.toTimeSpin)
        self.Bind(wx.EVT_SPIN_DOWN, self.OnDecrementToTime, self.toTimeSpin)
        self.toTimeEntryPanelSizer.Add(self.toTimeSpin)
        self.toTimeEntryPanel.SetSizerAndFit(self.toTimeEntryPanelSizer)
        self.toPanelSizer.Add(self.toTimeEntryPanel)
        self.toPanel.SetSizerAndFit(self.toPanelSizer)
        self.fromToPanelSizer.Add(self.toPanel)
        self.fromToPanel.SetSizerAndFit(self.fromToPanelSizer)
        self.innerDateTimePanelSizer.Add(self.fromToPanel)

        self.innerDateTimePanel.SetSizerAndFit(self.innerDateTimePanelSizer)
        self.dateTimePanel.SetSizerAndFit(self.dateTimeGroupBoxSizer)

        self.innerSchedulePanelSizer.AddSpacer(10)

        self.daysOfTheWeekPanel = wx.Panel(self.innerSchedulePanel, wx.ID_ANY)
        self.daysOfTheWeekGroupBox = wx.StaticBox(self.daysOfTheWeekPanel,
                                                  wx.ID_ANY,
                                                  label="Days of the week")
        # self.daysOfTheWeekGroupBox.SetFont(self.smallFont)
        self.daysOfTheWeekGroupBoxSizer = \
            wx.StaticBoxSizer(self.daysOfTheWeekGroupBox, wx.VERTICAL)
        self.daysOfTheWeekPanel.SetSizer(self.daysOfTheWeekGroupBoxSizer)
        self.innerDaysOfTheWeekPanel = wx.Panel(self.daysOfTheWeekPanel,
                                                wx.ID_ANY)
        self.innerDaysOfTheWeekPanelSizer = wx.FlexGridSizer(rows=2, cols=5,
                                                             hgap=10, vgap=10)
        self.innerDaysOfTheWeekPanel\
            .SetSizer(self.innerDaysOfTheWeekPanelSizer)

        self.mondayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                          label="Monday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.mondayCheckBox)
        self.tuesdayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                           label="Tuesday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.tuesdayCheckBox)
        self.wednesdayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                             label="Wednesday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.wednesdayCheckBox)
        self.thursdayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                            label="Thursday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.thursdayCheckBox)
        self.fridayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                          label="Friday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.fridayCheckBox)
        self.saturdayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                            label="Saturday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.saturdayCheckBox)
        self.sundayCheckBox = wx.CheckBox(self.innerDaysOfTheWeekPanel,
                                          label="Sunday")
        self.innerDaysOfTheWeekPanelSizer.Add(self.sundayCheckBox)

        self.innerDaysOfTheWeekPanel\
            .SetSizerAndFit(self.innerDaysOfTheWeekPanelSizer)
        self.daysOfTheWeekGroupBoxSizer.Add(self.innerDaysOfTheWeekPanel,
                                            flag=wx.EXPAND)
        self.daysOfTheWeekPanel.SetSizerAndFit(self.daysOfTheWeekGroupBoxSizer)
        self.innerSchedulePanelSizer.Add(self.daysOfTheWeekPanel,
                                         flag=wx.EXPAND)
        self.innerSchedulePanelSizer.AddSpacer(10)

        self.innerSchedulePanel.SetSizerAndFit(self.innerSchedulePanelSizer)

        schedulePanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=0, hgap=0)
        schedulePanelSizer.Add(self.innerSchedulePanel,
                               flag=wx.ALL, border=20)
        self.schedulePanel.SetSizerAndFit(schedulePanelSizer)

        self.OnScheduleTypeChange(None)

        self.settingsTabsNotebook.AddPage(self.schedulePanel, "Schedule")

        # Filters tab

        self.filtersPanelSizer = wx.FlexGridSizer(rows=9, cols=3,
                                                  vgap=5, hgap=5)
        self.filtersPanel.SetSizer(self.filtersPanelSizer)
        # self.filtersPanelSizer.AddGrowableCol(1)

        # Add blank space above the settings fields. Our FlexGridSizer
        # has 4 columns, so we'll add 4 units of blank space.  We don't
        # care about the width (so we use -1), but we choose a height of
        # 5px (plus the FlexGridSizer's default vgap).
        self.filtersPanelSizer.Add(wx.Size(-1, 5))
        self.filtersPanelSizer.Add(wx.Size(-1, 5))
        self.filtersPanelSizer.Add(wx.Size(-1, 5))

        self.userFolderFilterLabel = \
            wx.StaticText(self.filtersPanel, wx.ID_ANY,
                          "User Group folder name contains:",
                          style=wx.ST_NO_AUTORESIZE)
        self.filtersPanelSizer.Add(self.userFolderFilterLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.userFolderFilterField = wx.TextCtrl(self.filtersPanel,
                                                 wx.ID_ANY, "")
        if sys.platform.startswith("darwin"):
            self.userFolderFilterField.SetMinSize(wx.Size(290, -1))
        else:
            self.userFolderFilterField.SetMinSize(wx.Size(265, -1))
        self.filtersPanelSizer.Add(self.userFolderFilterField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.filtersPanel, wx.ID_ANY, "")
        self.filtersPanelSizer.Add(blankLine)

        self.expFolderFilterLabel = \
            wx.StaticText(self.filtersPanel, wx.ID_ANY,
                          "Experiment folder name contains:")
        self.filtersPanelSizer.Add(self.expFolderFilterLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.expFolderFilterField = wx.TextCtrl(self.filtersPanel,
                                                wx.ID_ANY, "")
        if sys.platform.startswith("darwin"):
            self.expFolderFilterField.SetMinSize(wx.Size(290, -1))
        else:
            self.expFolderFilterField.SetMinSize(wx.Size(265, -1))
        self.filtersPanelSizer.Add(self.expFolderFilterField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.filtersPanel, wx.ID_ANY, "")
        self.filtersPanelSizer.Add(blankLine)

        self.datasetFolderFilterLabel = \
            wx.StaticText(self.filtersPanel, wx.ID_ANY,
                          "Dataset folder name contains:")
        self.filtersPanelSizer.Add(self.datasetFolderFilterLabel,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.datasetFolderFilterField = wx.TextCtrl(self.filtersPanel,
                                                    wx.ID_ANY, "")
        if sys.platform.startswith("darwin"):
            self.datasetFolderFilterField.SetMinSize(wx.Size(290, -1))
        else:
            self.datasetFolderFilterField.SetMinSize(wx.Size(265, -1))
        self.filtersPanelSizer.Add(self.datasetFolderFilterField,
                                   flag=wx.EXPAND | wx.ALL, border=5)
        blankLine = wx.StaticText(self.filtersPanel, wx.ID_ANY, "")
        self.filtersPanelSizer.Add(blankLine)

        self.ignoreDatasetsOlderThanCheckBox = \
            wx.CheckBox(self.filtersPanel, wx.ID_ANY,
                        "Ignore datasets older than:")
        self.Bind(wx.EVT_CHECKBOX, self.OnIgnoreOldDatasetsCheckBox,
                  self.ignoreDatasetsOlderThanCheckBox)
        self.filtersPanelSizer.Add(self.ignoreDatasetsOlderThanCheckBox,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.ignoreIntervalPanel = wx.Panel(self.filtersPanel)
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

        self.filtersPanelSizer.Add(self.ignoreIntervalPanel, flag=wx.EXPAND,
                                   border=5)
        self.filtersPanelSizer.Add(wx.StaticText(self.filtersPanel,
                                                 wx.ID_ANY, ""))

        self.ignoreFilesNewerThanCheckBox = \
            wx.CheckBox(self.filtersPanel, wx.ID_ANY,
                        "Ignore files newer than:")
        self.Bind(wx.EVT_CHECKBOX, self.OnIgnoreNewFilesCheckBox,
                  self.ignoreFilesNewerThanCheckBox)
        self.filtersPanelSizer.Add(self.ignoreFilesNewerThanCheckBox,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.ignoreFilesIntervalPanel = wx.Panel(self.filtersPanel)
        self.ignoreFilesPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ignoreFilesIntervalPanel.SetSizer(self.ignoreFilesPanelSizer)

        self.ignoreFilesNewerThanSpinCtrl = \
            wx.SpinCtrl(self.ignoreFilesIntervalPanel, wx.ID_ANY,
                        "1", min=0, max=999)
        self.Bind(wx.EVT_SPINCTRL, self.OnIgnoreNewFilesSpinCtrl,
                  self.ignoreFilesNewerThanSpinCtrl)
        self.ignoreFilesNewerThanSpinCtrl.Enable(False)
        self.ignoreFilesPanelSizer.Add(self.ignoreFilesNewerThanSpinCtrl,
                                       flag=wx.EXPAND | wx.ALL, border=5)
        self.showingSingularMinutes = True
        self.ignoreFilesIntervalUnitLabel = \
           wx.StaticText(self.ignoreFilesIntervalPanel, wx.ID_ANY, "minute")
        self.ignoreFilesPanelSizer.Add(self.ignoreFilesIntervalUnitLabel,
                                       flag=wx.EXPAND | wx.ALL, border=5)

        self.filtersPanelSizer.Add(self.ignoreFilesIntervalPanel, flag=wx.EXPAND,
                                   border=5)
        self.filtersPanelSizer.Add(wx.StaticText(self.filtersPanel,
                                                 wx.ID_ANY, ""))

        self.includesFileCheckBox = \
            wx.CheckBox(self.filtersPanel, wx.ID_ANY,
                        "Include files matching patterns in:")
        self.Bind(wx.EVT_CHECKBOX, self.OnIncludeFiles,
                  self.includesFileCheckBox)
        self.filtersPanelSizer.Add(self.includesFileCheckBox,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.includesFilePanel = wx.Panel(self.filtersPanel)
        self.includesFilePanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.includesFilePanel.SetSizer(self.includesFilePanelSizer)
        # N.B. TE_RIGHT is ignored on Mac OS X.
        self.includesFileField = wx.TextCtrl(self.includesFilePanel,
                                             wx.ID_ANY, "",
                                             style=wx.TE_RIGHT)
        self.includesFilePanelSizer.Add(self.includesFileField,
                                        flag=wx.GROW | wx.ALL, border=5,
                                        proportion=3)
        self.browseIncludesFileButton = wx.Button(self.includesFilePanel,
                                                  wx.ID_ANY, "Browse...")
        self.browseIncludesFileButton.SetMaxSize(wx.Size(
            self.browseIncludesFileButton.GetSize().width, -1))
        self.Bind(wx.EVT_BUTTON, self.OnBrowseIncludesFile,
                  self.browseIncludesFileButton)
        self.includesFilePanelSizer.Add(self.browseIncludesFileButton,
                                        flag=wx.ALL, border=5, proportion=1)
        self.filtersPanelSizer.Add(self.includesFilePanel, flag=wx.EXPAND,
                                   border=5)
        self.filtersPanelSizer.Add(wx.StaticText(self.filtersPanel,
                                                 wx.ID_ANY, ""))

        self.excludesFileCheckBox = \
            wx.CheckBox(self.filtersPanel, wx.ID_ANY,
                        "Exclude files matching patterns in:")
        self.Bind(wx.EVT_CHECKBOX, self.OnExcludeFiles,
                  self.excludesFileCheckBox)
        self.filtersPanelSizer.Add(self.excludesFileCheckBox,
                                   flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.excludesFilePanel = wx.Panel(self.filtersPanel)
        self.excludesFilePanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.excludesFilePanel.SetSizer(self.excludesFilePanelSizer)
        # N.B. TE_RIGHT is ignored on Mac OS X.
        self.excludesFileField = wx.TextCtrl(self.excludesFilePanel,
                                             wx.ID_ANY, "",
                                             style=wx.TE_RIGHT)
        self.excludesFilePanelSizer.Add(self.excludesFileField,
                                        flag=wx.GROW | wx.ALL, border=5,
                                        proportion=3)
        self.browseExcludesFileButton = wx.Button(self.excludesFilePanel,
                                                  wx.ID_ANY, "Browse...")
        self.browseExcludesFileButton.SetMaxSize(wx.Size(
            self.browseExcludesFileButton.GetSize().width, -1))
        self.Bind(wx.EVT_BUTTON, self.OnBrowseExcludesFile,
                  self.browseExcludesFileButton)
        self.excludesFilePanelSizer.Add(self.browseExcludesFileButton,
                                        flag=wx.ALL, border=5, proportion=1)
        self.filtersPanelSizer.Add(self.excludesFilePanel, flag=wx.EXPAND,
                                   border=5)
        self.filtersPanelSizer.Add(wx.StaticText(self.filtersPanel,
                                                 wx.ID_ANY, ""))

        self.filtersPanel.Fit()
        self.settingsTabsNotebook.AddPage(self.filtersPanel, "Filters")

        # Advanced tab

        self.advancedPanelSizer = wx.FlexGridSizer(rows=10, cols=3,
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
            'User Group / Instrument / Full Name / Dataset',
            'User Group / Experiment / Dataset',
            'Experiment / Dataset',
            'Dataset']
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

        validateFolderStructureLabel = \
            wx.StaticText(self.advancedPanel, wx.ID_ANY,
                          "Validate folder structure:")
        self.advancedPanelSizer.Add(validateFolderStructureLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.validateFolderStructureCheckBox = \
            wx.CheckBox(self.advancedPanel, wx.ID_ANY, "")
        self.advancedPanelSizer\
            .Add(self.validateFolderStructureCheckBox,
                 flag=wx.EXPAND | wx.ALL, border=5)
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
                                                  wx.ID_ANY, "        "))

        self.groupPrefixLabel = wx.StaticText(self.advancedPanel, wx.ID_ANY,
                                              "User Group Prefix:")
        self.advancedPanelSizer.Add(self.groupPrefixLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.groupPrefixField = wx.TextCtrl(self.advancedPanel, wx.ID_ANY, "")
        self.advancedPanelSizer.Add(self.groupPrefixField,
                                    flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        maxUploadThreadsLabel = wx.StaticText(self.advancedPanel, wx.ID_ANY,
                                              "Maximum # of upload threads:")
        self.advancedPanelSizer.Add(maxUploadThreadsLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.maxUploadThreadsPanel = wx.Panel(self.advancedPanel)
        self.maxUploadThreadsPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.maxUploadThreadsPanel.SetSizer(self.maxUploadThreadsPanelSizer)

        self.maxUploadThreadsSpinCtrl = \
            wx.SpinCtrl(self.maxUploadThreadsPanel, wx.ID_ANY,
                        "5", min=1, max=99)
        self.maxUploadThreadsPanelSizer.Add(self.maxUploadThreadsSpinCtrl,
                                            flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(self.maxUploadThreadsPanel,
                                    flag=wx.EXPAND, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        maxUploadRetriesLabel = wx.StaticText(self.advancedPanel, wx.ID_ANY,
                                              "Maximum # of upload retries:")
        self.advancedPanelSizer.Add(maxUploadRetriesLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.maxUploadRetriesPanel = wx.Panel(self.advancedPanel)
        self.maxUploadRetriesPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.maxUploadRetriesPanel.SetSizer(self.maxUploadRetriesPanelSizer)

        self.maxUploadRetriesSpinCtrl = \
            wx.SpinCtrl(self.maxUploadRetriesPanel, wx.ID_ANY,
                        "1", min=0, max=99)
        self.maxUploadRetriesPanelSizer.Add(self.maxUploadRetriesSpinCtrl,
                                            flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(self.maxUploadRetriesPanel,
                                    flag=wx.EXPAND, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        startAutomaticallyOnLoginLabel = \
            wx.StaticText(self.advancedPanel, wx.ID_ANY,
                          "Start automatically on login:")
        self.advancedPanelSizer.Add(startAutomaticallyOnLoginLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.startAutomaticallyCheckBox = \
            wx.CheckBox(self.advancedPanel, wx.ID_ANY, "")
        self.advancedPanelSizer\
            .Add(self.startAutomaticallyCheckBox,
                 flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        self.uploadInvalidUserFoldersLabel = \
            wx.StaticText(self.advancedPanel, wx.ID_ANY,
                          "Upload invalid user folders:")
        self.advancedPanelSizer.Add(self.uploadInvalidUserFoldersLabel,
                                    flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.uploadInvalidUserFoldersCheckBox = \
            wx.CheckBox(self.advancedPanel, wx.ID_ANY, "")
        self.advancedPanelSizer\
            .Add(self.uploadInvalidUserFoldersCheckBox,
                 flag=wx.EXPAND | wx.ALL, border=5)
        self.advancedPanelSizer.Add(wx.StaticText(self.advancedPanel,
                                                  wx.ID_ANY, ""))

        self.advancedPanel.Fit()
        self.settingsTabsNotebook.AddPage(self.advancedPanel, "Advanced")

        self.settingsTabsNotebook.Fit()
        self.settingsTabsNotebook\
            .SetMinSize(wx.Size(generalPanelSize.GetWidth(),
                                generalPanelSize.height +
                                self.settingsTabsNotebook
                                .GetTabCtrlHeight()))
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

        # We need to use one of the standard IDs recognized by
        # StdDialogSizer:
        self.lockOrUnlockButton = wx.Button(self, wx.ID_APPLY, "Lock")
        buttonSizer.AddButton(self.lockOrUnlockButton)
        self.Bind(wx.EVT_BUTTON, self.OnLockOrUnlockSettings,
                  self.lockOrUnlockButton)

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
        if not folderStructure.startswith("User Group"):
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)

        if "User" in folderStructure or "Email" in folderStructure:
            self.uploadInvalidUserFoldersLabel.Show(True)
            self.uploadInvalidUserFoldersCheckBox.Show(True)
        else:
            self.uploadInvalidUserFoldersLabel.Show(False)
            self.uploadInvalidUserFoldersCheckBox.Show(False)

        if folderStructure.startswith("User Group"):
            self.uploadInvalidUserFoldersLabel.SetLabel(
                "Upload invalid group folders:")
        else:
            self.uploadInvalidUserFoldersLabel.SetLabel(
                "Upload invalid user folders:")

        if "Experiment" not in folderStructure:
            self.expFolderFilterLabel.Show(False)
            self.expFolderFilterField.SetValue("")
            self.expFolderFilterField.Show(False)

        if "User" not in folderStructure and \
                "Email" not in folderStructure:
            self.userFolderFilterLabel.Show(False)
            self.userFolderFilterField.SetValue("")
            self.userFolderFilterField.Show(False)

        if folderStructure.startswith("Username"):
            self.userFolderFilterLabel.SetLabel(
                "  Username folder name contains:")
        elif folderStructure.startswith("Email"):
            self.userFolderFilterLabel.SetLabel(
                "     Email folder name contains:")
        elif folderStructure.startswith("User Group"):
            self.userFolderFilterLabel.SetLabel(
                "User Group folder name contains:")

        self.Show()
        if validationMessage:
            dlg = wx.MessageDialog(self, validationMessage, "MyData - Invalid Settings",
                                   wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
    # General tab

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

    # Schedule tab

    def GetScheduleType(self):
        return self.scheduleTypeComboBox.GetValue()

    def SetScheduleType(self, scheduleType):
        self.scheduleTypeComboBox.SetValue(scheduleType)

    def IsMondayChecked(self):
        return self.mondayCheckBox.GetValue()

    def SetMondayChecked(self, checked):
        self.mondayCheckBox.SetValue(checked)

    def IsTuesdayChecked(self):
        return self.tuesdayCheckBox.GetValue()

    def SetTuesdayChecked(self, checked):
        self.tuesdayCheckBox.SetValue(checked)

    def IsWednesdayChecked(self):
        return self.wednesdayCheckBox.GetValue()

    def SetWednesdayChecked(self, checked):
        self.wednesdayCheckBox.SetValue(checked)

    def IsThursdayChecked(self):
        return self.thursdayCheckBox.GetValue()

    def SetThursdayChecked(self, checked):
        self.thursdayCheckBox.SetValue(checked)

    def IsFridayChecked(self):
        return self.fridayCheckBox.GetValue()

    def SetFridayChecked(self, checked):
        self.fridayCheckBox.SetValue(checked)

    def IsSaturdayChecked(self):
        return self.saturdayCheckBox.GetValue()

    def SetSaturdayChecked(self, checked):
        self.saturdayCheckBox.SetValue(checked)

    def IsSundayChecked(self):
        return self.sundayCheckBox.GetValue()

    def SetSundayChecked(self, checked):
        self.sundayCheckBox.SetValue(checked)

    def GetScheduledDate(self):
        return datetime.date(datetime.strptime(self.dateCtrl.GetValue(),
                                               "%d/%m/%Y"))

    def SetScheduledDate(self, date):
        self.dateCtrl.SetValue(date.strftime('%d/%m/%Y'))

    def GetScheduledTime(self):
        timeString = self.timeCtrl.GetValue()
        try:
            return datetime.time(datetime.strptime(timeString, "%I:%M %p"))
        except ValueError:
            return datetime.time(datetime.strptime(timeString, "%H:%M"))

    def SetScheduledTime(self, time):
        # http://www.wxpython.org/docs/api/wx.lib.masked.timectrl-module.html
        # NOTE: due to a problem with wx.DateTime, if the locale does not use
        # 'AM/PM' for its values, the default format will automatically change
        # to 24 hour format, and an AttributeError will be thrown if a non-24
        # format is specified.
        try:
            self.timeCtrl.SetValue(time.strftime("%I:%M %p"))
        except AttributeError:
            self.timeCtrl.SetValue(time.strftime("%H:%M"))

    def GetTimerMinutes(self):
        return self.timerNumCtrl.GetValue()

    def SetTimerMinutes(self, minutes):
        self.timerNumCtrl.SetValue(minutes)
        self.timerSpin.SetValue(minutes)

    def GetTimerFromTime(self):
        timeString = self.fromTimeCtrl.GetValue()
        try:
            return datetime.time(datetime.strptime(timeString, "%I:%M %p"))
        except ValueError:
            return datetime.time(datetime.strptime(timeString, "%H:%M"))

    def SetTimerFromTime(self, time):
        # http://www.wxpython.org/docs/api/wx.lib.masked.timectrl-module.html
        # NOTE: due to a problem with wx.DateTime, if the locale does not use
        # 'AM/PM' for its values, the default format will automatically change
        # to 24 hour format, and an AttributeError will be thrown if a non-24
        # format is specified.
        try:
            self.fromTimeCtrl.SetValue(time.strftime("%I:%M %p"))
        except AttributeError:
            self.fromTimeCtrl.SetValue(time.strftime("%H:%M"))

    def GetTimerToTime(self):
        timeString = self.toTimeCtrl.GetValue()
        try:
            return datetime.time(datetime.strptime(timeString, "%I:%M %p"))
        except ValueError:
            return datetime.time(datetime.strptime(timeString, "%H:%M"))

    def SetTimerToTime(self, time):
        # http://www.wxpython.org/docs/api/wx.lib.masked.timectrl-module.html
        # NOTE: due to a problem with wx.DateTime, if the locale does not use
        # 'AM/PM' for its values, the default format will automatically change
        # to 24 hour format, and an AttributeError will be thrown if a non-24
        # format is specified.
        try:
            self.toTimeCtrl.SetValue(time.strftime("%I:%M %p"))
        except AttributeError:
            self.toTimeCtrl.SetValue(time.strftime("%H:%M"))

    # Filters tab

    def GetUserFilter(self):
        return self.userFolderFilterField.GetValue()

    def SetUserFilter(self, userFilter):
        self.userFolderFilterField.SetValue(userFilter)

    def GetDatasetFilter(self):
        return self.datasetFolderFilterField.GetValue()

    def SetDatasetFilter(self, datasetFilter):
        self.datasetFolderFilterField.SetValue(datasetFilter)

    def GetExperimentFilter(self):
        return self.expFolderFilterField.GetValue()

    def SetExperimentFilter(self, experimentFilter):
        self.expFolderFilterField.SetValue(experimentFilter)

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

    def IgnoreNewFiles(self):
        return self.ignoreFilesNewerThanCheckBox.GetValue()

    def SetIgnoreNewFiles(self, ignoreNewFiles):
        self.ignoreFilesNewerThanCheckBox.SetValue(ignoreNewFiles)

    def GetIgnoreNewFilesMinutes(self):
        return self.ignoreFilesNewerThanSpinCtrl.GetValue()

    def SetIgnoreNewFilesMinutes(self, ignoreNewFilesMinutes):
        self.ignoreFilesNewerThanSpinCtrl.SetValue(ignoreNewFilesMinutes)

    def UseIncludesFile(self):
        return self.includesFileCheckBox.GetValue()

    def SetUseIncludesFile(self, useIncludesFile):
        return self.includesFileCheckBox.SetValue(useIncludesFile)

    def GetIncludesFile(self):
        return self.includesFileField.GetValue()

    def SetIncludesFile(self, includesFile):
        return self.includesFileField.SetValue(includesFile)

    def UseExcludesFile(self):
        return self.excludesFileCheckBox.GetValue()

    def SetUseExcludesFile(self, useExcludesFile):
        return self.excludesFileCheckBox.SetValue(useExcludesFile)

    def GetExcludesFile(self):
        return self.excludesFileField.GetValue()

    def SetExcludesFile(self, excludesFile):
        return self.excludesFileField.SetValue(excludesFile)

    # Advanced tab

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

    def ValidateFolderStructure(self):
        return self.validateFolderStructureCheckBox.GetValue()

    def SetValidateFolderStructure(self, validateFolderStructure):
        self.validateFolderStructureCheckBox.SetValue(validateFolderStructure)

    def GetMaxUploadThreads(self):
        return self.maxUploadThreadsSpinCtrl.GetValue()

    def SetMaxUploadThreads(self, numberOfThreads):
        self.maxUploadThreadsSpinCtrl.SetValue(numberOfThreads)

    def GetMaxUploadRetries(self):
        return self.maxUploadRetriesSpinCtrl.GetValue()

    def SetMaxUploadRetries(self, numberOfRetries):
        self.maxUploadRetriesSpinCtrl.SetValue(numberOfRetries)

    def StartAutomaticallyOnLogin(self):
        return self.startAutomaticallyCheckBox.GetValue()

    def SetStartAutomaticallyOnLogin(self, startAutomaticallyOnLogin):
        self.startAutomaticallyCheckBox.SetValue(
            startAutomaticallyOnLogin)

    def UploadInvalidUserOrGroupFolders(self):
        return self.uploadInvalidUserFoldersCheckBox.GetValue()

    def SetUploadInvalidUserOrGroupFolders(self, uploadInvalidUserOrGroupFolders):
        self.uploadInvalidUserFoldersCheckBox.SetValue(
            uploadInvalidUserOrGroupFolders)

    def Locked(self):
        return self.lockOrUnlockButton.GetLabel() == "Unlock"

    def SetLocked(self, locked):
        """
        When SettingsDialog is first displayed, it is in the unlocked
        state, so the button label says "Lock" (allowing the user to
        switch to the locked state).  When MyData reads the saved
        settings from disk, if it finds that settings were saved in
        the locked state, it will lock (disable) all of the dialog's
        fields.
        """
        if locked:
            self.DisableFields()
            self.lockOrUnlockButton.SetLabel("Unlock")
        else:
            self.EnableFields()
            self.lockOrUnlockButton.SetLabel("Lock")

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
        # If we are not running scans and uploads, but we could be
        # running settings validation, stop when Cancel is pressed.
        if not wx.GetApp().Processing():
            wx.GetApp().SetShouldAbort(True)
        event.Skip()

    def OnOK(self, event):  # pylint: disable=invalid-name
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
        wx.PostEvent(wx.GetApp().GetMainFrame(),
                     settingsDialogValidationEvent)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:",
                           defaultPath=self.GetDataDirectory()
                           .encode('ascii', 'ignore'))
        if dlg.ShowModal() == wx.ID_OK:
            self.dataDirectoryField.SetValue(dlg.GetPath())
        event.Skip()

    def OnBrowseIncludesFile(self, event):
        dlg = wx.FileDialog(self, "Choose a file:", "",
                            self.GetIncludesFile().encode('ascii', 'ignore'),
                            "", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.includesFileField.SetValue(dlg.GetPath())
            # Even though we use style=wx.TE_RIGHT,
            # this is necessary on Windows to ensure that
            # the right path of the file path (containing
            # the file name) is visible:
            self.includesFileField.SetInsertionPoint(
                self.includesFileField.GetLastPosition())
        event.Skip()

    def OnIncludeFiles(self, event):
        if self.includesFileCheckBox.IsChecked():
            self.browseIncludesFileButton.Enable(True)
            self.includesFileField.Enable(True)
        else:
            self.browseIncludesFileButton.Enable(False)
            self.includesFileField.Enable(False)
        if event:
            self.includesFileField.SetValue("")
        if event:
            event.Skip()

    def OnBrowseExcludesFile(self, event):
        dlg = wx.FileDialog(self, "Choose a file:", "",
                            self.GetIncludesFile().encode('ascii', 'ignore'),
                            "", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.excludesFileField.SetValue(dlg.GetPath())
            # Even though we use style=wx.TE_RIGHT,
            # this is necessary on Windows to ensure that
            # the right path of the file path (containing
            # the file name) is visible:
            self.excludesFileField.SetInsertionPoint(
                self.excludesFileField.GetLastPosition())
        event.Skip()

    def OnExcludeFiles(self, event):
        if self.excludesFileCheckBox.IsChecked():
            self.browseExcludesFileButton.Enable(True)
            self.excludesFileField.Enable(True)
        else:
            self.browseExcludesFileButton.Enable(False)
            self.excludesFileField.Enable(False)
        if event:
            self.excludesFileField.SetValue("")
        if event:
            event.Skip()

    def UpdateFieldsFromModel(self, settingsModel):
        # General tab
        self.SetInstrumentName(settingsModel.GetInstrumentName())
        self.SetFacilityName(settingsModel.GetFacilityName())
        self.SetContactName(settingsModel.GetContactName())
        self.SetContactEmail(settingsModel.GetContactEmail())
        self.SetMyTardisUrl(settingsModel.GetMyTardisUrl())
        self.SetDataDirectory(settingsModel.GetDataDirectory())
        self.SetUsername(settingsModel.GetUsername())
        self.SetApiKey(settingsModel.GetApiKey())

        # Schedule tab
        self.SetScheduleType(settingsModel.GetScheduleType())
        self.SetMondayChecked(settingsModel.IsMondayChecked())
        self.SetTuesdayChecked(settingsModel.IsTuesdayChecked())
        self.SetWednesdayChecked(settingsModel.IsWednesdayChecked())
        self.SetThursdayChecked(settingsModel.IsThursdayChecked())
        self.SetFridayChecked(settingsModel.IsFridayChecked())
        self.SetSaturdayChecked(settingsModel.IsSaturdayChecked())
        self.SetSundayChecked(settingsModel.IsSundayChecked())
        self.SetScheduledDate(settingsModel.GetScheduledDate())
        self.SetScheduledTime(settingsModel.GetScheduledTime())
        self.SetTimerMinutes(settingsModel.GetTimerMinutes())
        self.SetTimerFromTime(settingsModel.GetTimerFromTime())
        self.SetTimerToTime(settingsModel.GetTimerToTime())

        # Filters tab
        self.SetUserFilter(settingsModel.GetUserFilter())
        self.SetDatasetFilter(settingsModel.GetDatasetFilter())
        self.SetExperimentFilter(settingsModel.GetExperimentFilter())
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
        self.SetIgnoreNewFiles(settingsModel.IgnoreNewFiles())
        self.SetIgnoreNewFilesMinutes(settingsModel.GetIgnoreNewFilesMinutes())
        if settingsModel.IgnoreNewFiles():
            self.ignoreFilesNewerThanSpinCtrl.Enable(True)
        if int(settingsModel.GetIgnoreNewFilesMinutes()) == 1:
            self.showingSingularMinutes = True
            self.ignoreFilesIntervalUnitLabel.SetLabel("minute")
        else:
            self.showingSingularMinutes = False
            self.ignoreFilesIntervalUnitLabel.SetLabel("minutes")
        self.SetUseIncludesFile(settingsModel.UseIncludesFile())
        if settingsModel.UseIncludesFile():
            self.includesFileField.Enable(True)
            self.includesFileField.SetValue(settingsModel.GetIncludesFile())
            self.browseIncludesFileButton.Enable(True)
        else:
            self.includesFileField.Enable(False)
            self.includesFileField.SetValue("")
            self.browseIncludesFileButton.Enable(False)
        self.SetUseExcludesFile(settingsModel.UseExcludesFile())
        if settingsModel.UseExcludesFile():
            self.excludesFileField.Enable(True)
            self.excludesFileField.SetValue(settingsModel.GetExcludesFile())
            self.browseExcludesFileButton.Enable(True)
        else:
            self.excludesFileField.Enable(False)
            self.excludesFileField.SetValue("")
            self.browseExcludesFileButton.Enable(False)

        # Advanced tab
        self.SetFolderStructure(settingsModel.GetFolderStructure())
        self.SetDatasetGrouping(settingsModel.GetDatasetGrouping())
        self.SetGroupPrefix(settingsModel.GetGroupPrefix())
        self.SetMaxUploadThreads(settingsModel.GetMaxUploadThreads())
        self.SetMaxUploadRetries(settingsModel.GetMaxUploadRetries())
        self.SetValidateFolderStructure(
            settingsModel.ValidateFolderStructure())
        self.SetStartAutomaticallyOnLogin(
            settingsModel.StartAutomaticallyOnLogin())
        self.SetUploadInvalidUserOrGroupFolders(
            settingsModel.UploadInvalidUserOrGroupFolders())

        # This needs to go last, because it sets the enabled / disabled
        # state of many fields which depend on the values obtained from
        # the SettingsModel in the lines of code above.
        self.SetLocked(settingsModel.Locked())

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
        # pylint: disable=unused-argument
        mydataConfigPath = self.settingsModel.GetConfigPath()
        if mydataConfigPath is not None:
            dlg = wx.FileDialog(wx.GetApp().GetMainFrame(),
                                "Save MyData configuration as...", "",
                                "%s.cfg" % self.GetInstrumentName(), "*.cfg",
                                wx.SAVE | wx.OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                configPath = dlg.GetPath()
                self.settingsModel\
                    .SaveFieldsFromDialog(self,
                                          configPath=configPath)
                if configPath != wx.GetApp().GetConfigPath():
                    self.settingsModel.SaveFieldsFromDialog(
                        self, configPath=wx.GetApp().GetConfigPath())
        # event.Skip()

    def OnApiKeyFieldFocused(self, event):
        self.apiKeyField.SelectAll()
        event.Skip()

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
        event.Skip()

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
        event.Skip()

    def OnIgnoreNewFilesCheckBox(self, event):
        if event.IsChecked():
            self.ignoreFilesNewerThanSpinCtrl.SetValue(1)
            self.ignoreFilesNewerThanSpinCtrl.Enable(True)
            if not self.showingSingularMinutes:
                self.showingSingularMinutes = True
            self.ignoreFilesIntervalUnitLabel.SetLabel("minute")
        else:
            self.ignoreFilesNewerThanSpinCtrl.SetValue(0)
            self.ignoreFilesNewerThanSpinCtrl.Enable(False)
            if not self.showingSingularMinutes:
                self.showingSingularMinutes = False
            self.ignoreFilesIntervalUnitLabel.SetLabel("minutes")
        event.Skip()

    def OnIgnoreNewFilesSpinCtrl(self, event):
        if event.GetInt() == 1:
            if not self.showingSingularMinutes:
                self.ignoreFilesIntervalUnitLabel.SetLabel("minute")
                self.showingSingularMinutes = True
        else:
            if self.showingSingularMinutes:
                self.ignoreFilesIntervalUnitLabel.SetLabel("minutes")
                self.showingSingularMinutes = False
        event.Skip()

    # pylint: disable=no-self-use
    def OnHelp(self, event):
        """
        Open MyData documentation in the default web browser.
        """
        BeginBusyCursorIfRequired()
        import webbrowser
        webbrowser.open(
            "http://mydata.readthedocs.org/en/latest/settings.html")
        EndBusyCursorIfRequired()
        event.Skip()

    def OnSelectFolderStructure(self, event):
        """
        Update dialog fields according to selected folder structure.
        """
        # pylint: disable=too-many-branches
        folderStructure = self.folderStructureComboBox.GetValue()
        if folderStructure == 'Username / Dataset' or \
                folderStructure == 'Email / Dataset' or \
                folderStructure == 'Dataset':
            self.datasetGroupingField\
                .SetValue("Instrument Name - Data Owner's Full Name")
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)
            self.expFolderFilterLabel.Show(False)
            self.expFolderFilterField.SetValue("")
            self.expFolderFilterField.Show(False)
        elif folderStructure == \
                'Username / "MyTardis" / Experiment / Dataset' or \
                folderStructure == 'Username / Experiment / Dataset' or \
                folderStructure == 'Email / Experiment / Dataset' or \
                folderStructure == 'Experiment / Dataset':
            self.datasetGroupingField.SetValue("Experiment")
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)
            self.expFolderFilterLabel.Show(True)
            self.expFolderFilterField.Show(True)
        elif folderStructure == \
                'User Group / Instrument / Full Name / Dataset':
            self.datasetGroupingField.SetValue("Instrument - Full Name")
            self.groupPrefixLabel.Show(True)
            self.groupPrefixField.Show(True)
            self.expFolderFilterLabel.Show(False)
            self.expFolderFilterField.SetValue("")
            self.expFolderFilterField.Show(False)
        elif folderStructure == \
                'User Group / Experiment / Dataset':
            self.datasetGroupingField.SetValue("User Group - Experiment")
            self.groupPrefixLabel.Show(True)
            self.groupPrefixField.Show(True)
            self.expFolderFilterLabel.Show(True)
            self.expFolderFilterField.SetValue("")
            self.expFolderFilterField.Show(True)

        if "User" in folderStructure or \
                "Email" in folderStructure:
            self.userFolderFilterLabel.Show(True)
            self.userFolderFilterField.SetValue("")
            self.userFolderFilterField.Show(True)
        else:
            self.userFolderFilterLabel.Show(False)
            self.userFolderFilterField.SetValue("")
            self.userFolderFilterField.Show(False)

        if folderStructure.startswith("Username"):
            self.userFolderFilterLabel.SetLabel(
                "  Username folder name contains:")
        elif folderStructure.startswith("Email"):
            self.userFolderFilterLabel.SetLabel(
                "     Email folder name contains:")
        elif folderStructure.startswith("User Group"):
            self.userFolderFilterLabel.SetLabel(
                "User Group folder name contains:")

        if "User" in folderStructure or "Email" in folderStructure:
            self.uploadInvalidUserFoldersLabel.Show(True)
            self.uploadInvalidUserFoldersCheckBox.Show(True)
        else:
            self.uploadInvalidUserFoldersLabel.Show(False)
            self.uploadInvalidUserFoldersCheckBox.Show(False)

        if folderStructure.startswith("User Group"):
            self.uploadInvalidUserFoldersLabel.SetLabel(
                "Upload invalid group folders:")
        else:
            self.uploadInvalidUserFoldersLabel.SetLabel(
                "Upload invalid user folders:")

        event.Skip()

    def OnDropFiles(self, filePaths):
        """
        Handles drag and drop of a MyData.cfg file
        onto the settings dialog.
        """
        # pylint: disable=too-many-branches
        if self.Locked():
            message = \
                "Please unlock MyData's settings before importing " \
                "a configuration file."
            dlg = wx.MessageDialog(None, message, "MyData - Settings Locked",
                                   wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            return False
        self.settingsModel.LoadSettings(configPath=filePaths[0],
                                        checkForUpdates=False)
        self.UpdateFieldsFromModel(self.settingsModel)

        folderStructure = self.folderStructureComboBox.GetValue()
        if folderStructure == \
                'User Group / Instrument / Full Name / Dataset':
            self.groupPrefixLabel.Show(True)
            self.groupPrefixField.Show(True)
        else:
            self.groupPrefixLabel.Show(False)
            self.groupPrefixField.Show(False)

        if "Experiment" in folderStructure:
            self.expFolderFilterLabel.Show(True)
            self.expFolderFilterField.Show(True)
        else:
            self.expFolderFilterLabel.Show(False)
            self.expFolderFilterField.SetValue("")
            self.expFolderFilterField.Show(False)

        if "User" in folderStructure or \
                "Email" in folderStructure:
            self.userFolderFilterLabel.Show(True)
            self.userFolderFilterField.SetValue("")
            self.userFolderFilterField.Show(True)
        else:
            self.userFolderFilterLabel.Show(False)
            self.userFolderFilterField.SetValue("")
            self.userFolderFilterField.Show(False)

        if folderStructure.startswith("Username"):
            self.userFolderFilterLabel.SetLabel(
                "  Username folder name contains:")
        elif folderStructure.startswith("Email"):
            self.userFolderFilterLabel.SetLabel(
                "     Email folder name contains:")
        elif folderStructure.startswith("User Group"):
            self.userFolderFilterLabel.SetLabel(
                "User Group folder name contains:")
        return True

    def OnLockOrUnlockSettings(self, event):
        """
        Lock or unlock settings.
        """
        # pylint: disable=too-many-branches
        if self.lockOrUnlockButton.GetLabel() == "Lock":
            message = "Once settings have been locked, only an " \
                "administrator will be able to unlock them.\n\n" \
                "Are you sure you want to lock MyData's settings?"
            confirmationDialog = \
                wx.MessageDialog(None, message, "MyData - Lock Settings",
                                 wx.YES | wx.NO | wx.ICON_QUESTION)
            okToLock = confirmationDialog.ShowModal()
            if okToLock != wx.ID_YES:
                return
            unlockingSettings = False
            logger.debug("Locking settings.")
            self.lockOrUnlockButton.SetLabel("Unlock")
        else:
            unlockingSettings = True
            logger.debug("Requesting privilege elevation and "
                         "unlocking settings.")
            if sys.platform.startswith("win"):
                # pylint: disable=import-error
                # pylint: disable=no-name-in-module
                import win32com.shell.shell as shell
                import win32con
                from win32com.shell import shellcon
                import ctypes
                runningAsAdmin = ctypes.windll.shell32.IsUserAnAdmin()
                params = "--version "

                if not runningAsAdmin:
                    logger.info("Attempting to run \"%s --version\" "
                                "as an administrator." % sys.executable)
                    # pylint: disable=bare-except
                    try:
                        shell.ShellExecuteEx(
                            nShow=win32con.SW_SHOWNORMAL,
                            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                            lpVerb='runas',
                            lpFile=sys.executable,
                            lpParameters=params)
                    except:
                        logger.error("User privilege elevation failed.")
                        logger.error(traceback.format_exc())
                        return
            elif sys.platform.startswith("darwin"):
                logger.info("Attempting to run "
                            "\"echo MyData privilege elevation\" "
                            "as an administrator.")
                returncode = os.system("osascript -e "
                                       "'do shell script "
                                       "\"echo MyData privilege elevation\" "
                                       "with administrator privileges'")
                if returncode != 0:
                    raise Exception("Failed to get admin privileges.")
            self.lockOrUnlockButton.SetLabel("Lock")

        self.EnableFields(unlockingSettings)
        event.Skip()

    def EnableFields(self, enabled=True):
        # General tab
        self.instrumentNameField.Enable(enabled)
        self.facilityNameField.Enable(enabled)
        self.contactNameField.Enable(enabled)
        self.contactEmailField.Enable(enabled)
        self.dataDirectoryField.Enable(enabled)
        self.browseDataDirectoryButton.Enable(enabled)
        self.myTardisUrlField.Enable(enabled)
        self.usernameField.Enable(enabled)
        self.apiKeyField.Enable(enabled)

        # Schedule tab
        self.scheduleTypeComboBox.Enable(enabled)
        # Disable everything, then determine
        # what needs to be re-enabled by calling
        # self.OnScheduleTypeChange()
        self.mondayCheckBox.Enable(False)
        self.tuesdayCheckBox.Enable(False)
        self.wednesdayCheckBox.Enable(False)
        self.thursdayCheckBox.Enable(False)
        self.fridayCheckBox.Enable(False)
        self.saturdayCheckBox.Enable(False)
        self.sundayCheckBox.Enable(False)
        self.dateCtrl.Enable(False)
        self.dateSpin.Enable(False)
        self.timeCtrl.Enable(False)
        self.timeSpin.Enable(False)
        self.timerNumCtrl.Enable(False)
        self.timerSpin.Enable(False)
        self.fromTimeCtrl.Enable(False)
        self.fromTimeSpin.Enable(False)
        self.toTimeCtrl.Enable(False)
        self.toTimeSpin.Enable(False)
        if enabled:
            self.OnScheduleTypeChange(None)

        # Filters tab
        self.userFolderFilterField.Enable(enabled)
        self.datasetFolderFilterField.Enable(enabled)
        self.expFolderFilterField.Enable(enabled)
        self.ignoreDatasetsOlderThanCheckBox.Enable(enabled)
        self.ignoreDatasetsOlderThanSpinCtrl\
            .Enable(enabled)
        self.intervalUnitsComboBox.Enable(enabled)
        self.ignoreFilesNewerThanCheckBox.Enable(enabled)
        self.ignoreFilesNewerThanSpinCtrl.Enable(enabled)
        wx.PostEvent(self.ignoreFilesNewerThanCheckBox,
                     wx.CommandEvent(wx.EVT_BUTTON.typeId, self.GetId()))
        self.includesFileCheckBox.Enable(enabled)
        self.browseIncludesFileButton.Enable(enabled)
        self.includesFileField.Enable(enabled)
        if enabled:
            self.OnIncludeFiles(None)
        self.excludesFileCheckBox.Enable(enabled)
        self.browseExcludesFileButton.Enable(enabled)
        self.excludesFileField.Enable(enabled)
        if enabled:
            self.OnExcludeFiles(None)

        # Advanced tab
        self.folderStructureComboBox.Enable(enabled)
        self.datasetGroupingField.Enable(enabled)
        self.groupPrefixField.Enable(enabled)
        self.validateFolderStructureCheckBox.Enable(enabled)
        self.maxUploadThreadsSpinCtrl.Enable(enabled)
        self.maxUploadRetriesSpinCtrl.Enable(enabled)
        self.startAutomaticallyCheckBox.Enable(enabled)
        self.uploadInvalidUserFoldersCheckBox.Enable(enabled)
        self.Update()

    def DisableFields(self):
        self.EnableFields(False)

    def OnSpinTimer(self, event):
        self.timerNumCtrl.SetValue(event.GetPosition())

    def OnScheduleTypeChange(self, event):
        scheduleType = self.scheduleTypeComboBox.GetValue()
        if scheduleType in ("On Startup", "On Settings Saved"):
            self.SetScheduledDate(datetime.date(datetime.now()))
            self.SetScheduledTime(datetime.time(datetime.now()))
        enableDaysOfWeekCheckBoxes = (scheduleType == "Weekly")
        self.mondayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.mondayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.tuesdayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.tuesdayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.wednesdayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.wednesdayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.thursdayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.thursdayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.fridayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.fridayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.saturdayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.saturdayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.sundayCheckBox.Enable(enableDaysOfWeekCheckBoxes)
        self.sundayCheckBox.Show(enableDaysOfWeekCheckBoxes)
        self.daysOfTheWeekGroupBox.Show(enableDaysOfWeekCheckBoxes)
        enableDate = (scheduleType == "Once")
        self.dateLabel.Enable(enableDate)
        self.dateSpin.Enable(enableDate)
        self.dateCtrl.Enable(enableDate)
        enableTime = (scheduleType == "Once" or scheduleType == "Daily" or
                      scheduleType == "Weekly")
        self.timeLabel.Enable(enableTime)
        self.timeCtrl.Enable(enableTime)
        self.timeSpin.Enable(enableTime)
        enableTimer = (scheduleType == "Timer")
        self.timerLabel.Enable(enableTimer)
        self.timerNumCtrl.Enable(enableTimer)
        self.timerSpin.Enable(enableTimer)
        self.fromLabel.Enable(enableTimer)
        self.fromTimeCtrl.Enable(enableTimer)
        self.fromTimeSpin.Enable(enableTimer)
        self.toLabel.Enable(enableTimer)
        self.toTimeCtrl.Enable(enableTimer)
        self.toTimeSpin.Enable(enableTimer)
        if event:
            event.Skip()

    def OnIncrementDate(self, event):
        self.SetScheduledDate(self.GetScheduledDate() + timedelta(days=1))
        event.Skip()

    def OnDecrementDate(self, event):
        self.SetScheduledDate(self.GetScheduledDate() - timedelta(days=1))
        event.Skip()

    def OnIncrementTime(self, event):
        self.SetScheduledTime(AddMinutes(self.GetScheduledTime(), 1))
        event.Skip()

    def OnDecrementTime(self, event):
        self.SetScheduledTime(AddMinutes(self.GetScheduledTime(), -1))
        event.Skip()

    def OnIncrementFromTime(self, event):
        self.SetTimerFromTime(AddMinutes(self.GetTimerFromTime(), 1))
        event.Skip()

    def OnDecrementFromTime(self, event):
        self.SetTimerFromTime(AddMinutes(self.GetTimerFromTime(), -1))
        event.Skip()

    def OnIncrementToTime(self, event):
        self.SetTimerToTime(AddMinutes(self.GetTimerToTime(), 1))
        event.Skip()

    def OnDecrementToTime(self, event):
        self.SetTimerToTime(AddMinutes(self.GetTimerToTime(), -1))
        event.Skip()


def AddMinutes(initialTime, minutes):
    fulldate = datetime(100, 1, 1, initialTime.hour,
                        initialTime.minute, initialTime.second)
    fulldate = fulldate + timedelta(minutes=minutes)
    return fulldate.time()
