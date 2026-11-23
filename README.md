# reachymini 舵机调试助手

[English documentation](README_EN.md)

页面右上角可选择 **中文 / English**。语言切换会保留当前连接、备份和目标选择，并记住偏好；也可用 `http://127.0.0.1:8767/?lang=en` 直接打开英文版（端口按启动时的实际值填写）。Windows 使用 `python launch.py --lang en`、macOS 使用 `python3 launch.py --lang en` 可直接启动英文页面。英文使用说明见 `README_EN.md`。页面翻译工具产生的状态和诊断信息；下载的日志保留原始内容，串口驱动等外部错误可能保留系统语言。

把原命令行工具接到本机网页上，支持 XL330-M288（1200）和 XL330-M077（1190）、DYNAMIXEL Protocol 2.0。这是**控制表配置参数的备份与恢复**，不升级舵机固件。

原始 `dynamixel_xl330_backup_restore.py` 保持原样，网页服务复用其中的串口通信、配置项筛选、逐项写入及回读校验逻辑。内置默认参数 `DYNAMIXEL_XL330_BACKUP.json` 已替换为用户指定的 `backup_all_20261120_153857_997605.json`，内容完全一致。此前随附的 2026-08-19 参数保存在 `presets/DYNAMIXEL_XL330_BACKUP_original_20260819.json`，不会默认加载。

默认基准包含 9 台 V53 舵机：ID 10、17、18 的位置 P 为 200，ID 11～16 的位置 P 为 300，全部位置 I / D 为 0。服务启动时自动加载该基准，页面显示来源文件名。备份中的 Goal PWM 为 699 / 708，但它属于运动指令，仍不在配置恢复范围内；目标位置、速度、电流同样不写入。

## 安装与启动

先安装 Python 3.10 或更新版本。Windows 安装时勾选 **Add Python to PATH**。首次安装依赖需要联网。

Windows PowerShell：

```powershell
git clone https://github.com/xiehuangbao888/Reachymini_Servo_Assistant.git
cd Reachymini_Servo_Assistant
python -m pip install -r requirements.txt
python web_tool.py
```

如果已克隆并进入项目目录，只需执行最后两条命令。

macOS Terminal（推荐使用虚拟环境，避免系统 Python 的安装限制）：

```bash
git clone https://github.com/xiehuangbao888/Reachymini_Servo_Assistant.git
cd Reachymini_Servo_Assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python web_tool.py
```

启动后自动打开浏览器，默认地址为 <http://127.0.0.1:8765>。请保留终端窗口。Windows 与 macOS 使用相同代码，各自在连接 U2D2 的电脑上启动；不要跨系统复制 `.venv`。

常用启动选项：

```bash
# 默认端口被占用时
python web_tool.py --port 8767
# 英文页面
python web_tool.py --lang en --port 8767
# 只使用模拟设备，不接触真实串口
python web_tool.py --demo --port 8766
```

用 `Ctrl+C` 停止服务；真实写入进行中时请等待完成再退出。Windows 若只有 `py` 命令，可将 `python` 换为 `py -3`。

可选自动启动器：Windows 用 `python launch.py`，macOS 用 `python3 launch.py`。它自动创建 `.venv` 并检查、安装依赖，接受与 `web_tool.py` 相同的参数。

## 选错串口或扫描超时

连接和扫描在独立进程执行，最多等待 8 秒；异常驱动、串口打开、SDK 扫描或关闭阻塞时，会结束扫描进程后解除按钮锁定。也可点击“取消扫描”，等待状态结束后重新选择。扫描只发送发现设备的 Ping 指令，不写配置寄存器。恢复写入期间不提供强制取消。

Windows 串口一般显示为 `COM…`，macOS 一般显示为 `/dev/cu.usbserial…`；应按 U2D2 插拔前后出现的端口辨认，不要选择蓝牙串口。异常端口名称本身不会证明它是 U2D2。

如果仍运行旧版本且已卡住，先关闭原来的启动终端，再用上述命令启动新版本并刷新网页。若提示 8765 已被占用，关闭原服务后重试，或使用 `--port 8767` 启动另一个端口。

## Windows 虚拟环境（可选）

