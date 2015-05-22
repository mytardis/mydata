import os, sys, glob, fnmatch
from distutils.core import setup
from distutils.command.build import build
from distutils.command.install import install

import mydata

class CustomBuildCommand(build):
    """Customized build command."""
    def run(self):
        # build.run(self)
        print "Custom build command."

class CustomInstallCommand(install):
    """Customized install command."""
    def run(self):
        # install.run(self)
        print "Custom install command."

setup(name = "mydata",
    version = mydata.__version__,
    description = "GUI for uploading data to MyTardis",
    author = "James Wettenhall",
    author_email = "James.Wettenhall@monash.edu",
    license = "GNU GPLv3",
    url = "http://mydata.readthedocs.org/",
    packages = ['mydata'],
    
    data_files = files,
    
    ## Override some of the default distutils command classes with our own.
    cmdclass = {
        'build': CustomBuildCommand,
        'install': CustomInstallCommand,
    },
    
    scripts = ["run.py"],
    long_description = "GUI for uploading data to MyTardis",
    classifiers=[
      'Development Status :: 4 - Beta',
      'Intended Audience :: End Users/Desktop',
      'Intended Audience :: Science/Research',
      'Intended Audience :: Developers',
      'License :: GNU General Public License (GPL)',
      'Operating System :: Microsoft :: Windows',
      'Operating System :: MacOS :: MacOS X',
      'Programming Language :: Python',
      'Topic :: Database :: Front-Ends',
      'Topic :: System :: Archiving',
      ]
)
