# -*- coding: utf-8 -*-
"""
Spotify Şarkı Sözleri
Spotify'da çalan şarkının sözlerini ekranın istediğin yerinde, Spotify'ın
"Sözler" bölümündeki gibi hareketli ve senkron gösterir. Tam ekranda da üstte kalır.

Kullanım:
  - Sol tıkla sürükle      : pencereyi taşı
  - Sağ alt köşeden sürükle: boyutlandır
  - Ctrl + tekerlek        : yazı boyutu
  - Shift + tekerlek       : arka plan saydamlığı
  - Sağ tık / tepsi simgesi: tüm ayarlar
"""
import sys
import os
import re
import json
import time
import math
import bisect
import asyncio
import hashlib
import datetime
import threading
import ctypes

import requests
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject, QRectF, QSettings, QPoint, QLockFile, QDir
from PySide6.QtGui import (QPainter, QColor, QFont, QFontMetricsF, QPainterPath, QIcon, QPixmap,
                           QAction, QActionGroup, QGuiApplication)
from PySide6.QtWidgets import QApplication, QWidget, QMenu, QSystemTrayIcon

APP_NAME = "SpotifySozler"
UA = {"User-Agent": "SpotifySozlerOverlay/1.0"}
CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

THEMES = {
    "Koyu":          {"bg": "#121212", "active": (255, 255, 255, 1.0), "past": (255, 255, 255, .55), "future": (255, 255, 255, .30)},
    "Spotify Yeşili": {"bg": "#0e7a3c", "active": (255, 255, 255, 1.0), "past": (255, 255, 255, .70), "future": (0, 0, 0, .70)},
    "Gece Mavisi":   {"bg": "#1a2a4d", "active": (255, 255, 255, 1.0), "past": (200, 215, 255, .60), "future": (120, 150, 215, .55)},
    "Mor":           {"bg": "#4b1f6e", "active": (255, 255, 255, 1.0), "past": (255, 255, 255, .65), "future": (0, 0, 0, .65)},
    "Kırmızı":       {"bg": "#8c1d2c", "active": (255, 255, 255, 1.0), "past": (255, 255, 255, .65), "future": (0, 0, 0, .65)},
    "Şeffaf":        {"bg": None,      "active": (255, 255, 255, 1.0), "past": (255, 255, 255, .70), "future": (255, 255, 255, .45)},
}
GAP = "\u0000gap"  # müzik arası (♪) satırı


# --------------------------------------------------------------------------- Spotify durumu
class MediaWatcher(QThread):
    """Windows medya denetimlerinden (SMTC) Spotify'ın çalan parçasını ve konumunu okur."""
    state = Signal(dict)

    def run(self):
        asyncio.run(self._main())

    async def _main(self):
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as M
        mgr = None
        while not self.isInterruptionRequested():
            try:
                if mgr is None:
                    mgr = await M.request_async()
                st = await self._read(mgr)
            except Exception:
                mgr, st = None, {"ok": False}
            self.state.emit(st)
            await asyncio.sleep(0.25)

    async def _read(self, mgr):
        sess = None
        for s in mgr.get_sessions():
            if "spotify" in (s.source_app_user_model_id or "").lower():
                sess = s
                break
        if sess is None:
            return {"ok": False}
        props = await sess.try_get_media_properties_async()
        tl = sess.get_timeline_properties()
        info = sess.get_playback_info()
        playing = int(info.playback_status) == 4
        pos = tl.position.total_seconds()
        end = tl.end_time.total_seconds()
        try:
            age = (datetime.datetime.now(datetime.timezone.utc) - tl.last_updated_time).total_seconds()
        except Exception:
            age = -1
        valid = 0 <= age < 6 * 3600
        est = pos + age if (playing and valid) else pos
        return {"ok": True, "title": props.title or "", "artist": props.artist or "",
                "album": props.album_title or "", "playing": playing, "pos": pos,
                "est": est, "valid": valid, "end": end}


# --------------------------------------------------------------------------- Söz bulma
def parse_lrc(text):
    ts = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
    out = []
    for raw in text.splitlines():
        stamps = ts.findall(raw)
        txt = ts.sub("", raw).strip()
        for m, s in stamps:
            out.append((int(m) * 60 + float(s), txt))
    out.sort(key=lambda x: x[0])
    return out


