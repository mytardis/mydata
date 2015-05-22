import sys
import os


class ImageStyle():
    NORMAL = 0
    DISABLED = 1
    HOT = 2


class Images():
    def __init__(self):
        self.mediaFolderName = "media"
        if hasattr(sys, "frozen"):
            if sys.platform.startswith("darwin"):
                # When frozen with Py2App, the default working directory
                # will be /Applications/MyData.app/Contents/Resources/
                # and MyData's media folder will be placed inside that
                # directory, so we can use a relative path.
                self.mediaPath = self.mediaFolderName
            else:
                # On Windows, MyData's media folder will put installed
                # in the same directory as MyData.exe.
                self.mediaPath = os.path.join(os.path.dirname(sys.executable),
                                              self.mediaFolderName)
        else:
            self.mediaPath = \
                os.path.dirname(pkgutil.get_loader("mydata.media").filename)

        self.pngHotPath = os.path.join(self.mediaPath, 'Aha-Soft', 'png-hot')
        self.pngNormalPath = os.path.join(self.mediaPath, 'Aha-Soft',
                                          'png-normal')
        if sys.platform.startswith("win"):
            self.defaultIconSize = "24x24"
        else:
            self.defaultIconSize = "16x16"

    def GetImage(self, imageName, imageStyle=ImageStyle.NORMAL,
        if sys.platform.startswith("win"):
            iconSubdir = "icons24x24"
        else:
            iconSubdir = "icons16x16"
        self.connectedBitmap = \
            wx.Image(os.path.join(pngNormalPath, iconSubdir, "Connect.png"),
                     wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.disconnectedBitmap = \
            wx.Image(os.path.join(pngNormalPath,
                                  iconSubdir, "Disconnect.png"),
                     wx.BITMAP_TYPE_PNG).ConvertToBitmap()
###
        if hasattr(sys, "frozen"):
            if sys.platform.startswith("darwin"):
                self.mediaPath = ''
            else:
                self.mediaPath = os.path.dirname(sys.executable)
        else:
            self.mediaPath = os.path.dirname(os.path.realpath(__file__))
        pngHotPath = os.path.join(self.mediaPath, 'media', 'Aha-Soft',
                                  'png-hot')
        pngNormalPath = os.path.join(self.mediaPath, 'media', 'Aha-Soft',
                                     'png-normal')

        self.toolbar = self.frame.CreateToolBar()
        self.toolbar.SetToolBitmapSize(wx.Size(24, 24))  # sets icon size

        openIcon = wx.Image(os.path.join(pngNormalPath,
                                         "icons24x24", "Open folder.png"),
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        openTool = self.toolbar.AddSimpleTool(wx.ID_ANY, openIcon, "Open",
                                              "Open folder")
        self.Bind(wx.EVT_MENU, self.OnOpen, openTool)

        self.toolbar.AddSeparator()

        refreshIcon = wx.Image(os.path.join(pngNormalPath,
                                            "icons24x24", "Refresh.png"),
                               wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.refreshTool = self.toolbar.AddSimpleTool(wx.ID_REFRESH,
                                                      refreshIcon,
                                                      "Refresh", "")
        self.toolbar.EnableTool(wx.ID_REFRESH, True)
        self.Bind(wx.EVT_TOOL, self.OnRefresh, self.refreshTool,
                  self.refreshTool.GetId())

        self.toolbar.AddSeparator()

        settingsIcon = wx.Image(os.path.join(pngHotPath,
                                             "icons24x24", "Settings.png"),
                                wx.BITMAP_TYPE_PNG).ConvertToBitmap()
###
# uploads.py:

        self.inProgressIcon = wx.Image('media/Aha-Soft/png-normal/icons16x16/'
                                       'Refresh.png',
                                       wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.completedIcon = wx.Image('media/Aha-Soft/png-normal/icons16x16/'
                                      'Apply.png',
                                      wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.failedIcon = wx.Image('media/Aha-Soft/png-normal/icons16x16/'
                                   'Delete.png',
                                   wx.BITMAP_TYPE_PNG).ConvertToBitmap()

