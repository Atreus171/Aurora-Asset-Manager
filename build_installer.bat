@echo off
REM Aurora Asset Manager - Build Installer Script
REM Run this after installing Inno Setup 6+

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    echo Inno Setup 6 not found. Please install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

echo Building installer with Inno Setup...
%ISCC% AuroraAssetManager.iss

if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo Installer built successfully!
echo Output: dist\AuroraAssetManager_Setup_v1.5.2.exe
pause