def clean_title(t):
    t = re.sub(r"\s*[\(\[][^\)\]]*(remaster|feat|ft\.|live|version|edit|mix|from)[^\)\]]*[\)\]]", "", t, flags=re.I)
    t = re.split(r"\s+-\s+", t)[0]
    return t.strip()


def first_artist(a):
    return re.split(r",|&| feat\.? | ft\.? | x ", a, flags=re.I)[0].strip()


def _result(d):
    if d.get("instrumental"):
        return {"instrumental": True}
    if d.get("syncedLyrics"):
        return {"synced": parse_lrc(d["syncedLyrics"])}
    if d.get("plainLyrics"):
        return {"plain": [l.strip() for l in d["plainLyrics"].splitlines()]}
    return None


def lookup_lyrics(title, artist, album, duration):
    base = "https://lrclib.net/api"
    dur = int(round(duration)) if duration else None
    attempts = []
    if dur:
        attempts.append({"track_name": title, "artist_name": artist, "album_name": album, "duration": dur})
        attempts.append({"track_name": title, "artist_name": artist, "duration": dur})
    for params in attempts:
        r = requests.get(base + "/get", params=params, headers=UA, timeout=10)
        if r.status_code == 200:
            res = _result(r.json())
            if res:
                return res
    searches = [{"track_name": clean_title(title), "artist_name": first_artist(artist)},
                {"q": f"{first_artist(artist)} {clean_title(title)}"}]
    for params in searches:
        r = requests.get(base + "/search", params=params, headers=UA, timeout=10)
        if r.status_code != 200:
            continue
        items = r.json() or []
        if dur:
            items = [i for i in items if not i.get("duration") or abs(i["duration"] - dur) <= 6] or items
            items.sort(key=lambda i: abs((i.get("duration") or dur) - dur))
        for i in items:
            if i.get("syncedLyrics"):
                return _result(i)
        for i in items:
            res = _result(i)
            if res:
                return res
    return {"none": True}


class LyricsFetcher(QObject):
    done = Signal(str, object)

    def fetch(self, key, title, artist, album, duration):
        threading.Thread(target=self._run, args=(key, title, artist, album, duration), daemon=True).start()

    def _run(self, key, title, artist, album, duration):
        path = os.path.join(CACHE_DIR, hashlib.md5(key.encode("utf-8")).hexdigest() + ".json")
        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    self.done.emit(key, json.load(f))
                    return
        except Exception:
            pass
        try:
            res = lookup_lyrics(title, artist, album, duration)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False)
        except Exception:
            res = {"error": True}
        self.done.emit(key, res)


# --------------------------------------------------------------------------- Yardımcılar
def rgba(t):
    c = QColor(t[0], t[1], t[2])
    c.setAlphaF(t[3])
    return c


def mix(a, b, k):
    return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * k, a.greenF() + (b.greenF() - a.greenF()) * k,
                           a.blueF() + (b.blueF() - a.blueF()) * k, a.alphaF() + (b.alphaF() - a.alphaF()) * k)


def smoothstep(e0, e1, x):
    x = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return x * x * (3 - 2 * x)


def force_topmost(hwnd):
    # HWND_TOPMOST, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)


# --------------------------------------------------------------------------- Kenarlıksız tam ekran
# Oyunların "özel tam ekran" modu (Minecraft F11 gibi) hiçbir pencerenin üstte görünmesine izin vermez.
# Oyunu pencere modundayken kenarlıksız + ekran boyutunda yaparak aynı tam ekran görüntüsü elde edilir
# ve söz penceresi üstte kalabilir.
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsZoomed.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]

GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_CAPTION, WS_THICKFRAME, WS_SYSMENU = 0x00C00000, 0x00040000, 0x00080000
WS_MINIMIZEBOX, WS_MAXIMIZEBOX, WS_EX_TOPMOST = 0x00020000, 0x00010000, 0x00000008
SWP_FRAMECHANGED, SWP_NOZORDER, SWP_NOOWNERZORDER = 0x0020, 0x0004, 0x0200


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


_borderless_saved = {}


