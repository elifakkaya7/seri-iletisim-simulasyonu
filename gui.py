"""Simülasyonun ayarlarını değiştirip sonucu görmek için arayüz.

Çalıştırmak için: python gui.py  (tkinter Python ile birlikte gelir, ek kurulum yok)
Her şey tek pencerede, kaydırmadan görünür.
"""

import math
import struct
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from main import (BAUD_RATE, BIT_FLIP_PROB, LATENCY, LOSS_PROB, PACKET_COUNT,
                  SEED, SEND_INTERVAL, simulate)
from serisim.channel import VirtualChannel
from serisim.checksum import calculate
from serisim import packet as pkt
from serisim.packet import PACKET_SIZE, PAYLOAD_SIZE

# ---------- görünüm ----------
FONT = "Segoe UI"
MONO = "Consolas"
RADIUS = 12          # kartların köşe yuvarlaklığı
INSET = 5            # kart içeriğinin yuvarlak kenardan uzaklığı

THEMES = {
    "dark": {        # lacivert-gri
        "bg": "#10151d", "card": "#18202b", "border": "#283243", "row_alt": "#1d2633",
        "text": "#e6e9ef", "muted": "#8a94a6", "accent": "#6d8cf5", "accent_dark": "#5b79e0",
        "trough": "#2c3646", "knob_ring": "#18202b",
        "selected": "#2a3547", "ok": "#3a4556",
        "field_head": "#6d8cf5", "field_payload": "#5d6879",
        "button": "#1d2633", "button_hover": "#253041",
    },
    "light": {       # nötr açık gri / beyaz
        "bg": "#f2f4f7", "card": "#ffffff", "border": "#e2e6ec", "row_alt": "#f6f8fa",
        "text": "#1d2430", "muted": "#768194", "accent": "#4f6fe8", "accent_dark": "#3f5dd3",
        "trough": "#e1e5ec", "knob_ring": "#ffffff",
        "selected": "#e6ebf5", "ok": "#d9dee6",
        "field_head": "#4f6fe8", "field_payload": "#a9b2c0",
        "button": "#ffffff", "button_hover": "#f1f3f7",
    },
}
COLORS = dict(THEMES["dark"])

# Paketin başına gelene göre renk ve etiket (şeritte, çubukta ve tabloda aynı)
STATUS = {
    "ok":       (COLORS["ok"], "Sağlam"),
    "checksum": ("#f0a53c", "Checksum attı"),
    "range":    ("#c88a52", "Aralık kontrolü attı"),
    "missed":   ("#6d8cf5", "Fark edilmedi"),
    "lost":     ("#f06c6c", "Kayboldu"),
}
VERDICT_TO_STATUS = {
    "sağlam": "ok", "ATILDI (checksum)": "checksum", "ATILDI (aralık)": "range",
    "FARK EDİLMEDİ": "missed", "-": "lost",
}
# Paket alanları: (ad, ilk bayt, son bayt dahil, renk anahtarı)
FIELDS = [
    ("START", 0, 0, "field_head"),
    ("SEQ", 1, 1, "field_head"),
    ("LEN", 2, 2, "field_head"),
    ("PAYLOAD", 3, PACKET_SIZE - 2, "field_payload"),
    ("CHECKSUM", PACKET_SIZE - 1, PACKET_SIZE - 1, "field_head"),
]
# Hazır ayarlar: (düğme yazısı, baud, gecikme ms, kayıp %, bit flip)
PRESETS = [
    ("Gürültüsüz", BAUD_RATE, LATENCY * 1000, 0, 0),
    ("Kötü hat", 9600, 300, 20, 0.001),
]

BAUD_OPTIONS = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
BIT_FLIP_OPTIONS = [0, 0.00005, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005,
                    0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1]
STRIP_MAX = 1000     # şeritte gösterilecek en fazla paket
STRIP_MAX_HEIGHT = 110   # pencere küçükse kendiliğinden azalır
TABLE_MAX = 2000     # tabloda gösterilecek en fazla paket
BYTE_COLS = 12       # paket içi panelinde bir satırdaki bayt sayısı
SPLIT_MIN = 1200     # alt bölüm bu kadar genişse Baytlar ve Değerler yan yana gösterilir
BYTE_W, BYTE_H = 30, 18


