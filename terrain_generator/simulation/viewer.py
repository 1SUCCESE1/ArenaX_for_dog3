"""Interactive MuJoCo viewer for generated terrains."""

from __future__ import annotations

import time
from pathlib import Path

import mujoco
import mujoco.viewer

from ..robots import viewer_geomgroups


def view_xml(xml_path: str | Path, config_path: str | Path | None = None) -> None:
    """Open an interactive window and simulate the scene until it closes.

    ``config_path`` is the robot profile; its ``viewer_*_geomgroups`` decide
    which groups are drawn (the visual-mesh group differs per model -- d1 uses
    group 1, m20/go2/dog3 use group 2).
    """

    model = mujoco.MjModel.from_xml_path(str(xml_path))
    data = mujoco.MjData(model)
    hidden_groups, visible_groups = viewer_geomgroups(config_path)

    # launch_passive keeps the Python process in control of stepping and camera setup.
    with mujoco.viewer.launch_passive(model, data) as viewer:
        # Hide the collision proxies while retaining the visual meshes.
        # Collision geoms remain active for contacts.
        for group in hidden_groups:
            viewer.opt.geomgroup[int(group)] = 0
        for group in visible_groups:
            viewer.opt.geomgroup[int(group)] = 1
        viewer.cam.lookat[:] = [0.0, 0.0, 0.0]
        viewer.cam.distance = max(model.stat.extent * 1.8, 4.0)
        viewer.cam.azimuth = 135.0
        viewer.cam.elevation = -55.0
        viewer.sync()

        while viewer.is_running():
            step_start = time.perf_counter()
            mujoco.mj_step(model, data)
            viewer.sync()
            remaining = model.opt.timestep - (time.perf_counter() - step_start)
            if remaining > 0:
                time.sleep(remaining)
