import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audioswitcher import audio, config


class ConfigTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "groups.json"
            groups = [config.Group("A", "sinkA", "srcA"), config.Group("B", "sinkB")]
            config.save(groups, p)
            self.assertEqual(config.load(p), groups)

    def test_load_missing_or_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "g.json"
            self.assertEqual(config.load(p), [])
            p.write_text("{nope")
            self.assertEqual(config.load(p), [])

    def test_apply_sets_defaults_and_reports_missing(self):
        g = config.Group("A", "sink1", "gone")
        with mock.patch.object(audio, "list_sinks", return_value=[audio.Device("sink1", "S")]), \
             mock.patch.object(audio, "list_sources", return_value=[]), \
             mock.patch.object(audio, "set_default_sink") as ss, \
             mock.patch.object(audio, "set_default_source") as so:
            self.assertEqual(config.apply(g), ["gone"])
            ss.assert_called_once_with("sink1")
            so.assert_not_called()

    def test_active_group(self):
        a = config.Group("A", "s1", "m1")
        b = config.Group("B", "s2", "m2")
        with mock.patch.object(audio, "default_sink", return_value="s2"), \
             mock.patch.object(audio, "default_source", return_value="m2"):
            self.assertEqual(config.active_group_id([a, b]), b.id)
        with mock.patch.object(audio, "default_sink", return_value="s2"), \
             mock.patch.object(audio, "default_source", return_value="other"):
            self.assertEqual(config.active_group_id([a, b]), "")


class AudioTests(unittest.TestCase):
    def test_sources_exclude_monitors(self):
        data = [
            {"name": "mic", "description": "Mic", "monitor_of_sink": None},
            {"name": "x.monitor", "description": "Mon", "monitor_of_sink": 3},
        ]
        with mock.patch.object(audio, "_pactl", return_value=json.dumps(data)):
            self.assertEqual([d.name for d in audio.list_sources()], ["mic"])


if __name__ == "__main__":
    unittest.main()
