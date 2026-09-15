# ArenaX for dog3

把 **dog3 四足机器人（12-DOF 纯腿式）** 的策略接入 [ArenaX Robotics](https://github.com/Lain-Ego0/ArenaX)，
在 MuJoCo 中做地形与障碍通过性验证。

上游 ArenaX 提供场地编辑器（PyQt）+ 内嵌 MuJoCo 验证页面 + 地形生成；本仓库的增量是
**把 dog3 接进来**，并且把这套接入做成**配置驱动**的 —— 之后再加新机器人，只需补一份 profile，不必改代码。

![场地编辑器](assets/Image/editor-overview.png)

```
configs/dog3.yaml                 运行时 profile（观测布局、增益、延迟、出生高度…）
assets/dog3/mjcf/{dog3,scene}.xml + meshes/*.STL(17)
policies/dog3/policy.onnx         51 → 12
terrain_generator/robots.py       机器人注册表（GUI 下拉框也读它）
```

## 实测效果

同一份策略，命令 0.5 m/s、跑 15 秒，ArenaX 内置全部地形均通过：

| 地形 | 前进速度 | 存活 | 最大倾角 |
|---|---|---|---|
| `flat` | 0.081 m/s | ✓ | 10.8° |
| `noise` (height 0.05) | 0.084 m/s | ✓ | 10.0° |
| `noise` (height 0.1) | 0.081 m/s | ✓ | 10.1° |
| `stairs` (height 0.1) | 0.087 m/s | ✓ | 10.1° |
| `obstacle_mix` (height 0.1) | 0.081 m/s | ✓ | 10.1° |
| `slope` (height 0.1) | 0.027 m/s（上坡） | ✓ | 9.9° |

机器人步态为对角小跑，全地形无摔倒。

## 快速开始

```bash
./install.sh          # 用 uv 建 .venv（Python 3.12）并安装依赖
```

命令行跑策略：

```bash
.venv/bin/python -m terrain_generator.cli \
  --robot dog3 --policy policies/dog3/policy.onnx \
  --type obstacle_mix --height 0.1 --duration 30 --output generated/dog3
```

打开图形化场地编辑器（可布置障碍、从地形库加载完整场景，并点 `→` 进入内嵌 MuJoCo 页面）：

```bash
.venv/bin/python -m terrain_generator.cli --edit --output generated/editor
```

编辑器右侧的机器人下拉框选择 **Dog3** 即可运行 dog3 策略。

> 高度场地形请把 `--height` 缩放到 dog3 的尺度（**0.05–0.1 m**）：dog3 站高只有 0.30 m，
> 用上游默认的 0.8 m 会显著超出它的能力范围。

## 本仓库相对上游的改动

### 1. 配置驱动的多机器人泛化

`terrain_generator/simulation/m20.py` 原本把机器人相关的量写死在代码里，现在全部从 profile 读：

| 配置项 | 作用 |
|---|---|
| `obs_terms` | 观测按**项名列表**拼装（不再是固定顺序），并据此校验 `num_obs` |
| `action_scales` | 逐关节动作缩放（dog3：hip 0.125、thigh/calf 0.25） |
| `gait_phase` + `gait_period` | 6 维步态相位观测 `[sin φ, cos φ, sin(φ/2), cos(φ/2), sin(φ/4), cos(φ/4)]` |
| `num_obs_hist` | 历史帧数（dog3 为 0，即无历史） |
| `actuator_delay_steps` | 执行器延迟，对齐 Isaac 的 `DelayedPDActuator`（见下） |
| `spawn_clearance` | 出生点相对地形表面的余量（见下） |
| `viewer_camera_*` / `viewer_*_geomgroups` | 相机与 geom 分组，用于适配不同尺寸的机器人 |

新增 `terrain_generator/robots.py` 作为机器人注册表：`assets/<robot>` / `policies/<robot>` /
`configs/<robot>.yaml` 按约定自动推导，CLI、GUI、控制面板都不再硬编码机器人名。
m20 / go2 的既有行为保持不变（新配置项的默认值等于原行为）。

### 2. 两处 sim2sim 保真度修复

**执行器延迟**：训练端用的是 Isaac 的 `DelayedPDActuator(min_delay=0, max_delay=4)`，
即 **4 个物理步 = 20 ms = 一个完整控制周期**；而纯 MuJoCo 回路是零延迟，策略因此不产生步态
（关节摆幅只有 0.01–0.13 rad，原地站立）。补上 `actuator_delay_steps: 1` 后步态恢复。

延迟必须**同时**作用于「实际施加的力矩」和「回报给策略的 `last_action`」，两者不一致时效果反而更差：

| 配置 | 前进速度 | 关节摆幅 |
|---|---|---|
| 无延迟 | ≈0 | 0.13 |
| 只延迟观测回报的动作 | ≈0 | 0.13 |
| 只延迟实际施加的力矩 | ≈0 | 0.29（腿在动但不前进） |
| **两处一致延迟** | **0.080 m/s** | **0.35** |

**出生高度**：`init_base_height` 表示**站高**，因此应相对地形表面测量。原实现把它当成绝对 z，
在高度场地形上机器人会被按进地形（接触数从 8 涨到 68），腿被卡死。现在 `reset()` 会先测量出生点
周围的地面高度（4 点环状采样取中位数），再加上站高与 `spawn_clearance` 余量。

## 配置文件要点（`configs/dog3.yaml`）

| 项 | 值 | 说明 |
|---|---|---|
| `num_obs` | 51 | 45 本体 + 6 维步态相位 |
| `num_actions` | 12 | FL/FR/RL/RR × hip/thigh/calf |
| `obs_terms` | `[ang_vel, gravity, commands, dof_pos, dof_vel, actions, gait_phase]` | 顺序须与训练端一致 |
| `num_obs_hist` | 0 | 无历史帧 |
| `default_angles` | 全 0 | URDF 关节零位即站姿 |
| `kps` / `kds` | 40 / 1.0 | 与训练端执行器增益一致 |
| `action_scales` | hip 0.125、thigh/calf 0.25 | 逐关节 |
| `control_dt` / `simulation_dt` / `control_decimation` | 0.02 / 0.005 / 4 | 50 Hz 策略、200 Hz 物理 |
| `actuator_delay_steps` | 1 | 对齐训练端的执行器延迟 |
| `spawn_clearance` | 0.06 | 出生点高出地形表面 6 cm |

## 致谢

上游项目：[Lain-Ego0/ArenaX](https://github.com/Lain-Ego0/ArenaX) —— 场地编辑器、地形生成、
内嵌 MuJoCo 验证页面均来自上游。本仓库仅新增 dog3 接入与上述泛化 / 保真度改动。
