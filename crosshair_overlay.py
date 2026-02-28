#!/usr/bin/env python3
# Crosshair overlay app with system tray, settings, and config persistence
# Works on X11 (Linux Mint Cinnamon default)

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, Gdk, GLib, AppIndicator3
import cairo
import json
import math
import os
import sys

# ── Config ──────────────────────────────────────────────────────────────────

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "crosshair-overlay")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ICON_FILE = os.path.join(CONFIG_DIR, "crosshair-icon.svg")

DEFAULTS = {
	"line_color": [0.9, 0.9, 0.9],
	"line_width": 1.0,
	"line_opacity": 0.35,
	"dot_color": [1.0, 0.3, 0.3],
	"dot_radius": 2.5,
	"dot_opacity": 0.6,
}


def load_config():
	os.makedirs(CONFIG_DIR, exist_ok=True)
	try:
		with open(CONFIG_FILE, "r") as f:
			cfg = json.load(f)
		merged = dict(DEFAULTS)
		merged.update(cfg)
		return merged
	except (FileNotFoundError, json.JSONDecodeError):
		return dict(DEFAULTS)


def save_config(cfg):
	os.makedirs(CONFIG_DIR, exist_ok=True)
	with open(CONFIG_FILE, "w") as f:
		json.dump(cfg, f, indent=2)


def ensure_tray_icon():
	if os.path.exists(ICON_FILE):
		return
	os.makedirs(CONFIG_DIR, exist_ok=True)
	svg = (
		'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22">'
		'<line x1="11" y1="2" x2="11" y2="20" stroke="#ccc" stroke-width="1.5"/>'
		'<line x1="2" y1="11" x2="20" y2="11" stroke="#ccc" stroke-width="1.5"/>'
		'<circle cx="11" cy="11" r="2" fill="#e55"/>'
		'</svg>'
	)
	with open(ICON_FILE, "w") as f:
		f.write(svg)


# ── Crosshair Overlay ──────────────────────────────────────────────────────

class CrosshairOverlay(Gtk.Window):
	def __init__(self, cfg):
		super().__init__(title="Crosshair Overlay")

		self.set_decorated(False)
		self.set_resizable(False)
		self.set_keep_above(True)
		self.set_type_hint(Gdk.WindowTypeHint.DOCK)
		self.set_skip_taskbar_hint(True)
		self.set_skip_pager_hint(True)

		screen = Gdk.Screen.get_default()
		self.full_width = screen.get_width()
		self.full_height = screen.get_height()
		self.set_default_size(self.full_width, self.full_height)
		self.move(0, 0)

		self.set_app_paintable(True)
		visual = screen.get_rgba_visual()
		if visual:
			self.set_visual(visual)

		self.connect("draw", self.on_draw)

		self.mx = self.full_width // 2
		self.my = self.full_height // 2
		self.active = True
		self.apply_settings(cfg)

	def apply_settings(self, cfg):
		r, g, b = cfg["line_color"]
		self.line_color = (r, g, b, cfg["line_opacity"])
		self.line_width = cfg["line_width"]
		r, g, b = cfg["dot_color"]
		self.center_dot_color = (r, g, b, cfg["dot_opacity"])
		self.center_dot_radius = cfg["dot_radius"]
		self.queue_draw()

	def enable_click_through(self):
		gdk_win = self.get_window()
		if gdk_win:
			gdk_win.input_shape_combine_region(cairo.Region(), 0, 0)

	def poll_pointer(self):
		device = Gdk.Display.get_default().get_default_seat().get_pointer()
		_, x, y = device.get_position()
		if x != self.mx or y != self.my:
			self.mx = x
			self.my = y
			self.queue_draw()
		return True

	def on_draw(self, widget, cr):
		cr.set_source_rgba(0, 0, 0, 0)
		cr.set_operator(cairo.Operator.SOURCE)
		cr.paint()

		if not self.active:
			return True

		cr.set_operator(cairo.Operator.OVER)
		cr.set_line_width(self.line_width)

		cr.set_source_rgba(*self.line_color)
		cr.move_to(0, self.my)
		cr.line_to(self.full_width, self.my)
		cr.stroke()

		cr.move_to(self.mx, 0)
		cr.line_to(self.mx, self.full_height)
		cr.stroke()

		if self.center_dot_radius > 0:
			cr.set_source_rgba(*self.center_dot_color)
			cr.arc(self.mx, self.my, self.center_dot_radius, 0, 2 * math.pi)
			cr.fill()

		return True


# ── Settings Window ─────────────────────────────────────────────────────────

