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
	"crosshair_fullscreen": True,
	"crosshair_radius": 100,
	"dot_color": [1.0, 0.3, 0.3],
	"dot_radius": 2.5,
	"dot_opacity": 0.6,
	"tick_enabled": False,
	"tick_color": [0.9, 0.9, 0.9],
	"tick_opacity": 0.3,
	"tick_spacing": 10,
	"tick_major_every": 5,
	"tick_minor_length": 3.0,
	"tick_major_length": 6.0,
	"tick_labels": False,
	"tick_label_color": [0.9, 0.9, 0.9],
	"tick_label_opacity": 0.5,
	"tick_label_size": 9.0,
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
		self.crosshair_fullscreen = cfg["crosshair_fullscreen"]
		self.crosshair_radius = cfg["crosshair_radius"]
		r, g, b = cfg["dot_color"]
		self.center_dot_color = (r, g, b, cfg["dot_opacity"])
		self.center_dot_radius = cfg["dot_radius"]
		self.tick_enabled = cfg["tick_enabled"]
		r, g, b = cfg["tick_color"]
		self.tick_color = (r, g, b, cfg["tick_opacity"])
		self.tick_spacing = cfg["tick_spacing"]
		self.tick_major_every = cfg["tick_major_every"]
		self.tick_minor_length = cfg["tick_minor_length"]
		self.tick_major_length = cfg["tick_major_length"]
		self.tick_labels = cfg["tick_labels"]
		r, g, b = cfg["tick_label_color"]
		self.tick_label_color = (r, g, b, cfg["tick_label_opacity"])
		self.tick_label_size = cfg["tick_label_size"]
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
		if self.crosshair_fullscreen:
			h_left, h_right = 0, self.full_width
			v_top, v_bottom = 0, self.full_height
		else:
			r = self.crosshair_radius
			h_left, h_right = self.mx - r, self.mx + r
			v_top, v_bottom = self.my - r, self.my + r

		cr.move_to(h_left, self.my)
		cr.line_to(h_right, self.my)
		cr.stroke()

		cr.move_to(self.mx, v_top)
		cr.line_to(self.mx, v_bottom)
		cr.stroke()

		if self.tick_enabled and self.tick_spacing >= 5:
			cr.set_source_rgba(*self.tick_color)
			cr.set_line_width(1.0)
			sp = self.tick_spacing
			maj = self.tick_major_every
			minor_l = self.tick_minor_length
			major_l = self.tick_major_length
			labels = self.tick_labels

			if labels:
				cr.select_font_face("sans-serif",
					cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
				cr.set_font_size(self.tick_label_size)
				label_pad = 2

			# Ticks along the horizontal line
			i = 1
			dist = sp
			while self.mx + dist <= h_right or self.mx - dist >= h_left:
				is_major = maj > 0 and i % maj == 0
				length = major_l if is_major else minor_l
				for x in (self.mx + dist, self.mx - dist):
					if h_left <= x <= h_right:
						cr.move_to(x, self.my - length)
						cr.line_to(x, self.my + length)
						cr.stroke()
						if labels and is_major:
							cr.set_source_rgba(*self.tick_label_color)
							txt = str(dist)
							ext = cr.text_extents(txt)
							cr.move_to(x - ext.width / 2,
								self.my + major_l + label_pad + ext.height)
							cr.show_text(txt)
							cr.set_source_rgba(*self.tick_color)
				i += 1
				dist = i * sp

			# Ticks along the vertical line
			i = 1
			dist = sp
			while self.my + dist <= v_bottom or self.my - dist >= v_top:
				is_major = maj > 0 and i % maj == 0
				length = major_l if is_major else minor_l
				for y in (self.my + dist, self.my - dist):
					if v_top <= y <= v_bottom:
						cr.move_to(self.mx - length, y)
						cr.line_to(self.mx + length, y)
						cr.stroke()
						if labels and is_major:
							cr.set_source_rgba(*self.tick_label_color)
							txt = str(dist)
							ext = cr.text_extents(txt)
							cr.move_to(
								self.mx - major_l - label_pad - ext.width,
								y + ext.height / 2)
							cr.show_text(txt)
							cr.set_source_rgba(*self.tick_color)
				i += 1
				dist = i * sp

		if self.center_dot_radius > 0:
			cr.set_source_rgba(*self.center_dot_color)
			cr.arc(self.mx, self.my, self.center_dot_radius, 0, 2 * math.pi)
			cr.fill()

		return True


# ── Settings Window ─────────────────────────────────────────────────────────

class SettingsWindow(Gtk.Window):
	SECTION_MIN_WIDTH = 300

	def __init__(self, overlay, cfg):
		super().__init__(title="Crosshair Settings")
		self.overlay = overlay
		self.cfg = cfg

		self.set_default_size(660, -1)
		self.set_position(Gtk.WindowPosition.CENTER)
		self.connect("delete-event", self.on_delete)

		flowbox = Gtk.FlowBox()
		flowbox.set_homogeneous(True)
		flowbox.set_column_spacing(8)
		flowbox.set_row_spacing(8)
		flowbox.set_margin_top(12)
		flowbox.set_margin_bottom(12)
		flowbox.set_margin_start(12)
		flowbox.set_margin_end(12)
		flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
		flowbox.set_min_children_per_line(1)
		flowbox.set_max_children_per_line(4)
		self.add(flowbox)

		# ── Crosshair Line ──
		frame, grid = self._make_section("Crosshair Line")
		flowbox.add(frame)
		row = 0

		self.line_color_btn = self._add_color_row(
			grid, row, "Color", cfg["line_color"]); row += 1
		self.line_width_scale = self._add_scale_row(
			grid, row, "Width", 0.5, 10.0, 0.5, cfg["line_width"]); row += 1
		self.line_opacity_scale = self._add_scale_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["line_opacity"]); row += 1

		self.fullscreen_check = Gtk.CheckButton(label="Full screen")
		self.fullscreen_check.set_active(cfg["crosshair_fullscreen"])
		self.fullscreen_check.connect("toggled", self.on_fullscreen_toggled)
		grid.attach(self.fullscreen_check, 0, row, 2, 1); row += 1

		self.crosshair_radius_scale = self._add_scale_row(
			grid, row, "Radius", 5, 2000, 5, cfg["crosshair_radius"])
		self.crosshair_radius_scale.set_sensitive(not cfg["crosshair_fullscreen"])

		# ── Center Dot ──
		frame, grid = self._make_section("Center Dot")
		flowbox.add(frame)
		row = 0

		self.dot_color_btn = self._add_color_row(
			grid, row, "Color", cfg["dot_color"]); row += 1
		self.dot_radius_scale = self._add_scale_row(
			grid, row, "Radius", 0.0, 10.0, 0.5, cfg["dot_radius"]); row += 1
		self.dot_opacity_scale = self._add_scale_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["dot_opacity"])

		# ── Tick Marks ──
		frame, grid = self._make_section("Tick Marks")
		flowbox.add(frame)
		row = 0

		self.tick_check = Gtk.CheckButton(label="Enable")
		self.tick_check.set_active(cfg["tick_enabled"])
		self.tick_check.connect("toggled", self.on_tick_toggled)
		grid.attach(self.tick_check, 0, row, 2, 1); row += 1

		self.tick_color_btn = self._add_color_row(
			grid, row, "Color", cfg["tick_color"]); row += 1
		self.tick_opacity_scale = self._add_scale_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["tick_opacity"]); row += 1
		self.tick_spacing_scale = self._add_scale_row(
			grid, row, "Spacing", 5, 200, 1, cfg["tick_spacing"]); row += 1
		self.tick_major_every_scale = self._add_scale_row(
			grid, row, "Major every", 2, 20, 1, cfg["tick_major_every"]); row += 1
		self.tick_minor_length_scale = self._add_scale_row(
			grid, row, "Minor length", 1.0, 20.0, 0.5, cfg["tick_minor_length"]); row += 1
		self.tick_major_length_scale = self._add_scale_row(
			grid, row, "Major length", 1.0, 40.0, 0.5, cfg["tick_major_length"])

		# ── Tick Labels ──
		frame, grid = self._make_section("Tick Labels")
		flowbox.add(frame)
		row = 0

		self.tick_labels_check = Gtk.CheckButton(label="Enable")
		self.tick_labels_check.set_active(cfg["tick_labels"])
		self.tick_labels_check.connect("toggled", self.on_tick_labels_toggled)
		grid.attach(self.tick_labels_check, 0, row, 2, 1); row += 1

		self.tick_label_color_btn = self._add_color_row(
			grid, row, "Color", cfg["tick_label_color"]); row += 1
		self.tick_label_opacity_scale = self._add_scale_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["tick_label_opacity"]); row += 1
		self.tick_label_size_scale = self._add_scale_row(
			grid, row, "Size", 6.0, 24.0, 1.0, cfg["tick_label_size"])

		self._set_tick_controls_sensitive(cfg["tick_enabled"])
		self._set_label_controls_sensitive(cfg["tick_enabled"] and cfg["tick_labels"])

	def _make_section(self, title):
		frame = Gtk.Frame(label=title)
		frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
		frame.set_size_request(self.SECTION_MIN_WIDTH, -1)
		grid = Gtk.Grid(column_spacing=10, row_spacing=6)
		grid.set_margin_top(8)
		grid.set_margin_bottom(8)
		grid.set_margin_start(10)
		grid.set_margin_end(10)
		frame.add(grid)
		return frame, grid

	def _add_color_row(self, grid, row, label, rgb):
		grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
		btn = Gtk.ColorButton()
		btn.set_rgba(Gdk.RGBA(rgb[0], rgb[1], rgb[2], 1.0))
		btn.set_use_alpha(False)
		btn.connect("color-set", self.on_change)
		grid.attach(btn, 1, row, 1, 1)
		return btn

	def _add_scale_row(self, grid, row, label, lo, hi, step, value):
		grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
		scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, step)
		scale.set_value(value)
		scale.set_hexpand(True)
		scale.connect("value-changed", self.on_change)
		grid.attach(scale, 1, row, 1, 1)
		return scale

	def _set_tick_controls_sensitive(self, enabled):
		for w in (self.tick_color_btn, self.tick_opacity_scale,
				self.tick_spacing_scale, self.tick_major_every_scale,
				self.tick_minor_length_scale, self.tick_major_length_scale,
				self.tick_labels_check):
			w.set_sensitive(enabled)

	def _set_label_controls_sensitive(self, enabled):
		for w in (self.tick_label_color_btn, self.tick_label_opacity_scale,
				self.tick_label_size_scale):
			w.set_sensitive(enabled)

	def on_tick_toggled(self, btn):
		active = btn.get_active()
		self._set_tick_controls_sensitive(active)
		self._set_label_controls_sensitive(
			active and self.tick_labels_check.get_active())
		self.on_change()

	def on_tick_labels_toggled(self, btn):
		self._set_label_controls_sensitive(
			self.tick_check.get_active() and btn.get_active())
		self.on_change()

	def on_fullscreen_toggled(self, btn):
		self.crosshair_radius_scale.set_sensitive(not btn.get_active())
		self.on_change()

	def on_change(self, *_args):
		lc = self.line_color_btn.get_rgba()
		dc = self.dot_color_btn.get_rgba()
		tc = self.tick_color_btn.get_rgba()
		self.cfg.update({
			"line_color": [lc.red, lc.green, lc.blue],
			"line_width": self.line_width_scale.get_value(),
			"line_opacity": round(self.line_opacity_scale.get_value(), 2),
			"crosshair_fullscreen": self.fullscreen_check.get_active(),
			"crosshair_radius": int(self.crosshair_radius_scale.get_value()),
			"dot_color": [dc.red, dc.green, dc.blue],
			"dot_radius": self.dot_radius_scale.get_value(),
			"dot_opacity": round(self.dot_opacity_scale.get_value(), 2),
			"tick_enabled": self.tick_check.get_active(),
			"tick_color": [tc.red, tc.green, tc.blue],
			"tick_opacity": round(self.tick_opacity_scale.get_value(), 2),
			"tick_spacing": int(self.tick_spacing_scale.get_value()),
			"tick_major_every": int(self.tick_major_every_scale.get_value()),
			"tick_minor_length": self.tick_minor_length_scale.get_value(),
			"tick_major_length": self.tick_major_length_scale.get_value(),
			"tick_labels": self.tick_labels_check.get_active(),
			"tick_label_color": [
				self.tick_label_color_btn.get_rgba().red,
				self.tick_label_color_btn.get_rgba().green,
				self.tick_label_color_btn.get_rgba().blue],
			"tick_label_opacity": round(self.tick_label_opacity_scale.get_value(), 2),
			"tick_label_size": self.tick_label_size_scale.get_value(),
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
