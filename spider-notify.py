#!/usr/bin/env python3
"""
Notification daemon con icono propio.
Registers as org.freedesktop.Notifications and shows all system notifications
with a custom icon at the top of the screen, styled to match a dark/lavender theme.
"""
import os
import sys
import threading
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from PyQt6.QtWidgets import (QApplication, QLabel, QWidget, QHBoxLayout,
                              QVBoxLayout, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPixmap, QFontMetrics
from PyQt6.QtWidgets import QGraphicsOpacityEffect

# Pon aquí tu propio icono (PNG cuadrado, fondo transparente recomendado).
# Puedes sobreescribirlo sin tocar el código con la variable de entorno
# NOTIFY_ICON_PATH.
ICON_PNG = os.environ.get(
    "NOTIFY_ICON_PATH",
    os.path.expanduser("~/.local/share/icons/notify-icon.png")
)
BG_COLOR = "rgba(8, 4, 25, 215)"
BORDER_COLOR = "rgba(255, 255, 255, 22)"
TEXT_COLOR = "rgba(255, 255, 255, 220)"
MUTED_COLOR = "rgba(255, 255, 255, 140)"
ACCENT = "#b57bdb"   # lavender
Y_SHOWN = 18
POPUP_WIDTH = 380
ICON_SIZE = 44
DEFAULT_TIMEOUT_MS = 5000


class Notifier(QObject):
    show_signal = pyqtSignal(int, str, str, str, int, list)
    close_signal = pyqtSignal(int)

    def __init__(self, app, screen):
        super().__init__()
        self.app = app
        self.screen = screen
        self.popups = {}       # id -> NotificationWidget
        self.queue_y = Y_SHOWN
        self.show_signal.connect(self._show)
        self.close_signal.connect(self._close)

    def emit_notification(self, nid, app_name, summary, body, timeout_ms):
        actions = []
        t = timeout_ms if timeout_ms > 0 else DEFAULT_TIMEOUT_MS
        self.show_signal.emit(nid, app_name, summary, body, t, actions)

    def close_notification(self, nid):
        self.close_signal.emit(nid)

    def _show(self, nid, app_name, summary, body, timeout_ms, actions):
        if nid in self.popups:
            self.popups[nid].dismiss()
        w = NotificationWidget(nid, app_name, summary, body, timeout_ms,
                               self.screen, self._on_closed)
        self.popups[nid] = w
        w.show_at(self._next_y())

    def _close(self, nid):
        if nid in self.popups:
            self.popups[nid].dismiss()

    def _next_y(self):
        if not self.popups:
            return Y_SHOWN
        bottom = Y_SHOWN
        for w in self.popups.values():
            # w.y() is absolute; subtract screen.y() to get relative position
            rel_bottom = (w.y() - self.screen.y()) + w.height() + 8
            bottom = max(bottom, rel_bottom)
        return bottom

    def _on_closed(self, nid):
        self.popups.pop(nid, None)
        self._restack()

    def _restack(self):
        current_y = Y_SHOWN
        for w in self.popups.values():
            target_abs_y = self.screen.y() + current_y
            if w.y() != target_abs_y:
                w.move_to(target_abs_y)
            current_y += w.height() + 8


class NotificationWidget(QWidget):
    def __init__(self, nid, app_name, summary, body, timeout_ms, screen, on_closed):
        super().__init__()
        self.nid = nid
        self.screen = screen
        self.on_closed = on_closed
        self._anim_out = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(POPUP_WIDTH)

        self._build_ui(app_name, summary, body)
        self.adjustSize()

        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, self.dismiss)

    def _build_ui(self, app_name, summary, body):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setStyleSheet(f"""
            QWidget#card {{
                background-color: {BG_COLOR};
                border-radius: 20px;
                border: 1px solid {BORDER_COLOR};
            }}
        """)
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 14, 12)
        card_layout.setSpacing(12)

        # Icono
        icon_label = QLabel()
        icon_label.setStyleSheet("background: transparent; border: none;")
        pix = QPixmap(ICON_PNG)
        if not pix.isNull():
            pix = pix.scaled(ICON_SIZE, ICON_SIZE,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pix)
        icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)

        # Text block
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        if app_name:
            app_lbl = QLabel(app_name.upper())
            app_lbl.setStyleSheet(
                f"color: {ACCENT}; font-size: 9px; font-weight: 700; "
                "letter-spacing: 1px; background: transparent; border: none;"
            )
            text_col.addWidget(app_lbl)

        if summary:
            sum_lbl = QLabel(summary)
            sum_lbl.setWordWrap(True)
            sum_lbl.setStyleSheet(
                f"color: {TEXT_COLOR}; font-size: 13px; font-weight: 600; "
                "background: transparent; border: none;"
            )
            text_col.addWidget(sum_lbl)

        if body:
            body_lbl = QLabel(body)
            body_lbl.setWordWrap(True)
            body_lbl.setStyleSheet(
                f"color: {MUTED_COLOR}; font-size: 11px; "
                "background: transparent; border: none;"
            )
            text_col.addWidget(body_lbl)

        card_layout.addLayout(text_col, 1)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            f"color: {MUTED_COLOR}; background: transparent; border: none; "
            "font-size: 11px; padding: 0;"
        )
        close_btn.clicked.connect(self.dismiss)
        card_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        outer.addWidget(card)

    def show_at(self, target_y):
        # Use absolute virtual desktop coordinates
        sx = self.screen.x()
        sw = self.screen.width()
        w = self.width()
        h = self.height()
        x = sx + (sw - w) // 2
        y_hidden = self.screen.y() - h - 20
        abs_target_y = self.screen.y() + target_y

        self.setGeometry(x, y_hidden, w, h)
        self.show()

        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(240)
        anim.setStartValue(QRect(x, y_hidden, w, h))
        anim.setEndValue(QRect(x, abs_target_y, w, h))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim_in = anim

    def move_to(self, abs_y):
        if self._anim_out:
            return
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(200)
        anim.setStartValue(self.geometry())
        anim.setEndValue(QRect(self.x(), abs_y, self.width(), self.height()))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim_move = anim

    def dismiss(self):
        if self._anim_out:
            return
        self._anim_out = True  # flag to prevent double dismiss
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(180)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)
        fade.finished.connect(self._cleanup)
        fade.start()
        self._fade_anim = fade

    def _cleanup(self):
        self.on_closed(self.nid)
        self.close()
        self.deleteLater()