class SettingsWindow(Gtk.Window):
	def __init__(self, overlay, cfg):
		super().__init__(title="Crosshair Settings")
		self.overlay = overlay
		self.cfg = cfg

		self.set_default_size(360, -1)
		self.set_resizable(False)
		self.set_position(Gtk.WindowPosition.CENTER)
		self.connect("delete-event", self.on_delete)

		grid = Gtk.Grid(column_spacing=12, row_spacing=8)
		grid.set_margin_top(16)
		grid.set_margin_bottom(16)
		grid.set_margin_start(16)
		grid.set_margin_end(16)
		self.add(grid)
		row = 0

		# ── Crosshair Line ──
		header = Gtk.Label(label="<b>Crosshair Line</b>", use_markup=True, xalign=0)
		grid.attach(header, 0, row, 3, 1)
		row += 1

		grid.attach(Gtk.Label(label="Color", xalign=0), 0, row, 1, 1)
		self.line_color_btn = Gtk.ColorButton()
		r, g, b = cfg["line_color"]
		self.line_color_btn.set_rgba(Gdk.RGBA(r, g, b, 1.0))
		self.line_color_btn.set_use_alpha(False)
		self.line_color_btn.connect("color-set", self.on_change)
		grid.attach(self.line_color_btn, 1, row, 2, 1)
		row += 1

		grid.attach(Gtk.Label(label="Width", xalign=0), 0, row, 1, 1)
		self.line_width_scale = Gtk.Scale.new_with_range(
			Gtk.Orientation.HORIZONTAL, 0.5, 10.0, 0.5)
		self.line_width_scale.set_value(cfg["line_width"])
		self.line_width_scale.set_hexpand(True)
		self.line_width_scale.connect("value-changed", self.on_change)
		grid.attach(self.line_width_scale, 1, row, 2, 1)
		row += 1

		grid.attach(Gtk.Label(label="Opacity", xalign=0), 0, row, 1, 1)
		self.line_opacity_scale = Gtk.Scale.new_with_range(
			Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
		self.line_opacity_scale.set_value(cfg["line_opacity"])
		self.line_opacity_scale.set_hexpand(True)
		self.line_opacity_scale.connect("value-changed", self.on_change)
		grid.attach(self.line_opacity_scale, 1, row, 2, 1)
		row += 1

		# ── Separator ──
		grid.attach(Gtk.Separator(), 0, row, 3, 1)
		row += 1

		# ── Center Dot ──
		header = Gtk.Label(label="<b>Center Dot</b>", use_markup=True, xalign=0)
		grid.attach(header, 0, row, 3, 1)
		row += 1

		grid.attach(Gtk.Label(label="Color", xalign=0), 0, row, 1, 1)
		self.dot_color_btn = Gtk.ColorButton()
		r, g, b = cfg["dot_color"]
		self.dot_color_btn.set_rgba(Gdk.RGBA(r, g, b, 1.0))
		self.dot_color_btn.set_use_alpha(False)
		self.dot_color_btn.connect("color-set", self.on_change)
		grid.attach(self.dot_color_btn, 1, row, 2, 1)
		row += 1

		grid.attach(Gtk.Label(label="Radius", xalign=0), 0, row, 1, 1)
		self.dot_radius_scale = Gtk.Scale.new_with_range(
			Gtk.Orientation.HORIZONTAL, 0.0, 10.0, 0.5)
		self.dot_radius_scale.set_value(cfg["dot_radius"])
		self.dot_radius_scale.set_hexpand(True)
		self.dot_radius_scale.connect("value-changed", self.on_change)
		grid.attach(self.dot_radius_scale, 1, row, 2, 1)
		row += 1

		grid.attach(Gtk.Label(label="Opacity", xalign=0), 0, row, 1, 1)
		self.dot_opacity_scale = Gtk.Scale.new_with_range(
			Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
		self.dot_opacity_scale.set_value(cfg["dot_opacity"])
		self.dot_opacity_scale.set_hexpand(True)
		self.dot_opacity_scale.connect("value-changed", self.on_change)
		grid.attach(self.dot_opacity_scale, 1, row, 2, 1)

	def on_change(self, *_args):
		lc = self.line_color_btn.get_rgba()
		dc = self.dot_color_btn.get_rgba()
		self.cfg.update({
			"line_color": [lc.red, lc.green, lc.blue],
			"line_width": self.line_width_scale.get_value(),
			"line_opacity": round(self.line_opacity_scale.get_value(), 2),
			"dot_color": [dc.red, dc.green, dc.blue],
			"dot_radius": self.dot_radius_scale.get_value(),
			"dot_opacity": round(self.dot_opacity_scale.get_value(), 2),
		})
		self.overlay.apply_settings(self.cfg)
		save_config(self.cfg)

	def on_delete(self, *_args):
		self.hide()
		return True


# ── System Tray ─────────────────────────────────────────────────────────────

class TrayIcon:
	def __init__(self, overlay, settings_win):
		self.overlay = overlay
		self.settings_win = settings_win

		ensure_tray_icon()
		self.indicator = AppIndicator3.Indicator.new(
			"crosshair-overlay",
			"crosshair-icon",
			AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
		)
		self.indicator.set_icon_theme_path(CONFIG_DIR)
		self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

		menu = Gtk.Menu()

		item_toggle = Gtk.MenuItem(label="Toggle Crosshair")
		item_toggle.connect("activate", self.on_toggle)
		menu.append(item_toggle)

		item_settings = Gtk.MenuItem(label="Settings")
		item_settings.connect("activate", self.on_settings)
		menu.append(item_settings)

		menu.append(Gtk.SeparatorMenuItem())

		item_quit = Gtk.MenuItem(label="Quit")
		item_quit.connect("activate", self.on_quit)
		menu.append(item_quit)

		menu.show_all()
		self.indicator.set_menu(menu)

	def on_toggle(self, _item):
		self.overlay.active = not self.overlay.active
		self.overlay.queue_draw()

	def on_settings(self, _item):
		self.settings_win.show_all()
		self.settings_win.present()

	def on_quit(self, _item):
		Gtk.main_quit()


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
	cfg = load_config()
	save_config(cfg)

	overlay = CrosshairOverlay(cfg)
	overlay.show_all()
	overlay.enable_click_through()
	GLib.idle_add(overlay.poll_pointer)

	settings_win = SettingsWindow(overlay, cfg)
	tray = TrayIcon(overlay, settings_win)

	try:
		Gtk.main()
	except KeyboardInterrupt:
		sys.exit(0)
