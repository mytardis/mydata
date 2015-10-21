"""
EnhancedStatusBar Is A Slight Modification (Actually A Subclassing) Of
wx.StatusBar.  It Allows You To Add Almost Any Widget You Like To The
wx.StatusBar Of Your Main Frame Application And Also To Layout Them Properly.

Based on Andrea Gavana's implementation.
"""

import threading

import wx

# Horizontal Alignment Constants
ESB_ALIGN_CENTER_VERTICAL = 1
ESB_ALIGN_TOP = 2
ESB_ALIGN_BOTTOM = 3

# Vertical Alignment Constants
ESB_ALIGN_CENTER_HORIZONTAL = 11
ESB_ALIGN_LEFT = 12
ESB_ALIGN_RIGHT = 13

# Exact Fit (Either Horizontal Or Vertical Or Both) Constant
ESB_EXACT_FIT = 20


class EnhancedStatusBarItem(object):
    """
    EnhancedStatusBar Is A Slight Modification (Actually A Subclassing) Of
    wx.StatusBar.  It Allows You To Add Almost Any Widget You Like To The
    wx.StatusBar Of Your Main Frame Application And Also To Layout Them Properly.

    Based on Andrea Gavana's implementation.
    """
    # pylint: disable=too-few-public-methods
    # pylint: disable=unused-argument
    def __init__(self, widget, pos,
                 horizontalalignment=ESB_ALIGN_CENTER_HORIZONTAL,
                 verticalalignment=ESB_ALIGN_CENTER_VERTICAL):
        self.__dict__.update(locals())


