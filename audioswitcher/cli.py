"""Command line interface; also used by the Plasma widget."""
import argparse
import json
import subprocess
import sys

from . import config


def notify(title: str, body: str, icon: str) -> None:
    try:
        subprocess.run(
            ["notify-send", "-a", "Audio Switcher", "-i", icon, title, body],
            check=False,
        )
    except FileNotFoundError:
        pass


def apply_and_notify(group: config.Group) -> list[str]:
    missing = config.apply(group)
    if missing:
        notify(f"{group.name}: device missing", "\n".join(missing), "dialog-warning")
    else:
        notify(f"Audio: {group.name}", "Audio devices switched", group.icon)
    return missing


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="audio-switcher-ctl")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="print groups and active group as JSON")
    a = sub.add_parser("apply", help="apply a group by id or name")
    a.add_argument("group")
    args = p.parse_args(argv)

    groups = config.load()
    if args.cmd == "list":
        print(json.dumps({
            "active": config.active_group_id(groups),
            "groups": [g.__dict__ for g in groups],
        }))
        return 0
    match = next((g for g in groups if args.group in (g.id, g.name)), None)
    if not match:
        print(f"No such group: {args.group}", file=sys.stderr)
        return 1
    return 2 if apply_and_notify(match) else 0


if __name__ == "__main__":
    sys.exit(main())
