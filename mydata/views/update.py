"""
New version alert dialog
"""
import sys
import wx

from ..media import MYDATA_ICONS
from ..utils.versions import MYDATA_VERSIONS

if 'phoenix' in wx.PlatformInfo:
    from wx import Icon as EmptyIcon
    from wx.adv import HyperlinkCtrl
else:
    from wx import EmptyIcon
    from wx import HyperlinkCtrl

UPDATE_URL = "https://github.com/mytardis/mydata/releases/latest"
CONTACT_EMAIL = "store.star.help@monash.edu"


class NewVersionAlertDialog(wx.Dialog):
    """
    New version alert dialog
    """
    def __init__(self, parent, title, latestVersionTagName,
                 latestVersionChanges):

        super(NewVersionAlertDialog, self).__init__(
            parent, wx.ID_ANY, title, size=(680, 290), pos=(200, 150))

        bmp = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        icon = EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.SetIcon(icon)

        # Panels placed vertically
        verticalSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(verticalSizer)

        mainPanel = wx.Panel(self)
        verticalSizer.Add(mainPanel)

        okButton = wx.Button(self, wx.ID_ANY, ' OK ')
        okButton.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okButton.GetId())
        verticalSizer.Add(
            okButton, flag=wx.BOTTOM | wx.RIGHT | wx.ALIGN_RIGHT, border=20)

        # Panels placed horizontally
        horizSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=5, hgap=5)
        mainPanel.SetSizer(horizSizer)

        iconPanel = IconPanel(mainPanel)
        horizSizer.Add(iconPanel, flag=wx.EXPAND | wx.ALL, border=10)

        newVersionAlertPanel = NewVersionAlertPanel(
            mainPanel, latestVersionTagName, latestVersionChanges)
        horizSizer.Add(
            newVersionAlertPanel, flag=wx.EXPAND | wx.TOP | wx.RIGHT,
            border=10)

        horizSizer.Fit(mainPanel)
        verticalSizer.Fit(self)

    def OnOK(self, event):
        """
        User clicked OK
        """
        self.EndModal(wx.ID_OK)
        self.Hide()
        event.Skip()


class IconPanel(wx.Panel):
    """
    Panel containing MyData icon
    """
    def __init__(self, parent):
        super(IconPanel, self).__init__(parent)
        iconAsBitmap = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        wx.StaticBitmap(self, bitmap=iconAsBitmap, size=wx.Size(64, 64))


class ContactPanel(wx.Panel):
    """
    Panel containing contact email
    """
    def __init__(self, parent):
        super(ContactPanel, self).__init__(parent)
        sizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)
        self.SetSizer(sizer)
        contactLabel = wx.StaticText(
            self, label="For queries, please contact:")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        contactLabel.SetFont(font)
        sizer.Add(contactLabel, border=10, flag=wx.EXPAND)

        contactEmailHyperlink = HyperlinkCtrl(
            self, id=wx.ID_ANY, label=CONTACT_EMAIL,
            url="mailto:%s" % CONTACT_EMAIL)
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        contactEmailHyperlink.SetFont(font)
        sizer.Add(contactEmailHyperlink, border=10, flag=wx.LEFT)
        sizer.Fit(self)


class NewVersionAlertPanel(wx.Panel):
    """
    New version alert panel
    """
    def __init__(self, parent, latestVersionTagName, latestVersionChanges):
        if hasattr(sys, "frozen"):
            from .. import __version__ as VERSION
        else:
            from .. import LATEST_COMMIT as VERSION
        super(NewVersionAlertPanel, self).__init__(parent)
        sizer = wx.FlexGridSizer(rows=5, cols=1, vgap=5, hgap=5)
        self.SetSizer(sizer)
        newVersionAlertTitleLabel = wx.StaticText(
            self, label="MyData")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetPointSize(14)
        font.SetWeight(wx.BOLD)
        newVersionAlertTitleLabel.SetFont(font)
        sizer.Add(newVersionAlertTitleLabel)

        newVersionAlertTextLabel1 = wx.StaticText(
            self,
            label="You are running version v" + VERSION + "\n\n" +
            "The latest version is " + latestVersionTagName + "\n\n" +
            "Please download MyData %s from:" % latestVersionTagName)
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        newVersionAlertTextLabel1.SetFont(font)
        sizer.Add(newVersionAlertTextLabel1, flag=wx.EXPAND)

        newVersionAlertHyperlink = HyperlinkCtrl(
            self, id=wx.ID_ANY, label=UPDATE_URL,
            url=UPDATE_URL)
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        newVersionAlertHyperlink.SetFont(font)
        sizer.Add(newVersionAlertHyperlink, border=10, flag=wx.LEFT)

        self.latestVersionChangesTextCtrl = wx.TextCtrl(
            self, size=(600, 200),
            style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.latestVersionChangesTextCtrl, flag=wx.EXPAND)
        if sys.platform.startswith("darwin"):
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False,
                           u'Courier New')
        else:
            font = wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False,
                           u'Courier New')
        self.latestVersionChangesTextCtrl.SetFont(font)
        self.latestVersionChangesTextCtrl.AppendText(latestVersionChanges)
        self.latestVersionChangesTextCtrl.SetInsertionPoint(0)

        sizer.Add(ContactPanel(self), flag=wx.EXPAND)


if __name__ == "__main__":
    APP = wx.App()
    FRAME = wx.Frame(None, title='New version Alert Dialog Test')
    FRAME.Show()
    DIALOG = NewVersionAlertDialog(
        FRAME, 'New MyData Version Available',
        MYDATA_VERSIONS.latestVersionTagName,
        MYDATA_VERSIONS.latestVersionBody)
    DIALOG.ShowModal()
    APP.MainLoop()
