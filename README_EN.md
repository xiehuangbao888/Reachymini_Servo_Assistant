# reachymini Servo Assistant

[中文说明](README.md)

A local browser tool for backing up and restoring DYNAMIXEL XL330 settings and changing servo IDs. Supports XL330-M288 (1200), XL330-M077 (1190), and Protocol 2.0. It does not update servo firmware.

## Start on Windows or macOS

Install Python 3.10 or newer. On Windows, enable **Add Python to PATH** during installation. The initial dependency installation requires internet access.

Windows PowerShell:

```powershell
git clone https://github.com/xiehuangbao888/Reachymini_Servo_Assistant.git
cd Reachymini_Servo_Assistant
python -m pip install -r requirements.txt
python web_tool.py --lang en
```

If the repository is already cloned and your terminal is in its directory, run only the last two commands.

macOS Terminal (a virtual environment is recommended):

```bash
git clone https://github.com/xiehuangbao888/Reachymini_Servo_Assistant.git
cd Reachymini_Servo_Assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python web_tool.py --lang en
```

The server opens your browser at `http://127.0.0.1:8765/?lang=en`. Keep the terminal open. Do not copy `.venv` between operating systems.

The optional `launch.py` bootstrap creates `.venv` and installs dependencies automatically. Use `python launch.py --lang en` on Windows or `python3 launch.py --lang en` on macOS. It accepts the same options as `web_tool.py`.

If the port is already in use, stop the old service or choose another port:

```powershell
python web_tool.py --lang en --port 8767
```

Open `http://127.0.0.1:8767/?lang=en`. Use the **Language** selector to switch between English and Chinese. Your selection is remembered in this browser; a `lang` URL parameter takes precedence. Switching language does not scan or write to hardware.

For an entirely simulated workflow, add `--demo --port 8766`. Demo mode never accesses real servos. Stop the server with Ctrl+C; let an active write finish first.

## Connect and back up

1. Close the reachymini app and other programs using the serial port. Power the servos and support the mechanism before any write: torque will be turned off.
2. Connect USB, click **Refresh ports**, and select the newly appearing U2D2 port.
3. Select **1,000,000 bps** and click **Connect & scan**. Check the detected IDs, models and firmware.
4. Click **Back up all servos**, wait for completion, and save the **Download backup JSON** file.

A complete backup in the current session is required before restoring settings or changing an ID. Rescanning, disconnecting, inventory changes, or a write invalidate the previous authorization. Saved backup files are retained.

Default ID mapping:

- ID 10: base servo.
- IDs 11–16: servos 1–6, respectively.
- ID 17: right antenna.
- ID 18: left antenna.

Labels use this default mapping, not physical detection. If IDs have been changed, verify the actual connections.

## Restore settings

The built-in default is the user's `backup_all_20261120_153857_997605.json` snapshot, stored as `DYNAMIXEL_XL330_BACKUP.json`. All nine profiles use firmware V53. Position P is 200 for IDs 10, 17 and 18, and 300 for IDs 11–16; position I and D are zero for all nine.

1. Complete a fresh backup.
2. Use the built-in settings or click **Load JSON** to load another complete, compatible profile.
3. Select only the intended servos and click **Generate restore plan**.
4. Review the current/profile/final IDs and register values in the dialog, then click **Confirm restore**. No confirmation text is required. Click **Cancel** or press Esc to close without writing; generate a new plan when ready.
5. Wait for `RESTORE + VERIFY SUCCESS`. Save the log, power-cycle the servos, and test the robot.

Restore uses matching IDs and models, preserves IDs and baud rate, and checks firmware layout compatibility. It writes configuration, gains, profiles and indirect addresses. It does **not** write Goal Position, Goal Velocity, Goal Current, Goal PWM, LED, indirect data or runtime status. Torque remains OFF. Writes are checked individually and verified again at the end.

## Change a servo ID

1. Complete a fresh backup.
2. Under **Change servo ID**, select the current servo and an unused new ID from 0 to 252.
3. Click **Check & generate ID plan**. Review the dialog's current ID, new ID, model and firmware.
4. Click **Confirm change** to write, or **Cancel** / Esc to dismiss without writing. No confirmation text is required for ID changes.
5. Wait for `ID CHANGE + VERIFY SUCCESS`. The device list updates; make a new backup before another write.

The tool rechecks the bus and the new ID, turns torque off and verifies it, writes the ID, then checks the new ID, model, torque and bus inventory. It does not change PID or baud rate and does not rename profiles. Restore still needs a matching profile for the new ID.

Use the ID expected by the robot's software. If duplicate IDs already exist, connect only the servo you intend to change. An uncertain write is not automatically rolled back; rescan to find the actual ID.

## Logs and troubleshooting

- Initial serial connection and scan are isolated and time-limited to eight seconds. **Cancel scan** stops discovery; active hardware writes cannot be cancelled.
- Hardware backups are saved in `artifacts/hardware/`. Demo backups are in `artifacts/demo/` and cannot be used on physical hardware.
- The page translates known tool statuses and diagnostics. Downloaded logs retain their original text for troubleshooting; operating-system/driver messages may use the system language.
- The service listens only on `127.0.0.1`. Run it on the computer connected to U2D2.
- Software tests use simulated devices. Real U2D2 operation and macOS hardware behavior require testing on the target equipment.