无需激活虚拟环境，即可使用其中的 Python 安装和运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe web_tool.py
# 无硬件演示：
.\.venv\Scripts\python.exe web_tool.py --demo --port 8766
```

macOS / Linux：使用 Python 3.10+，创建虚拟环境、安装依赖，再运行 `python web_tool.py`。Linux 需有相应串口设备的访问权限。

## 恢复流程（例如排查 S5）

1. 退出 Reachy Mini 守护进程、调试程序等占用 U2D2 串口的软件。确认舵机正常供电，并托稳机构；关闭 Torque 会失去主动支撑。
2. 在“连接设备”中选择 U2D2 串口及 **1,000,000 bps**，点击“连接并扫描”。核对实际 ID、型号、固件和设备数量。
3. 点击“备份全部舵机”。必须完整读取当前总线上所有受支持的舵机，才能继续恢复。点击“下载备份 JSON”另存并保留。
4. 默认已加载随附标准参数。也可通过“更换 JSON”加载原工具生成的其他完整备份，包括以前导出的 `backup_all.json`，用于恢复配置参数。
5. 只勾选需要恢复的实际 ID。例如只修复 S5，先确认它的总线 ID，再只勾选这一台。**S5 不等于 ID 5，工具不猜测机构编号。**
6. 点击“生成恢复计划”，核对 `当前 ID / 档案 ID / 最终 ID`。展开详情可查看每个配置寄存器当前值和目标值；“差异 / 写入”分别表示变化项数和总写入项数。为保持完整配置，每个允许恢复的配置项都会写入，包括值相同的项。
7. 输入 `RESTORE`，点击“恢复并校验”。此按钮才会开始硬件写入。保持供电与 USB 连接，等待结果。
8. 保存日志。看到 `RESTORE + VERIFY SUCCESS` 后，给舵机断电再上电，在机器人上重新测试 S5 是否能自行到顶、是否仍有嗡嗡声或需要手推。若出现 `[FAIL]`，保留对应日志和原始备份以便诊断。

随附标准 JSON 实际包含 **9 台档案：ID 10–16 是 XL330-M288，ID 17–18 是 XL330-M077**。这不代表当前总线一定要有九台；以扫描结果及具体维护范围为准。网页不会自动选择任何恢复目标，也不会把文件中的所有舵机自动全部刷新。

## 修改舵机 ID

1. 扫描设备，完成“备份全部舵机”，并下载保存备份。
2. 在“修改舵机 ID”中选择当前舵机，填写 **0～252** 范围内未占用的新 ID。不能与当前 ID 相同，也不能使用总线上已有的 ID。
3. 点击“检查并生成修改计划”。此步骤只扫描与读取，不写入；核对当前 ID、新 ID 和型号。
4. 生成计划后会弹出确认窗口，显示当前 ID、新 ID、型号及固件。点击“确定修改”开始写入，点击“取消”或按 Esc 关闭弹窗，不写入舵机；取消后可重新生成计划。无需输入确认字符。软件写入前再次扫描并单独 Ping 检查新 ID，关闭目标舵机 Torque 并回读确认，然后写入 ID。
5. 等待 `ID CHANGE + VERIFY SUCCESS`。软件在新 ID 回读校验 ID 和 Torque，并核对整条总线设备列表。成功后页面更新 ID，Torque 保持关闭，再次写入前必须重新备份。

机器人程序按 ID 识别舵机，应改为机器人所预期的 ID。如果总线上已经有重复 ID，扫描可能无法区分它们，请只连接待修改的一台舵机再操作。ID 合法范围与重复 ID 限制见 [ROBOTIS 官方说明](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#id7)。

修改 ID 不依赖同 ID 的参数档案，也不会改变 PID、波特率或自动重命名参数档案。配置恢复仍采用 Same ID：例如改为 ID 20 后，默认文件中没有 ID 20，就不能直接选它恢复；应加载型号匹配、ID 正确的参数文件，或将 ID 改回机器人预期值。

写入异常时不自动回滚 ID，避免通信状态不确定时再次写错设备。软件会要求重新扫描以确认当前实际 ID，并在日志中保留旧 ID 和目标 ID。

## 写入规则

- 配置恢复采用 Same ID，不自动改 ID、改波特率。修改 ID 使用独立的“修改舵机 ID”操作；跨波特率迁移仍使用原命令行工具。
- 写入前检查型号；M288 与 M077 不能混用。固件 V53 前后的 Indirect Address 布局必须一致，避免把旧布局直接写入新固件。
- 上传 JSON 的寄存器名称、地址、长度、分类和数值类型均按脚本中的控制表验证，不信任文件自报的可写类别。档案缺少配置项、读取不完整或存在重复 ID 时拒绝使用。
- 全量备份必须在本服务当前连接中完成，不能上传旧备份来跳过。扫描、断开、总线变化或开始写入后，旧备份不再解锁下一次恢复；原文件仍保留。
- 写入前重新扫描，并再次读取计划中的配置项。配置与计划不同则中止，要求重新备份。
- 先关闭全部所选舵机的 Torque 并确认，再按顺序恢复配置 / PID / Profile / Indirect Address；不写 Goal Position / Velocity / Current / PWM、LED、Indirect Data 和运行状态。
- 保留 ID 和波特率，通过逐项回读和最终复核校验，最后恢复 Status Return Level。若档案将其设为 0，沿用原工具的规则：写入后只能 ping 确认在线，无法正常回读该项。
- 发生通信或校验错误后停止后续配置写入，尽力关闭已操作舵机的 Torque。物理断连、掉电或硬件故障时，软件无法保证成功关断；日志会明确报告未能确认的 ID。
- 恢复不会自动回滚已写入项。失败后需检查连接，重新扫描与完整备份，再决定是否用保存的原始备份恢复。

## 文件与日志

真实设备备份在 `artifacts/hardware/backup_all_时间戳.json`，每次生成新文件，不覆盖旧备份。演示文件在 `artifacts/demo/`，文件名带 `DEMO_`。会话日志保存为各目录的 `session_log.txt`，新会话会更新它，请及时导出。

服务只监听 `127.0.0.1`，不需要发布到公网；网页和 Python 服务必须运行在连接 U2D2 的电脑上。前端无 CDN 或其他联网依赖。串口仅在具体操作期间打开，操作结束即释放。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check web/app.js
node tests/test_i18n.js
```

自动化测试使用内存舵机，包括恢复限制、备份失败、配置变化、模型不匹配、写入中断与 Torque 关闭检查；不接触真实硬件。真实 U2D2 / 舵机通信需在设备上另行验收。
