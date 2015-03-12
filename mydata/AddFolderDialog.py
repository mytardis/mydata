import wx

from UserModel import UserModel


class AddFolderDialog(wx.Dialog):

    def __init__(
            self, parent, ID, title, usersModel,
            size=wx.DefaultSize, pos=wx.DefaultPosition,
            style=wx.DEFAULT_DIALOG_STYLE,
    ):

        wx.Dialog.__init__(self, parent, ID, title=title, size=size, pos=pos,
                           style=style)

        self.usersModel = usersModel

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)

        label = "Please enter the type of folder and its owner.\n" + \
                "You can create a new user record if necessary."
        staticText = wx.StaticText(self, -1, label)
        sizer.Add(staticText, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.fieldsPanel = wx.Panel(self)
        self.fieldsPanelSizer = wx.FlexGridSizer(rows=3, cols=3,
                                                 vgap=5, hgap=5)
        self.fieldsPanel.SetSizer(self.fieldsPanelSizer)

        self.folderTypeLabel = wx.StaticText(self.fieldsPanel, -1,
                                             "Folder type:")
        self.fieldsPanelSizer.Add(self.folderTypeLabel,
                                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        folderTypeList = ['User', 'Experiment', 'Dataset']
        self.folderTypeChoice = wx.Choice(self.fieldsPanel, -1,
                                          choices=folderTypeList)
        self.folderTypeChoice.SetSelection(2)  # Default to Dataset
        self.fieldsPanelSizer.Add(self.folderTypeChoice,
                                  flag=wx.EXPAND | wx.ALL, border=5)

        self.fieldsPanelSizer.Add(wx.StaticText(self.fieldsPanel))

        ownerLabel = wx.StaticText(self.fieldsPanel, -1, "Owner:")
        self.fieldsPanelSizer.Add(ownerLabel, flag=wx.ALIGN_RIGHT | wx.ALL,
                                  border=5)

        userList = self.usersModel.GetValuesForColname("Name")
        self.ownerChoice = wx.Choice(self.fieldsPanel, -1, choices=userList)
        self.ownerChoice.SetSelection(0)
        self.fieldsPanelSizer.Add(self.ownerChoice, flag=wx.EXPAND | wx.ALL,
                                  border=5)

        self.newUserButton = wx.Button(self.fieldsPanel, label="New User...")
        self.Bind(wx.EVT_BUTTON, self.OnAddNewUser, self.newUserButton)
        self.fieldsPanelSizer.Add(self.newUserButton,
                                  flag=wx.ALIGN_CENTRE | wx.ALL, border=5)

        self.fieldsPanel.Fit()

        sizer.Add(self.fieldsPanel, 0,
                  wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0,
                  wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def SetFolderType(self, folderTypeIndex):
        self.folderTypeChoice.SetSelection(folderTypeIndex)

    def GetFolderType(self):
        return self.folderTypeChoice\
            .GetString(self.folderTypeChoice.GetSelection())

    def GetOwnerName(self):
        return self.ownerChoice.GetString(self.ownerChoice.GetSelection())

    def OnAddNewUser(self, event):
        from AddUserDialog import AddUserDialog

        addUserDialog = AddUserDialog(self, -1, "Add User", size=(350, 200),
                                      style=wx.DEFAULT_DIALOG_STYLE)
        addUserDialog.CenterOnParent()

        if addUserDialog.ShowModal() == wx.ID_OK:
            if self.usersModel.Contains(addUserDialog.GetName(),
                                        addUserDialog.GetEmail()):
                message = "This user has already been added."
                dlg = wx.MessageDialog(None, message, "Add User",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                return
            dataViewId = self.usersModel.GetMaxDataViewId() + 1
            userRecord = UserModel(dataViewId=dataViewId,
                                   username=addUserDialog.GetUsername(),
                                   name=addUserDialog.GetName(),
                                   email=addUserDialog.GetEmail())
            self.usersModel.AddRow(userRecord)
            userList = self.usersModel.GetValuesForColname("Name")
            self.ownerChoice.Clear()
            self.ownerChoice.AppendItems(userList)
            self.ownerChoice\
                .SetSelection(userList.index(addUserDialog.GetName()))
