"""Robot profile registry.

A profile is a directory triple, all named after the profile:

    assets/<robot>/mjcf/scene.xml     robot + ground scene (terrain is merged in)
    policies/<robot>/policy.onnx      ONNX policy
    configs/<robot>.yaml              runtime profile (obs layout, gains, ...)

Adding a robot therefore means adding those three, plus its name in ``ROBOTS``.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ROBOTS: tuple[str, ...] = ("m20", "go2", "dog3", "d1")

_LABELS = {"m20": "M20", "go2": "Go2", "dog3": "Dog3", "d1": "D1"}


def robot_label(robot: str) -> str:
    """Human-readable name for a profile."""
    return _LABELS.get(robot, robot.upper())


def robot_scene(robot: str) -> Path:
    return PROJECT_ROOT / "assets" / robot / "mjcf" / "scene.xml"


def robot_policy(robot: str) -> Path:
    return PROJECT_ROOT / "policies" / robot / "policy.onnx"


def robot_config(robot: str) -> Path:
    return PROJECT_ROOT / "configs" / f"{robot}.yaml"


# Which geom groups a viewer should hide/show. m20/go2/dog3 keep collision
# proxies in group 1 and visual meshes in group 2, but that is a per-model
# convention, not a rule: d1's visual meshes live in group 1 (its group 2 is
# empty), so the legacy [1,3]/[2] default hides the whole robot and only the
# demo ball remains visible.
DEFAULT_HIDDEN_GEOMGROUPS: tuple[int, ...] = (1, 3)
DEFAULT_VISIBLE_GEOMGROUPS: tuple[int, ...] = (2,)


def viewer_geomgroups(config_path: str | Path | None) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return ``(hidden, shown)`` geom groups for a viewer, from the profile.

    Falls back to the legacy convention when no profile is given or the profile
    does not override the groups.
    """
    hidden, shown = DEFAULT_HIDDEN_GEOMGROUPS, DEFAULT_VISIBLE_GEOMGROUPS
    if config_path is not None:
        config_path = Path(config_path)
        if config_path.exists():
            import yaml

            config = yaml.safe_load(config_path.read_text()) or {}
            hidden = tuple(int(g) for g in config.get("viewer_hidden_geomgroups", hidden))
            shown = tuple(int(g) for g in config.get("viewer_visible_geomgroups", shown))
    return hidden, shown
