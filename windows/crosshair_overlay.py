#!/usr/bin/env python3
# Crosshair overlay app with system tray, settings, and config persistence
# Windows version — uses Win32 API (ctypes) + GDI+ for the overlay

import ctypes
import ctypes.wintypes as wt
import json
import math
import os
import sys
import threading

# ── Config ──────────────────────────────────────────────────────────────────

CONFIG_DIR = os.path.join(
	os.environ.get("APPDATA", os.path.expanduser("~")),
	"crosshair-overlay",
)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
FAVORITES_FILE = os.path.join(CONFIG_DIR, "favorites.json")

DEFAULTS = {
	"auto_start": False,
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


# ── Autostart (Registry) ────────────────────────────────────────────────────

import winreg

REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REGISTRY_VALUE_NAME = "CrosshairOverlay"


def _get_exe_path():
	"""Return the command to launch the app for the registry Run key."""
	if getattr(sys, "frozen", False):
		# Running as PyInstaller bundle
		return sys.executable
	return f'"{sys.executable}" "{os.path.realpath(sys.argv[0])}"'


def _set_autostart(enabled):
	"""Add or remove the startup registry entry under HKCU."""
	try:
		key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0,
			winreg.KEY_SET_VALUE)
		if enabled:
			winreg.SetValueEx(key, REGISTRY_VALUE_NAME, 0, winreg.REG_SZ,
				_get_exe_path())
		else:
			try:
				winreg.DeleteValue(key, REGISTRY_VALUE_NAME)
			except FileNotFoundError:
				pass
		winreg.CloseKey(key)
	except OSError as e:
		print(f"crosshair-overlay: registry error: {e}", file=sys.stderr)


def _get_autostart():
	"""Check if the startup registry entry exists."""
	try:
		key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0,
			winreg.KEY_READ)
		winreg.QueryValueEx(key, REGISTRY_VALUE_NAME)
		winreg.CloseKey(key)
		return True
	except (FileNotFoundError, OSError):
		return False


# ── Win32 Constants ─────────────────────────────────────────────────────────

# Window styles
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# Window messages
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_TIMER = 0x0113
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_KEYDOWN = 0x0100

# Custom messages
WM_APP_SETTINGS = 0x0400 + 1  # WM_USER+1
WM_APP_MODE = 0x0400 + 2      # WM_USER+2
WM_APP_QUIT = 0x0400 + 3      # WM_USER+3

# Virtual keys
VK_ESCAPE = 0x1B
VK_CONTROL = 0x11

# System metrics
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# SetWindowPos flags
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020

# GWL
GWL_EXSTYLE = -20

# Cursor
IDC_CROSS = 32515
IDC_ARROW = 32512

# UpdateLayeredWindow
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01

# DIB
DIB_RGB_COLORS = 0
BI_RGB = 0

# GDI+
SmoothingModeAntiAlias = 4
TextRenderingHintAntiAlias = 4
UnitPixel = 2
StringFormatFlagsNoWrap = 0x00001000
StringAlignmentCenter = 1
FontStyleRegular = 0
FontStyleBold = 1

HWND_TOPMOST = -1

# Types not defined in ctypes.wintypes
HCURSOR = ctypes.c_void_p
HICON = ctypes.c_void_p
HBRUSH = ctypes.c_void_p
HBITMAP = ctypes.c_void_p
HGDIOBJ = ctypes.c_void_p

# ── Win32 Structures ────────────────────────────────────────────────────────

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASSEX(ctypes.Structure):
	_fields_ = [
		("cbSize", wt.UINT),
		("style", wt.UINT),
		("lpfnWndProc", WNDPROC),
		("cbClsExtra", ctypes.c_int),
		("cbWndExtra", ctypes.c_int),
		("hInstance", wt.HINSTANCE),
		("hIcon", HICON),
		("hCursor", HCURSOR),
		("hbrBackground", HBRUSH),
		("lpszMenuName", wt.LPCWSTR),
		("lpszClassName", wt.LPCWSTR),
		("hIconSm", HICON),
	]


class BLENDFUNCTION(ctypes.Structure):
	_fields_ = [
		("BlendOp", ctypes.c_byte),
		("BlendFlags", ctypes.c_byte),
		("SourceConstantAlpha", ctypes.c_byte),
		("AlphaFormat", ctypes.c_byte),
	]


class BITMAPINFOHEADER(ctypes.Structure):
	_fields_ = [
		("biSize", wt.DWORD),
		("biWidth", ctypes.c_long),
		("biHeight", ctypes.c_long),
		("biPlanes", wt.WORD),
		("biBitCount", wt.WORD),
		("biCompression", wt.DWORD),
		("biSizeImage", wt.DWORD),
		("biXPelsPerMeter", ctypes.c_long),
		("biYPelsPerMeter", ctypes.c_long),
		("biClrUsed", wt.DWORD),
		("biClrImportant", wt.DWORD),
	]


class BITMAPINFO(ctypes.Structure):
	_fields_ = [
		("bmiHeader", BITMAPINFOHEADER),
	]


class GdiplusStartupInput(ctypes.Structure):
	_fields_ = [
		("GdiplusVersion", ctypes.c_uint32),
		("DebugEventCallback", ctypes.c_void_p),
		("SuppressBackgroundThread", wt.BOOL),
		("SuppressExternalCodecs", wt.BOOL),
	]


class PointF(ctypes.Structure):
	_fields_ = [("X", ctypes.c_float), ("Y", ctypes.c_float)]


class RectF(ctypes.Structure):
	_fields_ = [
		("X", ctypes.c_float),
		("Y", ctypes.c_float),
		("Width", ctypes.c_float),
		("Height", ctypes.c_float),
	]


# ── Win32 API Functions ─────────────────────────────────────────────────────

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32
gdiplus = ctypes.windll.gdiplus

# DPI awareness
user32.SetProcessDPIAware()

