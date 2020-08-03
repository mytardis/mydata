"""
Module to determine paths to icons etc.
"""

import sys
import os
import wx


class IconStyle(object):
    """
    Types of icons.
    """
    NORMAL = 0
    DISABLED = 1
    HOT = 2
    STRINGS = ['NORMAL', 'DISABLED', 'HOT']


class Icons(object):
    """
    Class to determine paths to icons etc.
    """
    def __init__(self):
        self.mediaFolderName = "media"
        if hasattr(sys, "frozen"):
            if sys.platform.startswith("darwin"):
                # When frozen with Py2App, the default working directory
                # will be /Applications/MyData.app/Contents/Resources/
                # and MyData's media folder will be placed inside that
                # directory, so we can use a relative path.
                self.mediaPath = self.mediaFolderName
                self.mediaPath = os.path.realpath(os.path.join(
                    os.path.dirname(sys.executable), "..", "Resources",
                    self.mediaFolderName))
            else:
                # On Windows, MyData's media folder will put installed
                # in the same directory as MyData.exe.
                self.mediaPath = os.path.join(os.path.dirname(sys.executable),
                                              self.mediaFolderName)
        else:
            self.mediaPath = os.path.dirname(os.path.realpath(__file__))

        self.pngHotPath = os.path.join(self.mediaPath, 'Aha-Soft', 'png-hot')
        self.pngNormalPath = os.path.join(self.mediaPath, 'Aha-Soft',
                                          'png-normal')
        if sys.platform.startswith("win"):
            self.defaultIconSize = "24x24"
        else:
            self.defaultIconSize = "16x16"

        self.iconsCache = {}

    def GetIconPath(self, name, vendor="Aha-Soft", style=IconStyle.NORMAL,
                    size=None, extension=None):
        """
        Get path to icon.
        """
        if not size:
            size = self.defaultIconSize
        if style == IconStyle.NORMAL:
            iconStyleFolderName = "png-normal"
        elif style == IconStyle.HOT:
            iconStyleFolderName = "png-hot"
        elif style == IconStyle.DISABLED:
            iconStyleFolderName = "png-disabled"
        else:
            raise Exception("Unsupported icon style was requested: %s"
                            % IconStyle.STRINGS[style])
        iconSubdir = "icons" + size
        if vendor in ["Aha-Soft", "new"]:
            return os.path.join(self.mediaPath, vendor, iconStyleFolderName,
                                iconSubdir, "%s.png" % name)
        if not extension:
            extension = "ico"
        return os.path.join(self.mediaPath, "%s.%s" % (name, extension))

    def GetIcon(self, name, vendor="Aha-Soft", style=IconStyle.NORMAL,
                size=None, extension=None):
        """
        Get icon, possibly from cache.
        """
        if not size:
            size = self.defaultIconSize
        cacheKey = '%s-%s-%s' % (name, IconStyle.STRINGS[style], size)
        iconPath = self.GetIconPath(name, vendor, style, size, extension)

        if cacheKey not in self.iconsCache:
            if vendor in ["Aha-Soft", "new"]:
                self.iconsCache[cacheKey] = \
                    wx.Image(iconPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            else:
                self.iconsCache[cacheKey] = \
                    wx.Image(iconPath, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        return self.iconsCache[cacheKey]

    def GetNewIcon(self, name):
        """
        http://icongal.com/gallery/iconset/508/drf
        """
        cacheKey = "new-icon-{}".format(name)
        if cacheKey not in self.iconsCache:
            iconPath = os.path.join(self.mediaPath, "DRF", "{}.png".format(name))
            self.iconsCache[cacheKey] = wx.Image(iconPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        return self.iconsCache[cacheKey]


MYDATA_ICONS = Icons()
