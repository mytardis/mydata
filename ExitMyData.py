"""
This module does nothing.  On Windows, it is used to build "Exit MyData.exe"
which also does nothing.  Before MyData runs "Exit MyData.exe" it requests
administrator privileges from the user.  This is to discourage
non-administrator users from shutting down MyData when it can instead run
quietly in the background.  "Exit MyData.exe" requires some DLLs to run,
but they are the same DLLs which are copied into MyData's dist directory
by its PyInstaller build script (packageWindowsVersion.py).
"""
pass