# Window functions
user32.CreateWindowExW.restype = wt.HWND
user32.CreateWindowExW.argtypes = [
	wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
	ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
	wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID,
]
user32.DefWindowProcW.restype = ctypes.c_long
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEX)]
user32.RegisterClassExW.restype = wt.ATOM
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.SetTimer.argtypes = [wt.HWND, ctypes.c_uint, wt.UINT, ctypes.c_void_p]
user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowPos.argtypes = [
	wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
	ctypes.c_int, ctypes.c_int, wt.UINT,
]
user32.UpdateLayeredWindow.argtypes = [
	wt.HWND, wt.HDC, ctypes.POINTER(wt.POINT), ctypes.POINTER(wt.SIZE),
	wt.HDC, ctypes.POINTER(wt.POINT), wt.DWORD,
	ctypes.POINTER(BLENDFUNCTION), wt.DWORD,
]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.SetCapture.argtypes = [wt.HWND]
user32.ReleaseCapture.restype = wt.BOOL
user32.LoadCursorW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
user32.LoadCursorW.restype = HCURSOR
user32.SetCursor.argtypes = [HCURSOR]
user32.SetCursor.restype = HCURSOR
user32.DestroyWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

# GDI
gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.CreateDIBSection.argtypes = [
	wt.HDC, ctypes.POINTER(BITMAPINFO), wt.UINT,
	ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD,
]
gdi32.CreateDIBSection.restype = HBITMAP
gdi32.SelectObject.argtypes = [wt.HDC, HGDIOBJ]
gdi32.SelectObject.restype = HGDIOBJ
gdi32.DeleteObject.argtypes = [HGDIOBJ]
gdi32.DeleteDC.argtypes = [wt.HDC]

# GDI+ functions
gdiplus.GdiplusStartup.argtypes = [
	ctypes.POINTER(ctypes.POINTER(ctypes.c_uint)),
	ctypes.POINTER(GdiplusStartupInput),
	ctypes.c_void_p,
]
gdiplus.GdiplusShutdown.argtypes = [ctypes.POINTER(ctypes.c_uint)]
gdiplus.GdipCreateFromHDC.argtypes = [wt.HDC, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipDeleteGraphics.argtypes = [ctypes.c_void_p]
gdiplus.GdipSetSmoothingMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetTextRenderingHint.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipCreatePen1.argtypes = [
	ctypes.c_uint32, ctypes.c_float, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p),
]
gdiplus.GdipDeletePen.argtypes = [ctypes.c_void_p]
gdiplus.GdipDrawLine.argtypes = [
	ctypes.c_void_p, ctypes.c_void_p,
	ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
]
gdiplus.GdipCreateSolidFill.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipDeleteBrush.argtypes = [ctypes.c_void_p]
gdiplus.GdipFillEllipse.argtypes = [
	ctypes.c_void_p, ctypes.c_void_p,
	ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
]
gdiplus.GdipDrawEllipse.argtypes = [
	ctypes.c_void_p, ctypes.c_void_p,
	ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
]
gdiplus.GdipFillRectangle.argtypes = [
	ctypes.c_void_p, ctypes.c_void_p,
	ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
]
gdiplus.GdipCreateFontFamilyFromName.argtypes = [
	wt.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
]
gdiplus.GdipCreateFont.argtypes = [
	ctypes.c_void_p, ctypes.c_float, ctypes.c_int, ctypes.c_int,
	ctypes.POINTER(ctypes.c_void_p),
]
gdiplus.GdipDeleteFont.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteFontFamily.argtypes = [ctypes.c_void_p]
gdiplus.GdipCreateStringFormat.argtypes = [
	ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p),
]
gdiplus.GdipDeleteStringFormat.argtypes = [ctypes.c_void_p]
gdiplus.GdipDrawString.argtypes = [
	ctypes.c_void_p, wt.LPCWSTR, ctypes.c_int,
	ctypes.c_void_p, ctypes.POINTER(RectF),
	ctypes.c_void_p, ctypes.c_void_p,
]
gdiplus.GdipMeasureString.argtypes = [
	ctypes.c_void_p, wt.LPCWSTR, ctypes.c_int,
	ctypes.c_void_p, ctypes.POINTER(RectF),
	ctypes.c_void_p, ctypes.POINTER(RectF),
	ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
]
gdiplus.GdipSetStringFormatAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]


# ── Helper Functions ────────────────────────────────────────────────────────

def argb(r, g, b, a):
	"""Convert float RGBA (0-1) to GDI+ ARGB uint32."""
	ai = int(max(0, min(1, a)) * 255)
	ri = int(max(0, min(1, r)) * 255)
	gi = int(max(0, min(1, g)) * 255)
	bi = int(max(0, min(1, b)) * 255)
	return (ai << 24) | (ri << 16) | (gi << 8) | bi


def create_pen(color_argb, width):
	pen = ctypes.c_void_p()
	gdiplus.GdipCreatePen1(ctypes.c_uint32(color_argb), ctypes.c_float(width), UnitPixel, ctypes.byref(pen))
	return pen


def create_brush(color_argb):
	brush = ctypes.c_void_p()
	gdiplus.GdipCreateSolidFill(ctypes.c_uint32(color_argb), ctypes.byref(brush))
	return brush


def draw_line(graphics, pen, x1, y1, x2, y2):
	gdiplus.GdipDrawLine(graphics, pen, ctypes.c_float(x1), ctypes.c_float(y1),
		ctypes.c_float(x2), ctypes.c_float(y2))


def fill_ellipse(graphics, brush, x, y, w, h):
	gdiplus.GdipFillEllipse(graphics, brush, ctypes.c_float(x), ctypes.c_float(y),
		ctypes.c_float(w), ctypes.c_float(h))


def draw_ellipse(graphics, pen, x, y, w, h):
	gdiplus.GdipDrawEllipse(graphics, pen, ctypes.c_float(x), ctypes.c_float(y),
		ctypes.c_float(w), ctypes.c_float(h))


def fill_rect(graphics, brush, x, y, w, h):
	gdiplus.GdipFillRectangle(graphics, brush, ctypes.c_float(x), ctypes.c_float(y),
		ctypes.c_float(w), ctypes.c_float(h))


def create_font(family_name, size, bold=False):
	family = ctypes.c_void_p()
	gdiplus.GdipCreateFontFamilyFromName(family_name, None, ctypes.byref(family))
	font = ctypes.c_void_p()
	style = FontStyleBold if bold else FontStyleRegular
	gdiplus.GdipCreateFont(family, ctypes.c_float(size), style, UnitPixel, ctypes.byref(font))
	gdiplus.GdipDeleteFontFamily(family)
	return font


