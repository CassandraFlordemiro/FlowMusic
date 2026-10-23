# -*- coding: utf-8 -*-
"""
Fast IPC Client for FlowMusic 360.
Communicates with the background daemon on 127.0.0.1:49360 and auto-starts it if needed.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time

from library import STATE_PATH

RPC_HOST = "127.0.0.1"
RPC_PORT = 49360
APPMUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_SCRIPT = os.path.join(APPMUSIC_DIR, "daemon.py")


def get_system_pythonw() -> str:
    candidates = [
        r"C:\Python314\pythonw.exe",
        r"C:\Python314\python.exe",
        shutil.which("pythonw.exe") or "",
        shutil.which("python.exe") or "",
        sys.executable,
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return sys.executable


def send_rpc(payload: dict, timeout: float = 0.25) -> dict | None:
    try:
        with socket.create_connection((RPC_HOST, RPC_PORT), timeout=timeout) as sock:
            sock.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            data = sock.recv(65536)
            if data:
                return json.loads(data.decode("utf-8"))
    except Exception:
        return None
    return None


def ensure_daemon_running(wait_up_to: float = 1.5) -> bool:
    status = send_rpc({"cmd": "status"}, timeout=0.12)
    if status and status.get("running"):
        return True

    pythonw = get_system_pythonw()
    creationflags = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
    try:
        subprocess.Popen(
            [pythonw, DAEMON_SCRIPT],
            cwd=APPMUSIC_DIR,
            creationflags=creationflags,
            close_fds=True,
        )
    except Exception:
        return False

    deadline = time.time() + wait_up_to
    while time.time() < deadline:
        time.sleep(0.08)
        status = send_rpc({"cmd": "status"}, timeout=0.12)
        if status and status.get("running"):
            return True
    return False


def get_fast_status() -> dict:
    # Try instant RPC first (80ms timeout so Flow Launcher never lags)
    resp = send_rpc({"cmd": "status"}, timeout=0.08)
    if resp:
        return resp

    # Auto-launch daemon in background without blocking Flow Launcher query
    pythonw = get_system_pythonw()
    creationflags = 0x00000008 | 0x08000000
    try:
        subprocess.Popen(
            [pythonw, DAEMON_SCRIPT],
            cwd=APPMUSIC_DIR,
            creationflags=creationflags,
            close_fds=True,
        )
    except Exception:
        pass

    # Fallback to last saved state snapshot if available
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["running"] = False
                return data
        except Exception:
            pass

    return {
        "running": False,
        "state": "stopped",
        "current_track": None,
        "next_track": None,
        "active_playlist": "Todas as Músicas",
        "volume": 80,
        "shuffle": False,
        "repeat": "all",
        "position_str": "00:00",
        "duration_str": "00:00",
    }


def execute_action(payload: dict) -> dict | None:
    resp = send_rpc(payload, timeout=0.35)
    if resp is not None:
        return resp
    if ensure_daemon_running(wait_up_to=2.0):
        return send_rpc(payload, timeout=0.6)
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd_name = sys.argv[1]
        print(json.dumps(execute_action({"cmd": cmd_name}), indent=2, ensure_ascii=False))
    else:
        ensure_daemon_running()
        print(json.dumps(get_fast_status(), indent=2, ensure_ascii=False))

