#!/usr/bin/env python3
"""Cross-platform bootstrap: python launch.py (Windows), python3 launch.py (macOS)."""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10 or newer is required.')
    env = ROOT / '.venv'
    python = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Creating local Python environment...', flush=True)
        venv.EnvBuilder(with_pip=True).create(env)
    subprocess.run([str(python), '-c', 'import sys; assert sys.version_info >= (3,10)'], check=True)
    probe = subprocess.run([str(python), '-c', 'import dynamixel_sdk, serial'], capture_output=True)
    if probe.returncode:
        print('Installing dependencies (first launch requires internet)...', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
    # Replace bootstrap so Ctrl+C is handled by the service, including active-write cleanup.
    os.execv(str(python), [str(python), str(ROOT / 'web_tool.py'), *sys.argv[1:]])


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Could not start XL330 Web Tool: {exc}') from exc