def measure_string(graphics, text, font, fmt):
	layout = RectF(0, 0, 10000, 10000)
	bound = RectF()
	gdiplus.GdipMeasureString(graphics, text, len(text), font, ctypes.byref(layout),
		fmt, ctypes.byref(bound), None, None)
	return bound.Width, bound.Height


def draw_string(graphics, text, font, brush, x, y, fmt):
	rect = RectF(x, y, 10000, 10000)
	gdiplus.GdipDrawString(graphics, text, len(text), font, ctypes.byref(rect), fmt, brush)


# ── Crosshair Overlay ──────────────────────────────────────────────────────

class CrosshairOverlay:
	def __init__(self, cfg):
		self.cfg = dict(cfg)
		self.active = True
		self.mode = "crosshair"
		self.mx = 0
		self.my = 0
		self.measure_start = None
		self.measure_end = None
		self.measuring = False

		# Virtual screen bounds
		self.vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
		self.vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
		self.vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
		self.vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

		self._cross_cursor = user32.LoadCursorW(None, ctypes.c_wchar_p(IDC_CROSS))
		self._arrow_cursor = user32.LoadCursorW(None, ctypes.c_wchar_p(IDC_ARROW))

		# Keep a reference to the wndproc so it won't be garbage collected
		self._wndproc_ref = WNDPROC(self._wndproc)

		hinstance = kernel32.GetModuleHandleW(None)
		wc = WNDCLASSEX()
		wc.cbSize = ctypes.sizeof(WNDCLASSEX)
		wc.style = 0
		wc.lpfnWndProc = self._wndproc_ref
		wc.hInstance = hinstance
		wc.hCursor = None
		wc.lpszClassName = "CrosshairOverlay"
		user32.RegisterClassExW(ctypes.byref(wc))

		self.hwnd = user32.CreateWindowExW(
			WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST |
			WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
			"CrosshairOverlay", "Crosshair",
			WS_POPUP | WS_VISIBLE,
			self.vx, self.vy, self.vw, self.vh,
			None, None, hinstance, None,
		)

		# 1ms polling timer
		user32.SetTimer(self.hwnd, 1, 1, None)

		self.apply_settings(cfg)
		self._redraw()

	def apply_settings(self, cfg):
		self.cfg = dict(cfg)
		if self.hwnd:
			self._redraw()

	def set_mode(self, mode):
		if self.mode == mode:
			return
		self.mode = mode
		if mode == "measure":
			# Remove WS_EX_TRANSPARENT and WS_EX_NOACTIVATE to receive clicks
			style = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
			style &= ~(WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
			user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style)
			user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
				SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
			user32.SetForegroundWindow(self.hwnd)
			user32.SetCursor(self._cross_cursor)
		else:
			self.measure_start = None
			self.measure_end = None
			self.measuring = False
			# Re-add WS_EX_TRANSPARENT and WS_EX_NOACTIVATE for click-through
			style = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
			style |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
			user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style)
			user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
				SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
		self._redraw()

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

	def _wndproc(self, hwnd, msg, wparam, lparam):
		if msg == WM_TIMER:
			if self.mode == "crosshair":
				pt = wt.POINT()
				user32.GetCursorPos(ctypes.byref(pt))
				if pt.x != self.mx or pt.y != self.my:
					self.mx = pt.x
					self.my = pt.y
					self._redraw()
			return 0

		elif msg == WM_LBUTTONDOWN:
			if self.mode == "measure":
				# lparam coords are client-relative; use screen coords
				pt = wt.POINT()
				user32.GetCursorPos(ctypes.byref(pt))
				self.measure_start = (pt.x, pt.y)
				self.measure_end = (pt.x, pt.y)
				self.measuring = True
				user32.SetCapture(hwnd)
				self._redraw()
				return 0

		elif msg == WM_MOUSEMOVE:
			if self.mode == "measure" and self.measuring:
				pt = wt.POINT()
				user32.GetCursorPos(ctypes.byref(pt))
				ex, ey = pt.x, pt.y
				if user32.GetKeyState(VK_CONTROL) & 0x8000 and self.measure_start:
					ex, ey = self._snap_endpoint(*self.measure_start, ex, ey)
				self.measure_end = (ex, ey)
				self._redraw()
				return 0
			elif self.mode == "measure":
				user32.SetCursor(self._cross_cursor)
				return 0

		elif msg == WM_LBUTTONUP:
			if self.mode == "measure" and self.measuring:
				pt = wt.POINT()
				user32.GetCursorPos(ctypes.byref(pt))
				ex, ey = pt.x, pt.y
				if user32.GetKeyState(VK_CONTROL) & 0x8000 and self.measure_start:
					ex, ey = self._snap_endpoint(*self.measure_start, ex, ey)
				self.measure_end = (ex, ey)
				self.measuring = False
				user32.ReleaseCapture()
				self._redraw()
				return 0

		elif msg == WM_KEYDOWN:
			if wparam == VK_ESCAPE and self.mode == "measure":
				self.set_mode("crosshair")
				return 0

		elif msg == WM_APP_SETTINGS:
			self._redraw()
			return 0

		elif msg == WM_APP_MODE:
			mode = "measure" if wparam == 1 else "crosshair"
			self.set_mode(mode)
			return 0

		elif msg == WM_APP_QUIT:
			user32.DestroyWindow(hwnd)
			return 0

		elif msg == WM_DESTROY:
			user32.PostQuitMessage(0)
			return 0

		return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

	def _redraw(self):
		cfg = self.cfg

		# Create memory DC and 32-bit ARGB bitmap
		screen_dc = user32.GetDC(None)
		mem_dc = gdi32.CreateCompatibleDC(screen_dc)

		bmi = BITMAPINFO()
		bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
		bmi.bmiHeader.biWidth = self.vw
		bmi.bmiHeader.biHeight = -self.vh  # top-down
		bmi.bmiHeader.biPlanes = 1
		bmi.bmiHeader.biBitCount = 32
		bmi.bmiHeader.biCompression = BI_RGB

		bits = ctypes.c_void_p()
		hbmp = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS,
			ctypes.byref(bits), None, 0)
		old_bmp = gdi32.SelectObject(mem_dc, hbmp)

		# Create GDI+ graphics from the DC
		graphics = ctypes.c_void_p()
		gdiplus.GdipCreateFromHDC(mem_dc, ctypes.byref(graphics))
		gdiplus.GdipSetSmoothingMode(graphics, SmoothingModeAntiAlias)
		gdiplus.GdipSetTextRenderingHint(graphics, TextRenderingHintAntiAlias)

		if self.active:
			if self.mode == "measure":
				# Fill with alpha=1 so every pixel is hittable — layered windows
				# do hit-testing on per-pixel alpha, so alpha=0 passes clicks through
				hit_brush = create_brush(argb(0, 0, 0, 1.0 / 255.0))
				fill_rect(graphics, hit_brush, 0, 0, self.vw, self.vh)
				gdiplus.GdipDeleteBrush(hit_brush)
				self._draw_measurement(graphics, cfg)
			elif self.mode == "crosshair":
				self._draw_crosshair(graphics, cfg)

		# Update the layered window
		blend = BLENDFUNCTION()
		blend.BlendOp = AC_SRC_OVER
		blend.BlendFlags = 0
		blend.SourceConstantAlpha = 255
		blend.AlphaFormat = AC_SRC_ALPHA

		pt_src = wt.POINT(0, 0)
		pt_dst = wt.POINT(self.vx, self.vy)
		sz = wt.SIZE(self.vw, self.vh)

		user32.UpdateLayeredWindow(
			self.hwnd, screen_dc,
			ctypes.byref(pt_dst), ctypes.byref(sz),
			mem_dc, ctypes.byref(pt_src),
			0, ctypes.byref(blend), ULW_ALPHA,
		)

		# Cleanup
		gdiplus.GdipDeleteGraphics(graphics)
		gdi32.SelectObject(mem_dc, old_bmp)
		gdi32.DeleteObject(hbmp)
		gdi32.DeleteDC(mem_dc)
		user32.ReleaseDC(None, screen_dc)

	def _draw_crosshair(self, graphics, cfg):
		r, g, b = cfg["line_color"]
		a = cfg["line_opacity"]
		lw = cfg["line_width"]

		# Convert screen coords to bitmap coords (relative to virtual screen)
		mx = self.mx - self.vx
		my = self.my - self.vy

		if cfg["crosshair_fullscreen"]:
			h_left, h_right = 0, self.vw
			v_top, v_bottom = 0, self.vh
		else:
			rad = cfg["crosshair_radius"]
			h_left, h_right = mx - rad, mx + rad
			v_top, v_bottom = my - rad, my + rad

		pen = create_pen(argb(r, g, b, a), lw)
		draw_line(graphics, pen, h_left, my, h_right, my)
		draw_line(graphics, pen, mx, v_top, mx, v_bottom)
		gdiplus.GdipDeletePen(pen)

		# Tick marks
		if cfg["tick_enabled"] and cfg["tick_spacing"] >= 5:
			tr, tg, tb = cfg["tick_color"]
			ta = cfg["tick_opacity"]
			tick_pen = create_pen(argb(tr, tg, tb, ta), 1.0)
			sp = cfg["tick_spacing"]
			maj = cfg["tick_major_every"]
			minor_l = cfg["tick_minor_length"]
			major_l = cfg["tick_major_length"]
			labels = cfg["tick_labels"]

			font = None
			fmt = None
			label_brush = None
			if labels:
				font = create_font("Segoe UI", cfg["tick_label_size"])
				fmt = ctypes.c_void_p()
				gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(fmt))
				lr, lg, lb = cfg["tick_label_color"]
				la = cfg["tick_label_opacity"]
				label_brush = create_brush(argb(lr, lg, lb, la))

			# Horizontal ticks
			i = 1
			dist = sp
			while mx + dist <= h_right or mx - dist >= h_left:
				is_major = maj > 0 and i % maj == 0
				length = major_l if is_major else minor_l
				for x in (mx + dist, mx - dist):
					if h_left <= x <= h_right:
						draw_line(graphics, tick_pen, x, my - length, x, my + length)
						if labels and is_major and font and label_brush:
							txt = str(dist)
							tw, th = measure_string(graphics, txt, font, fmt)
							draw_string(graphics, txt, font, label_brush,
								x - tw / 2, my + major_l + 2, fmt)
				i += 1
				dist = i * sp

			# Vertical ticks
			i = 1
			dist = sp
			while my + dist <= v_bottom or my - dist >= v_top:
				is_major = maj > 0 and i % maj == 0
				length = major_l if is_major else minor_l
				for y in (my + dist, my - dist):
					if v_top <= y <= v_bottom:
						draw_line(graphics, tick_pen, mx - length, y, mx + length, y)
						if labels and is_major and font and label_brush:
							txt = str(dist)
							tw, th = measure_string(graphics, txt, font, fmt)
							draw_string(graphics, txt, font, label_brush,
								mx - major_l - 2 - tw, y - th / 2, fmt)
				i += 1
				dist = i * sp

			gdiplus.GdipDeletePen(tick_pen)
			if font:
				gdiplus.GdipDeleteFont(font)
			if fmt:
				gdiplus.GdipDeleteStringFormat(fmt)
			if label_brush:
				gdiplus.GdipDeleteBrush(label_brush)

		# Center dot
		if cfg["dot_enabled"] and cfg["dot_radius"] > 0:
			dr = cfg["dot_radius"]
			dfr, dfg, dfb = cfg["dot_fill_color"]
			dfa = cfg["dot_fill_opacity"]
			fill_brush = create_brush(argb(dfr, dfg, dfb, dfa))
			fill_ellipse(graphics, fill_brush, mx - dr, my - dr, dr * 2, dr * 2)
			gdiplus.GdipDeleteBrush(fill_brush)

			dsr, dsg, dsb = cfg["dot_stroke_color"]
			dsa = cfg["dot_stroke_opacity"]
			if cfg["dot_stroke_width"] > 0 and dsa > 0:
				stroke_pen = create_pen(argb(dsr, dsg, dsb, dsa), cfg["dot_stroke_width"])
				draw_ellipse(graphics, stroke_pen, mx - dr, my - dr, dr * 2, dr * 2)
				gdiplus.GdipDeletePen(stroke_pen)

	def _draw_measurement(self, graphics, cfg):
		if self.measure_start is None or self.measure_end is None:
			return

		# Convert screen coords to bitmap coords
		x1 = self.measure_start[0] - self.vx
		y1 = self.measure_start[1] - self.vy
		x2 = self.measure_end[0] - self.vx
		y2 = self.measure_end[1] - self.vy

		r, g, b = cfg["line_color"]
		a = cfg["line_opacity"]
		lw = cfg["line_width"]

		# Measurement line
		pen = create_pen(argb(r, g, b, a), lw)
		draw_line(graphics, pen, x1, y1, x2, y2)
		gdiplus.GdipDeletePen(pen)

		# Endpoint dots
		dot_r = max(3, lw * 1.5)
		dot_brush = create_brush(argb(r, g, b, a))
		for px, py in ((x1, y1), (x2, y2)):
			fill_ellipse(graphics, dot_brush, px - dot_r, py - dot_r, dot_r * 2, dot_r * 2)
		gdiplus.GdipDeleteBrush(dot_brush)

		# Distance
		dx = x2 - x1
		dy = y2 - y1
		dist = math.hypot(dx, dy)
		if dist < 1:
			return

		# Ruler ticks
		if cfg["tick_enabled"] and cfg["tick_spacing"] >= 5:
			ux, uy = dx / dist, dy / dist
			px_v, py_v = -uy, ux  # perpendicular
			tr, tg, tb = cfg["tick_color"]
			ta = cfg["tick_opacity"]
			tick_pen = create_pen(argb(tr, tg, tb, ta), max(1, lw * 0.6))

			font = None
			fmt = None
			label_brush = None
			if cfg["tick_labels"]:
				font = create_font("Segoe UI", cfg["tick_label_size"])
				fmt = ctypes.c_void_p()
				gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(fmt))
				lr, lg, lb = cfg["tick_label_color"]
				la = cfg["tick_label_opacity"]
				label_brush = create_brush(argb(lr, lg, lb, la))

			steps = int(dist / cfg["tick_spacing"])
			for i in range(1, steps + 1):
				t = i * cfg["tick_spacing"]
				tx = x1 + ux * t
				ty = y1 + uy * t
				is_major = cfg["tick_major_every"] > 0 and i % cfg["tick_major_every"] == 0
				length = cfg["tick_major_length"] if is_major else cfg["tick_minor_length"]
				half = length / 2
				draw_line(graphics, tick_pen,
					tx - px_v * half, ty - py_v * half,
					tx + px_v * half, ty + py_v * half)
				if is_major and cfg["tick_labels"] and font and label_brush:
					lbl = "%d" % int(t)
					tw, th = measure_string(graphics, lbl, font, fmt)
					off = half + 2 + th / 2
					draw_string(graphics, lbl, font, label_brush,
						tx + px_v * off - tw / 2, ty + py_v * off - th / 2, fmt)

			gdiplus.GdipDeletePen(tick_pen)
			if font:
				gdiplus.GdipDeleteFont(font)
			if fmt:
				gdiplus.GdipDeleteStringFormat(fmt)
			if label_brush:
				gdiplus.GdipDeleteBrush(label_brush)

		# Distance label at midpoint
		# Use original screen delta for the label (not bitmap delta, they're the same)
		label = "%.1f px (%d, %d)" % (dist, int(dx), int(-dy))
		mid_x = (x1 + x2) / 2
		mid_y = (y1 + y2) / 2

		font = create_font("Segoe UI", 13, bold=True)
		fmt = ctypes.c_void_p()
		gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(fmt))

		tw, th = measure_string(graphics, label, font, fmt)
		pad = 4

		bg_x = mid_x - tw / 2 - pad
		bg_y = mid_y - 12 - th - pad
		bg_w = tw + pad * 2
		bg_h = th + pad * 2

		bg_brush = create_brush(argb(0, 0, 0, 0.7))
		fill_rect(graphics, bg_brush, bg_x, bg_y, bg_w, bg_h)
		gdiplus.GdipDeleteBrush(bg_brush)

		text_brush = create_brush(argb(1, 1, 1, 0.95))
		draw_string(graphics, label, font, text_brush,
			mid_x - tw / 2, mid_y - 12 - th, fmt)
		gdiplus.GdipDeleteBrush(text_brush)
		gdiplus.GdipDeleteFont(font)
		gdiplus.GdipDeleteStringFormat(fmt)

	def run(self):
		msg = wt.MSG()
		while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
			user32.TranslateMessage(ctypes.byref(msg))
			user32.DispatchMessageW(ctypes.byref(msg))


