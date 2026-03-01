@echo off
setlocal

set VERSION=1.0.0

echo === Building Crosshair Overlay v%VERSION% ===

REM Check for icon, generate if missing
if not exist "crosshair-overlay.ico" (
    echo Generating icon...
    python create_icon.py
    if errorlevel 1 (
        echo ERROR: Failed to generate icon. Make sure Pillow is installed.
        exit /b 1
    )
)

echo Running PyInstaller...
python -m PyInstaller --clean --noconfirm crosshair_overlay.spec
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

REM Rename the exe to include the version
if exist "dist\CrosshairOverlay-%VERSION%.exe" del "dist\CrosshairOverlay-%VERSION%.exe"
rename "dist\CrosshairOverlay.exe" "CrosshairOverlay-%VERSION%.exe"

echo.
echo === Build complete ===
echo Executable: dist\CrosshairOverlay-%VERSION%.exe

REM Check for Inno Setup compiler
where iscc >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo Running Inno Setup compiler...
    iscc /DAPP_VERSION=%VERSION% installer.iss
    if errorlevel 1 (
        echo ERROR: Inno Setup compilation failed.
        exit /b 1
    )
    echo Installer: Output\CrosshairOverlay-%VERSION%-Setup.exe
) else (
    echo.
    echo Inno Setup compiler (iscc) not found on PATH.
    echo To build the installer, install Inno Setup and run: iscc /DAPP_VERSION=%VERSION% installer.iss
)

endlocal