class NotificationServer(dbus.service.Object):
    BUS_NAME = "org.freedesktop.Notifications"
    OBJ_PATH = "/org/freedesktop/Notifications"
    IFACE = "org.freedesktop.Notifications"

    def __init__(self, bus, notifier):
        name = dbus.service.BusName(
            self.BUS_NAME, bus,
            replace_existing=True,
            allow_replacement=True,
            do_not_queue=True
        )
        super().__init__(name, self.OBJ_PATH)
        self.notifier = notifier
        self._id_counter = 0

    @dbus.service.method(IFACE, in_signature='', out_signature='as')
    def GetCapabilities(self):
        return ['body', 'body-markup', 'icon-static', 'persistence', 'urgency']

    @dbus.service.method(IFACE, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ('CustomNotify', 'custom-notify', '1.0', '1.2')

    @dbus.service.method(IFACE, in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body,
               actions, hints, expire_timeout):
        if replaces_id and replaces_id > 0:
            nid = int(replaces_id)
        else:
            self._id_counter += 1
            nid = self._id_counter
        self.notifier.emit_notification(
            nid, str(app_name), str(summary), str(body), int(expire_timeout)
        )
        return dbus.UInt32(nid)

    @dbus.service.method(IFACE, in_signature='u', out_signature='')
    def CloseNotification(self, id):
        self.notifier.close_notification(int(id))
        self.NotificationClosed(dbus.UInt32(id), dbus.UInt32(3))

    @dbus.service.signal(IFACE, signature='uu')
    def NotificationClosed(self, id, reason):
        pass

    @dbus.service.signal(IFACE, signature='us')
    def ActionInvoked(self, id, action_key):
        pass


def run_glib(loop):
    loop.run()


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    screen = app.primaryScreen().geometry()
    print(f"Using screen: {app.primaryScreen().name()} at ({screen.x()},{screen.y()}) {screen.width()}x{screen.height()}")

    notifier = Notifier(app, screen)

    session_bus = dbus.SessionBus()
    server = NotificationServer(session_bus, notifier)

    glib_loop = GLib.MainLoop()
    t = threading.Thread(target=run_glib, args=(glib_loop,), daemon=True)
    t.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
