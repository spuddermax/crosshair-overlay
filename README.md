# Crosshair Overlay

A lightweight, full-screen crosshair overlay for Linux (X11). The overlay is fully click-through — it draws crosshair lines and an optional center dot that follow your mouse cursor without interfering with any clicks or other input.

Includes a system tray icon for quick access to toggle visibility, open settings, or quit, and a settings window where all changes apply live.

![Screenshot](screenshot.png)

## Features

- Full-screen transparent overlay, always on top
- Complete click-through — all mouse input passes to windows below
- Customizable crosshair line color, width, and opacity
- Customizable center dot color, radius, and opacity
- Live-preview settings window (changes apply instantly)
- System tray icon with toggle, settings, and quit
- Settings persist across restarts (`~/.config/crosshair-overlay/config.json`)
- Multi-monitor support

## Requirements

- Python 3
- GTK 3 (`gir1.2-gtk-3.0`)
- AppIndicator3 (`gir1.2-appindicator3-0.1`)
- X11 display server

On Linux Mint / Ubuntu / Debian:

```bash
sudo apt install python3 gir1.2-gtk-3.0 gir1.2-appindicator3-0.1
```

Most of these are pre-installed on Linux Mint.

## Usage

```bash
python3 crosshair_overlay.py
```

A crosshair will appear on screen following your cursor, and a tray icon will appear in your system tray. Right-click the tray icon to:

- **Toggle Crosshair** — show or hide the crosshair
- **Settings** — open the settings window to adjust appearance
- **Quit** — exit the application

To stop the app from the terminal, press `Ctrl+C`.

## Configuration

Settings are stored in `~/.config/crosshair-overlay/config.json` and are created automatically on first run with sensible defaults:

| Setting | Default | Description |
|---|---|---|
| `line_color` | `[0.9, 0.9, 0.9]` | Crosshair line RGB (0.0 - 1.0) |
| `line_width` | `1.0` | Line thickness in pixels |
| `line_opacity` | `0.35` | Line opacity (0.0 - 1.0) |
| `dot_color` | `[1.0, 0.3, 0.3]` | Center dot RGB (0.0 - 1.0) |
| `dot_radius` | `2.5` | Dot radius in pixels |
| `dot_opacity` | `0.6` | Dot opacity (0.0 - 1.0) |

## Notes

The crosshair overlay will appear in screenshots only if your screenshot tool is set to capture the cursor.

## License

[MIT](LICENSE)
