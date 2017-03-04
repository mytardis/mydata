"""
Dialog for submitting the current session's log via HTTP POST
to a server.  The user can add their name, email and a comment.

The dialog is launched from the "Submit debug log" button at
the bottom of the Log tab within MyData's main window.
"""
import os
import sys
import wx

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))


class SubmitDebugReportDialog(wx.Dialog):
    """
    Dialog for submitting the current session's log via HTTP POST
    to a server.  The user can add their name, email and a comment.

    The dialog is launched from the "Submit debug log" button at
    the bottom of the Log tab within MyData's main window.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, parent, title, debugLog, settings):
        # pylint: disable=too-many-statements
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title, wx.DefaultPosition)

        self.settings = settings

        self.dialogSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=0, hgap=0)
        self.SetSizer(self.dialogSizer)

        self.dialogPanel = wx.Panel(self, wx.ID_ANY)
        self.dialogPanelSizer = wx.FlexGridSizer(10, 1, vgap=0, hgap=0)
        self.dialogPanel.SetSizer(self.dialogPanelSizer)

        self.dialogSizer.Add(self.dialogPanel,
                             flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM,
                             border=15)

        # Instructions label

        instructionsText = \
            "You can submit a debug report to the MyData developers."
        self.instructionsLabel = \
            wx.StaticText(self.dialogPanel, wx.ID_ANY,
                          instructionsText)
        self.instructionsLabel.SetMinSize(wx.Size(600, wx.ID_ANY))
        self.dialogPanelSizer.Add(self.instructionsLabel,
                                  flag=wx.EXPAND | wx.BOTTOM, border=15)

        # Contact details panel

        self.contactDetailsPanel = wx.Panel(self.dialogPanel,
                                            wx.ID_ANY)

        self.contactDetailsGroupBox = \
            wx.StaticBox(self.contactDetailsPanel, wx.ID_ANY,
                         label="Contact details")
        self.contactDetailsGroupBoxSizer = \
            wx.StaticBoxSizer(self.contactDetailsGroupBox, wx.VERTICAL)
        self.contactDetailsPanel.SetSizer(self.contactDetailsGroupBoxSizer)

        self.innerContactDetailsPanel = wx.Panel(self.contactDetailsPanel,
                                                 wx.ID_ANY)
        self.innerContactDetailsPanelSizer = \
            wx.FlexGridSizer(5, 2, vgap=0, hgap=10)
        self.innerContactDetailsPanel\
            .SetSizer(self.innerContactDetailsPanelSizer)

        self.innerContactDetailsPanelSizer.AddGrowableCol(1)

        # Name

        self.nameLabel = wx.StaticText(self.innerContactDetailsPanel,
                                       wx.ID_ANY, "Name:")
        self.innerContactDetailsPanelSizer.Add(self.nameLabel)

        contactName = self.settings.general.contactName

        self.nameField = wx.TextCtrl(self.innerContactDetailsPanel, wx.ID_ANY)
        self.nameField.SetValue(contactName)
        self.innerContactDetailsPanelSizer.Add(self.nameField, flag=wx.EXPAND)

        # Blank space

        self.innerContactDetailsPanelSizer\
            .Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))
        self.innerContactDetailsPanelSizer\
            .Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))

        # Email

        self.emailLabel = wx.StaticText(self.innerContactDetailsPanel,
                                        wx.ID_ANY, "Email address:")
        self.innerContactDetailsPanelSizer.Add(self.emailLabel)

        contactEmail = self.settings.general.contactEmail

        self.emailField = wx.TextCtrl(self.innerContactDetailsPanel, wx.ID_ANY)
        self.emailField.SetValue(contactEmail)
        self.innerContactDetailsPanelSizer.Add(self.emailField, flag=wx.EXPAND)

        # Blank space

        self.innerContactDetailsPanelSizer\
            .Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))
        self.innerContactDetailsPanelSizer\
            .Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))

        # Please contact me

        self.blankLabel = wx.StaticText(self.innerContactDetailsPanel,
                                        wx.ID_ANY, "")
        self.innerContactDetailsPanelSizer.Add(self.blankLabel)

        self.pleaseContactMeCheckBox = \
            wx.CheckBox(self.innerContactDetailsPanel, wx.ID_ANY,
                        "Please contact me")

        self.innerContactDetailsPanelSizer.Add(self.pleaseContactMeCheckBox,
                                               flag=wx.EXPAND)

        self.innerContactDetailsPanel.Fit()
        self.contactDetailsGroupBoxSizer.Add(self.innerContactDetailsPanel,
                                             flag=wx.EXPAND)
        self.contactDetailsPanel.Fit()

        self.dialogPanelSizer.Add(self.contactDetailsPanel, flag=wx.EXPAND)

        # Blank space

        self.dialogPanelSizer.Add(wx.StaticText(self.dialogPanel, wx.ID_ANY, ""))

        # Comments panel

        self.commentsPanel = wx.Panel(self.dialogPanel, wx.ID_ANY)

        self.commentsGroupBox = wx.StaticBox(self.commentsPanel, wx.ID_ANY,
                                             label="Comments")
        self.commentsGroupBoxSizer = wx.StaticBoxSizer(self.commentsGroupBox,
                                                       wx.VERTICAL)
        self.commentsPanel.SetSizer(self.commentsGroupBoxSizer)

        self.innerCommentsPanel = wx.Panel(self.commentsPanel, wx.ID_ANY)
        self.innerCommentsPanelSizer = wx.FlexGridSizer(10, 2, vgap=0, hgap=10)
        self.innerCommentsPanelSizer.AddGrowableCol(0)
        self.innerCommentsPanel.SetSizer(self.innerCommentsPanelSizer)

        self.commentsField = wx.TextCtrl(self.innerCommentsPanel, wx.ID_ANY,
                                         style=wx.TE_MULTILINE)
        self.commentsField.SetMinSize(wx.Size(wx.ID_ANY, 100))
        self.innerCommentsPanelSizer.Add(self.commentsField, flag=wx.EXPAND)

        if self.nameField.GetValue().strip() == "":
            self.nameField.SetFocus()
        elif self.emailField.GetValue().strip() == "":
            self.emailField.SetFocus()
        else:
            self.commentsField.SetFocus()

        self.innerCommentsPanel.Fit()
        self.commentsGroupBoxSizer.Add(self.innerCommentsPanel, flag=wx.EXPAND)
        self.commentsPanel.Fit()

        self.dialogPanelSizer.Add(self.commentsPanel, flag=wx.EXPAND)
        # Blank space

        self.dialogPanelSizer.Add(wx.StaticText(self.dialogPanel, wx.ID_ANY, ""))

        # Debug log panel

        self.debugLogPanel = wx.Panel(self.dialogPanel, wx.ID_ANY)

        self.debugLogGroupBox = wx.StaticBox(self.debugLogPanel, wx.ID_ANY,
                                             label="Debug log")
        self.debugLogGroupBoxSizer = wx.StaticBoxSizer(self.debugLogGroupBox,
                                                       wx.VERTICAL)
        self.debugLogPanel.SetSizer(self.debugLogGroupBoxSizer)

        self.innerDebugLogPanel = wx.Panel(self.debugLogPanel, wx.ID_ANY)
        self.innerDebugLogPanelSizer = wx.FlexGridSizer(10, 2, vgap=0, hgap=10)
        self.innerDebugLogPanelSizer.AddGrowableCol(0)
        self.innerDebugLogPanel.SetSizer(self.innerDebugLogPanelSizer)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            smallFont.SetPointSize(11)

        self.debugLogField = \
            wx.TextCtrl(self.innerDebugLogPanel, wx.ID_ANY,
                        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.debugLogField.SetValue(debugLog)
        self.debugLogField.SetFont(smallFont)
        self.debugLogField.SetMinSize(wx.Size(wx.ID_ANY, 100))
        self.innerDebugLogPanelSizer.Add(self.debugLogField, flag=wx.EXPAND)

        self.innerDebugLogPanel.Fit()
        self.debugLogGroupBoxSizer.Add(self.innerDebugLogPanel, flag=wx.EXPAND)
        self.debugLogPanel.Fit()

        self.dialogPanelSizer.Add(self.debugLogPanel, flag=wx.EXPAND)

        # Blank space

        self.dialogPanelSizer.Add(wx.StaticText(self.dialogPanel, wx.ID_ANY, ""))
        self.dialogPanelSizer.Add(wx.StaticText(self.dialogPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.dialogPanel, wx.ID_ANY)
        self.buttonsPanelSizer = wx.FlexGridSizer(1, 5, hgap=10, vgap=5)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.cancelButton = wx.Button(self.buttonsPanel, wx.NewId(), "Cancel")
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=self.cancelButton.GetId())

        self.submitButton = wx.Button(self.buttonsPanel, wx.NewId(), "Submit")
        self.submitButton.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.OnSubmit, id=self.submitButton.GetId())
        self.buttonsPanelSizer.Add(self.submitButton, flag=wx.BOTTOM, border=5)

        self.buttonsPanel.Fit()

        self.dialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT)

        # Calculate positions on dialog, using sizers

        self.dialogPanel.Fit()
        self.Fit()

        self.CenterOnParent()

    def OnCancel(self, event):
        """
        Close the Submit Debug Report dialog without submitting the report
        """
        self.EndModal(wx.ID_CANCEL)
        event.Skip()

    def OnSubmit(self, event):
        """
        Close the Submit Debug Report dialog and submit the report
        """
        self.EndModal(wx.ID_OK)
        event.Skip()

    def GetContactName(self):
        """
        Get the contact name to include in the header of the report
        """
        return self.nameField.GetValue().strip()

    def GetContactEmail(self):
        """
        Get the contact email to include in the header of the report
        """
        return self.emailField.GetValue().strip()

    def GetComments(self):
        """
        Get the comments to include in the header of the report
        """
        return self.commentsField.GetValue().strip()

    def GetPleaseContactMe(self):
        """
        Get the "Please Contact Me" checkbox state to include in
        the header of the report
        """
        return self.pleaseContactMeCheckBox.GetValue()
