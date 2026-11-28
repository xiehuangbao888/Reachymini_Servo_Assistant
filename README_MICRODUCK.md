# Microduck / Reachy Mini 模式

通过扫描前的两个按钮选择机器人。Microduck 预期 15 个舵机，Reachy Mini 预期 9 个。两种模式共用扫描、备份、参数恢复及修改 ID 流程；无固件烧录功能。

```bash
python web_tool.py --robot microduck --no-browser --lang zh --port 8767
```

Microduck 板载串口为 `/dev/ttyS2`，已配置总线速率为 1000000。访问串口前暂停 `robotd`，退出后恢复。适配的启动脚本位于安装目录上一级 `start-web.sh`。

机型切换会清空连接、扫描结果、备份和待执行计划；任务执行期间不可切换。备份 JSON 自动写入 `robot_type`。Microduck 内置 `MICRODUCK_BACKUP_2.json`，与用户提供的桌面 `2.json` 内容完全一致（duck-6f11 升级 OS v1.4.2 后的 15 台 XL330-M288 / V53 备份，电流上限 1000、位置 P 增益 200，均为原始值）。它是参考参数备份，不是出厂标准或舵机固件。切换到 Microduck 会自动载入，也可点击“使用内置参数”重新选择；载入不会写入舵机。另行导入只接受带 `robot_type: "microduck"` 的兼容备份；Reachy Mini 兼容原项目的无标记档案。带另一种机型标记的档案会被拒绝。

恢复流程：选择机型 → 扫描 → 备份全部可响应舵机 → 选择内置参数或导入该机型参考备份 → 勾选目标 → 生成计划 → 核对差异后确认。修改 ID 也要求当前备份、ID 空闲检查和独立确认。测试备份保存当前故障状态，不代表正常参考配置。

验证：`python -m unittest discover -s tests -q`；`node tests/test_i18n.js`。
