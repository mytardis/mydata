# http://timgolden.me.uk/python/win32_how_do_i/see_if_two_files_are_the_same_file.html

import os
import sys
import tempfile
import win32file


class Win32SamePath:

    def get_read_handle(self, filename):
        if os.path.isdir(filename):
            dwFlagsAndAttributes = win32file.FILE_FLAG_BACKUP_SEMANTICS
        else:
            dwFlagsAndAttributes = 0
        return win32file.CreateFile(
            filename,
            win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ,
            None,
            win32file.OPEN_EXISTING,
            dwFlagsAndAttributes,
            None
        )

    def get_unique_id(self, hFile):
        (
            attributes,
            created_at, accessed_at, written_at,
            volume,
            file_hi, file_lo,
            n_links,
            index_hi, index_lo
        ) = win32file.GetFileInformationByHandle(hFile)
        return volume, index_hi, index_lo

    def paths_are_equal(self, filename1, filename2):
        hFile1 = self.get_read_handle(filename1)
        hFile2 = self.get_read_handle(filename2)
        are_equal = (self.get_unique_id(hFile1) == self.get_unique_id(hFile2))
        hFile2.Close()
        hFile1.Close()
        return are_equal

#
# This bit of the example will only work on Win2k+; it
#  was the only way I could reasonably produce two different
#  files which were the same file, without knowing anything
#  about your drives, network etc.
#
# win32SameFile = Win32SameFile()
# filename1 = sys.executable
# filename2 = tempfile.mktemp(".exe")
# win32file.CreateHardLink(filename2, filename1, None)
# print filename1, filename2, win32SameFile.paths_are_equal(filename1, filename2)
# dir1 = "C:\\Python27"
# dir2 = "C:/Python27"
# print dir1, dir2, win32SameFile.paths_are_equal(dir1, dir2)
