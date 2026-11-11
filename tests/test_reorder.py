import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from audioswitcher import audio, cli, config
from audioswitcher.app import Backend, Tray


class ReorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        patch = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.directory.name})
        patch.start()
        self.addCleanup(patch.stop)
        self.groups = [
            config.Group("One", "s1", "m1", id="one"),
            config.Group("Two", "s2", "m2", id="two"),
            config.Group("Three", "s3", "m3", id="three"),
        ]
        config.save(self.groups)
        for name, value in [("list_sinks", []), ("list_sources", []),
                            ("default_sink", "s1"), ("default_source", "m1")]:
            patch = mock.patch.object(audio, name, return_value=value)
            patch.start()
            self.addCleanup(patch.stop)
        self.backend = Backend()
        self.addCleanup(self.backend._timer.stop)

    def test_move_persists_and_updates_tray_cycle_and_cli(self):
        tray = Tray(self.backend, lambda: None)
        self.addCleanup(tray.tray.hide)
        self.addCleanup(tray.menu.close)
        self.backend.moveGroup("three", -1)
        self.assertEqual([g.id for g in config.load()], ["one", "three", "two"])
        self.assertEqual([action.text() for action in tray.menu.actions()[:3]], ["One", "Three", "Two"])
        with mock.patch.object(self.backend, "applyGroup") as apply:
            tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
            apply.assert_called_once_with("three")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["list"]), 0)
        self.assertEqual([g["id"] for g in json.loads(output.getvalue())["groups"]],
                         ["one", "three", "two"])
        self.backend.moveGroup("three", 1)
        self.assertEqual([g.id for g in config.load()], ["one", "two", "three"])

    def test_boundaries_do_not_modify_or_save(self):
        with mock.patch.object(config, "save") as save:
            self.backend.moveGroup("one", -1)
            self.backend.moveGroup("three", 1)
            self.backend.moveGroup("missing", 1)
            save.assert_not_called()
        self.assertEqual([g.id for g in self.backend._groups], ["one", "two", "three"])

    def test_selection_and_unsaved_form_survive_moves(self):
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", self.backend)
        engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "audioswitcher/qml/Main.qml")))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        up = window.findChild(QObject, "moveGroupUp")
        down = window.findChild(QObject, "moveGroupDown")
        self.assertIsNotNone(up)
        self.assertIsNotNone(down)
        self.assertFalse(up.property("enabled"))
        self.assertTrue(down.property("enabled"))
        window.setProperty("selectedId", "two")
        self.app.processEvents()
        name = window.findChild(QObject, "groupName")
        self.assertIsNotNone(name)
        name.setProperty("text", "Unsaved edit")
        self.assertTrue(QMetaObject.invokeMethod(up, "click"))
        self.app.processEvents()
        self.assertEqual(window.property("selectedId"), "two")
        self.assertEqual(name.property("text"), "Unsaved edit")
        self.assertEqual([g.id for g in config.load()], ["two", "one", "three"])
        self.assertFalse(up.property("enabled"))
        self.assertTrue(down.property("enabled"))
        self.assertTrue(QMetaObject.invokeMethod(down, "click"))
        self.app.processEvents()
        self.assertEqual([g.id for g in config.load()], ["one", "two", "three"])
        self.assertEqual(name.property("text"), "Unsaved edit")