# ── Settings Window (tkinter) ──────────────────────────────────────────────

class SettingsWindow:
	def __init__(self, overlay, cfg, favorites):
		self.overlay = overlay
		self.overlay_hwnd = overlay.hwnd
		self.cfg = dict(cfg)
		self.favorites = favorites
		self.favorites_changed_cb = None
		self._root = None
		self._save_timer = None
		self._loading = False
		self._ready = threading.Event()

		# Start the tkinter thread once and keep it alive
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()
		self._ready.wait()

	def show(self):
		if self._root:
			self._root.after(0, self._do_show)

	def _do_show(self):
		# Sync widget values from current cfg before showing
		for key, entry in self._widgets.items():
			if entry[0] == "color":
				_, btn, _ = entry
				r, g, b = self.cfg[key]
				hex_color = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
				btn.configure(bg=hex_color, activebackground=hex_color)
				self._widgets[key] = ("color", btn, [r, g, b])
			elif entry[0] == "spin":
				entry[1].set(self.cfg[key])
			elif entry[0] == "check":
				entry[1].set(self.cfg[key])
		self._auto_start_var.set(_get_autostart())
		self._root.deiconify()
		self._root.lift()

	# Dark theme colors
	BG = "#2b2b2b"
	BG_SECTION = "#333333"
	BG_INPUT = "#3c3c3c"
	FG = "#cccccc"
	FG_DIM = "#999999"
	BORDER = "#555555"
	ACCENT = "#5294e2"
	BG_BTN = "#444444"
	BG_BTN_ACTIVE = "#555555"

	def _run(self):
		import tkinter as tk

		self._root = root = tk.Tk()
		root.title("Crosshair Settings")
		root.geometry("1100x580")
		root.resizable(True, True)
		root.configure(bg=self.BG)

		# Apply dark theme defaults to all widget classes
		root.option_add("*Background", self.BG)
		root.option_add("*Foreground", self.FG)
		root.option_add("*activeBackground", self.BG_BTN_ACTIVE)
		root.option_add("*activeForeground", self.FG)
		root.option_add("*selectBackground", self.ACCENT)
		root.option_add("*selectForeground", "#ffffff")
		root.option_add("*highlightBackground", self.BG)
		root.option_add("*highlightColor", self.BORDER)
		root.option_add("*troughColor", self.BG_INPUT)
		root.option_add("*insertBackground", self.FG)

		self._canvas = canvas = tk.Canvas(root, bg=self.BG, highlightthickness=0)
		scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
		self._flow_frame = tk.Frame(canvas, bg=self.BG)

		self._flow_frame.bind("<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
		self._canvas_window = canvas.create_window((0, 0), window=self._flow_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)

		canvas.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")

		self._widgets = {}
		self._sections = []
		self._flow_cols = 0
		cfg = self.cfg

		SECTION_MIN_WIDTH = 300
		PAD = 10

		# ── Crosshair Line ──
		frame = self._make_section("Crosshair Line")
		self._sections.append(frame)

		self._add_color_row(frame, "line_color", "Color", cfg["line_color"])
		self._add_spin_row(frame, "line_width", "Width", 0.5, 10.0, 0.5, cfg["line_width"])
		self._add_spin_row(frame, "line_opacity", "Opacity", 0.0, 1.0, 0.05, cfg["line_opacity"])
		self._add_check_row(frame, "crosshair_fullscreen", "Full screen", cfg["crosshair_fullscreen"])
		self._add_spin_row(frame, "crosshair_radius", "Radius", 5, 2000, 1, cfg["crosshair_radius"])

		# ── Center Dot ──
		frame = self._make_section("Center Dot")
		self._sections.append(frame)

		self._add_check_row(frame, "dot_enabled", "Enable", cfg["dot_enabled"])
		self._add_spin_row(frame, "dot_radius", "Radius", 1, 2000, 1, cfg["dot_radius"])
		self._add_color_row(frame, "dot_fill_color", "Fill color", cfg["dot_fill_color"])
		self._add_spin_row(frame, "dot_fill_opacity", "Fill opacity", 0.0, 1.0, 0.05, cfg["dot_fill_opacity"])
		self._add_color_row(frame, "dot_stroke_color", "Stroke color", cfg["dot_stroke_color"])
		self._add_spin_row(frame, "dot_stroke_opacity", "Stroke opacity", 0.0, 1.0, 0.05, cfg["dot_stroke_opacity"])
		self._add_spin_row(frame, "dot_stroke_width", "Stroke width", 0.5, 10.0, 0.5, cfg["dot_stroke_width"])

		# ── Tick Marks ──
		frame = self._make_section("Tick Marks")
		self._sections.append(frame)

		self._add_check_row(frame, "tick_enabled", "Enable", cfg["tick_enabled"])
		self._add_color_row(frame, "tick_color", "Color", cfg["tick_color"])
		self._add_spin_row(frame, "tick_opacity", "Opacity", 0.0, 1.0, 0.05, cfg["tick_opacity"])
		self._add_spin_row(frame, "tick_spacing", "Spacing", 5, 200, 1, cfg["tick_spacing"])
		self._add_spin_row(frame, "tick_major_every", "Major every", 2, 20, 1, cfg["tick_major_every"])
		self._add_spin_row(frame, "tick_minor_length", "Minor length", 1.0, 20.0, 0.5, cfg["tick_minor_length"])
		self._add_spin_row(frame, "tick_major_length", "Major length", 1.0, 40.0, 0.5, cfg["tick_major_length"])

		# ── Tick Labels ──
		frame = self._make_section("Tick Labels")
		self._sections.append(frame)

		self._add_check_row(frame, "tick_labels", "Enable", cfg["tick_labels"])
		self._add_color_row(frame, "tick_label_color", "Color", cfg["tick_label_color"])
		self._add_spin_row(frame, "tick_label_opacity", "Opacity", 0.0, 1.0, 0.05, cfg["tick_label_opacity"])
		self._add_spin_row(frame, "tick_label_size", "Size", 6.0, 24.0, 1.0, cfg["tick_label_size"])

		# ── Favorites ──
		frame = self._make_section("Favorites")
		self._sections.append(frame)

		save_row = tk.Frame(frame, bg=self.BG_SECTION)
		save_row.pack(fill="x", pady=2)
		self._fav_name_var = tk.StringVar()
		fav_entry = tk.Entry(save_row, textvariable=self._fav_name_var,
			bg=self.BG_INPUT, fg=self.FG, insertbackground=self.FG,
			relief="flat", highlightthickness=1, highlightcolor=self.BORDER,
			highlightbackground=self.BORDER)
		fav_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
		fav_entry.bind("<Return>", lambda e: self._save_favorite_from_entry())
		self._make_button(save_row, "Save", self._save_favorite_from_entry).pack(side="left")

		self._fav_list_frame = tk.Frame(frame, bg=self.BG_SECTION)
		self._fav_list_frame.pack(fill="x", pady=(4, 0))
		self._rebuild_favorites_list()

		# ── General ──
		frame = self._make_section("General")
		self._sections.append(frame)

		self._auto_start_var = tk.BooleanVar(value=_get_autostart())
		chk = tk.Checkbutton(frame, text="Start at login",
			variable=self._auto_start_var,
			bg=self.BG_SECTION, fg=self.FG,
			activebackground=self.BG_SECTION, activeforeground=self.FG,
			selectcolor=self.BG_INPUT, highlightthickness=0,
			command=self._on_auto_start_toggled)
		chk.pack(anchor="w", pady=2)

		# Flow layout: reflow sections into grid on resize
		self._section_min_width = SECTION_MIN_WIDTH
		self._pad = PAD
		canvas.bind("<Configure>", self._on_canvas_resize)
		self._reflow_sections(root.winfo_reqwidth())

		root.protocol("WM_DELETE_WINDOW", self._on_close)
		root.withdraw()  # Start hidden
		self._ready.set()
		root.mainloop()

	def _on_canvas_resize(self, event):
		width = event.width
		self._canvas.itemconfig(self._canvas_window, width=width)
		self._reflow_sections(width)

	def _reflow_sections(self, available_width):
		cols = max(1, available_width // (self._section_min_width + self._pad * 2))
		if cols == self._flow_cols:
			return
		self._flow_cols = cols

		for s in self._sections:
			s.grid_forget()

		for i, section in enumerate(self._sections):
			r, c = divmod(i, cols)
			section.grid(row=r, column=c, sticky="nsew",
				padx=self._pad, pady=self._pad // 2)

		for c in range(cols):
			self._flow_frame.columnconfigure(c, weight=1)

	def _rebuild_favorites_list(self):
		for child in self._fav_list_frame.winfo_children():
			child.destroy()
		import tkinter as tk
		for name in sorted(self.favorites):
			row = tk.Frame(self._fav_list_frame, bg=self.BG_SECTION)
			row.pack(fill="x", pady=1)
			self._make_button(row, name, lambda n=name: self._load_favorite(n),
				relief="flat", anchor="w").pack(side="left", fill="x", expand=True)
			self._make_button(row, "\u21bb",
				lambda n=name: self._confirm_update_favorite(n), width=3).pack(side="left", padx=(2, 0))
			self._make_button(row, "\u00d7",
				lambda n=name: self._delete_favorite(n), width=3).pack(side="left", padx=(2, 0))

	def _save_favorite_from_entry(self):
		name = self._fav_name_var.get().strip()
		if not name:
			return
		self._save_favorite(name)
		self._fav_name_var.set("")

	def _confirm_update_favorite(self, name):
		from tkinter import messagebox
		if messagebox.askyesno("Update Favorite",
				f'Update "{name}" to current settings?', parent=self._root):
			self._save_favorite(name)

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
		# Push to overlay and save
		self.overlay.apply_settings(self.cfg)
		save_config(self.cfg)
		# Update widgets if settings window is built
		if self._root:
			self._root.after(0, self._update_widgets_from_cfg)

	def _update_widgets_from_cfg(self):
		self._loading = True
		for key, entry in self._widgets.items():
			if entry[0] == "color":
				_, btn, _ = entry
				r, g, b = self.cfg[key]
				hex_color = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
				btn.configure(bg=hex_color, activebackground=hex_color)
				self._widgets[key] = ("color", btn, [r, g, b])
			elif entry[0] == "spin":
				entry[1].set(self.cfg[key])
			elif entry[0] == "check":
				entry[1].set(self.cfg[key])
		self._loading = False
		# Apply to overlay
		user32.PostMessageW(self.overlay_hwnd, WM_APP_SETTINGS, 0, 0)
		self._schedule_save()

	def _make_section(self, title):
		import tkinter as tk
		frame = tk.LabelFrame(self._flow_frame, text=title, padx=10, pady=8,
			bg=self.BG_SECTION, fg=self.FG)
		return frame

	def _make_button(self, parent, text, command, width=None, relief="raised", anchor=None):
		import tkinter as tk
		kw = dict(text=text, command=command, bg=self.BG_BTN, fg=self.FG,
			activebackground=self.BG_BTN_ACTIVE, activeforeground=self.FG,
			relief=relief, bd=1, highlightthickness=0)
		if width is not None:
			kw["width"] = width
		if anchor is not None:
			kw["anchor"] = anchor
		return tk.Button(parent, **kw)

	def _add_color_row(self, parent, key, label, value):
		import tkinter as tk

		row = tk.Frame(parent, bg=self.BG_SECTION)
		row.pack(fill="x", pady=2)
		tk.Label(row, text=label, width=14, anchor="w",
			bg=self.BG_SECTION, fg=self.FG).pack(side="left")
		r, g, b = value
		hex_color = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
		btn = tk.Button(row, bg=hex_color, width=6, relief="solid",
			activebackground=hex_color, highlightthickness=0, bd=1,
			command=lambda k=key, bt=None: self._pick_color(k))
		btn.pack(side="left", padx=5)
		self._widgets[key] = ("color", btn, value[:])

	def _add_spin_row(self, parent, key, label, lo, hi, step, value):
		import tkinter as tk

		row = tk.Frame(parent, bg=self.BG_SECTION)
		row.pack(fill="x", pady=2)
		tk.Label(row, text=label, width=14, anchor="w",
			bg=self.BG_SECTION, fg=self.FG).pack(side="left")
		var = tk.DoubleVar(value=value)
		digits = 2 if step < 0.1 else (1 if step < 1 else 0)
		fmt = f"%.{digits}f"
		spin = tk.Spinbox(row, from_=lo, to=hi, increment=step,
			textvariable=var, width=10, format=fmt,
			bg=self.BG_INPUT, fg=self.FG, insertbackground=self.FG,
			buttonbackground=self.BG_BTN, relief="flat",
			highlightthickness=1, highlightcolor=self.BORDER,
			highlightbackground=self.BORDER,
			command=lambda: self._on_change())
		spin.bind("<Return>", lambda e: self._on_change())
		spin.bind("<FocusOut>", lambda e: self._on_change())
		spin.pack(side="left", padx=5)
		self._widgets[key] = ("spin", var)

	def _add_check_row(self, parent, key, label, value):
		import tkinter as tk

		row = tk.Frame(parent, bg=self.BG_SECTION)
		row.pack(fill="x", pady=2)
		var = tk.BooleanVar(value=value)
		chk = tk.Checkbutton(row, text=label, variable=var,
			bg=self.BG_SECTION, fg=self.FG,
			activebackground=self.BG_SECTION, activeforeground=self.FG,
			selectcolor=self.BG_INPUT, highlightthickness=0,
			command=self._on_change)
		chk.pack(side="left")
		self._widgets[key] = ("check", var)

	def _pick_color(self, key):
		from tkinter import colorchooser
		wtype, btn, current = self._widgets[key]
		r, g, b = current
		initial = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
		result = colorchooser.askcolor(color=initial, title=f"Choose {key}")
		if result and result[0]:
			rgb = result[0]
			new_val = [rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0]
			hex_color = result[1]
			btn.configure(bg=hex_color, activebackground=hex_color)
			self._widgets[key] = ("color", btn, new_val)
			self._on_change()

	def _on_auto_start_toggled(self):
		enabled = self._auto_start_var.get()
		_set_autostart(enabled)
		self.cfg["auto_start"] = enabled
		self._schedule_save()

	def _on_change(self):
		if self._loading:
			return
		for key, entry in self._widgets.items():
			if entry[0] == "color":
				self.cfg[key] = entry[2][:]
			elif entry[0] == "spin":
				try:
					self.cfg[key] = entry[1].get()
				except Exception:
					pass
			elif entry[0] == "check":
				self.cfg[key] = entry[1].get()

		# Notify overlay on main thread
		user32.PostMessageW(self.overlay_hwnd, WM_APP_SETTINGS, 0, 0)
		self._schedule_save()

	def _schedule_save(self):
		if self._root is None:
			return
		if self._save_timer is not None:
			self._root.after_cancel(self._save_timer)
		self._save_timer = self._root.after(500, self._do_save)

	def _do_save(self):
		self._save_timer = None
		save_config(self.cfg)

	def _on_close(self):
		if self._save_timer is not None:
			self._root.after_cancel(self._save_timer)
			self._save_timer = None
			save_config(self.cfg)
		self._root.withdraw()


# ── System Tray (pystray) ──────────────────────────────────────────────────

class TrayIcon:
	def __init__(self, overlay, settings_win):
		self.overlay = overlay
		self.settings_win = settings_win
		self._current_mode = "crosshair"
		self._thread = None
		self._icon = None

	def start(self):
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()

	def _create_icon_image(self):
		from PIL import Image, ImageDraw
		size = 64
		img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
		draw = ImageDraw.Draw(img)

		# Circle
		draw.ellipse([8, 8, 56, 56], outline=(221, 221, 221, 153), width=2)
		# Cross lines
		draw.line([(32, 4), (32, 24)], fill=(221, 221, 221, 255), width=2)
		draw.line([(32, 40), (32, 60)], fill=(221, 221, 221, 255), width=2)
		draw.line([(4, 32), (24, 32)], fill=(221, 221, 221, 255), width=2)
		draw.line([(40, 32), (60, 32)], fill=(221, 221, 221, 255), width=2)
		# Center dot
		draw.ellipse([29, 29, 35, 35], fill=(238, 85, 85, 255))

		return img

	def _build_menu(self):
		import pystray

		def on_toggle(icon, item):
			self.overlay.active = not self.overlay.active
			self.overlay._redraw()

		def on_mode_crosshair(icon, item):
			self._current_mode = "crosshair"
			user32.PostMessageW(self.overlay.hwnd, WM_APP_MODE, 0, 0)

		def on_mode_measure(icon, item):
			self._current_mode = "measure"
			user32.PostMessageW(self.overlay.hwnd, WM_APP_MODE, 1, 0)

		def on_settings(icon, item):
			if self._current_mode != "crosshair":
				self._current_mode = "crosshair"
				user32.PostMessageW(self.overlay.hwnd, WM_APP_MODE, 0, 0)
			# Share the cfg dict so settings window reads/writes current state
			self.settings_win.cfg = self.overlay.cfg
			self.settings_win.show()

		def on_quit(icon, item):
			icon.stop()
			user32.PostMessageW(self.overlay.hwnd, WM_APP_QUIT, 0, 0)

		favs = self.settings_win.favorites
		if favs:
			def _make_fav_action(n):
				def action(icon, item):
					self.settings_win.load_favorite(n)
				return action
			fav_items = [
				pystray.MenuItem(name, _make_fav_action(name))
				for name in sorted(favs)
			]
		else:
			fav_items = [pystray.MenuItem("(empty)", None, enabled=False)]

		return pystray.Menu(
			pystray.MenuItem("Toggle Crosshair", on_toggle),
			pystray.Menu.SEPARATOR,
			pystray.MenuItem("Crosshair",
				on_mode_crosshair,
				checked=lambda item: self._current_mode == "crosshair",
				radio=True),
			pystray.MenuItem("Measure",
				on_mode_measure,
				checked=lambda item: self._current_mode == "measure",
				radio=True),
			pystray.Menu.SEPARATOR,
			pystray.MenuItem("Settings", on_settings),
			pystray.MenuItem("Favorites", pystray.Menu(*fav_items)),
			pystray.Menu.SEPARATOR,
			pystray.MenuItem("Quit", on_quit),
		)

	def _rebuild_favorites_menu(self):
		if self._icon:
			self._icon.menu = self._build_menu()
			self._icon.update_menu()

	def _run(self):
		import pystray

		self._icon = pystray.Icon("crosshair-overlay", self._create_icon_image(),
			"Crosshair Overlay", self._build_menu())
		self._icon.run()


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
	# Initialize GDI+
	gdi_token = ctypes.POINTER(ctypes.c_uint)()
	startup_input = GdiplusStartupInput()
	startup_input.GdiplusVersion = 1
	gdiplus.GdiplusStartup(ctypes.byref(gdi_token), ctypes.byref(startup_input), None)

	cfg = load_config()
	save_config(cfg)
	favs = load_favorites()

	overlay = CrosshairOverlay(cfg)
	settings_win = SettingsWindow(overlay, cfg, favs)
	tray = TrayIcon(overlay, settings_win)
	settings_win.favorites_changed_cb = tray._rebuild_favorites_menu
	tray.start()

	try:
		overlay.run()
	except KeyboardInterrupt:
		pass
	finally:
		gdiplus.GdiplusShutdown(gdi_token)
		sys.exit(0)
