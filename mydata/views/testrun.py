"""
Class for the Test Run results window, summarizing
the results of a dry run.
"""
import wx

from ..logs import logger
from ..threads.flags import FLAGS


class TestRunFrame(wx.Frame):
    """
    Class for the Test Run results window, summarizing
    the results of a dry run.
    """
    def __init__(self, parent, title="MyData - Test Run"):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title,
                          size=(800, 500),
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)

        panel = wx.Panel(self, wx.ID_ANY)
        self.textCtrl = \
            wx.TextCtrl(panel, wx.ID_ANY,
                        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)

        sizer = wx.FlexGridSizer(rows=2, cols=1, vgap=0, hgap=0)
        sizer.AddGrowableRow(0)
        sizer.AddGrowableCol(0)
        sizer.Add(self.textCtrl, flag=wx.EXPAND)

        self.saveButton = wx.Button(panel, wx.ID_ANY, "Save...")
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.saveButton)
        sizer.Add(self.saveButton,
                  flag=wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.RIGHT,
                  border=5)

        panel.SetSizerAndFit(sizer)

    def WriteLine(self, line):
        """
        Write a line of text to the text control.
        """
        self.textCtrl.WriteText(str(line) + '\n')

    def Clear(self):
        """
        Clear the contents of the text control.
        """
        self.textCtrl.SetValue("")

    def OnCloseFrame(self, event):  # pylint: disable=unused-argument
        """
        Don't actually destroy the frame, just hide it.
        """
        if FLAGS.testRunRunning:
            logger.info("Closing Test Run Window and calling OnStop.")
            wx.GetApp().OnStop(None)
        else:
            logger.info("Closing Test Run Window.")
        self.Hide()

    def OnSave(self, event):
        """
        Save the contents of the text control to a file.
        """
        dlg = wx.FileDialog(self,
                            "Save MyData test run summary as...", "",
                            "%s.txt" % self.GetTitle(), "*.txt",
                            wx.SAVE | wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            with open(dlg.GetPath(), 'w') as saveFile:
                for line in range(self.textCtrl.GetNumberOfLines()):
                    saveFile.write(self.textCtrl.GetLineText(line) + '\n')
        event.Skip()