def enable_sharp_text():
    """Windows'ta yüksek çözünürlüklü ekranlarda yazıların bulanık çıkmasını önler."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def blend(color_a, color_b, t):
    """İki rengi karıştırır (t=0 -> a, t=1 -> b). Saydamlık yerine kullanılır."""
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def field_of(index):
    for name, start, end, key in FIELDS:
        if start <= index <= end:
            return name, COLORS[key]
    return "", COLORS["muted"]


# Paketteki alanların arayüzde görünen kısa adları (Haberleşme Dokümanı sırasıyla)
VALUE_LABELS = [
    ("takim_numarasi", "Takım"), ("iha_enlem", "Enlem"), ("iha_boylam", "Boylam"),
    ("iha_irtifa", "İrtifa"), ("iha_dikilme", "Dikilme"), ("iha_yonelme", "Yönelme"),
    ("iha_yatis", "Yatış"), ("iha_hiz", "Hız"), ("iha_batarya", "Batarya"),
    ("iha_otonom", "Otonom"), ("iha_kilitlenme", "Kilitlenme"),
    ("hedef_merkez_X", "Hedef X"), ("hedef_merkez_Y", "Hedef Y"),
    ("hedef_genislik", "Genişlik"), ("hedef_yukseklik", "Yükseklik"),
]


def format_value(name, value):
    """Bir telemetri değerini kısa ve okunur bir yazıya çevirir."""
    if isinstance(value, float):
        if not math.isfinite(value) or abs(value) >= 1e7:
            return f"{value:.3g}"
        return f"{value:.6f}" if name in ("iha_enlem", "iha_boylam") else f"{value:.2f}"
    return str(value)


def payload_texts(raw):
    """Paketteki 53 baytlık veriyi çözüp yazı listesi döndürür.

    Checksum'a bakmaz: bozulmuş paketin bile içinde ne yazdığını gösterebilmek için.
    """
    values = struct.unpack(pkt.TELEMETRY_FORMAT, raw[3:-1])
    count = len(pkt.FIELDS)
    data = dict(zip(pkt.FIELDS, values[:count]))
    h, m, sec, ms = values[count:]
    texts = [format_value(key, data[key]) for key, _ in VALUE_LABELS]
    texts.append(f"{h:02d}:{m:02d}:{sec:02d}.{ms:03d}")
    return texts


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Canvas üzerine köşeleri yuvarlatılmış dikdörtgen çizer."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kw)


def mask_corners(canvas, w, h, r, color):
    """Dikdörtgenin köşelerini arka plan rengiyle örterek yuvarlak gösterir."""
    steps = 10
    for cx, cy, sx, sy in [(r, r, -1, -1), (w - r, r, 1, -1), (r, h - r, -1, 1), (w - r, h - r, 1, 1)]:
        corner = (cx + sx * r, cy + sy * r)
        arc = [(cx + sx * r * math.cos(math.pi / 2 * k / steps),
                cy + sy * r * math.sin(math.pi / 2 * k / steps)) for k in range(steps + 1)]
        canvas.create_polygon([corner, *arc], fill=color, outline=color)


# ---------- yuvarlak köşeli bileşenler ----------

class RoundPanel(tk.Canvas):
    """Yuvarlak köşeli kutu. İçerik self.inner çerçevesine konur.

    expand=False: yükseklik içeriğe göre ayarlanır.
    expand=True : kutu kendisine verilen alanı doldurur, içerik de onunla büyür.
    """

    def __init__(self, parent, expand=False, border=None, **kw):
        super().__init__(parent, bg=COLORS["bg"], highlightthickness=0, bd=0, height=20, **kw)
        self.expand = expand
        self.border = border or COLORS["border"]
        self.inner = tk.Frame(self, bg=COLORS["card"])
        self._window = self.create_window(INSET, INSET, anchor="nw", window=self.inner)
        self.bind("<Configure>", self._redraw)
        if not expand:
            self.inner.bind("<Configure>", self._fit_height, add="+")

    def _fit_height(self, _event=None):
        wanted = self.inner.winfo_reqheight() + 2 * INSET
        if int(self.cget("height")) != wanted:
            self.config(height=wanted)

    def _redraw(self, _event=None):
        w, h = self.winfo_width(), self.winfo_height()
        self.delete("shape")
        rounded_rect(self, 1, 1, w - 1, h - 1, RADIUS, fill=COLORS["card"],
                     outline=self.border, width=1, tags="shape")
        self.tag_lower("shape")
        self.itemconfig(self._window, width=max(1, w - 2 * INSET))
        if self.expand:
            self.itemconfig(self._window, height=max(1, h - 2 * INSET))

    def set_border(self, color):
        self.border = color
        self._redraw()


class RoundButton(tk.Canvas):
    """Yuvarlak köşeli, kenarlıklı düğme."""

    def __init__(self, parent, text, command, height=32, width=None, bg=None, font_size=9):
        super().__init__(parent, bg=bg or COLORS["card"], highlightthickness=0, bd=0,
                         height=height, cursor="hand2", **({"width": width} if width else {}))
        self.text, self.command, self.font_size = text, command, font_size
        self.hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self.command())

    def _set_hover(self, value):
        self.hover = value
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        fill = COLORS["button_hover"] if self.hover else COLORS["button"]
        rounded_rect(self, 1, 1, w - 1, h - 1, 8, fill=fill, outline=COLORS["border"])
        self.create_text(w / 2, h / 2, text=self.text, fill=COLORS["text"],
                         font=(FONT, self.font_size))


class Card(RoundPanel):
    """Başlığı ve isteğe bağlı yönerge etiketi (5.1 gibi) olan yuvarlak kutu."""

    def __init__(self, parent, title, tag=None, expand=False, **kw):
        super().__init__(parent, expand=expand, **kw)
        self.head = tk.Frame(self.inner, bg=COLORS["card"])
        self.head.pack(fill="x", padx=11, pady=(8, 4))
        self.title_label = tk.Label(self.head, text=title, bg=COLORS["card"], fg=COLORS["text"],
                                    font=(FONT, 10, "bold"))
        self.title_label.pack(side="left")
        if tag:
            tk.Label(self.head, text=tag, bg=COLORS["card"], fg=COLORS["muted"],
                     font=(FONT, 8)).pack(side="right")
        self.body = tk.Frame(self.inner, bg=COLORS["card"])
        self.body.pack(fill="both", expand=True, padx=11, pady=(0, 9))


class Slider:
    """Etiket + değer + yuvarlak kaydırıcı. values verilirse yalnızca o değerlere oturur."""

    PAD = 8

    def __init__(self, parent, label, from_=0, to=1, step=1, values=None,
                 fmt=str, on_release=None, on_move=None):
        self.values, self.step, self.fmt = values, step, fmt
        self.on_release, self.on_move = on_release, on_move
        self.lo, self.hi = (0, len(values) - 1) if values is not None else (from_, to)
        self.pos = self.lo

        row = tk.Frame(parent, bg=COLORS["card"])
        row.pack(fill="x", pady=(6, 0))
        tk.Label(row, text=label, bg=COLORS["card"], fg=COLORS["muted"],
                 font=(FONT, 9)).pack(side="left")
        self.value_label = tk.Label(row, bg=COLORS["card"], fg=COLORS["text"],
                                    font=(FONT, 9, "bold"))
        self.value_label.pack(side="right")

        self.canvas = tk.Canvas(parent, height=20, bg=COLORS["card"], highlightthickness=0,
                                cursor="hand2")
        self.canvas.pack(fill="x")
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Button-1>", self._drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.on_release and self.on_release())

    def _snap(self, raw):
        if self.values is not None:
            return min(self.hi, max(self.lo, round(raw)))
        return min(self.hi, max(self.lo, round(raw / self.step) * self.step))

    def _drag(self, event):
        width = self.canvas.winfo_width() - 2 * self.PAD
        frac = min(1, max(0, (event.x - self.PAD) / max(1, width)))
        new = self._snap(self.lo + frac * (self.hi - self.lo))
        if new != self.pos:
            self.pos = new
            self._changed()

    def _changed(self):
        self.value_label.config(text=self.fmt(self.get()))
        self._draw()
        if self.on_move:
            self.on_move()

    def _draw(self):
        c = self.canvas
        c.delete("all")
        w, y = c.winfo_width(), 10
        left, right = self.PAD, w - self.PAD
        frac = (self.pos - self.lo) / (self.hi - self.lo) if self.hi > self.lo else 0
        x = left + frac * (right - left)
        rounded_rect(c, left, y - 3, right, y + 3, 3, fill=COLORS["trough"], outline="")
        if x > left + 2:
            rounded_rect(c, left, y - 3, x, y + 3, 3, fill=COLORS["accent"], outline="")
        c.create_oval(x - 7, y - 7, x + 7, y + 7, fill=COLORS["accent"],
                      outline=COLORS["knob_ring"], width=2)

    def get(self):
        if self.values is not None:
            return self.values[int(self.pos)]
        return self.pos

    def set(self, value):
        self.pos = self._snap(self.values.index(value) if self.values is not None else value)
        self._changed()


class StatCard(RoundPanel):
    """Büyük sayı gösteren yuvarlak sonuç kutusu."""

    def __init__(self, parent, title, tag):
        super().__init__(parent)
        inner = tk.Frame(self.inner, bg=COLORS["card"])
        inner.pack(fill="both", expand=True, padx=11, pady=(6, 7))
        top = tk.Frame(inner, bg=COLORS["card"])
        top.pack(fill="x")
        tk.Label(top, text=title, bg=COLORS["card"], fg=COLORS["muted"],
                 font=(FONT, 9)).pack(side="left")
        tk.Label(top, text=tag, bg=COLORS["card"], fg=COLORS["muted"],
                 font=(FONT, 8)).pack(side="right")
        self.value = tk.Label(inner, text="-", bg=COLORS["card"], fg=COLORS["text"],
                              font=(FONT, 18, "bold"))
        self.value.pack(anchor="w")
        self.sub = tk.Label(inner, text="", bg=COLORS["card"], fg=COLORS["muted"],
                            font=(FONT, 8), justify="left", anchor="w")
        self.sub.pack(fill="x")
        self.inner.bind("<Configure>", lambda e: self.sub.config(
            wraplength=max(80, e.width - 26)), add="+")

    def update_values(self, value, sub="", alert=False):
        self.value.config(text=value, fg=STATUS["lost"][0] if alert else COLORS["text"])
        self.sub.config(text=sub)
        self.set_border(STATUS["lost"][0] if alert else COLORS["border"])


class CheckBox(tk.Canvas):
    """Tıklanabilir olduğu belli olan onay kutusu: belirgin kenarlıklı kutu, işaretlenince dolar."""

    def __init__(self, parent, text, variable, command=None):
        self.font = tkfont.Font(family=FONT, size=9)
        self.size = self.font.metrics("linespace") - 2
        width = self.size + 8 + self.font.measure(text) + 4
        super().__init__(parent, width=width, height=self.size + 6, bg=COLORS["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.text, self.variable, self.command = text, variable, command
        self.hover = False
        variable.trace_add("write", lambda *args: self._draw())
        self.bind("<Button-1>", self._toggle)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._draw()

    def _set_hover(self, value):
        self.hover = value
        self._draw()

    def _toggle(self, _event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        s, top = self.size, 3
        checked = self.variable.get()
        rounded_rect(self, 2, top, 2 + s, top + s, 5,
                     fill=COLORS["text"] if checked else COLORS["row_alt"],
                     outline=COLORS["text"] if (checked or self.hover) else COLORS["muted"],
                     width=2)
        if checked:
            self.create_line(2 + s * 0.25, top + s * 0.55, 2 + s * 0.43, top + s * 0.73,
                             2 + s * 0.78, top + s * 0.30, fill=COLORS["card"], width=2,
                             capstyle="round", joinstyle="round")
        self.create_text(s + 10, top + s / 2, text=self.text, anchor="w",
                         fill=COLORS["text"], font=self.font)


class PacketList(tk.Frame):
    """Alıcının kararlarını gösteren modern liste.

    Treeview yerine tuvalde çizilir: yuvarlak seçim, durum etiketleri (hap), ince kaydırma
    çubuğu. Yalnızca görünen satırlar çizildiği için binlerce satırda da akıcıdır.
    """

    ROW_H = 30
    HEADER_H = 28
    COLUMNS = [("Paket", 14), ("SEQ", 66), ("Kanalda", 112), ("Alıcının kararı", 214),
               ("Not", 392)]

    def __init__(self, parent, on_select):
        super().__init__(parent, bg=COLORS["card"])
        self.on_select = on_select
        self.font = tkfont.Font(family=FONT, size=9)
        self.font_small = tkfont.Font(family=FONT, size=8)
        self.font_chip = tkfont.Font(family=FONT, size=8, weight="bold")
        self.rows, self.index = [], {}
        self.offset, self.selected, self.hover = 0, None, None

        self.header = tk.Canvas(self, height=self.HEADER_H, bg=COLORS["card"],
                                highlightthickness=0)
        self.header.pack(fill="x")
        body = tk.Frame(self, bg=COLORS["card"])
        body.pack(fill="both", expand=True)
        self.bar = tk.Canvas(body, width=10, bg=COLORS["card"], highlightthickness=0)
        self.bar.pack(side="right", fill="y")
        self.canvas = tk.Canvas(body, height=60, bg=COLORS["card"], highlightthickness=0,
                                takefocus=1)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.header.bind("<Configure>", lambda e: self._draw_header())
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.canvas.bind("<Motion>", self._moved)
        self.canvas.bind("<Leave>", lambda e: self._set_hover(None))
        self.canvas.bind("<Button-1>", self._clicked)
        self.canvas.bind("<Up>", lambda e: self._step(-1))
        self.canvas.bind("<Down>", lambda e: self._step(1))
        for widget in (self.canvas, self.bar):
            widget.bind("<MouseWheel>", lambda e: self._scroll(-e.delta / 120 * 3))
            widget.bind("<Button-4>", lambda e: self._scroll(-3))
            widget.bind("<Button-5>", lambda e: self._scroll(3))
        self.bar.bind("<Button-1>", self._bar_drag)
        self.bar.bind("<B1-Motion>", self._bar_drag)

    # ----- veri -----
    def set_rows(self, rows):
        """rows: (paket no, seq, kanalda yazısı, durum anahtarı, not)"""
        self.rows = rows
        self.index = {row[0]: i for i, row in enumerate(rows)}
        self.offset = min(self.offset, self._max_offset())
        self._redraw()

    def set_selected(self, no, see=True):
        self.selected = no
        if see and no in self.index:
            self._ensure_visible(self.index[no])
        self._redraw()

    # ----- kaydırma -----
    def _view_h(self):
        return max(1, self.canvas.winfo_height())

    def _max_offset(self):
        return max(0, len(self.rows) * self.ROW_H - self._view_h())

    def _ensure_visible(self, i):
        top = i * self.ROW_H
        if top < self.offset:
            self.offset = top
        elif top + self.ROW_H > self.offset + self._view_h():
            self.offset = top + self.ROW_H - self._view_h()
        self.offset = min(max(0, self.offset), self._max_offset())

    def _scroll(self, rows):
        new = min(max(0, self.offset + rows * self.ROW_H), self._max_offset())
        if new != self.offset:
            self.offset = new
            self._redraw()

    def _bar_drag(self, event):
        height = max(1, self.bar.winfo_height())
        total = len(self.rows) * self.ROW_H
        if total <= self._view_h():
            return
        thumb = max(28, height * self._view_h() / total)
        frac = min(1, max(0, (event.y - thumb / 2) / max(1, height - thumb)))
        self.offset = int(frac * self._max_offset())
        self._redraw()

    # ----- etkileşim -----
    def _row_at(self, y):
        i = int((self.offset + y) // self.ROW_H)
        return i if 0 <= i < len(self.rows) else None

    def _moved(self, event):
        self._set_hover(self._row_at(event.y))

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self._redraw()

    def _clicked(self, event):
        self.canvas.focus_set()
        i = self._row_at(event.y)
        if i is not None:
            self._choose(i)

    def _step(self, delta):
        if not self.rows:
            return
        i = self.index.get(self.selected, -1 if delta > 0 else len(self.rows)) + delta
        self._choose(min(max(0, i), len(self.rows) - 1))

    def _choose(self, i):
        no = self.rows[i][0]
        self.set_selected(no)
        self.on_select(no)

    # ----- çizim -----
    def _fit(self, text, width, font):
        if width <= 8 or font.measure(text) <= width:
            return text if width > 8 else ""
        while text and font.measure(text + "…") > width:
            text = text[:-1]
        return text + "…"

    def _draw_header(self):
        c = self.header
        c.delete("all")
        w = c.winfo_width()
        for title, x in self.COLUMNS:
            c.create_text(x, self.HEADER_H / 2, text=title, anchor="w", fill=COLORS["muted"],
                          font=self.font_chip)
        c.create_line(0, self.HEADER_H - 1, w, self.HEADER_H - 1, fill=COLORS["border"])

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 50)
        first = int(self.offset // self.ROW_H)
        last = min(len(self.rows), int((self.offset + self._view_h()) // self.ROW_H) + 1)
        for i in range(first, last):
            self._draw_row(i, i * self.ROW_H - self.offset, w)
        self._draw_bar()

    def _draw_row(self, i, y, w):
        no, seq, channel, status, note = self.rows[i]
        h, cy = self.ROW_H, y + self.ROW_H / 2
        if no == self.selected:
            rounded_rect(c := self.canvas, 2, y + 2, w - 2, y + h - 2, 9,
                         fill=COLORS["selected"], outline=COLORS["border"])
        elif i == self.hover:
            rounded_rect(self.canvas, 2, y + 2, w - 2, y + h - 2, 9,
                         fill=COLORS["row_alt"], outline="")
        c = self.canvas
        x = [col[1] for col in self.COLUMNS]
        color = STATUS[status][0]
        c.create_text(x[0], cy, text=str(no), anchor="w", fill=COLORS["text"], font=self.font)
        c.create_text(x[1], cy, text=str(seq), anchor="w", fill=COLORS["muted"], font=self.font)
        channel_color = COLORS["muted"] if channel == "geldi" else color
        c.create_text(x[2], cy, text=channel, anchor="w", fill=channel_color, font=self.font)

        # durum etiketi: renkli nokta + yazı, yumuşak zeminli hap
        label = STATUS[status][1]
        chip_w = self.font_chip.measure(label) + 26
        fill = blend(COLORS["card"], color, 0.16 if status != "ok" else 0.45)
        rounded_rect(c, x[3], cy - 10, x[3] + chip_w, cy + 10, 10, fill=fill, outline="")
        c.create_oval(x[3] + 8, cy - 3, x[3] + 14, cy + 3, fill=color, outline="")
        c.create_text(x[3] + 20, cy, text=label, anchor="w",
                      fill=COLORS["text"] if status == "ok" else color, font=self.font_chip)

        if note:
            room = w - x[4] - 14
            c.create_text(x[4], cy, text=self._fit(note, room, self.font_small), anchor="w",
                          fill=COLORS["muted"], font=self.font_small)

    def _draw_bar(self):
        b = self.bar
        b.delete("all")
        height = max(1, b.winfo_height())
        total = len(self.rows) * self.ROW_H
        view = self._view_h()
        if total <= view:
            return
        thumb = max(28, height * view / total)
        y = (height - thumb) * self.offset / max(1, total - view)
        rounded_rect(b, 3, y, 8, y + thumb, 2, fill=blend(COLORS["card"], COLORS["muted"], 0.5),
                     outline="")


class SegmentedTabs(tk.Canvas):
    """Yuvarlak, iki seçenekli geçiş düğmesi. Seçili olan dolu renkle öne çıkar."""

    def __init__(self, parent, options, command, width=176, height=28):
        super().__init__(parent, width=width, height=height, bg=COLORS["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.options, self.command = options, command
        self.active, self.hover = options[0][0], None
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Motion>", self._moved)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<Button-1>", self._clicked)

    def _segment_at(self, x):
        width = max(1, self.winfo_width())
        index = min(len(self.options) - 1, max(0, int(x * len(self.options) / width)))
        return self.options[index][0]

    def _moved(self, event):
        self._set_hover(self._segment_at(event.x))

    def _set_hover(self, key):
        if key != self.hover:
            self.hover = key
            self._draw()

    def _clicked(self, event):
        key = self._segment_at(event.x)
        if key != self.active:
            self.command(key)

    def select(self, key):
        self.active = key
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = max(self.winfo_width(), 20), max(self.winfo_height(), 10)
        rounded_rect(self, 1, 1, w - 1, h - 1, h / 2, fill=COLORS["row_alt"],
                     outline=COLORS["border"])
        seg = w / len(self.options)
        for k, (key, text) in enumerate(self.options):
            x0 = k * seg
            if key == self.active:
                rounded_rect(self, x0 + 3, 3, x0 + seg - 3, h - 3, (h - 6) / 2,
                             fill=COLORS["selected"], outline=COLORS["muted"])
                color, weight = COLORS["text"], "bold"
            else:
                color = COLORS["text"] if key == self.hover else COLORS["muted"]
                weight = "normal"
            self.create_text(x0 + seg / 2, h / 2, text=text, fill=color,
                             font=(FONT, 9, weight))


# ---------- ana pencere ----------

class SimulationApp:
    def __init__(self, root: tk.Tk, theme="dark"):
        self.root = root
        self.theme = theme
        self.trace = []
        self.result = None
        self.settings = None
        self.selected = None
        self._pending = None
        self.view_mode = "bytes"

        root.title("Seri İletişim Simülasyonu")
        # pencere ekrana sığsın (tek sayfa, kaydırma yok)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        width, height = min(1320, sw - 40), min(860, sh - 90)
        root.geometry(f"{width}x{height}+{max(0, (sw - width) // 2)}+10")
        root.minsize(1100, 700)

        self.build()
        self.reset_defaults()
        self.run()

    # ---------- kurulum ----------

    def build(self):
        COLORS.clear()
        COLORS.update(THEMES[self.theme])
        STATUS["ok"] = (COLORS["ok"], "Sağlam")
        self.root.configure(bg=COLORS["bg"])
        self._setup_style()

        self.container = tk.Frame(self.root, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True, padx=18, pady=(12, 14))
        self._build_header(self.container)
        body = tk.Frame(self.container, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, pady=(10, 0))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_main(body)

    def toggle_theme(self):
        """Temayı değiştirir: ayarları saklar, arayüzü yeni renklerle yeniden kurar."""
        saved = {
            "baud": self.baud.get(), "latency": self.latency.get(), "loss": self.loss.get(),
            "flip": self.flip.get(), "count": self.count.get(), "seed": self.seed.get(),
            "random": self.random_seed.get(), "problems": self.only_problems.get(),
        }
        self.theme = "light" if self.theme == "dark" else "dark"
        self.container.destroy()
        self.build()
        self.baud.set(saved["baud"])
        self.latency.set(saved["latency"])
        self.loss.set(saved["loss"])
        self.flip.set(saved["flip"])
        self.count.set(saved["count"])
        self.seed.set(saved["seed"])
        self.random_seed.set(saved["random"])
        self.only_problems.set(saved["problems"])
        self.seed_entry.config(state="disabled" if saved["random"] else "normal")
        self.root.update_idletasks()
        self.render()

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TCheckbutton", background=COLORS["card"],
                        foreground=COLORS["text"], font=(FONT, 9),
                        indicatorbackground=COLORS["row_alt"], indicatorforeground=COLORS["accent"],
                        upperbordercolor=COLORS["border"], lowerbordercolor=COLORS["border"])
        style.map("App.TCheckbutton", background=[("active", COLORS["card"])],
                  indicatorbackground=[("selected", COLORS["row_alt"])])
        style.configure("Vertical.TScrollbar", background=COLORS["border"],
                        troughcolor=COLORS["card"], bordercolor=COLORS["card"],
                        lightcolor=COLORS["border"], darkcolor=COLORS["border"],
                        arrowcolor=COLORS["muted"], gripcount=0)

    # ----- üst satır -----
    def _build_header(self, parent):
        header = tk.Frame(parent, bg=COLORS["bg"])
        header.pack(fill="x")
        titles = tk.Frame(header, bg=COLORS["bg"])
        titles.pack(side="left")
        tk.Label(titles, text="Seri İletişim Bağlantı Simülasyonu", bg=COLORS["bg"],
                 fg=COLORS["text"], font=(FONT, 15, "bold")).pack(anchor="w")
        tk.Label(titles, bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 9),
                 text=f"START, SEQ, LEN, PAYLOAD ({PAYLOAD_SIZE} bayt), CHECKSUM: "
                      f"{PACKET_SIZE} baytlık paket, {1 / SEND_INTERVAL:.0f} Hz gönderim"
                 ).pack(anchor="w")
        RoundButton(header, "Açık tema" if self.theme == "dark" else "Koyu tema",
                    self.toggle_theme, width=96, bg=COLORS["bg"]).pack(side="right")

    # ----- sol: ayarlar -----
    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=COLORS["bg"], width=268)
        side.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        side.grid_propagate(False)
        side.pack_propagate(False)

        rerun = self.schedule_run
        channel = Card(side, "Sanal veri hattı", "5.1")
        channel.pack(fill="x")
        self.baud = Slider(channel.body, "Baud rate", values=BAUD_OPTIONS,
                           fmt=lambda v: f"{v:,}".replace(",", "."), on_release=rerun)
        self.latency = Slider(channel.body, "Gecikme", 0, 1000, 10,
                              fmt=lambda v: f"{v:.0f} ms", on_release=rerun)

        noise = Card(side, "Gürültü ve hata", "5.2")
        noise.pack(fill="x", pady=10)
        self.loss = Slider(noise.body, "Paket kaybı", 0, 100, 0.5,
                           fmt=lambda v: f"%{v:g}  ·  {v / 100:g}".replace(".", ","), on_release=rerun)
        self.flip_hint = None
        self.flip = Slider(noise.body, "Bit flip (bit başına)", values=BIT_FLIP_OPTIONS,
                           fmt=lambda v: f"{v:g}".replace(".", ","), on_release=rerun,
                           on_move=self._update_flip_hint)
        self.flip_hint = tk.Label(noise.body, bg=COLORS["card"], fg=COLORS["muted"],
                                  font=(FONT, 8), justify="left", anchor="w", wraplength=230)
        self.flip_hint.pack(fill="x", pady=(4, 0))

        sim = Card(side, "Simülasyon")
        sim.pack(fill="x")
        self.count = Slider(sim.body, "Paket sayısı", 100, 5000, 100,
                            fmt=lambda v: f"{v:.0f} · {v * SEND_INTERVAL:.0f} s",
                            on_release=rerun)

        seed_row = tk.Frame(sim.body, bg=COLORS["card"])
        seed_row.pack(fill="x", pady=(10, 0))
        tk.Label(seed_row, text="Seed", bg=COLORS["card"], fg=COLORS["muted"],
                 font=(FONT, 9)).pack(side="left")
        self.seed = tk.StringVar()
        self.random_seed = tk.BooleanVar()
        self.seed_entry = tk.Entry(
            seed_row, textvariable=self.seed, width=7, font=(FONT, 10), relief="flat",
            bg=COLORS["row_alt"], fg=COLORS["text"], insertbackground=COLORS["text"],
            disabledbackground=COLORS["card"], disabledforeground=COLORS["muted"],
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"])
        self.seed_entry.pack(side="left", padx=10, ipady=3)
        self.seed_entry.bind("<Return>", lambda e: self.run())
        CheckBox(seed_row, "Rastgele", self.random_seed,
                 self._seed_toggled).pack(side="left")

        # hazır ayarlar: varsayılan + PRESETS
        presets = tk.Frame(sim.body, bg=COLORS["card"])
        presets.pack(fill="x", pady=(10, 0))
        buttons = [("Varsayılan", self.reset_and_run)] + [
            (name, lambda v=values: self.apply_preset(*v)) for name, *values in PRESETS]
        for k, (name, command) in enumerate(buttons):
            presets.columnconfigure(k, weight=1, uniform="presets")
            RoundButton(presets, name, command, width=1, height=30, font_size=8).grid(
                row=0, column=k, sticky="ew", padx=(0 if k == 0 else 5, 0))

    # ----- sağ: sonuçlar -----
    def _build_main(self, parent):
        main = tk.Frame(parent, bg=COLORS["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        cards = tk.Frame(main, bg=COLORS["bg"])
        cards.grid(row=1, column=0, sticky="ew")
        for i in range(4):
            cards.columnconfigure(i, weight=1, uniform="cards")
        self.card_time = StatCard(cards, "Paket süresi", "5.1")
        self.card_valid = StatCard(cards, "Sağlam ulaşan", "5.3")
        self.card_lost = StatCard(cards, "Kaybolan", "5.2")
        self.card_bad = StatCard(cards, "Bozulan", "5.2")
        for i, card in enumerate([self.card_time, self.card_valid, self.card_lost, self.card_bad]):
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))

        # dağılım çubuğu + paket şeridi
        flow = Card(main, "Paketlerin akıbeti", "5.3")
        flow.grid(row=2, column=0, sticky="ew", pady=10)
        self.bar = tk.Canvas(flow.body, height=18, bg=COLORS["card"], highlightthickness=0)
        self.bar.pack(fill="x")
        self.bar.bind("<Configure>", lambda e: self.draw_bar())

        legend = tk.Frame(flow.body, bg=COLORS["card"])
        legend.pack(fill="x", pady=(6, 6))
        self.legend_labels = {}
        for key, (color, name) in STATUS.items():
            item = tk.Frame(legend, bg=COLORS["card"])
            item.pack(side="left", padx=(0, 16))
            dot = tk.Canvas(item, width=10, height=10, bg=COLORS["card"], highlightthickness=0)
            rounded_rect(dot, 0, 0, 10, 10, 3, fill=color, outline=color)
            dot.pack(side="left", padx=(0, 5))
            lbl = tk.Label(item, text=name, bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 9))
            lbl.pack(side="left")
            self.legend_labels[key] = (lbl, name)

        self.strip_title = tk.Label(flow.body, bg=COLORS["card"], fg=COLORS["muted"],
                                    font=(FONT, 8), anchor="w")
        self.strip_title.pack(fill="x")
        self.strip = tk.Canvas(flow.body, height=80, bg=COLORS["card"], highlightthickness=0)
        self.strip.pack(fill="x", pady=(4, 0))
        self.strip.bind("<Configure>", lambda e: self.draw_strip())
        self.strip.bind("<Motion>", self._strip_hover)
        self.strip.bind("<Leave>", lambda e: self._strip_hint())
        self.strip.bind("<Button-1>", self._strip_click)

        # alt: tablo + paketin içi
        bottom = tk.Frame(main, bg=COLORS["bg"])
        bottom.grid(row=3, column=0, sticky="nsew")
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(0, weight=1)
        self._build_table(bottom)
        self._build_inspector(bottom)

    def _build_table(self, parent):
        card = Card(parent, "Alıcının kararları", expand=True)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.only_problems = tk.BooleanVar(value=False)
        CheckBox(card.head, "Sadece sorunlu paketler", self.only_problems,
                 self.fill_table).pack(side="right")

        self.table = PacketList(card.body, self._row_clicked)
        self.table.pack(fill="both", expand=True)

    def _build_inspector(self, parent):
        """Paketin içi: geniş ekranda Baytlar ve Değerler ayrı iki kart, dar ekranda sekmeli tek kart."""
        width = BYTE_COLS * BYTE_W + 2 * 11 + 2 * INSET + 4 + 44   # değerler sığsın diye biraz geniş
        self.bottom = parent
        self.bytes_card = Card(parent, "Paketin içi", "5.3", expand=True, width=width)
        self.values_card = Card(parent, "Paketin içi", "5.3", expand=True, width=width)

        # dar ekranda başlıktaki geçiş düğmesi (geniş ekranda gizlenir)
        self.tabs_list = []
        for card in (self.bytes_card, self.values_card):
            tabs = SegmentedTabs(card.head, [("bytes", "Baytlar"), ("values", "Değerler")],
                                 self.set_view)
            self.tabs_list.append(tabs)

        # --- Baytlar kartı
        body = self.bytes_card.body
        self.inspect_title = tk.Label(body, bg=COLORS["card"], fg=COLORS["text"],
                                      font=(FONT, 9, "bold"), anchor="w", justify="left")
        self.inspect_title.pack(fill="x")
        rows = math.ceil(PACKET_SIZE / BYTE_COLS)
        self.bytes_canvas = tk.Canvas(body, width=BYTE_COLS * BYTE_W, height=rows * BYTE_H,
                                      bg=COLORS["card"], highlightthickness=0)
        self.bytes_canvas.pack(anchor="w", pady=(6, 4))

        legend = tk.Frame(body, bg=COLORS["card"])
        legend.pack(fill="x")
        for name, color in [("Header + CHECKSUM", COLORS["field_head"]),
                            ("PAYLOAD", COLORS["field_payload"]),
                            ("bozulan bayt", STATUS["lost"][0])]:
            dot = tk.Canvas(legend, width=9, height=9, bg=COLORS["card"], highlightthickness=0)
            rounded_rect(dot, 0, 0, 9, 9, 3, fill=color, outline=color)
            dot.pack(side="left", padx=(0, 4))
            tk.Label(legend, text=name, bg=COLORS["card"], fg=COLORS["muted"],
                     font=(FONT, 8)).pack(side="left", padx=(0, 10))

        self.inspect_info = tk.Label(body, bg=COLORS["card"], fg=COLORS["text"],
                                     font=(MONO, 9), anchor="w", justify="left",
                                     wraplength=BYTE_COLS * BYTE_W)
        self.inspect_info.pack(fill="x", pady=(6, 0))

        # --- Değerler kartı: 16 alan, iki sütun. Bozulan alan "gönderilen → gelen" görünür
        vbody = self.values_card.body
        self.values_title = tk.Label(vbody, bg=COLORS["card"], fg=COLORS["text"],
                                     font=(FONT, 9, "bold"), anchor="w", justify="left")
        self.values_title.pack(fill="x")
        grid = tk.Frame(vbody, bg=COLORS["card"])
        grid.pack(fill="x", pady=(6, 0))
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)
        names = [label for _, label in VALUE_LABELS] + ["GPS saati"]
        self.value_labels, self.name_labels = [], []
        for k, name in enumerate(names):
            r, col = k % 8, (k // 8) * 2
            label = tk.Label(grid, text=name, bg=COLORS["card"], fg=COLORS["muted"],
                             font=(FONT, 8), anchor="w", pady=0, bd=0)
            label.grid(row=r, column=col, sticky="w", padx=(0 if col == 0 else 14, 8))
            value = tk.Label(grid, bg=COLORS["card"], fg=COLORS["text"],
                             font=(MONO, 8), anchor="w", pady=0, bd=0)
            value.grid(row=r, column=col + 1, sticky="w")
            self.name_labels.append(label)
            self.value_labels.append(value)
        self.values_note = tk.Label(grid, bg=COLORS["card"], fg=COLORS["muted"],
                                    font=(FONT, 8), anchor="w", justify="left", pady=0, bd=0)
        self.values_note.grid(row=8, column=0, columnspan=4, sticky="w", pady=(4, 0))
        self.values_level = None
        self.values_card.bind("<Configure>", lambda e: self._fit_values_font(), add="+")

        self.split = None
        parent.bind("<Configure>", lambda e: self._layout_bottom())
        self._apply_layout()

    def _fit_values_font(self):
        """Değerler kartında yer varsa yazıları büyütür; yer yoksa küçük tutar."""
        w, h = self.values_card.winfo_width(), self.values_card.winfo_height()
        if w >= 500 and h >= 330:
            level, name_font, value_font, pad = 2, (FONT, 10), (MONO, 11), 3
        elif w >= 420 and h >= 300:
            level, name_font, value_font, pad = 1, (FONT, 9), (MONO, 9), 2
        else:
            level, name_font, value_font, pad = 0, (FONT, 8), (MONO, 8), 0
        if level == self.values_level:
            return
        self.values_level = level
        for label in self.name_labels:
            label.config(font=name_font, pady=pad)
        for label in self.value_labels:
            label.config(font=value_font, pady=pad)
        self.values_note.config(font=(FONT, 9 if level else 8))

    def _layout_bottom(self):
        """Alt bölüm genişliğine göre yan yana (geniş) ya da sekmeli (dar) yerleşimi seçer."""
        split = self.bottom.winfo_width() >= SPLIT_MIN
        if split != self.split:
            self.split = split
            self._apply_layout()

    def _apply_layout(self):
        parent = self.bottom
        self.bytes_card.grid_forget()
        self.values_card.grid_forget()
        for tabs in self.tabs_list:
            tabs.pack_forget()
        if self.split:      # geniş: tablo | Baytlar | Değerler
            parent.columnconfigure(0, weight=3)
            parent.columnconfigure(1, weight=0)
            parent.columnconfigure(2, weight=2)
            self.bytes_card.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
            self.values_card.grid(row=0, column=2, sticky="nsew")
            self.bytes_card.title_label.config(text="Baytlar")
            self.values_card.title_label.config(text="Değerler")
        else:               # dar: tablo | Paketin içi (sekmeli)
            parent.columnconfigure(0, weight=1)
            parent.columnconfigure(1, weight=0)
            parent.columnconfigure(2, weight=0)
            card = self.bytes_card if self.view_mode == "bytes" else self.values_card
            card.grid(row=0, column=1, sticky="nsew")
            for c in (self.bytes_card, self.values_card):
                c.title_label.config(text="Paketin içi")
            for tabs in self.tabs_list:
                tabs.pack(side="right", padx=(0, 8))
        for tabs in self.tabs_list:
            tabs.select(self.view_mode)

    def set_view(self, mode):
        """Dar ekranda Baytlar ya da Değerler sekmesini gösterir."""
        self.view_mode = mode
        for tabs in self.tabs_list:
            tabs.select(mode)
        if not self.split:
            self._apply_layout()

    # ---------- işlemler ----------

    def reset_defaults(self):
        self.baud.set(BAUD_RATE)
        self.latency.set(LATENCY * 1000)
        self.loss.set(LOSS_PROB * 100)
        self.flip.set(BIT_FLIP_PROB)
        self.count.set(PACKET_COUNT)
        self.seed.set(str(SEED))
        self.random_seed.set(False)
        self.seed_entry.config(state="normal")

    def reset_and_run(self):
        self.reset_defaults()
        self.run()

    def apply_preset(self, baud, latency_ms, loss_percent, flip):
        self.baud.set(baud)
        self.latency.set(latency_ms)
        self.loss.set(loss_percent)
        self.flip.set(flip)
        self.run()

    def _seed_toggled(self):
        self.seed_entry.config(state="disabled" if self.random_seed.get() else "normal")
        self.schedule_run()

    def _update_flip_hint(self):
        if self.flip_hint is None:
            return
        p = 1 - (1 - self.flip.get()) ** (PACKET_SIZE * 8)
        self.flip_hint.config(text=f"Paket bozulma "
                                   f"olasılığı ≈ %{100 * p:.1f}".replace(".", ","))

    def schedule_run(self):
        """Kaydırıcı bırakılınca kısa bir beklemeyle yeniden çalıştırır."""
        if not hasattr(self, "table"):
            return
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(120, self.run)

    def read_seed(self):
        if self.random_seed.get():
            return None
        try:
            return int(self.seed.get().strip())
        except ValueError:
            self.seed.set(str(SEED))
            return SEED

    def run(self):
        self._pending = None
        self.settings = {
            "baud_rate": self.baud.get(),
            "latency": self.latency.get() / 1000,
            "loss_prob": self.loss.get() / 100,
            "bit_flip_prob": self.flip.get(),
            "packet_count": int(self.count.get()),
            "seed": self.read_seed(),
        }
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        self.trace = []
        self.result = simulate(trace=self.trace, **self.settings)
        self.root.config(cursor="")
        # açılışta ilk sorunlu paketi göster
        self.selected = next((i for i, row in enumerate(self.trace)
                              if self._status_of(row) != "ok"), 0)
        self.render()

    def render(self):
        self.show_cards()
        self.draw_bar()
        self.draw_strip()
        self.fill_table()
        self.show_packet(self.selected)

    def counts(self) -> dict:
        r = self.result
        return {"ok": r["valid"], "checksum": r["corrupted"], "range": r["out_of_range"],
                "missed": r["missed"], "lost": r["lost"]}

    def show_cards(self):
        r, s = self.result, self.settings
        sent = r["sent"]
        duration = VirtualChannel(s["baud_rate"], s["latency"]).transmission_time(PACKET_SIZE)
        slow = duration > SEND_INTERVAL

        def num(value, digits=1):
            return f"{value:.{digits}f}".replace(".", ",")

        formula = (f"{PACKET_SIZE * 10} bit ÷ {s['baud_rate']:,} baud".replace(",", ".")
                   + f" + {s['latency'] * 1000:.0f} ms")
        if slow:   # paket, gönderim aralığından uzun sürüyor
            formula += f"\n⚠ {SEND_INTERVAL * 1000:.0f} ms'ye sığmıyor, 2 Hz'e yetişemez"
        self.card_time.update_values(f"{num(duration * 1000)} ms", formula, alert=slow)
        self.card_valid.update_values(
            f"%{num(100 * r['valid'] / sent)}", f"{r['valid']} / {sent} paket kullanılabilir")
        self.card_lost.update_values(
            str(r["lost"]), f"Alıcı SEQ ile buldu: {r['seq_lost']}")
        self.card_bad.update_values(
            str(r["flipped"]), f"checksum {r['corrupted']} · aralık {r['out_of_range']} · "
                               f"kaçan {r['missed']}")

        for key, n in self.counts().items():
            lbl, name = self.legend_labels[key]
            lbl.config(text=f"{name}  {n}")

    def draw_bar(self):
        self.bar.delete("all")
        if not self.result:
            return
        width, height = self.bar.winfo_width(), 18
        total = self.result["sent"]
        x = 0
        for key, n in self.counts().items():
            if n == 0:
                continue
            w = width * n / total
            self.bar.create_rectangle(x, 0, x + w, height, fill=STATUS[key][0], width=0)
            if w > 46:
                text_color = COLORS["text"] if key == "ok" else "#ffffff"
                self.bar.create_text(x + w / 2, height / 2,
                                     text=f"%{100 * n / total:.1f}".replace(".", ","),
                                     fill=text_color, font=(FONT, 8, "bold"))
            x += w
        mask_corners(self.bar, width, height, 5, COLORS["card"])

    def _strip_geometry(self):
        """Şeridi genişliğe ve en fazla yüksekliğe sığacak en büyük karelerle böler."""
        n = min(len(self.trace), STRIP_MAX)
        width = max(self.strip.winfo_width(), 100)
        for cell in range(14, 3, -1):
            cols = max(1, (width + 2) // (cell + 2))
            if math.ceil(n / cols) * (cell + 2) <= self._strip_max_height():
                return n, cell, cols
        return n, 4, max(1, (width + 2) // 6)

    def draw_strip(self):
        self.strip.delete("all")
        if not self.trace:
            return
        n, cell, cols = self._strip_geometry()
        rows = math.ceil(n / cols)
        self.strip.config(height=rows * (cell + 2))
        radius = 2 if cell >= 8 else 0
        for i in range(n):
            r, c = divmod(i, cols)
            x, y = c * (cell + 2), r * (cell + 2)
            color = STATUS[self._status_of(self.trace[i])][0]
            rounded_rect(self.strip, x, y, x + cell, y + cell, radius, fill=color, outline=color)
        if self.selected is not None and self.selected < n:
            r, c = divmod(self.selected, cols)
            x, y = c * (cell + 2), r * (cell + 2)
            rounded_rect(self.strip, x - 1, y - 1, x + cell + 1, y + cell + 1, 3,
                         fill="", outline=COLORS["text"], width=2)
        self._strip_hint()

    def _strip_hint(self):
        extra = f" (ilk {STRIP_MAX})" if len(self.trace) > STRIP_MAX else ""
        self.strip_title.config(text=f"Her kare bir paket{extra} · üzerine gel: ayrıntı · "
                                     f"tıkla: paketin içini göster",
                                fg=COLORS["muted"], font=(FONT, 8))

    def _strip_max_height(self):
        """Pencere kısaysa şerit küçülür; böylece her şey tek sayfaya sığar."""
        spare = self.root.winfo_height() - 690
        return max(30, min(STRIP_MAX_HEIGHT, spare))

    def _strip_index(self, event):
        if not self.trace:
            return None
        n, cell, cols = self._strip_geometry()
        c, r = event.x // (cell + 2), event.y // (cell + 2)
        i = r * cols + c
        return i if c < cols and 0 <= i < n else None

    def _strip_hover(self, event):
        i = self._strip_index(event)
        if i is None:
            self._strip_hint()
            return
        no, seq, channel, verdict, note = self.trace[i][:5]
        text = f"Paket {no} · SEQ {seq} · kanalda: {channel} · alıcı: {verdict}"
        if note:
            text += f" · {note}"
        status = self._status_of(self.trace[i])
        self.strip_title.config(text=text, fg=COLORS["text"] if status == "ok"
                                else STATUS[status][0], font=(FONT, 8, "bold"))

    def _strip_click(self, event):
        i = self._strip_index(event)
        if i is None:
            return
        if self.only_problems.get() and self._status_of(self.trace[i]) == "ok" \
                and not self.trace[i][4]:
            self.only_problems.set(False)
            self.fill_table()
        self.select(i)

    def select(self, i):
        self.selected = i
        self.table.set_selected(i)
        self.show_packet(i)
        self.draw_strip()

    def _row_clicked(self, no):
        """Listeden bir satır seçilince paketin içi ve şerit güncellenir."""
        self.selected = no
        self.show_packet(no)
        self.draw_strip()

    @staticmethod
    def _status_of(row):
        return "lost" if row[2] == "KAYBOLDU" else VERDICT_TO_STATUS[row[3]]

    def fill_table(self):
        rows = self.trace
        if self.only_problems.get():
            rows = [row for row in rows if self._status_of(row) != "ok" or row[4]]
        shown = []
        for row in rows[:TABLE_MAX]:
            status = self._status_of(row)
            no, seq, channel, verdict, note = row[:5]
            shown.append((no, seq, "kayboldu" if status == "lost" else channel, status, note))
        self.table.set_rows(shown)
        self.table.set_selected(self.selected)

    def show_packet(self, i):
        """Seçilen paketin 57 baytını alanlarına göre gösterir; bozulan baytları işaretler."""
        c = self.bytes_canvas
        c.delete("all")
        if i is None or i >= len(self.trace):
            return
        no, seq, channel, verdict, note, sent, received = self.trace[i]
        status = self._status_of(self.trace[i])
        shown = received if received is not None else sent
        lost = received is None

        title = f"Paket {no} · SEQ {seq} · {STATUS[status][1].lower()}"
        title_color = COLORS["text"] if status == "ok" else STATUS[status][0]
        self.inspect_title.config(text=title, fg=title_color)
        self.values_title.config(text=title, fg=title_color)

        for b in range(PACKET_SIZE):
            r, col = divmod(b, BYTE_COLS)
            x, y = col * BYTE_W, r * BYTE_H
            _, color = field_of(b)
            flipped = not lost and shown[b] != sent[b]
            fill = blend(COLORS["card"], color, 0.08 if lost else 0.22)
            outline = STATUS["lost"][0] if flipped else blend(COLORS["card"], color, 0.45)
            rounded_rect(c, x + 2, y + 2, x + BYTE_W - 2, y + BYTE_H - 2, 5, fill=fill,
                         outline=outline, width=2 if flipped else 1)
            text_color = STATUS["lost"][0] if flipped else (COLORS["muted"] if lost else COLORS["text"])
            c.create_text(x + BYTE_W / 2, y + BYTE_H / 2, text=f"{shown[b]:02X}",
                          fill=text_color, font=(MONO, 8, "bold" if flipped else "normal"))

        self.show_values(sent, received)

        if lost:
            info = ("Bu paket kanalda kayboldu, alıcıya hiç ulaşmadı.\n"
                    "Alıcı bunu bir sonraki paketin SEQ'inden anlar.")
        else:
            got = shown[-1]
            computed = calculate(shown[1:-1])
            match = "✓ tutuyor" if got == computed else "✕ tutmuyor"
            flips = []
            for b in range(PACKET_SIZE):
                diff = shown[b] ^ sent[b]
                for bit in range(8):
                    if diff & (1 << bit):
                        flips.append(f"bayt {b}/bit {bit}")
            lines = [f"Checksum : {got:02X} geldi, {computed:02X} hesaplandı {match[0]}"]
            if flips:
                head = ", ".join(flips[:2]) + (f" (+{len(flips) - 2})" if len(flips) > 2 else "")
                lines.append(f"Bozulan  : {head}")
                if status == "missed":
                    lines.append("XOR checksum bu bozulmayı yakalayamadı.")
            else:
                lines.append("Bozulan bit yok, paket olduğu gibi geldi.")
            info = "\n".join(lines)
        self.inspect_info.config(text=info)


    def show_values(self, sent, received):
        """Değerler sekmesini doldurur: gönderilen değerler, bozulanlar kırmızı."""
        sent_texts = payload_texts(sent)
        got_texts = payload_texts(received) if received is not None else None
        changed = 0
        for k, label in enumerate(self.value_labels):
            if got_texts is None:                      # paket kayboldu: yalnızca gönderilen
                label.config(text=sent_texts[k], fg=COLORS["muted"])
            elif got_texts[k] != sent_texts[k]:        # bit bozulması bu alanı değiştirdi
                label.config(text=f"{sent_texts[k]} → {got_texts[k]}", fg=STATUS["lost"][0])
                changed += 1
            else:
                label.config(text=sent_texts[k], fg=COLORS["text"])
        if got_texts is None:
            note = "Paket kayboldu; yukarıdakiler gönderilen değerler."
        elif changed:
            note = f"{changed} alan yolda bozuldu (kırmızı: gönderilen → gelen)."
        else:
            note = "Gönderilen ve gelen değerler aynı."
        self.values_note.config(text=note)


if __name__ == "__main__":
    enable_sharp_text()
    root = tk.Tk()
    SimulationApp(root)
    root.mainloop()
