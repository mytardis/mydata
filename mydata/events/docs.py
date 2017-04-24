"""
mydata/events/help.py:

Help-related event handlers methods.
"""
from ..utils import OpenUrl


def OnHelp(event):
    """
    Called when the user clicks the Help icon on the
    main toolbar.
    """
    new = 2  # Open in a new tab, if possible
    url = "http://mydata.readthedocs.org/en/latest/"
    OpenUrl(url, new=new)
    event.Skip()


def OnWalkthrough(event):
    """
    Mac OS X Only.
    Called when the user clicks the Mac OS X Walkthrough
    menu item in the Help menu.
    """
    new = 2  # Open in a new tab, if possible
    url = "http://mydata.readthedocs.org/en/latest/macosx-walkthrough.html"
    OpenUrl(url, new=new)
    event.Skip()
