@echo off
setlocal

echo === Building Crosshair Overlay ===

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
pyinstaller --clean --noconfirm crosshair_overlay.spec
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

echo.
echo === Build complete ===
echo Executable: dist\CrosshairOverlay.exe

REM Check for Inno Setup compiler
where iscc >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo Running Inno Setup compiler...
    iscc installer.iss
    if errorlevel 1 (
        echo ERROR: Inno Setup compilation failed.
        exit /b 1
    )
    echo Installer: Output\CrosshairOverlay-0.6.0-Setup.exe
) else (
    echo.
    echo Inno Setup compiler (iscc) not found on PATH.
    echo To build the installer, install Inno Setup and run: iscc installer.iss
)

endlocal
