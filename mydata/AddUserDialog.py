import wx
import re


class AddUserDialog(wx.Dialog):

    def __init__(
            self, parent, ID, title, size=wx.DefaultSize,
            pos=wx.DefaultPosition,
            style=wx.DEFAULT_DIALOG_STYLE):

        wx.Dialog.__init__(self, parent, ID, title=title, size=size, pos=pos,
                           style=style)

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)

        label = "Please enter the name and email address of the new user."
        staticText = wx.StaticText(self, -1, label)
        sizer.Add(staticText, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.fieldsPanel = wx.Panel(self)
        self.fieldsPanelSizer = wx.FlexGridSizer(rows=2, cols=2,
                                                 vgap=5, hgap=5)
        self.fieldsPanel.SetSizer(self.fieldsPanelSizer)

        self.fieldsPanelSizer.AddGrowableCol(1)

        self.usernameLabel = wx.StaticText(self.fieldsPanel, -1, "Username:")
        self.fieldsPanelSizer.Add(self.usernameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.usernameField = wx.TextCtrl(self.fieldsPanel, -1, "")
        self.fieldsPanelSizer.Add(self.usernameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)

        self.nameLabel = wx.StaticText(self.fieldsPanel, -1, "Name:")
        self.fieldsPanelSizer.Add(self.nameLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.nameField = wx.TextCtrl(self.fieldsPanel, -1, "")
        self.fieldsPanelSizer.Add(self.nameField,
                                  flag=wx.EXPAND | wx.ALL, border=5)

        emailLabel = wx.StaticText(self.fieldsPanel, -1, "Email:")
        self.fieldsPanelSizer.Add(emailLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        self.emailField = wx.TextCtrl(self.fieldsPanel, -1, "")
        self.fieldsPanelSizer.Add(self.emailField,
                                  flag=wx.EXPAND | wx.ALL, border=5)

        self.fieldsPanel.Fit()

        sizer.Add(self.fieldsPanel, 0,
                  wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT |
                  wx.TOP, 5)

        buttonSizer = wx.StdDialogButtonSizer()

        self.okButton = wx.Button(self, wx.ID_OK)
        self.okButton.SetDefault()
        buttonSizer.AddButton(self.okButton)
        self.Bind(wx.EVT_BUTTON, self.onOK, self.okButton)

        self.cancelButton = wx.Button(self, wx.ID_CANCEL)
        buttonSizer.AddButton(self.cancelButton)
        buttonSizer.Realize()

        sizer.Add(buttonSizer, 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def GetUsername(self):
        return self.usernameField.GetValue()

    def GetName(self):
        return self.nameField.GetValue()

    def GetEmail(self):
        return self.emailField.GetValue()

    def onOK(self, event):

        if self.GetUsername().strip() == "":
            message = "Please enter a username."
            dlg = wx.MessageDialog(None, message, "Add User",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.usernameField.SetFocus()
        elif self.GetName().strip() == "":
            message = "Please enter a name."
            dlg = wx.MessageDialog(None, message, "Add User",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.nameField.SetFocus()
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", self.GetEmail()):
            message = "Please enter a valid email address."
            dlg = wx.MessageDialog(None, message, "Add User",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.emailField.SetFocus()
            self.emailField.SelectAll()
        else:
            event.Skip()
