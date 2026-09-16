# ArenaX for dog3 / D1

[English](README_en.md)

把 **dog3（12-DOF 纯腿四足）** 和 **D1（16-DOF 轮足四足）** 的策略接入
[ArenaX Robotics](https://github.com/Lain-Ego0/ArenaX)，在 MuJoCo 中做地形与障碍通过性验证。

上游 ArenaX 提供场地编辑器（PyQt）+ 内嵌 MuJoCo 验证页面 + 地形生成。本仓库在其之上做了三件事：

1. **接入 dog3 与 D1** 两个机器人（模型、策略、配置、注册表）；
2. 把机器人接入做成**配置驱动** —— 以后再加新机器人，只需补一份 profile，不必改代码；
3. 修了两处 **sim2sim 保真度**问题（执行器延迟、出生高度），否则策略在纯 MuJoCo 里不出步态。

![场地编辑器](assets/Image/editor-overview.png)

```
configs/<robot>.yaml                     运行时 profile（观测布局、增益、延迟、出生高度…）
assets/<robot>/mjcf/{<robot>,scene}.xml  模型资产（含 meshes/*.STL）
policies/<robot>/policy.onnx             ONNX 策略
terrain_generator/robots.py              机器人注册表（CLI 与 GUI 下拉框都读它）
```

## 已接入机器人

| 机器人 | 构型 | obs → act | 策略来源 | 关键差异 |
|---|---|---|---|---|
| **dog3** | 12-DOF 纯腿四足（hip/thigh/calf ×4） | **51 → 12** | dog3lab（Isaac Lab 训练） | 含 6 维步态相位观测 |
| **D1** | 16-DOF **轮足**四足（hip/thigh/calf/**wheel** ×4） | **57 → 16** | InstinctLab `d1_locomotion_flat` | 轮子走**软件速度环**，无步态相位观测 |

两者共用同一套代码路径：观测按 `obs_terms` 项名列表拼装、动作按逐关节 `action_scales` 缩放、
轮子（`wheel_indices`）由 `kd * (action*vel_scale − dq)` 驱动，腿由 PD 位置环驱动。
m20 / go2 的既有行为保持不变。

## 实测效果

两表均为「同一份策略、命令 0.5 m/s」下的 ArenaX 实测（**地形长度取得足够长，避免走下 8 m 边缘**）：

**dog3**（12-DOF 纯腿，跑 15 s）

| 地形 | 前进速度 | 存活 | 最大倾角 |
|---|---|---|---|
| `flat` | 0.081 m/s | ✓ | 10.8° |
| `noise` (height 0.05) | 0.084 m/s | ✓ | 10.0° |
| `noise` (height 0.1) | 0.081 m/s | ✓ | 10.1° |
| `stairs` (height 0.1) | 0.087 m/s | ✓ | 10.1° |
| `obstacle_mix` (height 0.1) | 0.081 m/s | ✓ | 10.1° |
| `slope` (height 0.1) | 0.027 m/s（上坡） | ✓ | 9.9° |

**D1**（16-DOF 轮足，跑 20 s）

| 地形 | 前进距离 | 均速 | 存活 | 最大倾角 |
|---|---|---|---|---|
| `flat` | 6.36 m | 0.32 m/s | ✓ | 1.19° |
| `noise` (height 0.1) | 6.15 m | 0.31 m/s | ✓ | 8.31° |
| `stairs` (height 0.1) | 5.94 m | 0.30 m/s | ✓ | 2.40° |
| `slope` (height 0.1) | 6.22 m | 0.31 m/s | ✓ | 1.64° |
| `obstacle_mix` (height 0.05) | 2.82 m | 0.14 m/s | ✓ | 4.12° |

两个机器人在全部内置地形上均无摔倒；D1 的跟踪约 0.31/0.5 ≈ 62%，与其训练侧
`error_vel_xy ≈ 0.5`（"能用但不精准"）一致。

## 快速开始

使用仓库自带的 `.venv`：

```bash
./install.sh          # 用 uv 建 .venv（Python 3.12）并安装依赖；Windows 用 .\install.ps1
```

命令行跑策略（**必须带 `--policy`**，它才会把机器人场景合并进地形）：

```bash
# dog3
.venv/bin/python -m terrain_generator.cli \
  --robot dog3 --policy policies/dog3/policy.onnx \
  --type obstacle_mix --height 0.1 --length 30 --cols 384 \
  --duration 30 --output generated/dog3

# D1
.venv/bin/python -m terrain_generator.cli \
  --robot d1 --policy policies/d1/policy.onnx \
  --type flat --length 30 --cols 384 \
  --duration 60 --output generated/d1
```

不带 `--headless` 会弹出 MuJoCo 交互窗口；加 `--headless` 则只打印量化结果：

```text
Episode 1: {'survived': True, 'distance_x': 6.36, 'max_tilt_deg': 1.19}
```

打开图形化场地编辑器（布置障碍、从地形库加载完整场景，点 `→` 进入内嵌 MuJoCo 页面）：

```bash
.venv/bin/python -m terrain_generator.cli --edit --output generated/editor
```

编辑器右侧的机器人下拉框会列出 **M20 / Go2 / Dog3 / D1**（读自 `terrain_generator/robots.py`）。

> **两个踩坑提醒**
> 1. **必须带 `--policy`**：`base_scene`（把机器人场景并入地形）只在传 `--policy` 时设置。
>    否则生成的 XML 里机器人关节数为 0，画面里只剩地形和演示小球。
>    自检：`grep -c FL_hip_joint generated/d1/terrain.xml` 应 > 0。
> 2. **地形别用默认的 8 m**：机器人走到约 4.3 m 就出边缘掉了（看起来像"通过性失败"）。
>    高度场地形请把 `--height` 缩放到机器人尺度（dog3：0.05–0.1 m；D1：≤0.1 m）。

## 本仓库相对上游的改动

### 1. 配置驱动的多机器人泛化

`terrain_generator/simulation/m20.py` 原本把机器人相关的量写死在代码里，现在全部从 profile 读：

| 配置项 | 作用 |
|---|---|
| `obs_terms` | 观测按**项名列表**拼装（不再是固定顺序），并据此校验 `num_obs` |
| `action_scales` / `vel_scale` | 逐关节动作缩放；轮子用 `vel_scale`（速度目标 = action × vel_scale） |
| `wheel_indices` | 轮子关节下标；这些关节的姿态项在观测里置零、位置环里跳过 |
| `gait_phase` + `gait_period` | 6 维步态相位观测 `[sin φ, cos φ, sin(φ/2), cos(φ/2), sin(φ/4), cos(φ/4)]`（dog3 用，D1 不用） |
| `num_obs_hist` | 历史帧数（dog3 / D1 均为 0，即无历史；m20 为 5） |
| `actuator_delay_steps` | 执行器延迟，对齐 Isaac 的 `DelayedPDActuator`（见下） |
| `spawn_clearance` | 出生点相对地形表面的余量（见下） |
| `viewer_camera_*` / `viewer_*_geomgroups` | 相机与 geom 分组，用于适配不同尺寸 / 不同分组的机器人 |

新增 `terrain_generator/robots.py` 作为机器人注册表：`assets/<robot>` / `policies/<robot>` /
`configs/<robot>.yaml` 按约定自动推导，CLI、GUI、控制面板都不再硬编码机器人名
（`--robot` 的可选值也改为读注册表）。

`viewer_geomgroups()` 同时修掉了一处硬编码：原来观看器写死「隐藏 group 1、显示 group 2」，
这是 m20/go2/dog3 的约定；而 **D1 的视觉 mesh 在 group 1、group 2 是空的**，
按老逻辑会把整只机器人藏掉、只剩演示小球。现在按 profile 的
`viewer_hidden_geomgroups` / `viewer_visible_geomgroups` 决定。

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

## 配置要点

### `configs/dog3.yaml`

| 项 | 值 | 说明 |
|---|---|---|
| `num_obs` / `num_actions` | 51 / 12 | 45 本体 + 6 步态相位 |
| `obs_terms` | `[ang_vel, gravity, commands, dof_pos, dof_vel, actions, gait_phase]` | 顺序须与训练端一致 |
| `num_obs_hist` | 0 | 无历史帧 |
| `default_angles` | 全 0 | URDF 关节零位即站姿 |
| `kps` / `kds` | 40 / 1.0 | 与训练端执行器增益一致 |
| `action_scales` | hip 0.125、thigh/calf 0.25 | 逐关节 |
| `control_dt` / `simulation_dt` / `control_decimation` | 0.02 / 0.005 / 4 | 50 Hz 策略、200 Hz 物理 |
| `actuator_delay_steps` | 1 | 对齐训练端执行器延迟 |
| `spawn_clearance` | 0.06 | 出生点高出地形表面 6 cm |
| `wheel_indices` | `[]` | 纯腿 |

### `configs/d1.yaml`

| 项 | 值 | 说明 |
|---|---|---|
| `num_obs` / `num_actions` | 57 / 16 | 3+3+3+16(`dof_pos`)+16(`dof_vel`)+16(`actions`) |
| `obs_terms` | `[ang_vel, gravity, commands, dof_pos, dof_vel, actions]` | 顺序须与训练端一致（**无 gait_phase**） |
| `num_obs_hist` | 0 | 无历史帧 |
| `default_angles` | `[0, 0.8, −1.5, 0] ×4` | **关节零位不是站姿**（全零时腿更伸，站高 0.50 m；训练站姿 0.37 m） |
| `kps` / `kds` | 腿 `60 / 2.0`、轮 `0 / 0.5` | 轮子的 `kd` 即软件速度环增益 |
| `torque_limits` | 腿 60、轮 12 N·m | 与训练端 effort limit 一致 |
| `action_scales` / `vel_scale` | 腿 0.25、轮 `vel_scale 5.0` | 轮：`tau = kd·(action·5.0 − dq)` |
| `wheel_indices` | `[3, 7, 11, 15]` | FL/FR/RL/RR 的 foot 关节 |
| `control_dt` / `simulation_dt` / `control_decimation` | 0.02 / 0.005 / 4 | 50 Hz 策略、200 Hz 物理 |
| `viewer_hidden_geomgroups` / `viewer_visible_geomgroups` | `[3]` / `[1]` | D1 的视觉在 group 1（非 group 2） |

## 致谢

上游项目：[Lain-Ego0/ArenaX](https://github.com/Lain-Ego0/ArenaX) —— 场地编辑器、地形生成、
内嵌 MuJoCo 验证页面均来自上游。本仓库仅新增 dog3 / D1 接入与上述泛化 / 保真度改动。
