# Keyboard zoom slider for brightness (Linux)

An optional extra, not part of the app or the `.deb`. It turns the zoom slider on the **Microsoft Digital Media Pro Keyboard** (USB ID `045e:00b0`) into a brightness control for Crosshair Overlay: push it one way to brighten the crosshair, the other way to dim it, and hold it to keep going.

It needs Crosshair Overlay 1.2.0 or later. Older versions don't handle the signals it sends, and quit when they receive one.

## How it works

The slider sends the `KEY_ZOOMIN` and `KEY_ZOOMOUT` keys, about 30 times a second while held. X11 can't see key codes above 255, so neither the desktop nor the app ever receives them. The helper reads them straight from the keyboard's media-key device instead, and sends the running overlay `SIGUSR1` to raise the brightness one step or `SIGUSR2` to lower it.

| File | What it does |
|---|---|
| `crosshair-slider` | The helper. Python 3 standard library only. |
| `crosshair-slider.service` | A systemd user service that starts it at login. |
| `70-crosshair-slider.rules` | A udev rule that lets the logged-in user read the keyboard's media-key device, and nothing else. |

## Install

From this folder:

```bash
install -Dm755 crosshair-slider ~/.local/bin/crosshair-slider
install -Dm644 crosshair-slider.service ~/.config/systemd/user/crosshair-slider.service
sudo install -m644 70-crosshair-slider.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=input --action=change
systemctl --user daemon-reload
systemctl --user enable --now crosshair-slider
```

If the slider runs backwards, swap `signal.SIGUSR1` and `signal.SIGUSR2` in the helper's `SIGNALS` line.

To remove it:

```bash
systemctl --user disable --now crosshair-slider
rm ~/.local/bin/crosshair-slider ~/.config/systemd/user/crosshair-slider.service
sudo rm /etc/udev/rules.d/70-crosshair-slider.rules
```

## Other keyboards

Other keyboards with a zoom slider or zoom keys may work with small changes. These haven't been tested.

1. Find the device that sends the keys. Run `sudo evtest`, pick each of the keyboard's devices in turn, and move the slider. Note the device name and the key codes it shows.
2. In `crosshair-slider`, set `DEVICE` to that device's path under `/dev/input/by-id/`, and change `KEY_ZOOMIN` and `KEY_ZOOMOUT` if the codes differ.
3. In `70-crosshair-slider.rules`, change the `ATTRS{name}` match to that device's name.

Any other program can drive the brightness the same way, by sending the signals:

```bash
pkill -USR1 -f '^python3 /usr/bin/crosshair-overlay'
```
