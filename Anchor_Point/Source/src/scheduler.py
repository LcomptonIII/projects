"""Shared scheduling helpers used by both CLI and GUI."""
from __future__ import annotations
import platform
import subprocess


def create_schedule(task_name: str, cmd: str, run_at: str) -> tuple[bool, str]:
    if platform.system() == "Windows":
        r = subprocess.run(["schtasks", "/Create", "/TN", task_name, "/TR", cmd,
                            "/SC", "DAILY", "/ST", run_at, "/F"], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr or r.stdout).strip()
    hour, minute = run_at.split(":")
    lines = _cron_lines(task_name)
    lines.append(f"{minute} {hour} * * * {cmd}   # {task_name}")
    return _cron_write(lines)


def remove_schedule(task_name: str) -> tuple[bool, str]:
    if platform.system() == "Windows":
        r = subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr or r.stdout).strip()
    return _cron_write(_cron_lines(task_name))


def query_schedule(task_name: str) -> tuple[bool, str]:
    if platform.system() == "Windows":
        r = subprocess.run(["schtasks", "/Query", "/TN", task_name, "/FO", "LIST"],
                           capture_output=True, text=True, encoding="oem", errors="replace")
        if r.returncode != 0:
            return False, ""
        keywords = ("start time", "hora de inicio", "startzeit", "heure de début", "ora di inizio", "開始時刻")
        for line in r.stdout.splitlines():
            if any(k in line.lower() for k in keywords):
                value = line.split(":", 1)[-1].strip(); parts = value.split(":")
                if len(parts) >= 2:
                    return True, f"{parts[0].strip().zfill(2)}:{parts[1].strip()[:2]}"
        return True, "?"
    for line in _cron_raw_lines():
        if f"# {task_name}" in line:
            parts=line.split()
            if len(parts)>=2:
                return True, f"{parts[1].zfill(2)}:{parts[0].zfill(2)}"
    return False, ""


def _cron_raw_lines() -> list[str]:
    r=subprocess.run(["crontab","-l"], capture_output=True, text=True)
    return (r.stdout if r.returncode == 0 else "").splitlines()


def _cron_lines(task_name: str) -> list[str]:
    return [line for line in _cron_raw_lines() if f"# {task_name}" not in line and "# CrunchyExporter" not in line]


def _cron_write(lines: list[str]) -> tuple[bool, str]:
    r=subprocess.run(["crontab","-"], input="\n".join(lines)+"\n", text=True, capture_output=True)
    return r.returncode == 0, r.stderr.strip()