def _win_text(hwnd, fn):
    buf = ctypes.create_unicode_buffer(256)
    fn(hwnd, buf, 256)
    return buf.value


def find_minecraft():
    """Minecraft penceresini bulur: Java sürümü ve tüm istemcileri (SonOyuncu, Lunar, Badlion…)
    GLFW/LWJGL penceresi kullanır; Bedrock'un başlığı 'Minecraft'tır."""
    named, other = [], []
    proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            cls = _win_text(hwnd, user32.GetClassNameW)
            title = _win_text(hwnd, user32.GetWindowTextW)
            if not title:
                return True
            if (cls.startswith("GLFW") or cls == "LWJGL") and "helper" not in cls.lower():
                (named if "minecraft" in title.lower() else other).append(hwnd)
            elif title.strip() == "Minecraft":
                named.append(hwnd)
        return True

    user32.EnumWindows(proto(cb), 0)
    found = named + other
    return found[0] if found else None


def is_exclusive_fullscreen(hwnd):
    style = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    return not (style & WS_CAPTION) and bool(ex & WS_EX_TOPMOST) and hwnd not in _borderless_saved


def _press_key(vk):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP


def _leave_exclusive_fullscreen(hwnd):
    """Oyunu öne getirip F11'e basarak özel tam ekrandan pencere moduna geçirir."""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    if user32.GetForegroundWindow() != hwnd:
        _press_key(0x12)  # Alt: Windows'un öne getirme kısıtlamasını kaldırır
        user32.SetForegroundWindow(hwnd)
    time.sleep(0.7)
    if user32.GetForegroundWindow() != hwnd:
        return False
    # Ctrl+Alt bırakılmadan F11 gönderilirse oyun Ctrl+Alt+F11 görür
    t0 = time.time()
    while time.time() - t0 < 2 and any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B)):
        time.sleep(0.03)
    _press_key(0x7A)  # F11
    for _ in range(30):
        time.sleep(0.1)
        if not is_exclusive_fullscreen(hwnd):
            time.sleep(0.4)
            return True
    return False


def toggle_borderless(hwnd):
    """Pencereyi kenarlıksız tam ekran yapar; tekrar çağrılınca eski haline döndürür."""
    if not hwnd:
        return "Pencere bulunamadı."
    if hwnd in _borderless_saved:
        style, r = _borderless_saved.pop(hwnd)
        user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
        user32.SetWindowPos(hwnd, 0, r.left, r.top, r.right - r.left, r.bottom - r.top,
                            SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOOWNERZORDER)
        return "Pencere eski haline döndü."
    if is_exclusive_fullscreen(hwnd) and not _leave_exclusive_fullscreen(hwnd):
        return ("Oyun özel tam ekrandan çıkarılamadı. Oyunda F11 ile pencere moduna geç, "
                "sonra Ctrl+Alt+F'ye bas.")
    style = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
    if user32.IsZoomed(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    _borderless_saved[hwnd] = (style, r)
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE,
                             style & ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX))
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi))
    m = mi.rcMonitor
    user32.SetWindowPos(hwnd, 0, m.left, m.top, m.right - m.left, m.bottom - m.top,
                        SWP_FRAMECHANGED | SWP_NOOWNERZORDER)
    return "Kenarlıksız tam ekran açıldı. Geri almak için tekrar Ctrl+Alt+F."


class HotkeyThread(QThread):
    """Ctrl+Alt+F genel kısayolunu dinler."""
    pressed = Signal()
    failed = Signal()

    def run(self):
        self.tid = ctypes.windll.kernel32.GetCurrentThreadId()
        # MOD_ALT | MOD_CONTROL | MOD_NOREPEAT
        if not user32.RegisterHotKey(None, 1, 0x0001 | 0x0002 | 0x4000, ord("F")):
            self.failed.emit()
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                self.pressed.emit()
        user32.UnregisterHotKey(None, 1)

    def stop(self):
        if getattr(self, "tid", None):
            user32.PostThreadMessageW(self.tid, 0x0012, 0, 0)  # WM_QUIT
        self.wait(1000)


