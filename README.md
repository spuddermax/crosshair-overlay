# Crosshair Overlay

A lightweight, full-screen crosshair overlay for Linux (X11). The overlay is fully click-through — it draws crosshair lines and an optional center dot that follow your mouse cursor without interfering with any clicks or other input.

Includes a built-in **pixel ruler** with configurable tick marks and distance labels, turning your cursor into a measuring tool for graphic design, game development, UI work, or any task that benefits from precise pixel measurements.

A system tray icon provides quick access to toggle visibility, open settings, or quit. All settings apply live and persist across restarts.

## Screenshots

The crosshair overlay in action, showing the crosshair lines and center dot following the cursor:

![Crosshair overlay in action](screenshot.png)

Using the crosshair with a radius of 170 in Inkscape, making the exact point of the fill tool easily seen:

![Crosshair overlay in Inkscape](screenshot-inkscape.png)

The built-in ruler with tick marks and distance labels — measure pixel distances directly from your cursor in any application:

![Crosshair overlay with ruler ticks](screenshot-inkscape-ruler.png)

## Features

- Full-screen transparent overlay, always on top
- Complete click-through — all mouse input passes to windows below
- Customizable crosshair line color, width, and opacity
- Full screen or fixed-radius crosshair size
- Customizable center dot color, radius, and opacity
- **Pixel ruler** — tick marks along the crosshair lines with configurable spacing and major/minor sizes
- **Distance labels** — pixel-distance readouts at major ticks with customizable color, opacity, and font size
- Live-preview settings window with responsive layout
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
| `crosshair_fullscreen` | `true` | Lines span the full screen |
| `crosshair_radius` | `100` | Line radius from center in pixels (when not fullscreen) |
| `dot_color` | `[1.0, 0.3, 0.3]` | Center dot RGB (0.0 - 1.0) |
| `dot_radius` | `2.5` | Dot radius in pixels |
| `dot_opacity` | `0.6` | Dot opacity (0.0 - 1.0) |
| `tick_enabled` | `false` | Show ruler tick marks along crosshair lines |
| `tick_color` | `[0.9, 0.9, 0.9]` | Tick mark RGB (0.0 - 1.0) |
| `tick_opacity` | `0.3` | Tick mark opacity (0.0 - 1.0) |
| `tick_spacing` | `10` | Pixels between minor ticks (5 - 200) |
| `tick_major_every` | `5` | Every Nth tick is a major (longer) tick |
| `tick_minor_length` | `3.0` | Minor tick length in pixels (each side of line) |
| `tick_major_length` | `6.0` | Major tick length in pixels (each side of line) |
| `tick_labels` | `false` | Show pixel-distance labels at major ticks |
| `tick_label_color` | `[0.9, 0.9, 0.9]` | Label text RGB (0.0 - 1.0) |
| `tick_label_opacity` | `0.5` | Label text opacity (0.0 - 1.0) |
| `tick_label_size` | `9.0` | Label font size in pixels (6 - 24) |

## Notes

The crosshair overlay will appear in screenshots only if your screenshot tool is set to capture the cursor.

## License

[MIT](LICENSE)
