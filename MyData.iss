; MyData - Desktop application for uploading data to MyTardis
; Copyright (c) 2012-2013, Monash e-Research Centre (Monash University, Australia)
; All rights reserved.
; 
; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation, either version 3 of the License, or
; any later version.
; 
; In addition, redistribution and use in source and binary forms, with or without
; modification, are permitted provided that the following conditions are met:
; 
; -  Redistributions of source code must retain the above copyright
; notice, this list of conditions and the following disclaimer.
; 
; -  Redistributions in binary form must reproduce the above copyright
; notice, this list of conditions and the following disclaimer in the
; documentation and/or other materials provided with the distribution.
; 
; -  Neither the name of the Monash University nor the names of its
; contributors may be used to endorse or promote products derived from
; this software without specific prior written permission.
; 
; THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
; ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
; WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
; IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
; DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
; (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
; ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
; (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
; SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. SEE THE
; GNU GENERAL PUBLIC LICENSE FOR MORE DETAILS.
; 
; You should have received a copy of the GNU General Public License
; along with this program.  If not, see <http://www.gnu.org/licenses/>.
; 
; Enquiries: help@massive.org.au

;MyData InnoSetup script
;Change OutputDir to suit your build environment

#define MyDataAppName "MyData"
#define MyDataAppExeName "MyData.exe"

[Setup]
AppName={#MyDataAppName}
AppVersion=0.0.4
DefaultDirName={pf}\{#MyDataAppName}
DefaultGroupName={#MyDataAppName}
UninstallDisplayIcon={app}\{#MyDataAppExeName}
Compression=lzma2
SolidCompression=yes
OutputDir=.

[Files]
Source: "dist\MyData\*.*"; DestDir: "{app}"; Flags: recursesubdirs

[Tasks]
Name: "StartMenuEntry" ; Description: "Start MyData when Windows starts" ; GroupDescription: "Windows Startup";

[Dirs]
Name: "{pf}\{#MyDataAppName}\openssh-5.4p1-1-msys-1.0.13\home"; Permissions: "users-modify"

[Icons]
Name: "{group}\{#MyDataAppName}"; Filename: "{app}\{#MyDataAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyDataAppName}}"; Filename: "{uninstallexe}"
;Name: "{userstartup}\{#MyDataAppName}"; Filename: "{app}\{#MyDataAppExeName}"; Tasks:StartMenuEntry;
Name: "{commonstartup}\{#MyDataAppName}"; Filename: "{app}\{#MyDataAppExeName}"; Tasks:StartMenuEntry; Parameters: "--background"
