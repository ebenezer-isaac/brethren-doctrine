"""Verify no ingest/embed Python processes are still running.

Walks the Windows ``wmic`` process table (with a PowerShell fallback when
``wmic`` is absent on a modern image) looking for any ``python.exe``
whose command line matches one of the forbidden ingest/embed modules.
Exits 0 if none are running; exit 1 lists offenders.

Forbidden patterns:
    ingest.lexical
    embed_cultural
    embed_lexical
    run_cultural_scrape

Usage:
    python tools/check_no_ingest_procs.py [--self-test]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable


FORBIDDEN_PATTERNS: tuple[str, ...] = (
    r"ingest\.lexical",
    r"embed_cultural",
    r"embed_lexical",
    r"run_cultural_scrape",
)

_FORBIDDEN_RE = re.compile("|".join(FORBIDDEN_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class Process:
    pid: int
    command_line: str


def _list_via_wmic() -> list[Process] | None:
    wmic = shutil.which("wmic")
    if wmic is None:
        return None
    try:
        proc = subprocess.run(
            [
                wmic,
                "process",
                "where",
                "name='python.exe'",
                "get",
                "ProcessId,CommandLine",
                "/format:csv",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return _parse_wmic_csv(proc.stdout)


def _parse_wmic_csv(stdout: str) -> list[Process]:
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].lower().split(",")
    try:
        cl_idx = header.index("commandline")
        pid_idx = header.index("processid")
    except ValueError:
        return []
    out: list[Process] = []
    for ln in lines[1:]:
        # Last 2 fields are CommandLine,ProcessId after the Node column.
        # wmic CSV may have embedded commas inside command line. Use
        # rsplit from the right to peel off the PID, then everything
        # between the first comma and the PID is the command line.
        parts = ln.split(",")
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        cl = ",".join(parts[1:-1])
        out.append(Process(pid=pid, command_line=cl))
    return out


def _list_via_powershell() -> list[Process]:
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps is None:
        return []
    try:
        proc = subprocess.run(
            [
                ps,
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                "Select-Object ProcessId,CommandLine | "
                "ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    import json

    raw = json.loads(proc.stdout)
    if isinstance(raw, dict):
        raw = [raw]
    out: list[Process] = []
    for r in raw:
        pid = int(r.get("ProcessId") or 0)
        cl = r.get("CommandLine") or ""
        out.append(Process(pid=pid, command_line=cl))
    return out


def list_python_procs() -> list[Process]:
    via_wmic = _list_via_wmic()
    if via_wmic is not None:
        return via_wmic
    return _list_via_powershell()


def find_offenders(procs: Iterable[Process]) -> list[Process]:
    return [p for p in procs if _FORBIDDEN_RE.search(p.command_line)]


def _self_test() -> int:
    sample = [
        Process(pid=1, command_line="python.exe -m pytest tests/"),
        Process(pid=2, command_line="python.exe -m ingest.lexical.run --dataset macula"),
        Process(pid=3, command_line="C:\\Py\\python.exe E:\\repo\\embed_lexical.py"),
        Process(pid=4, command_line="python.exe my_safe_script.py"),
    ]
    bad = find_offenders(sample)
    assert {p.pid for p in bad} == {2, 3}, bad
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    procs = list_python_procs()
    offenders = find_offenders(procs)
    if not offenders:
        print(f"OK: scanned {len(procs)} python.exe procs, zero forbidden patterns.")
        return 0
    print(
        f"FAIL: {len(offenders)} forbidden ingest/embed process(es) running",
        file=sys.stderr,
    )
    for p in offenders:
        print(f"  pid={p.pid} cmdline={p.command_line}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
