import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from audioswitcher.app import Tray
from audioswitcher.config import Group


class FakeBackend(QObject):
    changed = Signal()

    def __init__(self, groups, active=""):
        super().__init__()
        self._groups = groups
        self._active = active
        self._poll = mock.Mock()
        self.applyGroup = mock.Mock()


class TrayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.groups = [Group("One", id="one"), Group("Two", id="two"), Group("Three", id="three")]
        self.backend = FakeBackend(self.groups, "one")
        self.show_window = mock.Mock()
        self.tray = Tray(self.backend, self.show_window)

    def tearDown(self):
        self.tray.tray.hide()
        self.tray.menu.close()

    def test_left_click_cycles_and_wraps(self):
        for active, expected in [("one", "two"), ("two", "three"), ("three", "one"), ("", "one")]:
            with self.subTest(active=active):
                self.backend._active = active
                self.tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
                self.backend.applyGroup.assert_called_with(expected)
        self.assertEqual(self.backend._poll.call_count, 4)
        self.show_window.assert_not_called()

    def test_click_refreshes_active_group_before_cycling(self):
        self.backend._poll.side_effect = lambda: setattr(self.backend, "_active", "two")
        self.tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
        self.backend.applyGroup.assert_called_once_with("three")

    def test_empty_groups_open_editor(self):
        self.backend._groups = []
        self.tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
        self.show_window.assert_called_once()
        self.backend.applyGroup.assert_not_called()

    def test_single_group_is_applied(self):
        self.backend._groups = self.groups[:1]
        self.tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
        self.backend.applyGroup.assert_called_once_with("one")

    def test_context_activation_does_not_cycle_and_menu_actions_remain(self):
        self.tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
        self.backend.applyGroup.assert_not_called()
        self.assertIs(self.tray.tray.contextMenu(), self.tray.menu)
        self.tray.menu.actions()[1].trigger()
        self.backend.applyGroup.assert_called_once_with("two")
        edit_action = next(action for action in self.tray.menu.actions() if action.text() == "Edit groups…")
        edit_action.trigger()
        self.show_window.assert_called_once()
