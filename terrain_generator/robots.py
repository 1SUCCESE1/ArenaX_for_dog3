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

ROBOTS: tuple[str, ...] = ("m20", "go2", "dog3")

_LABELS = {"m20": "M20", "go2": "Go2", "dog3": "Dog3"}


def robot_label(robot: str) -> str:
    """Human-readable name for a profile."""
    return _LABELS.get(robot, robot.upper())


def robot_scene(robot: str) -> Path:
    return PROJECT_ROOT / "assets" / robot / "mjcf" / "scene.xml"


def robot_policy(robot: str) -> Path:
    return PROJECT_ROOT / "policies" / robot / "policy.onnx"


def robot_config(robot: str) -> Path:
    return PROJECT_ROOT / "configs" / f"{robot}.yaml"
