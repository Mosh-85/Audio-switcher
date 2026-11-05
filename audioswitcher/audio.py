"""Thin wrapper around pactl (works with PipeWire's pulse server and PulseAudio)."""
import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    name: str
    description: str


def _pactl(*args: str) -> str:
    return subprocess.run(
        ["pactl", *args], check=True, capture_output=True, text=True
    ).stdout


def _list(kind: str) -> list[dict]:
    return json.loads(_pactl("--format=json", "list", kind))


def list_sinks() -> list[Device]:
    return [Device(d["name"], d.get("description", d["name"])) for d in _list("sinks")]


def list_sources() -> list[Device]:
    """Input devices, excluding the 'monitor' loopbacks of output devices."""
    return [
        Device(d["name"], d.get("description", d["name"]))
        for d in _list("sources")
        if d.get("monitor_of_sink") is None and not d["name"].endswith(".monitor")
    ]


def default_sink() -> str:
    return _pactl("get-default-sink").strip()


def default_source() -> str:
    return _pactl("get-default-source").strip()


def set_default_sink(name: str) -> None:
    _pactl("set-default-sink", name)


def set_default_source(name: str) -> None:
    _pactl("set-default-source", name)