class EnhancedStatusBar(wx.StatusBar):
    """
    EnhancedStatusBar Is A Slight Modification (Actually A Subclassing) Of
    wx.StatusBar.  It Allows You To Add Almost Any Widget You Like To The
    wx.StatusBar Of Your Main Frame Application And Also To Layout Them Properly.

    Based on Andrea Gavana's implementation.
    """

    def __init__(self, parent, style=wx.STB_SIZEGRIP,
                 name="EnhancedStatusBar"):
        """Default Class Constructor.

        EnhancedStatusBar.__init__(self, parent,
                                   style=wx.STB_SIZEGRIP,
                                   name="EnhancedStatusBar")
        """

        wx.StatusBar.__init__(self, parent, wx.ID_ANY, style, name)

        self._items = {}  # pylint: disable=invalid-name
        self._curPos = 0  # pylint: disable=invalid-name
        self._parent = parent  # pylint: disable=invalid-name

        self.statusbarConnIcon = None
        self.statusbarStaticText = None

        self.Bind(wx.EVT_SIZE, self.OnSize)
        if threading.current_thread().name == "MainThread":
            self.OnSize(None)
        else:
            wx.CallAfter(self.OnSize, None)

    def SetStatusMessage(self, msg):
        """
        Set status message.
        """
        if not self.statusbarStaticText:
            self.statusbarStaticText = wx.StaticText(self, wx.ID_ANY, "")
            self.AddWidget(self.statusbarStaticText, pos=0)
        self.statusbarStaticText.SetLabel(msg)

        self.OnSize(None)

    def SetStatusConnectionIcon(self, bitmap):
        """
        Set status connection icon.
        """
        if not self.statusbarConnIcon:
            self.statusbarConnIcon = wx.StaticBitmap(self, wx.ID_ANY)
            self.AddWidget(self.statusbarConnIcon, pos=1)
        self.statusbarConnIcon.SetBitmap(bitmap)
        self.OnSize(None)

    def OnSize(self, event):
        """
        Handles The wx.EVT_SIZE Events For The StatusBar.

        Actually, All The Calculations Linked To HorizontalAlignment And
        VerticalAlignment Are Done In This Function.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches

        for pos, item in self._items.items():
            widget = item.widget
            horizontalalignment = item.horizontalalignment
            verticalalignment = item.verticalalignment

            rect = self.GetFieldRect(pos)
            widgetsize = widget.GetSize()

            rect = self.GetFieldRect(pos)

            if horizontalalignment == ESB_EXACT_FIT:

                if verticalalignment == ESB_EXACT_FIT:
                    widget.SetSize((rect.width - 2, rect.height - 2))
                    widget.SetPosition((rect.x - 1, rect.y - 1))
                elif verticalalignment == ESB_ALIGN_CENTER_VERTICAL:
                    if widgetsize[1] < rect.width - 1:
                        diffs = (rect.height - widgetsize[1]) / 2
                        widget.SetSize((rect.width - 2, widgetsize[1]))
                        widget.SetPosition((rect.x - 1, rect.y + diffs))
                    else:
                        widget.SetSize((rect.width - 2, widgetsize[1]))
                        widget.SetPosition((rect.x - 1, rect.y - 1))
                elif verticalalignment == ESB_ALIGN_TOP:
                    widget.SetSize((rect.width - 2, widgetsize[1]))
                    widget.SetPosition((rect.x - 1, rect.y))
                elif verticalalignment == ESB_ALIGN_BOTTOM:
                    widget.SetSize((rect.width - 2, widgetsize[1]))
                    widget.SetPosition(
                        (rect.x - 1, rect.height - widgetsize[1]))

            elif horizontalalignment == ESB_ALIGN_LEFT:

                xpos = rect.x - 1
                if verticalalignment == ESB_EXACT_FIT:
                    widget.SetSize((widgetsize[0], rect.height - 2))
                    widget.SetPosition((xpos, rect.y - 1))
                elif verticalalignment == ESB_ALIGN_CENTER_VERTICAL:
                    if widgetsize[1] < rect.height - 1:
                        diffs = (rect.height - widgetsize[1]) / 2
                        widget.SetPosition((xpos, rect.y + diffs))
                    else:
                        widget.SetSize((widgetsize[0], rect.height - 2))
                        widget.SetPosition((xpos, rect.y - 1))
                elif verticalalignment == ESB_ALIGN_TOP:
                    widget.SetPosition((xpos, rect.y))
                elif verticalalignment == ESB_ALIGN_BOTTOM:
                    widget.SetPosition((xpos, rect.height - widgetsize[1]))

            elif horizontalalignment == ESB_ALIGN_RIGHT:

                xpos = rect.x + rect.width - widgetsize[0] - 1
                if verticalalignment == ESB_EXACT_FIT:
                    widget.SetSize((widgetsize[0], rect.height - 2))
                    widget.SetPosition((xpos, rect.y - 1))
                elif verticalalignment == ESB_ALIGN_CENTER_VERTICAL:
                    if widgetsize[1] < rect.height - 1:
                        diffs = (rect.height - widgetsize[1]) / 2
                        widget.SetPosition((xpos, rect.y + diffs))
                    else:
                        widget.SetSize((widgetsize[0], rect.height - 2))
                        widget.SetPosition((xpos, rect.y - 1))
                elif verticalalignment == ESB_ALIGN_TOP:
                    widget.SetPosition((xpos, rect.y))
                elif verticalalignment == ESB_ALIGN_BOTTOM:
                    widget.SetPosition((xpos, rect.height - widgetsize[1]))

            elif horizontalalignment == ESB_ALIGN_CENTER_HORIZONTAL:

                xpos = rect.x + (rect.width - widgetsize[0]) / 2 - 1
                if verticalalignment == ESB_EXACT_FIT:
                    widget.SetSize((widgetsize[0], rect.height))
                    widget.SetPosition((xpos, rect.y))
                elif verticalalignment == ESB_ALIGN_CENTER_VERTICAL:
                    if widgetsize[1] < rect.height - 1:
                        diffs = (rect.height - widgetsize[1]) / 2
                        widget.SetPosition((xpos, rect.y + diffs))
                    else:
                        widget.SetSize((widgetsize[0], rect.height - 1))
                        widget.SetPosition((xpos, rect.y + 1))
                elif verticalalignment == ESB_ALIGN_TOP:
                    widget.SetPosition((xpos, rect.y))
                elif verticalalignment == ESB_ALIGN_BOTTOM:
                    widget.SetPosition((xpos, rect.height - widgetsize[1]))

        if event is not None:
            event.Skip()

    def AddWidget(self, widget,
                  horizontalalignment=ESB_ALIGN_CENTER_HORIZONTAL,
                  verticalalignment=ESB_ALIGN_CENTER_VERTICAL, pos=-1):
        """Add A Widget To The EnhancedStatusBar.

        Parameters:

        - horizontalalignment: This Can Be One Of:
          a) ESB_EXACT_FIT: The Widget Will Fit Horizontally The StatusBar
             Field Width;
          b) ESB_ALIGN_CENTER_HORIZONTAL: The Widget Will Be Centered
             Horizontally In
             The StatusBar Field;
          c) ESB_ALIGN_LEFT: The Widget Will Be Left Aligned In The
             StatusBar Field;
          d) ESB_ALIGN_RIGHT: The Widget Will Be Right Aligned In The
             StatusBar Field;

        - verticalalignment:
          a) ESB_EXACT_FIT: The Widget Will Fit Vertically The StatusBar
             Field Height;
          b) ESB_ALIGN_CENTER_VERTICAL: The Widget Will Be Centered
             Vertically In The StatusBar Field;
          c) ESB_ALIGN_BOTTOM: The Widget Will Be Bottom Aligned In The
             StatusBar Field;
          d) ESB_ALIGN_TOP: The Widget Will Be TOP Aligned In The
             StatusBar Field;

        """

        if pos == -1:
            pos = self._curPos
            self._curPos += 1

        # if self.GetFieldsCount() <= pos:
            # raise Exception("\nERROR: EnhancedStatusBar has a max of %d items, "
            # "you tried to set item #%d" % (self.GetFieldsCount(), pos))

        if horizontalalignment not in [ESB_ALIGN_CENTER_HORIZONTAL,
                                       ESB_EXACT_FIT,
                                       ESB_ALIGN_LEFT, ESB_ALIGN_RIGHT]:
            raise Exception('\nERROR: Parameter "horizontalalignment" Should Be One Of '
                            '"ESB_ALIGN_CENTER_HORIZONTAL", "ESB_ALIGN_LEFT", '
                            '"ESB_ALIGN_RIGHT", "ESB_EXACT_FIT"')

        if verticalalignment not in [ESB_ALIGN_CENTER_VERTICAL, ESB_EXACT_FIT,
                                     ESB_ALIGN_TOP, ESB_ALIGN_BOTTOM]:
            raise Exception('\nERROR: Parameter "verticalalignment" Should Be One Of '
                            '"ESB_ALIGN_CENTER_VERTICAL", "ESB_ALIGN_TOP", '
                            '"ESB_ALIGN_BOTTOM", "ESB_EXACT_FIT"')

        try:
            self.RemoveChild(self._items[pos].widget)
        except KeyError:
            pass

        self._items[pos] = \
            EnhancedStatusBarItem(widget, pos,
                                  horizontalalignment, verticalalignment)
        # self.SetFieldsCount(len(self._items.keys()))

        if threading.current_thread().name == "MainThread":
            self.OnSize(None)
        else:
            wx.CallAfter(self.OnSize, None)
