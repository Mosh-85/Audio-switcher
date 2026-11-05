"""Tray icon + group editor window."""
import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import audio, config
from .cli import apply_and_notify

APP_ID = "audio-switcher"


def autostart_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / f"{APP_ID}.desktop"


class Backend(QObject):
    changed = Signal()
    devicesChanged = Signal()
    autostartChanged = Signal()

    def __init__(self):
        super().__init__()
        self._groups = config.load()
        self._active = ""
        self._sinks: list[dict] = []
        self._sources: list[dict] = []
        self.refreshDevices()
        self._refresh_active()
        # Pick up changes made by the CLI/widget and external default-device changes.
        self._timer = QTimer(self, interval=1500)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def _poll(self):
        groups = config.load()
        if groups != self._groups:
            self._groups = groups
            self.changed.emit()
        self._refresh_active()

    def _refresh_active(self):
        try:
            active = config.active_group_id(self._groups)
        except Exception:
            active = ""
        if active != self._active:
            self._active = active
            self.changed.emit()

    @Property("QVariantList", notify=changed)
    def groups(self):
        return [g.__dict__.copy() for g in self._groups]

    @Property(str, notify=changed)
    def activeId(self):
        return self._active

    @Property("QVariantList", notify=devicesChanged)
    def sinks(self):
        return self._sinks

    @Property("QVariantList", notify=devicesChanged)
    def sources(self):
        return self._sources

    @Property(bool, notify=autostartChanged)
    def autostart(self):
        return autostart_file().exists()

    @Slot(bool)
    def setAutostart(self, enabled: bool):
        f = autostart_file()
        if enabled:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "[Desktop Entry]\nType=Application\nName=Audio Switcher\n"
                "Exec=audio-switcher\nIcon=audio-headset\n"
                "X-KDE-autostart-after=panel\n"
            )
        else:
            f.unlink(missing_ok=True)
        self.autostartChanged.emit()

    @Slot()
    def refreshDevices(self):
        try:
            self._sinks = [{"name": d.name, "description": d.description} for d in audio.list_sinks()]
            self._sources = [{"name": d.name, "description": d.description} for d in audio.list_sources()]
        except Exception:
            self._sinks, self._sources = [], []
        self.devicesChanged.emit()

    @Slot(result=str)
    def addGroup(self) -> str:
        g = config.Group(name=f"Group {len(self._groups) + 1}")
        self._groups.append(g)
        self._persist()
        return g.id

    @Slot(str, str, str, str, str)
    def saveGroup(self, gid, name, sink, source, icon):
        for g in self._groups:
            if g.id == gid:
                g.name, g.sink, g.source, g.icon = name, sink, source, icon or "audio-headset"
        self._persist()

    @Slot(str)
    def deleteGroup(self, gid):
        self._groups = [g for g in self._groups if g.id != gid]
        self._persist()

    @Slot(str)
    def applyGroup(self, gid):
        for g in self._groups:
            if g.id == gid:
                apply_and_notify(g)
        self._refresh_active()

    def _persist(self):
        config.save(self._groups)
        self.changed.emit()


class Tray:
    def __init__(self, backend: Backend, show_window):
        self.backend = backend
        self.tray = QSystemTrayIcon(QIcon.fromTheme("audio-headset"))
        self.tray.setToolTip("Audio Switcher")
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(
            lambda r: show_window() if r == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self.show_window = show_window
        backend.changed.connect(self.rebuild)
        self.rebuild()
        self.tray.show()

    def rebuild(self):
        self.menu.clear()
        for g in self.backend._groups:
            act = QAction(QIcon.fromTheme(g.icon), g.name, self.menu)
            act.setCheckable(True)
            act.setChecked(g.id == self.backend._active)
            act.triggered.connect(lambda _=False, gid=g.id: self.backend.applyGroup(gid))
            self.menu.addAction(act)
        if self.backend._groups:
            self.menu.addSeparator()
        self.menu.addAction(QIcon.fromTheme("configure"), "Edit groups…", self.show_window)
        self.menu.addAction(QIcon.fromTheme("application-exit"), "Quit", QApplication.quit)
        active = next((g for g in self.backend._groups if g.id == self.backend._active), None)
        self.tray.setIcon(QIcon.fromTheme(active.icon if active else "audio-headset"))
        self.tray.setToolTip(f"Audio Switcher — {active.name}" if active else "Audio Switcher")


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Switcher")
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)
    # Use the Plasma look when qqc2-desktop-style is installed.
    engine = QQmlApplicationEngine()
    has_kde_style = any(
        (Path(p) / "org" / "kde" / "desktop").is_dir() for p in engine.importPathList()
    )
    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("org.kde.desktop" if has_kde_style else "Fusion")

    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    def show_window():
        window.show()
        window.raise_()
        window.requestActivate()

    def release_window():
        # Destroying the native window removes it from the task manager while in the tray.
        if not window.isVisible():
            window.destroy()

    window.visibleChanged.connect(lambda: QTimer.singleShot(0, release_window))
    tray = Tray(backend, show_window)  # noqa: F841 (kept alive)
    if "--background" not in sys.argv:
        show_window()
    else:
        window.hide()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
