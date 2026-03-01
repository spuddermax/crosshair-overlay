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
FAVORITES_FILE = os.path.join(CONFIG_DIR, "favorites.json")
ICON_FILE = os.path.join(CONFIG_DIR, "crosshair-icon.svg")

DEFAULTS = {
	"line_color": [0.9, 0.9, 0.9],
	"line_width": 1.0,
	"line_opacity": 0.35,
	"crosshair_fullscreen": True,
	"crosshair_radius": 100,
	"dot_enabled": True,
	"dot_radius": 3,
	"dot_fill_color": [1.0, 0.3, 0.3],
	"dot_fill_opacity": 0.6,
	"dot_stroke_color": [1.0, 1.0, 1.0],
	"dot_stroke_opacity": 0.0,
	"dot_stroke_width": 1.0,
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
	try:
		os.makedirs(CONFIG_DIR, exist_ok=True)
		with open(CONFIG_FILE, "w") as f:
			json.dump(cfg, f, indent=2)
	except OSError as e:
		print(f"crosshair-overlay: failed to save config: {e}", file=sys.stderr)


def load_favorites():
	os.makedirs(CONFIG_DIR, exist_ok=True)
	try:
		with open(FAVORITES_FILE, "r") as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		return {}


def save_favorites(favs):
	try:
		os.makedirs(CONFIG_DIR, exist_ok=True)
		with open(FAVORITES_FILE, "w") as f:
			json.dump(favs, f, indent=2)
	except OSError as e:
		print(f"crosshair-overlay: failed to save favorites: {e}", file=sys.stderr)


def ensure_tray_icon():
	if os.path.exists(ICON_FILE):
		return
	os.makedirs(CONFIG_DIR, exist_ok=True)
	svg = (
		'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">'
		'<circle cx="24" cy="24" r="18" fill="none" stroke="#ddd" stroke-width="1.5" opacity="0.6"/>'
		'<line x1="24" y1="2" x2="24" y2="18" stroke="#ddd" stroke-width="2" stroke-linecap="round"/>'
		'<line x1="24" y1="30" x2="24" y2="46" stroke="#ddd" stroke-width="2" stroke-linecap="round"/>'
		'<line x1="2" y1="24" x2="18" y2="24" stroke="#ddd" stroke-width="2" stroke-linecap="round"/>'
		'<line x1="30" y1="24" x2="46" y2="24" stroke="#ddd" stroke-width="2" stroke-linecap="round"/>'
		'<circle cx="24" cy="24" r="3" fill="#e55"/>'
		'<circle cx="24" cy="24" r="3" fill="none" stroke="#fff" stroke-width="0.5" opacity="0.5"/>'
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
		self.set_accept_focus(False)

		screen = Gdk.Screen.get_default()
		display = Gdk.Display.get_default()
		n = display.get_n_monitors()
		rects = [display.get_monitor(i).get_geometry() for i in range(n)]
		x0 = min(r.x for r in rects)
		y0 = min(r.y for r in rects)
		x1 = max(r.x + r.width for r in rects)
		y1 = max(r.y + r.height for r in rects)
		self.full_width = x1 - x0
		self.full_height = y1 - y0
		self.set_default_size(self.full_width, self.full_height)
		self.move(x0, y0)

		self.set_app_paintable(True)
		visual = screen.get_rgba_visual()
		if visual:
			self.set_visual(visual)

		self.connect("draw", self.on_draw)

		self.add_events(
			Gdk.EventMask.BUTTON_PRESS_MASK |
			Gdk.EventMask.BUTTON_RELEASE_MASK |
			Gdk.EventMask.POINTER_MOTION_MASK |
			Gdk.EventMask.KEY_PRESS_MASK)
		self.connect("button-press-event", self.on_button_press)
		self.connect("button-release-event", self.on_button_release)
		self.connect("motion-notify-event", self.on_motion_notify)
		self.connect("key-press-event", self.on_key_press)

		self.mx = self.full_width // 2
		self.my = self.full_height // 2
		self.active = True
		self.mode = "crosshair"
		self.mode_changed_cb = None
		self.measure_start = None
		self.measure_end = None
		self.measuring = False
		self.apply_settings(cfg)

	def apply_settings(self, cfg):
		def rgba(color_key, opacity_key):
			r, g, b = cfg[color_key]
			return (r, g, b, cfg[opacity_key])

		self.line_color = rgba("line_color", "line_opacity")
		self.line_width = cfg["line_width"]
		self.crosshair_fullscreen = cfg["crosshair_fullscreen"]
		self.crosshair_radius = cfg["crosshair_radius"]
		self.dot_enabled = cfg["dot_enabled"]
		self.center_dot_radius = cfg["dot_radius"]
		self.dot_fill_color = rgba("dot_fill_color", "dot_fill_opacity")
		self.dot_stroke_color = rgba("dot_stroke_color", "dot_stroke_opacity")
		self.dot_stroke_width = cfg["dot_stroke_width"]
		self.tick_enabled = cfg["tick_enabled"]
		self.tick_color = rgba("tick_color", "tick_opacity")
		self.tick_spacing = cfg["tick_spacing"]
		self.tick_major_every = cfg["tick_major_every"]
		self.tick_minor_length = cfg["tick_minor_length"]
		self.tick_major_length = cfg["tick_major_length"]
		self.tick_labels = cfg["tick_labels"]
		self.tick_label_color = rgba("tick_label_color", "tick_label_opacity")
		self.tick_label_size = cfg["tick_label_size"]
		self.queue_draw()

	def enable_click_through(self):
		gdk_win = self.get_window()
		if gdk_win:
			gdk_win.input_shape_combine_region(cairo.Region(), 0, 0)

	def disable_click_through(self):
		gdk_win = self.get_window()
		if gdk_win:
			rect = cairo.RectangleInt(0, 0, self.full_width, self.full_height)
			gdk_win.input_shape_combine_region(cairo.Region(rect), 0, 0)

	def set_mode(self, mode):
		if self.mode == mode:
			return
		self.mode = mode
		if mode == "measure":
			self.disable_click_through()
			self.set_accept_focus(True)
			self.present()
			gdk_win = self.get_window()
			if gdk_win:
				gdk_win.set_cursor(
					Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "crosshair"))
				gdk_win.focus(Gdk.CURRENT_TIME)
		else:
			self.measure_start = None
			self.measure_end = None
			self.measuring = False
			self.set_accept_focus(False)
			self.enable_click_through()
			gdk_win = self.get_window()
			if gdk_win:
				gdk_win.set_cursor(None)
		self.queue_draw()
		if self.mode_changed_cb:
			self.mode_changed_cb(mode)

	def on_button_press(self, widget, event):
		if self.mode != "measure" or event.button != 1:
			return False
		self.measure_start = (event.x_root, event.y_root)
		self.measure_end = (event.x_root, event.y_root)
		self.measuring = True
		self.queue_draw()
		return True

	def _snap_endpoint(self, x1, y1, x2, y2):
		dx = x2 - x1
		dy = y2 - y1
		dist = math.hypot(dx, dy)
		if dist < 1:
			return x2, y2
		angle = math.atan2(dy, dx)
		snap = math.radians(15)
		angle = round(angle / snap) * snap
		return x1 + dist * math.cos(angle), y1 + dist * math.sin(angle)

	def on_button_release(self, widget, event):
		if self.mode != "measure" or event.button != 1:
			return False
		ex, ey = event.x_root, event.y_root
		if event.state & Gdk.ModifierType.CONTROL_MASK and self.measure_start:
			ex, ey = self._snap_endpoint(*self.measure_start, ex, ey)
		self.measure_end = (ex, ey)
		self.measuring = False
		self.queue_draw()
		return True

	def on_motion_notify(self, widget, event):
		if self.mode != "measure" or not self.measuring:
			return False
		ex, ey = event.x_root, event.y_root
		if event.state & Gdk.ModifierType.CONTROL_MASK and self.measure_start:
			ex, ey = self._snap_endpoint(*self.measure_start, ex, ey)
		self.measure_end = (ex, ey)
		self.queue_draw()
		return True

	def on_key_press(self, widget, event):
		if event.keyval == Gdk.KEY_Escape and self.mode == "measure":
			self.set_mode("crosshair")
			return True
		return False

	def poll_pointer(self):
		if self.mode != "crosshair":
			return True
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

		if self.mode == "crosshair":
			self._draw_crosshair(cr)
		elif self.mode == "measure":
			self._draw_measurement(cr)

		return True

	def _draw_crosshair(self, cr):
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

		if self.dot_enabled and self.center_dot_radius > 0:
			cr.new_path()
			cr.arc(self.mx, self.my, self.center_dot_radius, 0, 2 * math.pi)
			cr.set_source_rgba(*self.dot_fill_color)
			cr.fill_preserve()
			if self.dot_stroke_width > 0 and self.dot_stroke_color[3] > 0:
				cr.set_line_width(self.dot_stroke_width)
				cr.set_source_rgba(*self.dot_stroke_color)
				cr.stroke()
			else:
				cr.new_path()

	def _draw_measurement(self, cr):
		if self.measure_start is None or self.measure_end is None:
			return

		x1, y1 = self.measure_start
		x2, y2 = self.measure_end

		# Draw the measurement line
		cr.set_line_width(self.line_width)
		cr.set_source_rgba(*self.line_color)
		cr.move_to(x1, y1)
		cr.line_to(x2, y2)
		cr.stroke()

		# Draw endpoint dots
		dot_r = max(3, self.line_width * 1.5)
		for px, py in ((x1, y1), (x2, y2)):
			cr.new_path()
			cr.arc(px, py, dot_r, 0, 2 * math.pi)
			cr.set_source_rgba(*self.line_color)
			cr.fill()

		# Ruler ticks along the measurement line
		dx = x2 - x1
		dy = y2 - y1
		dist = math.hypot(dx, dy)
		if dist < 1:
			return

		if self.tick_enabled and self.tick_spacing >= 5:
			cr.save()
			ux, uy = dx / dist, dy / dist
			px, py = -uy, ux  # perpendicular
			cr.set_line_width(max(1, self.line_width * 0.6))
			cr.set_source_rgba(*self.tick_color)
			if self.tick_labels:
				cr.select_font_face("sans-serif",
					cairo.FONT_SLANT_NORMAL,
					cairo.FONT_WEIGHT_NORMAL)
				cr.set_font_size(self.tick_label_size)
			steps = int(dist / self.tick_spacing)
			for i in range(1, steps + 1):
				t = i * self.tick_spacing
				tx = x1 + ux * t
				ty = y1 + uy * t
				is_major = (self.tick_major_every > 0 and
					i % self.tick_major_every == 0)
				length = (self.tick_major_length if is_major
					else self.tick_minor_length)
				half = length / 2
				cr.set_source_rgba(*self.tick_color)
				cr.move_to(tx - px * half, ty - py * half)
				cr.line_to(tx + px * half, ty + py * half)
				cr.stroke()
				if is_major and self.tick_labels:
					lbl = "%d" % int(t)
					cr.set_source_rgba(*self.tick_label_color)
					ext_t = cr.text_extents(lbl)
					off = half + 2 + ext_t.height / 2
					cr.move_to(tx + px * off - ext_t.width / 2,
						ty + py * off + ext_t.height / 2)
					cr.show_text(lbl)
			cr.restore()

		# Distance label at midpoint

		label = "%.1f px (%d, %d)" % (dist, int(dx), int(-dy))
		mid_x = (x1 + x2) / 2
		mid_y = (y1 + y2) / 2

		cr.select_font_face("sans-serif",
			cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
		cr.set_font_size(13)
		ext = cr.text_extents(label)

		pad = 4
		bg_x = mid_x - ext.width / 2 - pad
		bg_y = mid_y - 12 - ext.height - pad
		bg_w = ext.width + pad * 2
		bg_h = ext.height + pad * 2

		# Dark background
		cr.set_source_rgba(0, 0, 0, 0.7)
		cr.rectangle(bg_x, bg_y, bg_w, bg_h)
		cr.fill()

		# Label text
		cr.set_source_rgba(1, 1, 1, 0.95)
		cr.move_to(mid_x - ext.width / 2, mid_y - 12)
		cr.show_text(label)


# ── Settings Window ─────────────────────────────────────────────────────────

class SettingsWindow(Gtk.Window):
	SECTION_MIN_WIDTH = 300

	def __init__(self, overlay, cfg, favorites):
		super().__init__(title="Crosshair Settings")
		self.overlay = overlay
		self.cfg = cfg
		self.favorites = favorites
		self.favorites_changed_cb = None
		self._save_timer = None
		self._loading = False

		self.set_default_size(1100, 580)
		self.set_position(Gtk.WindowPosition.CENTER)
		self.connect("delete-event", self.on_delete)

		scroll = Gtk.ScrolledWindow()
		scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
		self.add(scroll)

		flowbox = Gtk.FlowBox()
		flowbox.set_homogeneous(False)
		flowbox.set_column_spacing(8)
		flowbox.set_row_spacing(8)
		flowbox.set_margin_top(12)
		flowbox.set_margin_bottom(12)
		flowbox.set_margin_start(12)
		flowbox.set_margin_end(12)
		flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
		flowbox.set_min_children_per_line(1)
		flowbox.set_max_children_per_line(4)
		scroll.add(flowbox)

		# ── Crosshair Line ──
		frame, grid = self._make_section("Crosshair Line")
		flowbox.add(frame)
		row = 0

		self.line_color_btn = self._add_color_row(
			grid, row, "Color", cfg["line_color"]); row += 1
		self.line_width_spin = self._add_spin_row(
			grid, row, "Width", 0.5, 10.0, 0.5, cfg["line_width"], 1); row += 1
		self.line_opacity_spin = self._add_spin_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["line_opacity"], 2); row += 1

		self.fullscreen_check = Gtk.CheckButton(label="Full screen")
		self.fullscreen_check.set_active(cfg["crosshair_fullscreen"])
		self.fullscreen_check.connect("toggled", self.on_fullscreen_toggled)
		grid.attach(self.fullscreen_check, 0, row, 2, 1); row += 1

		self.crosshair_radius_spin = self._add_spin_row(
			grid, row, "Radius", 5, 2000, 1, cfg["crosshair_radius"])
		self.crosshair_radius_spin.set_sensitive(not cfg["crosshair_fullscreen"])

		# ── Center Dot ──
		frame, grid = self._make_section("Center Dot")
		flowbox.add(frame)
		row = 0

		self.dot_check = Gtk.CheckButton(label="Enable")
		self.dot_check.set_active(cfg["dot_enabled"])
		self.dot_check.connect("toggled", self.on_dot_toggled)
		grid.attach(self.dot_check, 0, row, 2, 1); row += 1

		self.dot_radius_spin = self._add_spin_row(
			grid, row, "Radius", 1, 2000, 1, cfg["dot_radius"]); row += 1
		self.dot_fill_color_btn = self._add_color_row(
			grid, row, "Fill color", cfg["dot_fill_color"]); row += 1
		self.dot_fill_opacity_spin = self._add_spin_row(
			grid, row, "Fill opacity", 0.0, 1.0, 0.05, cfg["dot_fill_opacity"], 2); row += 1
		self.dot_stroke_color_btn = self._add_color_row(
			grid, row, "Stroke color", cfg["dot_stroke_color"]); row += 1
		self.dot_stroke_opacity_spin = self._add_spin_row(
			grid, row, "Stroke opacity", 0.0, 1.0, 0.05, cfg["dot_stroke_opacity"], 2); row += 1
		self.dot_stroke_width_spin = self._add_spin_row(
			grid, row, "Stroke width", 0.5, 10.0, 0.5, cfg["dot_stroke_width"], 1)

		self._set_dot_controls_sensitive(cfg["dot_enabled"])

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
		self.tick_opacity_spin = self._add_spin_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["tick_opacity"], 2); row += 1
		self.tick_spacing_spin = self._add_spin_row(
			grid, row, "Spacing", 5, 200, 1, cfg["tick_spacing"]); row += 1
		self.tick_major_every_spin = self._add_spin_row(
			grid, row, "Major every", 2, 20, 1, cfg["tick_major_every"]); row += 1
		self.tick_minor_length_spin = self._add_spin_row(
			grid, row, "Minor length", 1.0, 20.0, 0.5, cfg["tick_minor_length"], 1); row += 1
		self.tick_major_length_spin = self._add_spin_row(
			grid, row, "Major length", 1.0, 40.0, 0.5, cfg["tick_major_length"], 1)

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
		self.tick_label_opacity_spin = self._add_spin_row(
			grid, row, "Opacity", 0.0, 1.0, 0.05, cfg["tick_label_opacity"], 2); row += 1
		self.tick_label_size_spin = self._add_spin_row(
			grid, row, "Size", 6.0, 24.0, 1.0, cfg["tick_label_size"])

		self._set_tick_controls_sensitive(cfg["tick_enabled"])
		self._set_label_controls_sensitive(cfg["tick_enabled"] and cfg["tick_labels"])

		# ── Favorites ──
		fav_frame = Gtk.Frame(label="Favorites")
		fav_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
		fav_frame.set_size_request(self.SECTION_MIN_WIDTH, -1)
		fav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		fav_box.set_margin_top(8)
		fav_box.set_margin_bottom(8)
		fav_box.set_margin_start(10)
		fav_box.set_margin_end(10)
		fav_frame.add(fav_box)
		flowbox.add(fav_frame)

		save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		self.fav_name_entry = Gtk.Entry()
		self.fav_name_entry.set_placeholder_text("Favorite name")
		self.fav_name_entry.set_hexpand(True)
		self.fav_name_entry.connect("activate", lambda _: self._save_favorite_from_entry())
		save_row.pack_start(self.fav_name_entry, True, True, 0)
		save_btn = Gtk.Button(label="Save")
		save_btn.connect("clicked", lambda _: self._save_favorite_from_entry())
		save_row.pack_start(save_btn, False, False, 0)
		fav_box.pack_start(save_row, False, False, 0)

		self.fav_listbox = Gtk.ListBox()
		self.fav_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
		fav_box.pack_start(self.fav_listbox, True, True, 0)
		self._rebuild_favorites_list()

	def _rebuild_favorites_list(self):
		for child in self.fav_listbox.get_children():
			self.fav_listbox.remove(child)
		for name in sorted(self.favorites):
			row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
			label = Gtk.Label(label=name, xalign=0)
			label.set_hexpand(True)
			load_btn = Gtk.Button(label=name)
			load_btn.set_relief(Gtk.ReliefStyle.NONE)
			load_btn.set_hexpand(True)
			load_btn.get_child().set_xalign(0)
			load_btn.connect("clicked", lambda _b, n=name: self._load_favorite(n))
			row.pack_start(load_btn, True, True, 0)
			update_btn = Gtk.Button(label="\u21bb")
			update_btn.set_tooltip_text("Update to current settings")
			update_btn.connect("clicked", lambda _b, n=name: self._save_favorite(n))
			row.pack_start(update_btn, False, False, 0)
			del_btn = Gtk.Button(label="\u00d7")
			del_btn.set_tooltip_text("Delete")
			del_btn.connect("clicked", lambda _b, n=name: self._delete_favorite(n))
			row.pack_start(del_btn, False, False, 0)
			self.fav_listbox.add(row)
		self.fav_listbox.show_all()

	def _save_favorite_from_entry(self):
		name = self.fav_name_entry.get_text().strip()
		if not name:
			return
		self._save_favorite(name)
		self.fav_name_entry.set_text("")

	def _save_favorite(self, name):
		self.favorites[name] = dict(self.cfg)
		save_favorites(self.favorites)
		self._rebuild_favorites_list()
		if self.favorites_changed_cb:
			self.favorites_changed_cb()

	def _delete_favorite(self, name):
		self.favorites.pop(name, None)
		save_favorites(self.favorites)
		self._rebuild_favorites_list()
		if self.favorites_changed_cb:
			self.favorites_changed_cb()

	def _load_favorite(self, name):
		if name not in self.favorites:
			return
		self.load_favorite(name)

	def load_favorite(self, name):
		if name not in self.favorites:
			return
		saved = self.favorites[name]
		self.cfg.update(saved)
		self._update_widgets_from_cfg()
		self.overlay.apply_settings(self.cfg)
		self._schedule_save()

	def _update_widgets_from_cfg(self):
		self._loading = True
		cfg = self.cfg
		self.line_color_btn.set_rgba(Gdk.RGBA(*cfg["line_color"], 1.0))
		self.line_width_spin.set_value(cfg["line_width"])
		self.line_opacity_spin.set_value(cfg["line_opacity"])
		self.fullscreen_check.set_active(cfg["crosshair_fullscreen"])
		self.crosshair_radius_spin.set_value(cfg["crosshair_radius"])
		self.crosshair_radius_spin.set_sensitive(not cfg["crosshair_fullscreen"])
		self.dot_check.set_active(cfg["dot_enabled"])
		self.dot_radius_spin.set_value(cfg["dot_radius"])
		self.dot_fill_color_btn.set_rgba(Gdk.RGBA(*cfg["dot_fill_color"], 1.0))
		self.dot_fill_opacity_spin.set_value(cfg["dot_fill_opacity"])
		self.dot_stroke_color_btn.set_rgba(Gdk.RGBA(*cfg["dot_stroke_color"], 1.0))
		self.dot_stroke_opacity_spin.set_value(cfg["dot_stroke_opacity"])
		self.dot_stroke_width_spin.set_value(cfg["dot_stroke_width"])
		self._set_dot_controls_sensitive(cfg["dot_enabled"])
		self.tick_check.set_active(cfg["tick_enabled"])
		self.tick_color_btn.set_rgba(Gdk.RGBA(*cfg["tick_color"], 1.0))
		self.tick_opacity_spin.set_value(cfg["tick_opacity"])
		self.tick_spacing_spin.set_value(cfg["tick_spacing"])
		self.tick_major_every_spin.set_value(cfg["tick_major_every"])
		self.tick_minor_length_spin.set_value(cfg["tick_minor_length"])
		self.tick_major_length_spin.set_value(cfg["tick_major_length"])
		self.tick_labels_check.set_active(cfg["tick_labels"])
		self.tick_label_color_btn.set_rgba(Gdk.RGBA(*cfg["tick_label_color"], 1.0))
		self.tick_label_opacity_spin.set_value(cfg["tick_label_opacity"])
		self.tick_label_size_spin.set_value(cfg["tick_label_size"])
		self._set_tick_controls_sensitive(cfg["tick_enabled"])
		self._set_label_controls_sensitive(cfg["tick_enabled"] and cfg["tick_labels"])
		self._loading = False

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
		btn.props.use_alpha = False
		btn.connect("color-set", self.on_change)
		grid.attach(btn, 1, row, 1, 1)
		return btn

	def _add_spin_row(self, grid, row, label, lo, hi, step, value, digits=0):
		grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
		adj = Gtk.Adjustment(value=value, lower=lo, upper=hi,
			step_increment=step, page_increment=step * 10)
		spin = Gtk.SpinButton(adjustment=adj, digits=digits)
		spin.set_hexpand(True)
		spin.connect("value-changed", self.on_change)
		grid.attach(spin, 1, row, 1, 1)
		return spin

	def _set_tick_controls_sensitive(self, enabled):
		for w in (self.tick_color_btn, self.tick_opacity_spin,
				self.tick_spacing_spin, self.tick_major_every_spin,
				self.tick_minor_length_spin, self.tick_major_length_spin,
				self.tick_labels_check):
			w.set_sensitive(enabled)

	def _set_label_controls_sensitive(self, enabled):
		for w in (self.tick_label_color_btn, self.tick_label_opacity_spin,
				self.tick_label_size_spin):
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

	def _set_dot_controls_sensitive(self, enabled):
		for w in (self.dot_radius_spin, self.dot_fill_color_btn,
				self.dot_fill_opacity_spin, self.dot_stroke_color_btn,
				self.dot_stroke_opacity_spin, self.dot_stroke_width_spin):
			w.set_sensitive(enabled)

	def on_dot_toggled(self, btn):
		self._set_dot_controls_sensitive(btn.get_active())
		self.on_change()

	def on_fullscreen_toggled(self, btn):
		self.crosshair_radius_spin.set_sensitive(not btn.get_active())
		self.on_change()

	def on_change(self, *_args):
		if self._loading:
			return
		lc = self.line_color_btn.get_rgba()
		dfc = self.dot_fill_color_btn.get_rgba()
		dsc = self.dot_stroke_color_btn.get_rgba()
		tc = self.tick_color_btn.get_rgba()
		self.cfg.update({
			"line_color": [lc.red, lc.green, lc.blue],
			"line_width": self.line_width_spin.get_value(),
			"line_opacity": round(self.line_opacity_spin.get_value(), 2),
			"crosshair_fullscreen": self.fullscreen_check.get_active(),
			"crosshair_radius": int(self.crosshair_radius_spin.get_value()),
			"dot_enabled": self.dot_check.get_active(),
			"dot_radius": int(self.dot_radius_spin.get_value()),
			"dot_fill_color": [dfc.red, dfc.green, dfc.blue],
			"dot_fill_opacity": round(self.dot_fill_opacity_spin.get_value(), 2),
			"dot_stroke_color": [dsc.red, dsc.green, dsc.blue],
			"dot_stroke_opacity": round(self.dot_stroke_opacity_spin.get_value(), 2),
			"dot_stroke_width": self.dot_stroke_width_spin.get_value(),
			"tick_enabled": self.tick_check.get_active(),
			"tick_color": [tc.red, tc.green, tc.blue],
			"tick_opacity": round(self.tick_opacity_spin.get_value(), 2),
			"tick_spacing": int(self.tick_spacing_spin.get_value()),
			"tick_major_every": int(self.tick_major_every_spin.get_value()),
			"tick_minor_length": self.tick_minor_length_spin.get_value(),
			"tick_major_length": self.tick_major_length_spin.get_value(),
			"tick_labels": self.tick_labels_check.get_active(),
			"tick_label_color": [
				self.tick_label_color_btn.get_rgba().red,
				self.tick_label_color_btn.get_rgba().green,
				self.tick_label_color_btn.get_rgba().blue],
			"tick_label_opacity": round(self.tick_label_opacity_spin.get_value(), 2),
			"tick_label_size": self.tick_label_size_spin.get_value(),
		})
		self.overlay.apply_settings(self.cfg)
		self._schedule_save()

	def _schedule_save(self):
		if self._save_timer is not None:
			GLib.source_remove(self._save_timer)
		self._save_timer = GLib.timeout_add(500, self._do_save)

	def _do_save(self):
		self._save_timer = None
		save_config(self.cfg)
		return False

	def on_delete(self, *_args):
		if self._save_timer is not None:
			GLib.source_remove(self._save_timer)
			self._save_timer = None
			save_config(self.cfg)
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

		# Mode heading and radio items
		mode_label = Gtk.MenuItem(label="Mode")
		mode_label.set_sensitive(False)
		menu.append(mode_label)

		self.radio_crosshair = Gtk.RadioMenuItem(label="  Crosshair")
		self.radio_crosshair.set_active(True)
		self.radio_crosshair.connect("toggled", self.on_mode_changed, "crosshair")
		menu.append(self.radio_crosshair)

		self.radio_measure = Gtk.RadioMenuItem.new_with_label_from_widget(
			self.radio_crosshair, "  Measure")
		self.radio_measure.connect("toggled", self.on_mode_changed, "measure")
		menu.append(self.radio_measure)

		item_settings = Gtk.MenuItem(label="Settings")
		item_settings.connect("activate", self.on_settings)
		menu.append(item_settings)

		self.fav_menu_item = Gtk.MenuItem(label="Favorites")
		self.fav_submenu = Gtk.Menu()
		self.fav_menu_item.set_submenu(self.fav_submenu)
		menu.append(self.fav_menu_item)
		self._rebuild_favorites_menu()

		menu.append(Gtk.SeparatorMenuItem())

		item_quit = Gtk.MenuItem(label="Quit")
		item_quit.connect("activate", self.on_quit)
		menu.append(item_quit)

		menu.show_all()
		self.indicator.set_menu(menu)
		self.overlay.mode_changed_cb = self._sync_mode_radio

	def _rebuild_favorites_menu(self):
		for child in self.fav_submenu.get_children():
			self.fav_submenu.remove(child)
		favs = self.settings_win.favorites
		if favs:
			for name in sorted(favs):
				item = Gtk.MenuItem(label=name)
				item.connect("activate", lambda _i, n=name: self.settings_win.load_favorite(n))
				self.fav_submenu.append(item)
		else:
			item = Gtk.MenuItem(label="(empty)")
			item.set_sensitive(False)
			self.fav_submenu.append(item)
		self.fav_submenu.show_all()

	def _sync_mode_radio(self, mode):
		if mode == "crosshair" and not self.radio_crosshair.get_active():
			self.radio_crosshair.set_active(True)
		elif mode == "measure" and not self.radio_measure.get_active():
			self.radio_measure.set_active(True)

	def on_toggle(self, _item):
		self.overlay.active = not self.overlay.active
		self.overlay.queue_draw()

	def on_mode_changed(self, item, mode):
		if item.get_active():
			self.overlay.set_mode(mode)

	def on_settings(self, _item):
		if self.overlay.mode != "crosshair":
			self.radio_crosshair.set_active(True)
		self.settings_win.show_all()
		self.settings_win.present()

	def on_quit(self, _item):
		Gtk.main_quit()


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
	cfg = load_config()
	save_config(cfg)
	favs = load_favorites()

	overlay = CrosshairOverlay(cfg)
	overlay.show_all()
	overlay.enable_click_through()
	GLib.timeout_add(1, overlay.poll_pointer)

	settings_win = SettingsWindow(overlay, cfg, favs)
	tray = TrayIcon(overlay, settings_win)
	settings_win.favorites_changed_cb = tray._rebuild_favorites_menu

	try:
		Gtk.main()
	except KeyboardInterrupt:
		sys.exit(0)
