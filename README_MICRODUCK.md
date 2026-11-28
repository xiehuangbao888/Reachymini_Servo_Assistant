# Microduck 舵机调试助手使用指南

适用于本项目的 **Microduck 模式**，以 face-board-v1、板载串口 `/dev/ttyS2` 和 XL330 舵机为例。本文按 2026-11-28 的代码整理；其他硬件版本请先核对串口和舵机型号。

本工具支持扫描、读取控制表、JSON 备份、恢复参数和修改 ID。**“恢复参数”不是刷写舵机固件，也不是更新 Microduck OS 或安装跑步策略。** 系统升级包 `.raucb`、策略文件 `.onnx` 都不能导入这里。

## 目录

- [1. 使用前准备](#1-使用前准备)
- [2. 已安装的鸭子：快速打开网页](#2-已安装的鸭子快速打开网页)
- [3. 首次安装](#3-首次安装)
- [4. 连接与扫描](#4-连接与扫描)
- [5. 保存与查看备份](#5-保存与查看备份)
- [6. 恢复舵机参数](#6-恢复舵机参数)
- [7. 修改舵机 ID](#7-修改舵机-id)
- [8. 退出并恢复机器人服务](#8-退出并恢复机器人服务)
- [9. 同时使用两只鸭子](#9-同时使用两只鸭子)
- [10. 常见问题](#10-常见问题)
- [11. 更新助手与演示模式](#11-更新助手与演示模式)
- [12. 参考与验证范围](#12-参考与验证范围)

## 1. 使用前准备

### 程序运行在哪里

推荐方式：**助手运行在鸭子上，电脑通过 SSH 隧道打开网页。** 鸭子上的 Python 程序访问 `/dev/ttyS2`，电脑负责显示界面。仅在电脑上启动网页，不能隔着 Wi-Fi 读取鸭子的板载串口。

也可以在电脑上运行助手，通过外接、兼容的 DYNAMIXEL TTL 串口适配器检测独立舵机。这时选择适配器的真实串口，并按硬件要求供电，不使用 `/dev/ttyS2`；不要同时让鸭子主板和外部适配器驱动同一总线。

### 准备事项

1. 让鸭子平放或可靠支撑。暂停 `robotd` 或恢复参数时，关节可能失去支撑；恢复服务时也可能重新上力。
2. 保证电量和连接稳定。拆接舵机线前先关机断电，不在写入期间拔电或关闭终端。
3. 电脑与鸭子之间网络可达，鸭子已开启 SSH。
4. 确认要操作的机器人名称、蓝牙地址和当前 IP；多只鸭子不要只凭旧 IP 区分。
5. 退出其他使用舵机串口的程序。助手运行期间暂停 `robotd`，不要同时用遥控器控制鸭子。

在**电脑**终端查看当前 IP（前提是电脑已安装并可使用 `duckctl`）：

```bash
duckctl scan
```

本文中的 `DUCK_IP` 都是占位符，要替换成扫描到的 IP，不能原样输入，也不要在地址后带逗号。SSH 用户名以下使用 `microduck`，密码使用该设备实际设置的登录密码；蓝牙 PIN 不是 SSH 密码。

在**电脑**连接，在**鸭子**检查健康状态：

```bash
ssh microduck@DUCK_IP
```

```bash
robotctl version
robotctl health
```

若 SSH 被拒绝，先按当前固件的官方说明开启 Wi-Fi SSH。此前测试的 OS v1.4.2 可通过长按脸部维护按钮约 5 秒、听到提示声后临时开启；不同固件以官方文档为准。不要为解决一次连接问题直接禁用 SSH 身份校验。

## 2. 已安装的鸭子：快速打开网页

这一节适用于已经按此前部署方案安装、且存在下列文件的鸭子：

```text
/var/lib/robot/tools/servo-assistant/
├── app/                 # 本项目代码
├── venv/                # 鸭子自身的 Python 环境
└── start-web.sh          # 另外部署的服务切换脚本
```

**`start-web.sh` 不在本仓库中。** 刚下载本仓库的新设备请从第 3 节安装；不要假定已经有此脚本。此前脚本固定使用端口 8767，如果设备上的脚本曾被改为其他端口，以脚本内容为准。

在**电脑终端**执行：

```bash
ssh -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -L 127.0.0.1:8767:127.0.0.1:8767 \
  microduck@DUCK_IP \
  'sh /var/lib/robot/tools/servo-assistant/start-web.sh'
```

输入 SSH 密码；脚本请求 `sudo` 时，按提示输入对应密码。保持终端打开，看到服务启动地址后，在**电脑浏览器**打开：

[http://127.0.0.1:8767/?lang=zh](http://127.0.0.1:8767/?lang=zh)

此前部署的脚本会记录 `robotd` 原状态、暂停它，并在正常退出时尝试恢复原先运行的服务。如果启动前服务本来已停止，脚本不会自动将其启动。

网页操作：**选择 Microduck → `/dev/ttyS2` → `1000000` → 连接并扫描 → 备份全部舵机**。

完成后按第 8 节退出。关闭浏览器标签页不会停止助手，也不会恢复 `robotd`。

## 3. 首次安装

以下命令明确区分执行位置。Microduck OS 是嵌入式系统，不应直接照搬 Ubuntu 的 `apt install` 命令，也不要替换系统 Python。

### 3.1 在鸭子的数据目录准备代码

在**鸭子的 SSH 终端**执行：

```bash
sudo mkdir -p /var/lib/robot/tools/servo-assistant
sudo chown "$(id -u):$(id -g)" /var/lib/robot/tools/servo-assistant
cd /var/lib/robot/tools/servo-assistant
```

如果鸭子有 Git 且能访问 GitHub：

```bash
git clone https://github.com/xiehuangbao888/Reachymini_Servo_Assistant.git app
```

若 `app` 已存在，不要覆盖；先检查是不是已经安装，再参考第 11 节更新。

如果鸭子没有 Git，可以在**电脑**的空目录下载压缩包并上传：

```bash
curl -fL https://github.com/xiehuangbao888/Reachymini_Servo_Assistant/archive/refs/heads/main.tar.gz \
  -o servo-assistant-main.tar.gz
scp servo-assistant-main.tar.gz microduck@DUCK_IP:/var/lib/robot/tools/servo-assistant/
```

再在**鸭子**上解压到新建的空 `app` 目录：

```bash
cd /var/lib/robot/tools/servo-assistant
mkdir app
tar -xzf servo-assistant-main.tar.gz --strip-components=1 -C app
```

### 3.2 在鸭子上安装独立 Python 环境

项目要求 Python 3.10 或更高版本，已部署方案使用 Python 3.12。先检查：

```bash
python3 --version
```

若已有满足版本要求、包含 `venv` 和 `pip` 的 Python，在**鸭子**执行：

```bash
cd /var/lib/robot/tools/servo-assistant
python3 -m venv venv
./venv/bin/python -m pip install -r app/requirements.txt
```

若系统 Python 不满足条件，可使用 uv 安装独立 Python。下面是需要鸭子可访问下载源、系统架构和运行库受 uv 支持的替代方法；不要把电脑上的 x86 Python 或 `.venv` 直接复制到 ARM 鸭子上：

```bash
cd /var/lib/robot/tools/servo-assistant
curl -fL https://astral.sh/uv/install.sh -o install-uv.sh
# 可先查看下载的安装脚本；将 uv 放在数据目录，不修改 shell 配置。
env UV_INSTALL_DIR="$PWD/uv-bin" UV_NO_MODIFY_PATH=1 sh install-uv.sh
export UV_PYTHON_INSTALL_DIR="$PWD/python"
export UV_CACHE_DIR="$PWD/uv-cache"
export UV_HTTP_TIMEOUT=600
./uv-bin/uv python install 3.12
./uv-bin/uv venv --python 3.12 venv
./uv-bin/uv pip install --python venv/bin/python -r app/requirements.txt
```

若有网络、架构或运行库错误，应先解决该错误；此替代安装路线不代表已经在所有 Microduck OS 版本实测通过。相关选项见 [uv Python 安装](https://docs.astral.sh/uv/guides/install-python/)和[安装器说明](https://docs.astral.sh/uv/reference/installer/)。

验证环境：

```bash
./venv/bin/python -c "import dynamixel_sdk, serial; print('舵机助手依赖正常')"
ls -l /dev/ttyS2
```

### 3.3 首次手动启动：服务与网页

准备好支撑，记录服务原状态。在**鸭子终端**执行：

```bash
systemctl is-active robotd
sudo systemctl stop robotd
cd /var/lib/robot/tools/servo-assistant
./venv/bin/python app/web_tool.py --robot microduck --no-browser --lang zh --port 8767
```

本节是手动方式，**不会自动恢复 `robotd`**，用完必须按第 8 节处理。若串口权限不足，见第 10 节。

在**电脑另开一个终端**建立隧道：

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -L 127.0.0.1:8767:127.0.0.1:8767 microduck@DUCK_IP
```

隧道连接后一直没有输出通常是正常的。保持两个终端都打开，再访问：

[http://127.0.0.1:8767/?lang=zh](http://127.0.0.1:8767/?lang=zh)

服务只监听鸭子本机 `127.0.0.1`，因此不要直接访问 `http://鸭子IP:8767`。`--port` 是网页端口，与 SSH 的 22 端口、串口波特率是三回事。本指南显式指定 8767；程序不带 `--port` 时默认是 8765。

## 4. 连接与扫描

1. 在“选择机器人”中点击 **Microduck**，确认页面提示预期 15 个舵机。
2. 点击“刷新串口”，选择 **`/dev/ttyS2`**。
3. 波特率选择 **`1000000`**，点击“连接并扫描”。
4. 核对实际 ID、型号、固件版本、缺失 ID 和额外 ID。

Microduck 已配置的总线使用 1 Mbps。`57600` 可能用于未配置的新舵机，不是整只已配置鸭子的常规扫描速率。网页选择波特率只改变通信尝试，不会修改舵机中的波特率。

扫描使用所选波特率，不会自动遍历所有波特率。一次扫描超时约 8 秒，可点击“取消扫描”。有些错误文字沿用“U2D2”，板载模式下应对应检查 `/dev/ttyS2`、供电和服务占用。

### 默认 ID 对照

左右以机器人自身为准；标签按标准 ID 标注，改过 ID 或接线后须核对实际关节。

| ID | 位置 | ID | 位置 |
|---|---|---|---|
| 10 | 右髋偏航 | 20 | 左髋偏航 |
| 11 | 右髋侧倾 | 21 | 左髋侧倾 |
| 12 | 右髋俯仰 | 22 | 左髋俯仰 |
| 13 | 右膝 | 23 | 左膝 |
| 14 | 右脚踝 | 24 | 左脚踝 |
| 30 | 颈部俯仰 | 31 | 头部俯仰 |
| 32 | 头部偏航 | 33 | 头部侧倾 |
| 34 | 嘴部 | — | — |

整机预期 15 个舵机，包含嘴部；步态策略常说的 14 个动作不包含嘴部，两者不要混淆。

**扫描到 15 个只证明通信响应，不代表齿轮、零点、带载运动或温度都正常。** 本工具不是步态或关节运动测试程序。

切换机型会断开当前连接，清空扫描结果、当前备份状态和待执行计划，并载入对应机型的内置参数；已保存到磁盘的备份不会被删除。任务执行期间不能切换机型。

## 5. 保存与查看备份

点击 **“备份全部舵机”**，等待读取完成，再点击下载备份文件。即使只想恢复一台，也需要先备份当前总线上所有响应且受支持的舵机。

备份默认保存于**运行助手的设备**上：

```text
app/artifacts/hardware/backup_all_时间戳.json
```

下载后的副本由电脑浏览器保存到其下载目录，不会自动放到桌面。建议将副本命名为“机器人名称＋日期＋操作前/后”，并保留原始 JSON 内容。也可从电脑复制整个备份目录：

```bash
scp -r microduck@DUCK_IP:/var/lib/robot/tools/servo-assistant/app/artifacts/hardware ./microduck-backups
```

JSON 包含机型标记 `robot_type: "microduck"`、扫描连接信息及每台舵机的控制表。可查阅 `Hardware Error Status`、`Present Input Voltage`、`Present Temperature`、`Homing Offset`、`Current Limit` 和增益等条目。

扫描表主要显示 ID、型号和固件，**不是电压、温度的实时仪表盘**；要获取新的寄存器快照，需要重新备份。寄存器 `value` 通常是原始数值，例如 `Present Input Voltage=77` 表示 7.7 V；不要把所有寄存器值都直接当作安培、角度等工程单位。

“完整备份”指本次响应且受支持的舵机控制表读取完整，**不保证整机 15 台都在线**。例如只扫描到 14 台，备份仍可能成功，但缺失的那一台没有被备份。发现读取失败项时，文件会保留供诊断，程序不允许用该状态继续写入。

扫描、断开连接或切换机型后需要重新备份；恢复或修改 ID 的写入尝试也会使当前备份授权失效，下一次写入前必须再备份。

## 6. 恢复舵机参数

### 6.1 选择正确档案

Microduck 模式自动载入仓库内的 [`MICRODUCK_BACKUP_2.json`](MICRODUCK_BACKUP_2.json)，也可点击 **“使用内置参数”** 重新选择。

该档案与此前用户保存的桌面 `2.json` 内容一致，来源是 duck-6f11 升级 OS v1.4.2 后的 15 台 XL330-M288、舵机固件 V53 备份。其中 Current Limit=1000、Position P Gain=200，均是寄存器原始值。

它是**一台具体鸭子的参考备份，不是厂家认证的出厂参数或固件包**；不能因为按钮叫“内置参数”就假定适合所有硬件和机械零点。载入档案只选择参考数据，不会写入舵机。

也可点击 **“更换 JSON”** 导入自己的 Microduck 备份。不要导入 Reachy Mini 的档案。没有 `robot_type` 标记的旧档案按 Reachy Mini 处理；确认是旧 Microduck 备份时，应先核实来源和控制表结构再适配，不能只改标签绕过检查。

### 6.2 生成计划、确认与校验

1. 扫描并完成当前总线备份，将文件下载到电脑。
2. 选择内置参数或导入有可靠来源的备份。
3. 只勾选要恢复的舵机，点击 **“生成恢复计划”**。
4. 核对当前 ID、档案 ID、最终 ID、型号及各寄存器的写入前后值。
5. 确认目标和参数无误后点击 **“确认恢复”**；保持支撑、供电和终端连接。
6. 等待日志报告校验结果，下载日志。不要把“已开始”当作成功。
7. 完成后重新备份、按第 8 节退出，并按成功提示安排断电再上电检查。

网页要求当前 ID、档案 ID、最终 ID 一致，型号匹配，并保持当前总线波特率；档案波特率不同会被拒绝。固件版本对应的 Indirect Address 布局也会检查兼容性。

计划中的“差异数”不等于最终“写入数”。即使差异为零，确认恢复仍可能重写配置；只检查状态时无需点击确认。生成计划后若寄存器发生变化，程序会拒绝旧计划，要求重新备份和生成计划。

### 6.3 写入范围与结果

恢复会写入支持的配置项，包括适用的 EEPROM 配置、PID/PI 增益、Profile 设置、Watchdog 和 Indirect Address 等。Status Return Level 最后处理。

不把备份中的 Goal Position、Goal Velocity、Goal Current、Goal PWM 等运行命令回放到机器人，也不写回只读状态或 Indirect Data。**ID 修改使用独立功能；本网页不提供总线波特率修改流程。**

写入过程中会关闭目标舵机扭矩，结束后保持 **Torque OFF**。成功标志是日志中的 `RESTORE + VERIFY SUCCESS` 及各目标回读校验通过。失败时可能已有部分配置写入，**不是自动回滚**；不要连续重试，应先保存日志、重新读取和确认当前状态。

## 7. 修改舵机 ID

用于修复更换舵机后的 ID，或按实际装配纠正 ID；机器人控制程序依赖固定的关节 ID，不能随意编号。

1. 完成当前连接的全量备份。
2. 在“修改舵机 ID”选择当前舵机，输入未占用的新 ID（0～252）。
3. 点击 **“检查并生成修改计划”**，核对旧 ID、新 ID 和实际关节。
4. 点击 **“确定修改”**，等待写入和回读结果。
5. 再次扫描并重新备份，确认目标以新 ID 响应。

工具会检查新 ID 是否占用，修改时关闭目标扭矩，完成后保持关闭。参数档案不会随 ID 自动改名；之后恢复参数按新 ID 匹配。

若总线上已有重复 ID，广播扫描不能可靠区分两台同 ID 舵机。应先关机断电，隔离出待修改的一台，再上电操作，不能在整条重复 ID 总线上尝试“任选一台”修改。

## 8. 退出并恢复机器人服务

1. 等待当前扫描、备份或写入任务结束，并下载备份和日志。
2. 在运行助手的终端按 `Ctrl+C`。出现等待当前操作结束提示时，等它完成。
3. 若使用第 2 节的既有脚本，观察其恢复服务结果；sudo 会话过期可能要求再次输入密码。
4. 若手动启动，或者意外断线，重新 SSH 登录，确认助手进程已退出后恢复此前运行的服务：

```bash
ps -ef | grep '[w]eb_tool.py'
sudo systemctl start robotd
systemctl is-active robotd
robotctl health
```

如果仍看到助手进程，先回到启动它的终端正常退出，避免与 `robotd` 同时访问串口。不应对仍在写入的进程直接强制终止。

恢复服务前保持鸭子受支撑。若服务原本因维修而被人工停用，先确认维修完成，再决定是否启动。最后关闭电脑的 SSH 隧道终端。

官方运行时启动可能重新设置部分舵机参数；助手里的改动不一定会长期保留。Homing Offset 等参数还涉及机械装配，恢复备份不等同于零点校准。

## 9. 同时使用两只鸭子

每只鸭子使用独立终端和独立本地网页端口。在每次写入前确认终端连接的是哪只鸭子。

本工具校验请求中的 Host 端口，**建议本地隧道端口、鸭子服务端口、浏览器地址三者一致**：

| 设备 | 鸭子上的助手端口 | 电脑隧道映射 | 电脑浏览器 |
|---|---|---|---|
| 第一只 | `--port 8767` | `8767:127.0.0.1:8767` | `http://127.0.0.1:8767/?lang=zh` |
| 第二只 | `--port 8768` | `8768:127.0.0.1:8768` | `http://127.0.0.1:8768/?lang=zh` |

第二只采用第 3.3 节手动启动方式，把两条命令中的 8767 全部替换为 8768，并换成第二只鸭子的 IP。固定 8767 的旧启动脚本不会因为你改变 SSH 隧道端口就自动改成 8768。

不要在同一只鸭子上启动两个助手去竞争 `/dev/ttyS2`。

## 10. 常见问题

### SSH 超时、拒绝连接或主机密钥变化

- **超时**：重新扫描 IP，确认网络可达，检查访客 Wi-Fi 的设备隔离和代理/VPN 路由。
- **Connection refused**：目标拒绝 SSH 连接，检查 SSH 是否开启；这不是密码错误。
- **主机密钥变化**：先核实该 IP 对应的是自己的鸭子，以及是否刚升级/重装系统。确认身份后再清理该 IP 的旧记录并重连：

```bash
ssh-keygen -R DUCK_IP
ssh microduck@DUCK_IP
```

不要用关闭 `StrictHostKeyChecking` 代替身份确认。

### 网页打不开、端口被占用或出现 Host/请求错误

确认鸭子上的服务仍运行，电脑 SSH 隧道没有退出，浏览器使用 `127.0.0.1` 或 `localhost`，并核对三处端口一致。出现 `Address already in use` 时，检查是否已有旧隧道或助手；关闭对应实例或按第 9 节完整换端口。

### 找不到 `/dev/ttyS2`，或提示权限不足

先确认 Python 程序运行在鸭子上，再检查：

```bash
ls -l /dev/ttyS2
id
```

串口不存在时应检查硬件/系统版本，不能改选 Reachy Mini 的 `/dev/ttyAMA3` 来碰运气。权限不足时优先按设备权限配置解决；必要的临时诊断可以用同一虚拟环境的绝对路径运行，但会产生 root 所有的备份文件：

```bash
sudo /var/lib/robot/tools/servo-assistant/venv/bin/python \
  /var/lib/robot/tools/servo-assistant/app/web_tool.py \
  --robot microduck --no-browser --lang zh --port 8767
```

同样必须先暂停 `robotd`。不建议用 `chmod 777` 放开串口。

### 扫描超时、找不到舵机或少了一台

依次检查支撑和供电、`robotd` 是否已停止、串口是否正确、波特率是否为 1000000、是否有其他串口程序。仍缺失时关机断电检查线缆、接头、连接顺序及是否存在重复 ID。

缺失 ID 不能通过恢复其他舵机的参数来修复。“未响应”也不足以判定舵机本体损坏。新舵机可能采用不同 ID/波特率，应单独检测；本网页不能把不同波特率的新舵机自动初始化为整机配置。

### 有错误码，是否代表坏了

备份中的 `Hardware Error Status` 是位掩码，要结合该型号控制表、温度、供电和机器人配置判断。此前 Microduck 实机记录中出现过电压报警位为 1、但官方健康检查正常的情况；不能仅凭这一位或某一次电压读数断定损坏。也不要通过盲目改报警阈值或 Shutdown 来消除故障提示。

所有 ID 都响应也不能排除摔落后的齿轮、零点或负载问题。恢复服务后结合 `robotctl health` 与受支撑状态下的检查判断。

### 参数不匹配、备份失效或恢复按钮不可用

确认选择 Microduck，备份来自当前连接且完整，参考档案机型/型号/ID/波特率相符。切换机型、重新扫描、修改 ID 或尝试写入后重新备份。不要手工篡改档案标签绕过型号和机型检查。

### 用完后鸭子不走了

先检查是否仍有助手进程、`robotd` 是否恢复、`robotctl health` 是否正常。恢复写入后 Torque 保持关闭是工具的预期行为；不要在助手仍占用串口时启动运动控制。

## 11. 更新助手与演示模式

### 更新已有 Git 安装

退出助手并将备份另存到电脑，再在鸭子执行：

```bash
cd /var/lib/robot/tools/servo-assistant/app
git status --short
git pull --ff-only
../venv/bin/python -m pip install -r requirements.txt
```

有本地代码修改或合并冲突时先保留并核对，不要直接 `reset --hard`。使用 uv 创建且没有 pip 的环境，可以在上一级目录使用 `./uv-bin/uv pip install --python venv/bin/python -r app/requirements.txt`。

压缩包安装没有 Git 历史，不能直接 `git pull`；把新版解压到另一目录验证后再替换代码，并保留旧 `app/artifacts`、环境目录和原始备份。更新助手不会自动升级 Microduck OS 或舵机固件。

### 在电脑上熟悉界面

安装好项目依赖后，可以运行纯内存演示：

```bash
python web_tool.py --demo --robot microduck --lang zh --port 8767
```

演示不会访问真实串口。当前模拟设备沿用原项目的小型样本，不是完整的 15 舵机 Microduck，因此可能显示缺失或不匹配；不要用演示扫描结果判断实体鸭子，也不要把演示备份作为真实恢复参数。

## 12. 参考与验证范围

- [项目主说明](README.md)
- [Microduck 官方操作说明](https://github.com/pollen-robotics/microduck/blob/main/docs/robot/cheatsheet.md)
- [Microduck 官方蓝牙工具说明](https://github.com/pollen-robotics/microduck/blob/main/docs/robot/duckctl.md)
- [XL330-M288 控制表](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)

本项目此前实机验证过扫描、读取备份和生成计划；恢复参数、修改 ID 的自动测试使用模拟总线，不等于所有硬件状态下的写入结果都经过实机验证。文中的首次安装替代方案和故障排查命令需结合实际系统执行。

开发者验证命令（已安装依赖及 Node.js 的环境）：

```bash
python -m unittest discover -s tests -q
node tests/test_i18n.js
node --check web/app.js
```
