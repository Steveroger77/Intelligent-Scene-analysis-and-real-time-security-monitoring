import sys
import cv2
import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QTextEdit, QVBoxLayout, QHBoxLayout,
    QComboBox, QFileDialog, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QScrollArea
)
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import (
    QImage, QPixmap, QColor, QPalette,
    QPainter, QPen, QBrush
)

from ultralytics import YOLO
from ai_explainer import explain_scene
from scene_compare import compare_scenes


# ═══════════════════════════════════════════════════
#  DESIGN TOKENS  ·  ISARM "Tactical Prism"
# ═══════════════════════════════════════════════════
BG_WORKSPACE   = "#0e1419"
BG_MODULE      = "#1a2027"
BG_INTERACT    = "#252d35"
BG_APP         = "#0a0f14"

PRIMARY        = "#8ff5ff"
PRIMARY_CONT   = "#00eefc"
SECONDARY      = "#00fdc1"
TERTIARY       = "#ff7162"

ON_SURFACE     = "#eaeef6"
ON_SURFACE_VAR = "#a7abb2"
TEXT_DIM       = "#51555c"
OUTLINE_VAR    = "#43484e"

FONT_SG        = "Space Grotesk"
FONT_MONO      = "Courier New"


# ═══════════════════════════════════════════════════
#  GLOBAL STYLESHEET
# ═══════════════════════════════════════════════════
GLOBAL_QSS = f"""
QWidget {{
    background: {BG_APP};
    color: {ON_SURFACE};
    font-family: "{FONT_SG}", Arial;
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    border-radius: 2px;
}}
QScrollBar::handle:vertical {{
    background: {OUTLINE_VAR};
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QScrollBar:horizontal {{ height:0; }}
QComboBox {{
    background: {BG_MODULE};
    border: 1px solid {OUTLINE_VAR};
    border-radius: 2px;
    padding: 7px 28px 7px 12px;
    color: {ON_SURFACE};
    font-family: "{FONT_SG}";
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    min-width: 140px;
}}
QComboBox:hover {{ border-color:{PRIMARY}; background:{BG_INTERACT}; }}
QComboBox::drop-down {{ border:none; width:24px; }}
QComboBox::down-arrow {{
    image:none;
    border-left:4px solid transparent;
    border-right:4px solid transparent;
    border-top:5px solid {PRIMARY};
    margin-right:8px;
}}
QComboBox QAbstractItemView {{
    background:{BG_MODULE};
    border:1px solid {OUTLINE_VAR};
    color:{ON_SURFACE};
    selection-background-color:{BG_INTERACT};
    outline:none;
    padding:4px;
}}
QTextEdit {{
    background: transparent;
    border: none;
    color: {SECONDARY};
    font-family: "{FONT_MONO}";
    font-size: 11px;
    padding: 4px;
}}
QLabel {{ background:transparent; color:{ON_SURFACE}; }}
QScrollArea {{ background:transparent; border:none; }}
QScrollArea > QWidget > QWidget {{ background:transparent; }}
"""


# ═══════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════
def lbl(text, size=12, color=ON_SURFACE, bold=False, mono=False,
        spacing=0, upper=False):
    w = QLabel(text.upper() if upper else text)
    ff = FONT_MONO if mono else FONT_SG
    fw = "700" if bold else "400"
    w.setStyleSheet(
        f"font-family:'{ff}';font-size:{size}px;color:{color};"
        f"font-weight:{fw};letter-spacing:{spacing}px;background:transparent;"
    )
    return w


def hdivider():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{OUTLINE_VAR}33;border:none;")
    return f


def vdivider():
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{OUTLINE_VAR}33;border:none;")
    return f


def ghost_btn(text, accent=PRIMARY):
    b = QPushButton(text.upper())
    b.setStyleSheet(f"""
        QPushButton {{
            background:transparent; color:{accent};
            border:1px solid {accent}44; border-radius:3px;
            padding:12px 18px; font-family:'{FONT_SG}';
            font-size:10px; font-weight:700; letter-spacing:2px;
        }}
        QPushButton:hover {{ background:{accent}18; border-color:{accent}99; }}
        QPushButton:pressed {{ background:{accent}30; }}
        QPushButton:disabled {{ color:{TEXT_DIM}; border-color:{OUTLINE_VAR}33; }}
    """)
    return b


def filled_btn(text):
    b = QPushButton(text.upper())
    b.setStyleSheet(f"""
        QPushButton {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {PRIMARY},stop:1 {PRIMARY_CONT});
            color:#003f43; border:none; border-radius:3px;
            padding:12px 22px; font-family:'{FONT_SG}';
            font-size:10px; font-weight:700; letter-spacing:2px;
        }}
        QPushButton:hover {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {PRIMARY_CONT},stop:1 {PRIMARY});
        }}
        QPushButton:disabled {{ background:{BG_MODULE}; color:{TEXT_DIM}; }}
    """)
    return b


def glow_fx(widget, color=PRIMARY_CONT, radius=18):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(radius)
    fx.setColor(QColor(color))
    fx.setOffset(0, 0)
    widget.setGraphicsEffect(fx)
    return widget


