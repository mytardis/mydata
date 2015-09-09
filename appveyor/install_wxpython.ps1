# Script to install wxPython under Windows
# Author: James Wettenhall
# License: CC0 1.0 Universal: http://creativecommons.org/publicdomain/zero/1.0/

$BASE_URL = "http://sourceforge.net/projects/wxpython/files/wxPython/"


function Download ($filename, $url) {
    $webclient = New-Object System.Net.WebClient

    $basedir = $pwd.Path + "\"
    $filepath = $basedir + $filename
    if (Test-Path $filename) {
        Write-Host "Reusing" $filepath
        return $filepath
    }

    # Download and retry up to 3 times in case of network transient errors.
    Write-Host "Downloading" $filename "from" $url
    $retry_attempts = 2
    for($i=0; $i -lt $retry_attempts; $i++){
        try {
            $webclient.DownloadFile($url, $filepath)
            break
        }
        Catch [Exception]{
            Start-Sleep 1
        }
    }
    if (Test-Path $filepath) {
        Write-Host "File saved at" $filepath
    } else {
        # Retry once to get the error message if any at the last try
        $webclient.DownloadFile($url, $filepath)
    }
    return $filepath
}


function ParseWxPythonVersion ($wxpython_version) {
    $version_obj = [version]$wxpython_version
    return ($version_obj.major, $version_obj.minor, $version_obj.build, "")
}


function DownloadWxPython ($wxpython_version, $platform) {
    $major, $minor, $micro, $prerelease = ParseWxPythonVersion $wxpython_version
    $dir = "$wxpython_version"
    $filename = "wxPython$major.$minor-$platform-$wxpython_version-py27.exe"
    $url = "$BASE_URL/$dir/$filename"
    $filepath = Download $filename $url
    return $filepath
}


function InstallWxPython ($wxpython_version, $architecture, $wxpython_home) {
    Write-Host "Installing wxPython" $wxpython_version "for" $architecture "bit architecture to" $wxpython_home
    $major, $minor, $micro, $prerelease = ParseWxPythonVersion $wxpython_version
    if (Test-Path "$wxpython_home\wx-$major.$minor-msw") {
        Write-Host "$wxpython_home\wx-$major.$minor-msw" "already exists, skipping."
        return $false
    }
    if ($architecture -eq "32") {
        $platform = "win32"
    } else {
        $platform = "win64"
    }
    $installer_path = DownloadWxPython $wxpython_version $platform
    $installer_ext = [System.IO.Path]::GetExtension($installer_path)
    Write-Host "Installing $installer_path to $wxpython_home"
    $install_log = $wxpython_home + ".log"
    InstallWxPythonEXE $installer_path $wxpython_home $install_log
    if (Test-Path $wxpython_home) {
        Write-Host "Python $wxpython_version ($architecture) installation complete"
    } else {
        Write-Host "Failed to install wxPython in $wxpython_home"
        Get-Content -Path $install_log
        Exit 1
    }
}


function InstallWxPythonEXE ($exepath, $wxpython_home, $install_log) {
    $install_args = "/quiet InstallAllUsers=1 TargetDir=$wxpython_home"
    RunCommand $exepath $install_args
}


function RunCommand ($command, $command_args) {
    Write-Host $command $command_args
    Start-Process -FilePath $command -ArgumentList $command_args -Wait -Passthru
}


function main () {
    InstallWxPython $env:WXPYTHON_VERSION $env:WXPYTHON_ARCH $env:WXPYTHON
}

main