def make_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#1DB954"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, 60, 60)
    p.setBrush(QColor("#000000"))
    for i, y in enumerate((18, 30, 42)):
        w = 36 - i * 8
        p.drawRoundedRect(32 - w // 2 - 4, y, w, 6, 3, 3)
    p.end()
    return QIcon(pm)


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(on):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pyw):
                pyw = sys.executable
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, f'"{pyw}" "{os.path.abspath(__file__)}"')
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass


# --------------------------------------------------------------------------- Pencere
class LyricsOverlay(QWidget):
    PAD = 26
    GRIP = 18

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool |
                         Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setMinimumSize(260, 120)
        self.setWindowTitle("Spotify Şarkı Sözleri")

        self.cfg = QSettings("ClaudeTools", APP_NAME)
        self.font_px = int(self.cfg.value("font_px", 30))
        self.theme = self.cfg.value("theme", "Koyu")
        if self.theme not in THEMES:
            self.theme = "Koyu"
        self.bg_opacity = float(self.cfg.value("bg_opacity", 0.78))
        self.align_center = self.cfg.value("align_center", "false") == "true"
        self.show_header = self.cfg.value("show_header", "true") == "true"
        self.offset = float(self.cfg.value("offset", 0.0))
        self.locked = self.cfg.value("locked", "false") == "true"
        geo = self.cfg.value("geometry")
        if geo:
            self.setGeometry(*[int(v) for v in geo])
        else:
            scr = QGuiApplication.primaryScreen().availableGeometry()
            w, h = 720, 320
            self.setGeometry(scr.x() + (scr.width() - w) // 2, scr.bottom() - h - 60, w, h)

        # oynatma durumu
        self.track_key = None
        self.title = self.artist = ""
        self.duration = 0.0
        self.clk_base, self.clk_mono, self.clk_playing = 0.0, time.monotonic(), False
        self.last_raw = None

        # söz durumu
        self.lines, self.times = [], []
        self.estimated = False
        self.message = "Spotify bekleniyor…"
        self.layout_dirty = True
        self.heights, self.centers, self.act = [], [], []
        self.scroll = 0.0
        self.idx = -1
        self.msg_alpha = 1.0

        self.drag_off = None
        self.resizing = None
        self.hover = False
        self.last_tick = time.monotonic()

        self.fetcher = LyricsFetcher()
        self.fetcher.done.connect(self.on_lyrics)
        self.watcher = MediaWatcher()
        self.watcher.state.connect(self.on_state)
        self.watcher.start()

        self.anim = QTimer(self, timeout=self.tick)
        self.anim.start(16)
        self.top_timer = QTimer(self, timeout=self.keep_on_top)
        self.top_timer.start(800)

        self.tray = QSystemTrayIcon(make_icon(), self)
        self.tray.setToolTip("Spotify Şarkı Sözleri")
        self.tray_menu = QMenu()
        self.tray_menu.aboutToShow.connect(lambda: self.build_menu(self.tray_menu))
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.on_tray)
        self.tray.show()

        self.hotkey = HotkeyThread()
        self.hotkey.pressed.connect(self.borderless_foreground)
        self.hotkey.failed.connect(lambda: self.notify("Ctrl+Alt+F kısayolu başka bir program tarafından kullanılıyor. "
                                                       "Menüden 'Minecraft'ı kenarlıksız tam ekran yap'ı kullan."))
        self.hotkey.start()

        self.apply_lock(self.locked, save=False)

    # ---------------------------------------------------------------- zaman
    def now_pos(self):
        return self.clk_base + ((time.monotonic() - self.clk_mono) if self.clk_playing else 0.0)

    def set_clock(self, pos, playing):
        self.clk_base, self.clk_mono, self.clk_playing = pos, time.monotonic(), playing

    def on_state(self, st):
        if not st.get("ok"):
            if self.track_key is not None or not self.lines:
                self.track_key = None
                self.title = self.artist = ""
                self.set_lines([], [])
                self.message = "Spotify'da bir şarkı çal"
            self.clk_playing = False
            return
        key = st["title"] + "\x1f" + st["artist"]
        self.duration = st["end"]
        if key != self.track_key:
            self.track_key = key
            self.title, self.artist = st["title"], st["artist"]
            self.set_clock(st["est"], st["playing"])
            self.set_lines([], [])
            if not st["artist"] or not st["title"]:
                self.message = "Reklam / bilinmeyen parça"
            else:
                self.message = "Sözler yükleniyor…"
                self.fetcher.fetch(key, st["title"], st["artist"], st["album"], st["end"])
        else:
            cur = self.now_pos()
            if st["playing"] != self.clk_playing or not st["playing"]:
                self.set_clock(st["est"], st["playing"])
            elif st["valid"]:
                if abs(st["est"] - cur) > 0.6:
                    self.set_clock(st["est"], True)
            elif st["pos"] != self.last_raw:
                self.set_clock(st["pos"], True)
        self.last_raw = st["pos"]

    def on_lyrics(self, key, res):
        if key != self.track_key:
            return
        if res.get("synced"):
            data = [(t, x) for t, x in res["synced"]]
            lines, times = [], []
            if data and data[0][0] > 4:
                lines.append(GAP)
                times.append(0.0)
            for t, x in data:
                lines.append(x if x else GAP)
                times.append(t)
            self.estimated = False
            self.set_lines(lines, times)
        elif res.get("plain"):
            src = [l for l in res["plain"]]
            while src and not src[-1]:
                src.pop()
            dur = self.duration or 200
            a, b = dur * 0.08, dur * 0.92
            n = max(1, len(src))
            self.estimated = True
            self.set_lines([l if l else GAP for l in src], [a + (b - a) * i / n for i in range(len(src))])
        elif res.get("instrumental"):
            self.message = "♪  Enstrümantal  ♪"
        elif res.get("error"):
            self.message = "Sözlere ulaşılamadı (internet?) – tekrar denenecek"
            QTimer.singleShot(15000, lambda k=key: self.retry(k))
        else:
            self.message = "Bu şarkı için söz bulunamadı"

    def retry(self, key):
        if key == self.track_key and not self.lines:
            path = os.path.join(CACHE_DIR, hashlib.md5(key.encode("utf-8")).hexdigest() + ".json")
            if os.path.exists(path):
                os.remove(path)
            t, a = key.split("\x1f")
            self.fetcher.fetch(key, t, a, "", self.duration)

    def set_lines(self, lines, times):
        self.lines, self.times = lines, times
        self.act = [0.0] * len(lines)
        self.idx = -1
        self.scroll = 0.0
        self.layout_dirty = True

    # ---------------------------------------------------------------- yerleşim
    def lyric_font(self):
        f = QFont("Segoe UI")
        f.setPixelSize(self.font_px)
        f.setWeight(QFont.Bold)
        return f

    def text_flags(self):
        return Qt.TextWordWrap | (Qt.AlignHCenter if self.align_center else Qt.AlignLeft) | Qt.AlignVCenter

    def relayout(self):
        fm = QFontMetricsF(self.lyric_font())
        tw = self.width() - 2 * self.PAD
        spacing = self.font_px * 0.55
        self.heights, self.centers = [], []
        y = 0.0
        for ln in self.lines:
            if ln == GAP:
                h = fm.height()
            else:
                h = fm.boundingRect(QRectF(0, 0, tw, 1e6), self.text_flags(), ln).height()
            self.heights.append(h)
            self.centers.append(y + h / 2)
            y += h + spacing
        self.layout_dirty = False

    # ---------------------------------------------------------------- animasyon
    def tick(self):
        now = time.monotonic()
        dt = min(0.1, now - self.last_tick)
        self.last_tick = now
        if self.layout_dirty:
            self.relayout()
        if self.lines:
            t = self.now_pos() + self.offset
            self.idx = bisect.bisect_right(self.times, t) - 1
            target = self.centers[max(self.idx, 0)]
            k = 1 - math.exp(-dt * 8.5)
            self.scroll += (target - self.scroll) * k
            ka = 1 - math.exp(-dt * 10)
            for i in range(len(self.act)):
                self.act[i] += ((1.0 if i == self.idx else 0.0) - self.act[i]) * ka
        self.update()

    def keep_on_top(self):
        if self.isVisible():
            try:
                force_topmost(int(self.winId()))
            except Exception:
                pass

    # ---------------------------------------------------------------- çizim
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        W, H = self.width(), self.height()
        th = THEMES[self.theme]
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, W - 1, H - 1), 18, 18)
        transparent = th["bg"] is None or self.bg_opacity < 0.02
        if th["bg"] is not None:
            bg = QColor(th["bg"])
            bg.setAlphaF(self.bg_opacity)
            p.fillPath(path, bg)
        if (self.hover or transparent) and not self.locked:
            # kenarlık + boyutlandırma tutamacı yalnızca fare üzerindeyken
            p.setPen(QColor(255, 255, 255, 70 if self.hover else 0))
            p.drawPath(path)
            if self.hover:
                p.setPen(QColor(255, 255, 255, 120))
                for d in (6, 11, 16):
                    p.drawLine(W - d, H - 4, W - 4, H - d)
        p.setClipPath(path)

        top = 8.0
        if self.show_header and self.title:
            hf = QFont("Segoe UI")
            hf.setPixelSize(max(11, int(self.font_px * 0.42)))
            hf.setWeight(QFont.DemiBold)
            p.setFont(hf)
            fm = QFontMetricsF(hf)
            icon = "▶" if self.clk_playing else "❚❚"
            txt = f"{icon}  {self.title}  •  {self.artist}" + ("   (zamanlama tahmini)" if self.estimated and self.lines else "")
            txt = fm.elidedText(txt, Qt.ElideRight, W - 2 * self.PAD)
            c = rgba(th["active"])
            c.setAlphaF(0.6)
            p.setPen(c)
            hr = QRectF(self.PAD, 10, W - 2 * self.PAD, fm.height())
            p.drawText(hr, (Qt.AlignHCenter if self.align_center else Qt.AlignLeft) | Qt.AlignVCenter, txt)
            top = 10 + fm.height() + 4

        if not self.lines:
            f = self.lyric_font()
            f.setPixelSize(max(14, int(self.font_px * 0.75)))
            p.setFont(f)
            c = rgba(th["past"])
            p.setPen(c)
            p.drawText(QRectF(self.PAD, top, W - 2 * self.PAD, H - top - 8),
                       Qt.AlignCenter | Qt.TextWordWrap, self.message)
            return

        font = self.lyric_font()
        p.setFont(font)
        area_h = H - top
        cy = top + area_h * 0.42
        tw = W - 2 * self.PAD
        c_act, c_past, c_fut = rgba(th["active"]), rgba(th["past"]), rgba(th["future"])
        shadow_strength = 0.75 if transparent else 0.25
        flags = self.text_flags()
        now_t = self.now_pos() + self.offset

        for i, ln in enumerate(self.lines):
            h = self.heights[i]
            y = cy + (self.centers[i] - self.scroll)
            if y + h < top - 10 or y - h > H + 10:
                continue
            a = self.act[i]
            base = c_past if (self.idx >= 0 and i < self.idx) else c_fut
            col = mix(base, c_act, a)
            dist = abs(y - cy) / max(1.0, area_h * 0.62)
            fade = 1 - smoothstep(0.5, 1.0, dist)
            if y < top + h * 0.3:
                fade *= smoothstep(top - h * 0.4, top + h * 0.3, y)
            if fade <= 0.01:
                continue
            col.setAlphaF(col.alphaF() * fade)
            s = 0.9 + 0.1 * a
            ax = W / 2 if self.align_center else self.PAD
            p.save()
            p.translate(ax, y)
            p.scale(s, s)
            rect = QRectF(-tw / 2 if self.align_center else 0, -h / 2, tw, h)
            if ln == GAP:
                self.draw_gap(p, rect, col, i, now_t, a)
            else:
                sh = QColor(0, 0, 0)
                sh.setAlphaF(min(1.0, col.alphaF() * shadow_strength))
                p.setPen(sh)
                p.drawText(rect.translated(0, 2), flags, ln)
                p.setPen(col)
                p.drawText(rect, flags, ln)
            p.restore()

    def draw_gap(self, p, rect, col, i, now_t, a):
        r = self.font_px * 0.17
        n = 3
        gapw = r * 3.2
        total = gapw * (n - 1)
        x0 = rect.center().x() - total / 2 if self.align_center else rect.left() + r
        cy = rect.center().y()
        if i == self.idx and i + 1 < len(self.times):
            dur = max(0.5, self.times[i + 1] - self.times[i])
            prog = max(0.0, min(1.0, (now_t - self.times[i]) / dur))
        else:
            prog = 0.0
        breathe = 1 + 0.12 * a * math.sin(time.monotonic() * 4.0)
        p.setPen(Qt.NoPen)
        for k in range(n):
            lit = max(0.0, min(1.0, prog * n - k))
            c = QColor(col)
            c.setAlphaF(col.alphaF() * (0.35 + 0.65 * lit) if a > 0.05 else col.alphaF() * 0.6)
            p.setBrush(c)
            rr = r * breathe
            p.drawEllipse(QRectF(x0 + k * gapw - rr, cy - rr, rr * 2, rr * 2))

    # ---------------------------------------------------------------- fare
    def in_grip(self, pos):
        return pos.x() > self.width() - self.GRIP and pos.y() > self.height() - self.GRIP

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.in_grip(e.position().toPoint()):
                self.resizing = (e.globalPosition().toPoint(), self.size())
            else:
                self.drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        gp = e.globalPosition().toPoint()
        if self.resizing:
            start, size = self.resizing
            d = gp - start
            self.resize(max(self.minimumWidth(), size.width() + d.x()), max(self.minimumHeight(), size.height() + d.y()))
            self.layout_dirty = True
        elif self.drag_off is not None:
            self.move(gp - self.drag_off)
        else:
            self.setCursor(Qt.SizeFDiagCursor if self.in_grip(e.position().toPoint()) else Qt.SizeAllCursor)

    def mouseReleaseEvent(self, e):
        if self.drag_off is not None or self.resizing:
            self.drag_off = None
            self.resizing = None
            self.save_geometry()

    def enterEvent(self, e):
        self.hover = True

    def leaveEvent(self, e):
        self.hover = False

    def resizeEvent(self, e):
        self.layout_dirty = True

    def wheelEvent(self, e):
        d = 1 if e.angleDelta().y() > 0 else -1
        if e.modifiers() & Qt.ControlModifier:
            self.set_font(self.font_px + d * 2)
        elif e.modifiers() & Qt.ShiftModifier:
            self.set_opacity(self.bg_opacity + d * 0.05)

    def contextMenuEvent(self, e):
        m = QMenu(self)
        self.build_menu(m)
        m.exec(e.globalPos())

    def on_tray(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visible()

    # ---------------------------------------------------------------- ayarlar
    def save(self, k, v):
        self.cfg.setValue(k, v)

    def save_geometry(self):
        g = self.geometry()
        self.save("geometry", [g.x(), g.y(), g.width(), g.height()])

    def set_font(self, px):
        self.font_px = max(12, min(96, px))
        self.save("font_px", self.font_px)
        self.layout_dirty = True

    def set_opacity(self, v):
        self.bg_opacity = max(0.0, min(1.0, v))
        self.save("bg_opacity", self.bg_opacity)

    def set_offset(self, v):
        self.offset = round(v, 2)
        self.save("offset", self.offset)

    def apply_lock(self, on, save=True):
        self.locked = on
        if save:
            self.save("locked", "true" if on else "false")
        vis = self.isVisible() or not save
        self.setWindowFlag(Qt.WindowTransparentForInput, on)
        if vis:
            self.show()
            self.keep_on_top()

    def notify(self, text):
        self.tray.showMessage("Spotify Şarkı Sözleri", text, QSystemTrayIcon.Information, 5000)

    def borderless_foreground(self):
        hwnd = user32.GetForegroundWindow()
        if not hwnd or hwnd == int(self.winId()):
            return
        self.notify(toggle_borderless(hwnd))
        self.keep_on_top()

    def borderless_minecraft(self):
        hwnd = find_minecraft()
        if not hwnd:
            self.notify("Minecraft penceresi bulunamadı. Önce Minecraft'ı aç (pencere modunda).")
            return
        self.notify(toggle_borderless(hwnd))
        self.keep_on_top()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.keep_on_top()

    def center_window(self):
        scr = self.screen().availableGeometry()
        self.move(scr.x() + (scr.width() - self.width()) // 2, scr.y() + (scr.height() - self.height()) // 2)
        self.save_geometry()

    def build_menu(self, m):
        m.clear()
        head = QAction(f"♪ {self.title} – {self.artist}" if self.title else "Spotify Şarkı Sözleri", m)
        head.setEnabled(False)
        m.addAction(head)
        m.addSeparator()

        m.addAction("Gizle" if self.isVisible() else "Göster", self.toggle_visible)
        lock = m.addAction("Kilitle (tıklamalar arkaya geçsin)")
        lock.setCheckable(True)
        lock.setChecked(self.locked)
        lock.toggled.connect(self.apply_lock)
        m.addSeparator()

        fs = m.addMenu(f"Yazı boyutu ({self.font_px}px)")
        fs.addAction("Büyüt  (Ctrl + tekerlek)", lambda: self.set_font(self.font_px + 4))
        fs.addAction("Küçült", lambda: self.set_font(self.font_px - 4))
        for v in (20, 26, 32, 40, 52, 64):
            fs.addAction(f"{v}px", lambda v=v: self.set_font(v))

        tm = m.addMenu("Tema")
        g = QActionGroup(tm)
        for name in THEMES:
            a = tm.addAction(name, lambda n=name: (setattr(self, "theme", n), self.save("theme", n)))
            a.setCheckable(True)
            a.setChecked(name == self.theme)
            g.addAction(a)

        om = m.addMenu(f"Arka plan saydamlığı (%{int(round(self.bg_opacity * 100))})")
        for v in (0, 25, 50, 65, 78, 90, 100):
            om.addAction(f"%{v}" + ("  (sadece yazı)" if v == 0 else ""), lambda v=v: self.set_opacity(v / 100))

        al = m.addAction("Ortalı yazı")
        al.setCheckable(True)
        al.setChecked(self.align_center)
        al.toggled.connect(lambda on: (setattr(self, "align_center", on),
                                       self.save("align_center", "true" if on else "false"),
                                       setattr(self, "layout_dirty", True)))
        hd = m.addAction("Şarkı adını göster")
        hd.setCheckable(True)
        hd.setChecked(self.show_header)
        hd.toggled.connect(lambda on: (setattr(self, "show_header", on),
                                       self.save("show_header", "true" if on else "false")))

        sm = m.addMenu(f"Senkron ayarı ({self.offset:+.1f} sn)")
        sm.addAction("Sözler geride kalıyor → 0.3 sn öne al", lambda: self.set_offset(self.offset + 0.3))
        sm.addAction("Sözler önde gidiyor → 0.3 sn geri al", lambda: self.set_offset(self.offset - 0.3))
        sm.addAction("Sıfırla", lambda: self.set_offset(0.0))

        m.addSeparator()
        m.addAction("Minecraft'ı kenarlıksız tam ekran yap / geri al", self.borderless_minecraft)
        m.addAction("Öndeki oyunu kenarlıksız tam ekran yap:  Ctrl+Alt+F").setEnabled(False)
        m.addSeparator()
        m.addAction("Ekranın ortasına getir", self.center_window)
        m.addAction("Bu şarkının sözlerini yeniden ara", self.refetch)
        au = m.addAction("Windows açılışında başlat")
        au.setCheckable(True)
        au.setChecked(autostart_enabled())
        au.toggled.connect(set_autostart)
        m.addSeparator()
        m.addAction("Çıkış", self.quit)

    def refetch(self):
        if self.track_key:
            path = os.path.join(CACHE_DIR, hashlib.md5(self.track_key.encode("utf-8")).hexdigest() + ".json")
            if os.path.exists(path):
                os.remove(path)
            self.set_lines([], [])
            self.message = "Sözler yükleniyor…"
            self.fetcher.fetch(self.track_key, self.title, self.artist, "", self.duration)

    def quit(self):
        self.save_geometry()
        self.watcher.requestInterruption()
        self.watcher.wait(1500)
        self.hotkey.stop()
        for hwnd in list(_borderless_saved):
            toggle_borderless(hwnd)  # çıkarken oyun pencerelerini eski haline getir
        self.tray.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(os.path.join(QDir.tempPath(), APP_NAME + ".lock"))
    if not lock.tryLock(100):
        return  # zaten çalışıyor
    w = LyricsOverlay()
    w.show()
    w.keep_on_top()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
