import wx
import wx.aui
import re


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, ID, title, size=wx.DefaultSize,
                 pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE):

        wx.Dialog.__init__(self, parent, ID, title=title, size=size, pos=pos,
                           style=style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY,
                              "Please enter your instrument name, " +
                              "institution name, data directory, " +
                              "MyTardis URL " +
                              "(beginning with http or https), MyTardis " +
                              "default username, and MyTardis API key.")
        label.Wrap(350)
        sizer.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 15)

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

        self.institutionNameLabel = wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                  "Institution Name:")
        self.fieldsPanelSizer.Add(self.institutionNameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.institutionNameField = wx.TextCtrl(self.fieldsPanel, wx.ID_ANY,
                                                "")
        self.fieldsPanelSizer.Add(self.institutionNameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)
        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel, wx.ID_ANY,
                                                ""))

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

    def GetInstrumentName(self):
        return self.instrumentNameField.GetValue()

    def SetInstrumentName(self, instrumentName):
        self.instrumentNameField.SetValue(instrumentName)

    def GetMyTardisUrl(self):
        return self.myTardisUrlField.GetValue()

    def GetInstitutionName(self):
        return self.institutionNameField.GetValue()

    def SetInstitutionName(self, institutionName):
        self.institutionNameField.SetValue(institutionName)

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

        if self.GetMyTardisUrl().strip() == "":
            message = "Please enter a valid MyTardis URL."
            dlg = wx.MessageDialog(None, message, "Settings",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.myTardisUrlField.SetFocus()
        if self.GetInstitutionName().strip() == "":
            message = "Please enter a valid institution name."
            dlg = wx.MessageDialog(None, message, "Settings",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.institutionNameField.SetFocus()
        elif self.GetUsername().strip() == "":
            message = "Please enter a MyTardis username."
            dlg = wx.MessageDialog(None, message, "Settings",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.usernameField.SetFocus()
            self.usernameField.SelectAll()
        elif self.GetApiKey().strip() == "":
            message = "Please enter the MyTardis API key."
            dlg = wx.MessageDialog(None, message, "Settings",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.apiKeyField.SetFocus()
            self.apiKeyField.SelectAll()
        else:
            event.Skip()

    def OnBrowse(self, event):
        dlg = wx.DirDialog(self, "Choose a directory:")
        if dlg.ShowModal() == wx.ID_OK:
            self.dataDirectoryField.SetValue(dlg.GetPath())
