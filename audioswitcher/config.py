"""Group storage and the logic for applying a group."""
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import audio


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "audio-switcher" / "groups.json"


@dataclass
class Group:
    name: str
    sink: str = ""  # output device name, empty = leave unchanged
    source: str = ""  # input device name, empty = leave unchanged
    icon: str = "audio-headset"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


def load(path: Path | None = None) -> list[Group]:
    path = path or config_path()
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [Group(**{k: g[k] for k in Group.__dataclass_fields__ if k in g}) for g in data.get("groups", [])]


def save(groups: list[Group], path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"groups": [asdict(g) for g in groups]}, indent=2))
    tmp.replace(path)


def apply(group: Group) -> list[str]:
    """Set default devices. Returns names of devices that are currently unavailable."""
    missing = []
    sinks = {d.name for d in audio.list_sinks()}
    sources = {d.name for d in audio.list_sources()}
    if group.sink:
        if group.sink in sinks:
            audio.set_default_sink(group.sink)
        else:
            missing.append(group.sink)
    if group.source:
        if group.source in sources:
            audio.set_default_source(group.source)
        else:
            missing.append(group.source)
    return missing


def active_group_id(groups: list[Group]) -> str:
    """Id of the first group whose devices match the current defaults, else ''."""
    sink, source = audio.default_sink(), audio.default_source()
    for g in groups:
        if (g.sink or g.source) and (not g.sink or g.sink == sink) and (not g.source or g.source == source):
            return g.id
    return ""
