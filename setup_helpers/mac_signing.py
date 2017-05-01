"""
Methods for signing Mac builds.

Mac builds must be signed on a machine running macOS / Mac OS X.

Before signing builds, you must:

    1. Install the Xcode command-line tools:
        From the Terminal, type: xcode-select --install

    2. Have a "Developer ID Application" certificate in your KeyChain:
        (i) You or your organization must have:
              - an account at https://developer.apple.com/ and
              - an Apple Developer Program membership.
       (ii) Once you can log into https://developer.apple.com/ and
            access an active Apple Developer Program account, you will
            be able to create a "Developer ID Application" certificate.
"""
import commands
import os

MYDATA_IDENTIFIER = 'org.mytardis.MyData'


class CertificateNotFound(Exception):
    """
    Certificate not found exception.
    """


class MacSigning(object):
    """
    Methods for signing Mac builds.
    """
    def __init__(self, identifier):
        self.identifier = identifier
        self.certificateNamePattern = "Developer ID Application"
        self.signCmd = "codesign --force"
        self.verifyCmds = [
            "codesign -vvvv",
            "spctl --assess --raw --type execute --verbose=4"
        ]

    @property
    def certificateName(self):
        """
        This assumes that you only have one Developer ID Application
        certificate in your key chain.  You need to have a private key
        attached to the certificate in your key chain, so generally you
        will need to create a certificate-signing request on the build
        machine, upload it to the Apple Developer Portal, and download a
        new certificate with a private key attached.
        """
        cmd = 'certtool y | grep "%s"' % self.certificateNamePattern
        certificateLine = commands.getoutput(cmd)
        try:
            return certificateLine.split(": ", 1)[1]
        except IndexError:
            raise CertificateNotFound()

    def SignApp(self, appPath):
        """
        Digitally sign MyData.app
        """
        thingsToSign = [
            'add-loginitem',
            'delete-loginitem',
            'loginitem-exists',
            'MyData Notifications',
            'MyData'
        ]
        for thing in thingsToSign:
            cmd = ('%s -i %s --sign "%s" --verbose=4 '
                   '"%s/Contents/MacOS/%s"'
                   % (self.signCmd, self.identifier, self.certificateName,
                      appPath, thing))
            print cmd
            os.system(cmd)

    def VerifySignature(self, appPath):
        """
        Verify signature of MyData.app
        """
        for verifyCmd in self.verifyCmds:
            cmd = "%s %s" % (verifyCmd, appPath)
            print cmd
            os.system(cmd)


MAC_SIGNING = MacSigning(MYDATA_IDENTIFIER)