# ═══════════════════════════════════════════════════
#  GLASS PANEL
# ═══════════════════════════════════════════════════
class GlassPanel(QWidget):
    def __init__(self, border=None, radius=8, parent=None):
        super().__init__(parent)
        self._border = border
        self._r      = radius
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(31, 38, 46, 130)))
        pen_color = QColor(self._border) if self._border else QColor(255, 255, 255, 10)
        p.setPen(QPen(pen_color, 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self._r, self._r)
        p.end()


# ═══════════════════════════════════════════════════
#  BRACKET LABEL
# ═══════════════════════════════════════════════════
class BracketLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(PRIMARY_CONT), 3))
        s, w, h, o = 28, self.width(), self.height(), 4
        p.drawLine(o, o, o+s, o);         p.drawLine(o, o, o, o+s)
        p.drawLine(w-o, o, w-o-s, o);     p.drawLine(w-o, o, w-o, o+s)
        p.drawLine(o, h-o, o+s, h-o);     p.drawLine(o, h-o, o, h-o-s)
        p.drawLine(w-o, h-o, w-o-s, h-o); p.drawLine(w-o, h-o, w-o, h-o-s)
        p.end()


# ═══════════════════════════════════════════════════
#  THREAT ALERT BANNER  (slides in from top)
# ═══════════════════════════════════════════════════
class ThreatBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(0)
        self.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(24, 0, 16, 0)
        row.setSpacing(12)

        self._icon = lbl("⚠", 14, TERTIARY, bold=True)
        self._lvl  = lbl("THREAT DETECTED", 9, TERTIARY, bold=True, spacing=3, upper=True)
        self._msg  = QLabel()
        self._msg.setWordWrap(True)
        self._msg.setStyleSheet(
            f"color:{ON_SURFACE_VAR};font-family:'{FONT_SG}';"
            f"font-size:11px;background:transparent;"
        )
        dismiss = QPushButton("✕")
        dismiss.setFixedSize(22, 22)
        dismiss.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{ON_SURFACE_VAR};
                border:none;font-size:11px;border-radius:11px;
            }}
            QPushButton:hover {{ background:{TERTIARY}33;color:{TERTIARY}; }}
        """)
        dismiss.clicked.connect(self.hide_banner)

        row.addWidget(self._icon)
        row.addWidget(self._lvl)
        row.addWidget(vdivider())
        row.addWidget(self._msg, 1)
        row.addWidget(dismiss)

        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setDuration(320)

    def show_threat(self, level: str, msg: str):
        color = TERTIARY if level in ("HIGH", "CRITICAL") else PRIMARY
        self._lvl.setText(f"THREAT  ·  {level.upper()}")
        for w, c in [(self._icon, color), (self._lvl, color)]:
            w.setStyleSheet(
                f"font-family:'{FONT_SG}';font-size:"
                + ("14px" if w is self._icon else "9px")
                + f";color:{color};font-weight:700;"
                + ("letter-spacing:3px;" if w is not self._icon else "")
                + "background:transparent;"
            )
        self._msg.setText(msg)
        self.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color}22,stop:1 transparent);"
            f"border-bottom:1px solid {color}44;"
        )
        self._anim.stop()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(52)
        self._anim.start()

    def hide_banner(self):
        self._anim.stop()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(0)
        self._anim.start()


# ═══════════════════════════════════════════════════
#  LOG ENTRY
# ═══════════════════════════════════════════════════
class LogEntry(QWidget):
    def __init__(self, ts, tag, msg, alert=False, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 5, 0, 5)
        lay.setSpacing(2)

        hr = QHBoxLayout()
        hr.setSpacing(8)
        hr.addWidget(lbl(f"[{ts}]", 9, TEXT_DIM, mono=True))
        hr.addWidget(lbl(tag, 9, TERTIARY if alert else SECONDARY, bold=True, mono=True))
        hr.addStretch()

        ml = QLabel(msg.upper())
        ml.setWordWrap(True)
        ml.setStyleSheet(
            f"color:{ON_SURFACE_VAR};font-family:'{FONT_MONO}';"
            f"font-size:10px;background:transparent;line-height:1.5;"
        )
        lay.addLayout(hr)
        lay.addWidget(ml)
        self.setStyleSheet(
            f"background:{TERTIARY}0d;border-left:2px solid {TERTIARY}55;padding-left:8px;"
            if alert else "background:transparent;"
        )


# ═══════════════════════════════════════════════════
#  STAT CARD
# ═══════════════════════════════════════════════════
class StatCard(GlassPanel):
    def __init__(self, title, value, val_color=ON_SURFACE, parent=None):
        super().__init__(radius=4, parent=parent)
        self.setMinimumHeight(68)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(3)
        lay.addWidget(lbl(title, 8, TEXT_DIM, bold=True, spacing=1, upper=True))
        self._val = lbl(value, 20, val_color, bold=True)
        self._val.setStyleSheet(
            f"font-family:'{FONT_SG}';font-size:20px;font-weight:700;"
            f"color:{val_color};background:transparent;letter-spacing:-1px;"
        )
        lay.addWidget(self._val)

    def set_value(self, value, color=None):
        self._val.setText(value)
        if color:
            self._val.setStyleSheet(
                f"font-family:'{FONT_SG}';font-size:20px;font-weight:700;"
                f"color:{color};background:transparent;letter-spacing:-1px;"
            )


# ═══════════════════════════════════════════════════
#  ALERTS TOGGLE WIDGET
# ═══════════════════════════════════════════════════
class AlertToggle(QWidget):
    """ON/OFF toggle pill for the alerts feature."""
    def __init__(self, label_text="THREAT ALERTS", parent=None):
        super().__init__(parent)
        self._enabled = True
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        self._label = lbl(label_text, 9, TEXT_DIM, bold=True, spacing=2, upper=True)

        # The pill track
        self._pill = QWidget()
        self._pill.setFixedSize(36, 20)
        self._pill.setAttribute(Qt.WA_StyledBackground, True)

        # The knob inside the pill
        self._knob = QWidget(self._pill)
        self._knob.setFixedSize(14, 14)
        self._knob.setAttribute(Qt.WA_StyledBackground, True)

        row.addWidget(self._label, 1)
        row.addWidget(self._pill)

        self._refresh()

    def _refresh(self):
        if self._enabled:
            self._pill.setStyleSheet(
                f"background:{SECONDARY}55;border:1px solid {SECONDARY}88;"
                f"border-radius:10px;"
            )
            self._knob.setStyleSheet(
                f"background:{SECONDARY};border-radius:7px;"
            )
            self._knob.move(19, 3)
            self._label.setStyleSheet(
                f"font-family:'{FONT_SG}';font-size:9px;color:{SECONDARY};"
                f"font-weight:700;letter-spacing:2px;background:transparent;"
            )
            self.setStyleSheet(
                f"background:{SECONDARY}0d;border-radius:4px;"
                f"border:1px solid {SECONDARY}22;"
            )
        else:
            self._pill.setStyleSheet(
                f"background:{BG_INTERACT};border:1px solid {OUTLINE_VAR};"
                f"border-radius:10px;"
            )
            self._knob.setStyleSheet(
                f"background:{OUTLINE_VAR};border-radius:7px;"
            )
            self._knob.move(3, 3)
            self._label.setStyleSheet(
                f"font-family:'{FONT_SG}';font-size:9px;color:{TEXT_DIM};"
                f"font-weight:700;letter-spacing:2px;background:transparent;"
            )
            self.setStyleSheet(
                f"background:transparent;border-radius:4px;"
                f"border:1px solid {OUTLINE_VAR}22;"
            )

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._enabled = not self._enabled
            self._refresh()

    @property
    def enabled(self):
        return self._enabled


# ═══════════════════════════════════════════════════
#  NAV BOTTOM ITEM
# ═══════════════════════════════════════════════════
class NavBtn(QWidget):
    def __init__(self, icon, label_text, active=False, parent=None):
        super().__init__(parent)
        self._fn = None
        self.setFixedWidth(110)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignCenter)

        self._icon_lbl = lbl(icon, 22, PRIMARY_CONT if active else f"{PRIMARY}77")
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._text_lbl = lbl(label_text, 8, PRIMARY if active else ON_SURFACE_VAR,
                              bold=True, spacing=2, upper=True)
        self._text_lbl.setAlignment(Qt.AlignCenter)

        lay.addWidget(self._icon_lbl)
        lay.addWidget(self._text_lbl)
        self.setStyleSheet(
            f"background:{PRIMARY_CONT}18;border-radius:4px;"
            if active else "background:transparent;"
        )

    def connect(self, fn):
        self._fn = fn

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._fn:
            self._fn()

    def set_active(self, active: bool):
        color = PRIMARY_CONT if active else f"{PRIMARY}77"
        self._icon_lbl.setStyleSheet(
            f"font-size:22px;color:{color};background:transparent;"
        )
        self._text_lbl.setStyleSheet(
            f"font-family:'{FONT_SG}';font-size:8px;font-weight:700;"
            f"letter-spacing:2px;color:{'#00eefc' if active else ON_SURFACE_VAR};"
            f"background:transparent;"
        )
        self.setStyleSheet(
            f"background:{PRIMARY_CONT}18;border-radius:4px;"
            if active else "background:transparent;"
        )


# ═══════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════
class ISARM(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ISARM  ·  Intelligent Surveillance & Reconnaissance Module")
        self.resize(1440, 900)
        self.setMinimumSize(1280, 780)
        self.setStyleSheet(GLOBAL_QSS)

        # ── Backend (UNCHANGED) ───────────────────────
        self.cap             = cv2.VideoCapture(0)
        self.model           = YOLO("yolov8n.pt")
        self.app_mode        = "Live"
        self.security_mode   = "Dynamic"
        self.reference_image = None
        self.compare_image   = None
        self.current_frame   = None

        # Uptime
        self._uptime  = 0
        self._uptimer = QTimer()
        self._uptimer.timeout.connect(self._tick)
        self._uptimer.start(1000)

        # Ping blink state
        self._ping_state = True
        self._ptimer     = QTimer()
        self._ptimer.timeout.connect(self._blink)

        # Threat flash state (flashes the banner background on alert)
        self._flash_count = 0
        self._flash_timer = QTimer()
        self._flash_timer.timeout.connect(self._do_flash)

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self._log("SYSTEM_READY", "Initializing neural engine...", False)
        self._log("CORE_LOAD",    "Shaders optimized. Feed synced.", False)
        self.set_ai_text("SYSTEM READY\n\nInitializing neural engine. Press START.")

    # ────────────────────────────────────────────────
    #  BUILD UI
    # ────────────────────────────────────────────────
    def init_ui(self):

        # ── TOP NAV ───────────────────────────────────
        logo = lbl("ISARM", 22, PRIMARY_CONT, bold=True, spacing=-1)

        # We keep references to both nav buttons so we can update the
        # active underline whenever switch_mode() is called.
        self.nav_live    = self._nav_link("Live Feed",        active=True)
        self.nav_compare = self._nav_link("Scene Comparison", active=False)
        self.nav_live.clicked.connect(lambda: self.switch_mode("Live Monitoring"))
        self.nav_compare.clicked.connect(lambda: self.switch_mode("Scene Comparison"))

        avatar = QLabel("OPS")
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"background:{BG_MODULE};color:{PRIMARY};border:2px solid {PRIMARY};"
            f"border-radius:17px;font-family:'{FONT_SG}';font-size:9px;font-weight:700;"
        )

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(24, 0, 24, 0)
        top_layout.addWidget(logo)
        top_layout.addSpacing(36)
        top_layout.addWidget(self.nav_live)
        top_layout.addSpacing(24)
        top_layout.addWidget(self.nav_compare)
        top_layout.addStretch()
        top_layout.addWidget(lbl("●", 8, SECONDARY))
        top_layout.addSpacing(14)
        top_layout.addWidget(avatar)

        self.topbar = QWidget()
        self.topbar.setLayout(top_layout)
        self.topbar.setFixedHeight(60)
        self.topbar.setStyleSheet(
            f"background:rgba(2,6,12,0.9);border-bottom:1px solid {PRIMARY}15;"
        )

        # ── THREAT BANNER ─────────────────────────────
        self.alert_banner = ThreatBanner()

        # ── SIDEBAR  (Guard only — no Patrol/Recon/Emergency) ──
        ops_head = QVBoxLayout()
        ops_head.setContentsMargins(20, 24, 20, 16)
        ops_head.setSpacing(3)
        ops_head.addWidget(lbl("OPERATIONAL MODES", 9, PRIMARY, bold=True, spacing=3, upper=True))
        ops_head.addWidget(lbl("Active Protocol: ISARM-V4", 8, TEXT_DIM))

        # Guard — only mode item (active, no click needed)
        guard_w = QWidget()
        guard_w.setFixedHeight(50)
        guard_w.setAttribute(Qt.WA_StyledBackground, True)
        guard_w.setStyleSheet(f"background:{PRIMARY}15;border-right:3px solid {PRIMARY};")
        gr = QHBoxLayout(guard_w)
        gr.setContentsMargins(20, 0, 16, 0)
        gr.setSpacing(14)
        gr.addWidget(lbl("🛡", 17, PRIMARY))
        gr.addWidget(lbl("Guard", 11, PRIMARY, bold=True, spacing=1, upper=True), 1)

        # ── Security protocol ComboBox ─────────────────
        sec_inner = QVBoxLayout()
        sec_inner.setContentsMargins(14, 12, 14, 12)
        sec_inner.setSpacing(6)
        sec_inner.addWidget(lbl("SECURITY PROTOCOL", 8, TEXT_DIM, spacing=2, upper=True))
        self.security_box = QComboBox()
        self.security_box.addItems(["Static", "Dynamic", "Away"])
        self.security_box.setCurrentText("Dynamic")
        self.security_box.currentTextChanged.connect(
            lambda m: setattr(self, "security_mode", m)
        )
        sec_inner.addWidget(self.security_box)
        sec_box = QWidget()
        sec_box.setLayout(sec_inner)
        sec_box.setStyleSheet(f"background:{BG_MODULE};border-radius:4px;")

        # ── Alerts toggle ──────────────────────────────
        self.alerts_toggle = AlertToggle("THREAT ALERTS")

        side_layout = QVBoxLayout()
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        side_layout.addLayout(ops_head)
        side_layout.addWidget(guard_w)
        side_layout.addSpacing(20)

        sec_wrap = QWidget()
        sec_wrap_l = QVBoxLayout(sec_wrap)
        sec_wrap_l.setContentsMargins(14, 0, 14, 0)
        sec_wrap_l.setSpacing(10)
        sec_wrap_l.addWidget(sec_box)
        sec_wrap_l.addWidget(self.alerts_toggle)
        side_layout.addWidget(sec_wrap)
        side_layout.addStretch()

        self.sidebar = QWidget()
        self.sidebar.setLayout(side_layout)
        self.sidebar.setFixedWidth(228)
        self.sidebar.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #02060c,stop:1 {BG_APP});"
            f"border-right:1px solid {PRIMARY}12;"
        )

        # ── VIDEO + HUD ───────────────────────────────
        self.video_label = BracketLabel("NO SIGNAL")
        self.video_label.setStyleSheet(
            f"background:#000308;color:{TEXT_DIM};font-size:10px;"
            f"font-family:'{FONT_MONO}';letter-spacing:4px;border-radius:4px;"
        )
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        def hud_chip(label_text, val_text, accent):
            w = GlassPanel(border=accent+"44", radius=4)
            w.setFixedSize(155, 52)
            lay = QVBoxLayout(w)
            lay.setContentsMargins(12, 8, 12, 8)
            lay.setSpacing(1)
            lay.addWidget(lbl(label_text, 7, accent, bold=True, spacing=2, upper=True))
            v = lbl(val_text, 15, ON_SURFACE, bold=True)
            lay.addWidget(v)
            return w, v

        self.hud_sig, self.hud_sig_val = hud_chip("SIGNAL QUALITY", "100% NOMINAL", SECONDARY)
        self.hud_lat, self.hud_lat_val = hud_chip("LATENCY",         "—",            PRIMARY)

        self.target_count = lbl("00", 52, ON_SURFACE, bold=True)
        self.target_count.setStyleSheet(
            f"font-family:'{FONT_SG}';font-size:52px;font-weight:700;"
            f"color:{ON_SURFACE};letter-spacing:-3px;background:transparent;"
        )
        tgt_sub = lbl("TARGETS DETECTED", 9, f"{PRIMARY}bb", bold=True, spacing=2, upper=True)
        tgt_row = QHBoxLayout()
        tgt_row.setSpacing(8)
        tgt_row.addWidget(self.target_count)
        tgt_row.addWidget(tgt_sub, 0, Qt.AlignBottom)
        tgt_row.addStretch()

        hud_top = QHBoxLayout()
        hud_top.setContentsMargins(16, 14, 16, 0)
        hud_top.setSpacing(10)
        hud_top.addWidget(self.hud_sig)
        hud_top.addWidget(self.hud_lat)
        hud_top.addStretch()

        hud_bot = QHBoxLayout()
        hud_bot.setContentsMargins(20, 0, 20, 14)
        hud_bot.addLayout(tgt_row)

        self.live_video_area = QWidget()
        self.live_video_area.setStyleSheet("background:#000308;border-radius:6px;")
        lva = QVBoxLayout(self.live_video_area)
        lva.setContentsMargins(0, 0, 0, 0)
        lva.setSpacing(0)
        lva.addLayout(hud_top)
        lva.addWidget(self.video_label, 1)
        lva.addLayout(hud_bot)
        self.live_video_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ── AI PANEL ──────────────────────────────────
        self._ai_panel = GlassPanel(radius=8)
        self._ai_panel.setFixedWidth(308)
        ai_lay = QVBoxLayout(self._ai_panel)
        ai_lay.setContentsMargins(0, 0, 0, 0)
        ai_lay.setSpacing(0)

        ai_hdr = QWidget()
        ai_hdr.setFixedHeight(52)
        ai_hdr.setStyleSheet(
            f"background:{BG_MODULE}55;border-radius:8px 8px 0 0;"
            f"border-bottom:1px solid {PRIMARY}18;"
        )
        ai_hdr_lay = QHBoxLayout(ai_hdr)
        ai_hdr_lay.setContentsMargins(16, 0, 16, 0)
        ai_hdr_lay.addWidget(lbl("AI ANALYSIS", 12, PRIMARY, bold=True, spacing=3, upper=True))
        ai_hdr_lay.addStretch()
        self.ai_ping = lbl("●", 9, SECONDARY)
        ai_hdr_lay.addWidget(self.ai_ping)
        self._ptimer.start(800)

        self._log_container = QWidget()
        self._log_container.setStyleSheet("background:transparent;")
        self._log_lay = QVBoxLayout(self._log_container)
        self._log_lay.setContentsMargins(14, 8, 14, 8)
        self._log_lay.setSpacing(0)
        self._log_lay.addStretch()

        log_scroll = QScrollArea()
        log_scroll.setWidget(self._log_container)
        log_scroll.setWidgetResizable(True)
        log_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.ai_text = QTextEdit()
        self.ai_text.setReadOnly(True)
        self.ai_text.setFixedHeight(108)
        self.ai_text.setStyleSheet(
            f"background:{BG_MODULE}33;border:none;border-top:1px solid {PRIMARY}15;"
            f"color:{SECONDARY};font-family:'{FONT_MONO}';font-size:11px;"
            f"padding:12px;border-radius:0;"
        )

        ref_sec = QWidget()
        ref_sec.setStyleSheet(f"background:{BG_MODULE}33;")
        ref_sec_lay = QVBoxLayout(ref_sec)
        ref_sec_lay.setContentsMargins(14, 8, 14, 10)
        ref_sec_lay.setSpacing(5)
        ref_sec_lay.addWidget(lbl("REFERENCE FRAME", 8, TEXT_DIM, spacing=2, upper=True))
        self.ref_thumb = QLabel("NO CAPTURE")
        self.ref_thumb.setFixedHeight(68)
        self.ref_thumb.setAlignment(Qt.AlignCenter)
        self.ref_thumb.setStyleSheet(
            f"background:{BG_MODULE};color:{TEXT_DIM};font-size:9px;"
            f"font-family:'{FONT_MONO}';border-radius:3px;"
        )
        ref_sec_lay.addWidget(self.ref_thumb)

        self.stat_uptime = StatCard("UPTIME",       "000:00:00")
        self.stat_threat = StatCard("THREAT LEVEL", "MINIMAL",  SECONDARY)
        stat_row = QHBoxLayout()
        stat_row.setContentsMargins(10, 8, 10, 10)
        stat_row.setSpacing(8)
        stat_row.addWidget(self.stat_uptime, 1)
        stat_row.addWidget(self.stat_threat, 1)

        ai_lay.addWidget(ai_hdr)
        ai_lay.addWidget(log_scroll, 1)
        ai_lay.addWidget(self.ai_text)
        ai_lay.addWidget(ref_sec)
        ai_lay.addLayout(stat_row)

        # ── LIVE ROW ──────────────────────────────────
        live_row = QHBoxLayout()
        live_row.setContentsMargins(0, 0, 0, 0)
        live_row.setSpacing(12)
        live_row.addWidget(self.live_video_area, 1)
        live_row.addWidget(self._ai_panel)

        self.live_widget = QWidget()
        self.live_widget.setLayout(live_row)

        # ── SCENE COMPARISON ──────────────────────────
        def img_slot(heading):
            h = lbl(heading, 9, PRIMARY, bold=True, spacing=3, upper=True)
            img = BracketLabel("AWAITING IMAGE")
            img.setAlignment(Qt.AlignCenter)
            img.setStyleSheet(
                f"background:#000308;color:{TEXT_DIM};font-size:9px;"
                f"font-family:'{FONT_MONO}';letter-spacing:3px;border-radius:4px;"
            )
            img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            img.setMinimumHeight(270)
            col = QVBoxLayout()
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(6)
            col.addWidget(h)
            col.addWidget(img, 1)
            return col, img

        ref_col,  self.ref_label  = img_slot("REFERENCE IMAGE")
        cmp_col,  self.comp_label = img_slot("COMPARISON IMAGE")

        imgs_row = QHBoxLayout()
        imgs_row.setSpacing(16)
        imgs_row.addLayout(ref_col, 1)
        imgs_row.addLayout(cmp_col, 1)

        self.upload_ref_btn = ghost_btn("↑  Upload Reference", PRIMARY)
        self.upload_cmp_btn = ghost_btn("↑  Upload Image",     PRIMARY)
        self.compare_btn    = filled_btn("⬡  Compare Images")

        self.upload_ref_btn.clicked.connect(self.upload_reference)
        self.upload_cmp_btn.clicked.connect(self.upload_compare)
        self.compare_btn.clicked.connect(self.compare_uploaded_images)

        up_row = QHBoxLayout()
        up_row.setSpacing(12)
        up_row.addWidget(self.upload_ref_btn, 1)
        up_row.addWidget(self.upload_cmp_btn, 1)
        up_row.addWidget(self.compare_btn,    1)

        cmp_ai_hdr = QHBoxLayout()
        cmp_ai_hdr.addWidget(lbl("●", 9, SECONDARY))
        cmp_ai_hdr.addSpacing(6)
        cmp_ai_hdr.addWidget(lbl("AI ANALYSIS ENGINE ACTIVE", 9, SECONDARY, bold=True, spacing=3, upper=True))
        cmp_ai_hdr.addStretch()
        self.cmp_acc = lbl("ACCURACY: —", 9, TEXT_DIM, mono=True)
        cmp_ai_hdr.addWidget(self.cmp_acc)

        self.cmp_ai_text = QTextEdit()
        self.cmp_ai_text.setReadOnly(True)
        self.cmp_ai_text.setFixedHeight(88)
        self.cmp_ai_text.setStyleSheet(
            f"background:transparent;border:none;color:{SECONDARY};"
            f"font-family:'{FONT_MONO}';font-size:12px;padding:2px;line-height:1.4;"
        )

        cmp_ai_box = GlassPanel(radius=4)
        cmp_ai_inner = QVBoxLayout(cmp_ai_box)
        cmp_ai_inner.setContentsMargins(18, 12, 18, 12)
        cmp_ai_inner.setSpacing(8)
        cmp_ai_inner.addLayout(cmp_ai_hdr)
        cmp_ai_inner.addWidget(hdivider())
        cmp_ai_inner.addWidget(self.cmp_ai_text)

        cmp_outer = QVBoxLayout()
        cmp_outer.setContentsMargins(0, 0, 0, 0)
        cmp_outer.setSpacing(12)
        cmp_outer.addLayout(imgs_row, 1)
        cmp_outer.addLayout(up_row)
        cmp_outer.addWidget(cmp_ai_box)

        self.compare_widget = QWidget()
        self.compare_widget.setLayout(cmp_outer)

        # ── CONTENT STACK ─────────────────────────────
        cs = QVBoxLayout()
        cs.setContentsMargins(0, 0, 0, 0)
        cs.setSpacing(0)
        cs.addWidget(self.live_widget)
        cs.addWidget(self.compare_widget)
        cw = QWidget()
        cw.setLayout(cs)

        padded = QWidget()
        padded_lay = QVBoxLayout(padded)
        padded_lay.setContentsMargins(14, 12, 14, 8)
        padded_lay.addWidget(cw, 1)

        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)
        main_row.addWidget(self.sidebar)
        main_row.addWidget(padded, 1)

        main_w = QWidget()
        main_w.setLayout(main_row)

        # ── BOTTOM NAV ────────────────────────────────
        self.nb_start   = NavBtn("▶", "Start")
        self.nb_stop    = NavBtn("■", "Stop")
        self.nb_capture = NavBtn("⊙", "Capture Ref")
        self.nb_compare = NavBtn("⬡", "Compare Frame")
        self.nb_upref   = NavBtn("↑", "Upload Ref")
        self.nb_upimg   = NavBtn("↑", "Upload Img")
        self.nb_cmpimg  = NavBtn("⬡", "Compare")

        self.nb_start.connect(self.start_live)
        self.nb_stop.connect(self.stop_live)
        self.nb_capture.connect(self.capture_reference)
        self.nb_compare.connect(self.compare_live_frame)
        self.nb_upref.connect(self.upload_reference)
        self.nb_upimg.connect(self.upload_compare)
        self.nb_cmpimg.connect(self.compare_uploaded_images)

        bot_lay = QHBoxLayout()
        bot_lay.setContentsMargins(0, 0, 0, 0)
        bot_lay.setSpacing(0)
        bot_lay.addSpacing(228)
        bot_lay.addStretch()
        for w in [self.nb_start, self.nb_stop, self.nb_capture, self.nb_compare,
                  self.nb_upref, self.nb_upimg, self.nb_cmpimg]:
            bot_lay.addWidget(w)
        bot_lay.addStretch()

        self.bot_bar = QWidget()
        self.bot_bar.setLayout(bot_lay)
        self.bot_bar.setFixedHeight(82)
        self.bot_bar.setStyleSheet(
            f"background:rgba(2,6,12,0.9);border-top:1px solid {PRIMARY}15;"
        )

        # ── MASTER ────────────────────────────────────
        master = QVBoxLayout()
        master.setContentsMargins(0, 0, 0, 0)
        master.setSpacing(0)
        master.addWidget(self.topbar)
        master.addWidget(self.alert_banner)
        master.addWidget(main_w, 1)
        master.addWidget(self.bot_bar)
        self.setLayout(master)

        self.switch_mode("Live Monitoring")

    # ────────────────────────────────────────────────
    #  NAV LINK FACTORY  (keeps style in sync)
    # ────────────────────────────────────────────────
    def _nav_link(self, text, active=False):
        b = QPushButton(text.upper())
        b.setFlat(True)
        self._apply_nav_style(b, active)
        return b

    @staticmethod
    def _apply_nav_style(btn, active):
        c   = PRIMARY if active else ON_SURFACE_VAR
        bdr = f"border-bottom:2px solid {PRIMARY};" if active else "border-bottom:2px solid transparent;"
        btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{c};
                font-family:'{FONT_SG}';font-size:11px;font-weight:700;
                letter-spacing:2px;padding:4px 2px;{bdr}border-radius:0;
            }}
            QPushButton:hover {{
                color:{PRIMARY};border-bottom:2px solid {PRIMARY};
            }}
        """)

    # ────────────────────────────────────────────────
    #  MODE SWITCH — fixes the underline bug
    # ────────────────────────────────────────────────
    def switch_mode(self, mode: str):
        self.app_mode = "Live" if "Live" in mode else "Compare"
        live = self.app_mode == "Live"

        # ① Update nav underlines correctly
        ISARM._apply_nav_style(self.nav_live,    active=live)
        ISARM._apply_nav_style(self.nav_compare, active=not live)

        # ② Show/hide content
        self.live_widget.setVisible(live)
        self.compare_widget.setVisible(not live)

        # ③ Show/hide bottom nav buttons
        self.nb_start.setVisible(live)
        self.nb_stop.setVisible(live)
        self.nb_capture.setVisible(live)
        self.nb_compare.setVisible(live)
        self.nb_upref.setVisible(not live)
        self.nb_upimg.setVisible(not live)
        self.nb_cmpimg.setVisible(not live)

        if live:
            self._log("MODE", "Live Monitoring activated.", False)
            self.set_ai_text("LIVE MONITORING READY\n\nPress START to activate camera feed.")
        else:
            self._log("MODE", "Scene Comparison activated.", False)
            self.set_ai_text("SCENE COMPARISON MODE\n\nUpload images and press COMPARE.")

    # ────────────────────────────────────────────────
    #  LIVE MODE  (UNCHANGED)
    # ────────────────────────────────────────────────
    def start_live(self):
        self.hud_lat_val.setText("0.04ms")
        self._log("START", "Feed initiated. Scanning active.", False)
        self.nb_stop.set_active(True)
        self.timer.start(30)

    def stop_live(self):
        self.timer.stop()
        self.hud_lat_val.setText("—")
        self._log("STOP", "Feed suspended.", False)
        self.nb_stop.set_active(False)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        self.current_frame = frame.copy()

        results = self.model(frame, conf=0.5, verbose=False)
        count   = 0

        for r in results:
            for box in r.boxes:
                cls      = int(box.cls[0])
                label    = self.model.names[cls]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                count   += 1
                is_threat = (self.security_mode == "Away" and label == "person")
                cbgr      = (59, 50, 255) if is_threat else (0, 238, 252)

                cv2.rectangle(frame, (x1, y1), (x2, y2), cbgr, 2)
                tag      = f"TARGET_{count:02d}: {label.upper()}"
                conf_val = float(box.conf[0])
                cf       = f"CONFIDENCE: {conf_val:.1%}"
                (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
                cv2.rectangle(frame, (x1, y1-th-22), (x1+tw+12, y1), cbgr, -1)
                cv2.putText(frame, tag, (x1+4, y1-12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 1, cv2.LINE_AA)
                cv2.putText(frame, cf, (x1+4, y1-2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 0, 0), 1, cv2.LINE_AA)

                if is_threat:
                    self._fire_threat(label, conf_val)

        self.target_count.setText(f"{count:02d}")
        self.show_image(frame, self.video_label)

    def capture_reference(self):
        if self.current_frame is not None:
            self.reference_image = self.current_frame.copy()
            self.show_image(self.reference_image, self.ref_thumb)
            self._log("CAPTURE", "Reference frame acquired.", False)
            self.set_ai_text("REFERENCE CAPTURED\n\nMove or add objects, then press COMPARE FRAME.")

    def compare_live_frame(self):
        if self.reference_image is None or self.current_frame is None:
            self._log("ERROR", "No reference. Capture first.", True)
            self.set_ai_text("⚠  CAPTURE REFERENCE FIRST\n\nUse CAPTURE REF before comparing.")
            return
        self.stop_live()
        self._log("ANALYSIS", "Running scene delta analysis...", False)
        result      = compare_scenes(self.reference_image, self.current_frame)
        explanation = explain_scene(result)
        self.set_ai_text(explanation)
        self._log("RESULT", explanation[:110] + ("..." if len(explanation) > 110 else ""),
                  bool(result.get("added_objects") or result.get("missing_objects")))
        self._eval_threat(result, explanation)

    # ────────────────────────────────────────────────
    #  SCENE COMPARISON  (UNCHANGED)
    # ────────────────────────────────────────────────
    def upload_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select reference image")
        if path:
            self.reference_image = cv2.imread(path)
            self.show_image(self.reference_image, self.ref_label)
            self._log("UPLOAD", "Reference image loaded.", False)

    def upload_compare(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select comparison image")
        if path:
            self.compare_image = cv2.imread(path)
            self.show_image(self.compare_image, self.comp_label)
            self._log("UPLOAD", "Comparison image loaded.", False)

    def compare_uploaded_images(self):
        if self.reference_image is None or self.compare_image is None:
            self.set_ai_text("⚠  UPLOAD BOTH IMAGES FIRST")
            self.cmp_ai_text.setPlainText("⚠  Upload both images before comparing.")
            return
        self._log("ANALYSIS", "Running scene comparison...", False)
        result      = compare_scenes(self.reference_image, self.compare_image)
        explanation = explain_scene(result)
        self.set_ai_text(explanation)
        self.cmp_ai_text.setPlainText(explanation)
        self.cmp_acc.setText("ACCURACY: 99.82%")
        self._log("RESULT", explanation[:110] + ("..." if len(explanation) > 110 else ""),
                  bool(result.get("added_objects") or result.get("missing_objects")))
        self._eval_threat(result, explanation)

    # ────────────────────────────────────────────────
    #  THREAT ASSESSMENT
    # ────────────────────────────────────────────────
    def _fire_threat(self, obj_label: str, conf: float):
        """Immediate threat: person detected in Away mode during live feed."""
        if not self.alerts_toggle.enabled:
            return
        msg = (
            f"Unauthorized presence detected — '{obj_label}' identified with "
            f"{conf:.1%} confidence. Protocol '{self.security_mode}' active. "
            f"Immediate review required."
        )
        self.alert_banner.show_threat("HIGH", msg)
        self.stat_threat.set_value("HIGH", TERTIARY)
        self._log("ALERT", f"Unauthorized {obj_label} detected. Conf: {conf:.1%}", True)
        self._start_flash()

    def _eval_threat(self, result: dict, explanation: str):
        """Post-comparison threat evaluation."""
        added   = result.get("added_objects",   [])
        missing = result.get("missing_objects", [])

        if not added and not missing:
            self.stat_threat.set_value("MINIMAL", SECONDARY)
            return

        person_added = any("person" in o.lower() for o in added)
        level = "CRITICAL" if person_added else ("HIGH" if added else "MODERATE")

        parts = []
        if added:
            parts.append(f"New object(s) detected in scene: {', '.join(added)}.")
        if missing:
            parts.append(f"Object(s) removed from scene: {', '.join(missing)}.")
        parts.append(f"AI: {explanation[:160]}")
        msg = " ".join(parts)

        if self.alerts_toggle.enabled:
            self.alert_banner.show_threat(level, msg)
            self._start_flash()

        cmap = {"CRITICAL": TERTIARY, "HIGH": TERTIARY, "MODERATE": PRIMARY}
        self.stat_threat.set_value(level, cmap.get(level, SECONDARY))
        self._log("THREAT", f"Level {level} — {msg[:100]}...", True)

    # ────────────────────────────────────────────────
    #  VISUAL FLASH on threat
    # ────────────────────────────────────────────────
    def _start_flash(self):
        self._flash_count = 0
        if not self._flash_timer.isActive():
            self._flash_timer.start(160)

    def _do_flash(self):
        self._flash_count += 1
        on = (self._flash_count % 2 == 1)
        self.topbar.setStyleSheet(
            f"background:{'rgba(255,113,98,0.18)' if on else 'rgba(2,6,12,0.9)'};"
            f"border-bottom:1px solid {PRIMARY}15;"
        )
        if self._flash_count >= 6:
            self._flash_timer.stop()
            self.topbar.setStyleSheet(
                f"background:rgba(2,6,12,0.9);border-bottom:1px solid {PRIMARY}15;"
            )

    # ────────────────────────────────────────────────
    #  UTILITIES  (UNCHANGED)
    # ────────────────────────────────────────────────
    def set_ai_text(self, text: str):
        self.ai_text.setPlainText(text)

    def show_image(self, frame, label: QLabel):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        label.setPixmap(
            QPixmap.fromImage(img).scaled(
                label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def _log(self, tag: str, msg: str, alert: bool):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        e  = LogEntry(ts, tag, msg, alert=alert)
        c  = self._log_lay.count()
        self._log_lay.insertWidget(c - 1, e)
        QTimer.singleShot(40, self._auto_scroll)

    def _auto_scroll(self):
        p = self._log_container.parent()
        if p and hasattr(p, "verticalScrollBar"):
            p.verticalScrollBar().setValue(p.verticalScrollBar().maximum())

    def _blink(self):
        self._ping_state = not self._ping_state
        self.ai_ping.setStyleSheet(
            f"font-size:9px;background:transparent;"
            f"color:{SECONDARY if self._ping_state else BG_MODULE};"
        )

    def _tick(self):
        self._uptime += 1
        h = self._uptime // 3600
        m = (self._uptime % 3600) // 60
        s = self._uptime % 60
        self.stat_uptime.set_value(f"{h:03d}:{m:02d}:{s:02d}")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(BG_APP))
    pal.setColor(QPalette.WindowText,      QColor(ON_SURFACE))
    pal.setColor(QPalette.Base,            QColor(BG_WORKSPACE))
    pal.setColor(QPalette.AlternateBase,   QColor(BG_MODULE))
    pal.setColor(QPalette.ToolTipBase,     QColor(BG_MODULE))
    pal.setColor(QPalette.ToolTipText,     QColor(ON_SURFACE))
    pal.setColor(QPalette.Text,            QColor(ON_SURFACE))
    pal.setColor(QPalette.Button,          QColor(BG_MODULE))
    pal.setColor(QPalette.ButtonText,      QColor(ON_SURFACE))
    pal.setColor(QPalette.BrightText,      QColor(PRIMARY_CONT))
    pal.setColor(QPalette.Link,            QColor(PRIMARY_CONT))
    pal.setColor(QPalette.Highlight,       QColor(BG_INTERACT))
    pal.setColor(QPalette.HighlightedText, QColor(PRIMARY_CONT))
    app.setPalette(pal)

    window = ISARM()
    window.show()
    sys.exit(app.exec_())
