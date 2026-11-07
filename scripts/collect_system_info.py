#!/usr/bin/env python3
"""Collect cross-platform, read-only system information for HPC experiments."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PERFORMANCE_ENV_KEYS = (
    "OMP_NUM_THREADS",
    "OMP_PROC_BIND",
    "OMP_PLACES",
    "OMP_SCHEDULE",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "TBB_NUM_THREADS",
    "CUDA_VISIBLE_DEVICES",
    "HIP_VISIBLE_DEVICES",
    "ROCR_VISIBLE_DEVICES",
    "SYCL_DEVICE_FILTER",
)


COMMON_COMMANDS = {
    "cmake": ["cmake", "--version"],
    "ninja": ["ninja", "--version"],
    "gcc": ["gcc", "--version"],
    "gxx": ["g++", "--version"],
    "clangxx": ["clang++", "--version"],
    "clang_cl": ["clang-cl", "--version"],
    "msvc": ["cl"],
    "icpx": ["icpx", "--version"],
    "nvcc": ["nvcc", "--version"],
    "hipcc": ["hipcc", "--version"],
    "nvidia_smi": [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total,pci.bus_id",
        "--format=csv,noheader",
    ],
    "rocm_smi": ["rocm-smi", "--showproductname"],
    "mpirun": ["mpirun", "--version"],
}


def platform_commands() -> dict[str, list[str]]:
    if os.name == "nt":
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        commands: dict[str, list[str]] = {"power_plan": ["powercfg", "/GETACTIVESCHEME"]}
        if powershell:
            queries = {
                "windows_cpu": "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | ConvertTo-Json -Compress",
                "windows_memory": "Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed,ConfiguredClockSpeed,Manufacturer | ConvertTo-Json -Compress",
                "windows_gpu": "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress",
                "windows_os": "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress",
            }
            commands.update({name: [powershell, "-NoProfile", "-Command", query] for name, query in queries.items()})
        return commands
    return {
        "uname": ["uname", "-a"],
        "lscpu": ["lscpu"],
        "numa": ["numactl", "--hardware"],
        "memory": ["free", "-h"],
        "lsmem": ["lsmem"],
        "perf": ["perf", "--version"],
        "likwid": ["likwid-topology", "-v"],
        "vtune": ["vtune", "--version"],
        "papi": ["papi_avail"],
    }


def run_command(command: list[str], timeout: float) -> dict[str, Any]:
    executable = command[0] if Path(command[0]).is_file() else shutil.which(command[0])
    if not executable:
        return {"available": False, "command": command, "returncode": None, "stdout": "", "stderr": "tool not found"}
    try:
        process = subprocess.run(
            [executable, *command[1:]],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "available": True,
            "command": [executable, *command[1:]],
            "returncode": process.returncode,
            "stdout": process.stdout.strip(),
            "stderr": process.stderr.strip(),
        }
    except Exception as exc:
        return {
            "available": True,
            "command": [executable, *command[1:]],
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def process_affinity() -> dict[str, Any]:
    if hasattr(os, "sched_getaffinity"):
        cpus = sorted(os.sched_getaffinity(0))
        return {"logical_cpus": cpus, "count": len(cpus)}
    if os.name == "nt":
        try:
            import ctypes

            process_mask = ctypes.c_size_t()
            system_mask = ctypes.c_size_t()
            kernel32 = ctypes.windll.kernel32
            ok = kernel32.GetProcessAffinityMask(
                kernel32.GetCurrentProcess(),
                ctypes.byref(process_mask),
                ctypes.byref(system_mask),
            )
            if ok:
                return {
                    "process_mask_hex": hex(process_mask.value),
                    "system_mask_hex": hex(system_mask.value),
                    "count": process_mask.value.bit_count(),
                }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
    return {"count": os.cpu_count()}


def read_linux_state() -> dict[str, str]:
    if os.name == "nt":
        return {}
    paths = {
        "cpu0_scaling_governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "transparent_hugepage_enabled": Path("/sys/kernel/mm/transparent_hugepage/enabled"),
        "perf_event_paranoid": Path("/proc/sys/kernel/perf_event_paranoid"),
    }
    state: dict[str, str] = {}
    for name, path in paths.items():
        try:
            state[name] = path.read_text(encoding="utf-8").strip()
        except OSError:
            state[name] = "unavailable"
    return state


def write_text(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# System information summary",
        "",
        f"Created: {data['created_at']}",
        f"Platform: {platform.platform()}",
        f"Machine: {platform.machine()}",
        f"Logical CPUs visible: {data['affinity'].get('count')}",
        "",
        "## Performance environment",
    ]
    environment = data["performance_environment"]
    lines.extend(f"{key}={value}" for key, value in environment.items())
    if not environment:
        lines.append("none recorded")
    for name, result in data["commands"].items():
        lines.extend(["", f"## {name}"])
        if not result["available"]:
            lines.append("tool not found")
            continue
        if result["stdout"]:
            lines.append(result["stdout"])
        if result["stderr"]:
            lines.extend(["[stderr]", result["stderr"]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default="system-info.json", help="JSON output path.")
    parser.add_argument("--text", default="system-info.txt", help="Text output path.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout per probe command.")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")

    commands = {**COMMON_COMMANDS, **platform_commands()}
    data = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "affinity": process_affinity(),
        "linux_state": read_linux_state(),
        "performance_environment": {key: os.environ[key] for key in PERFORMANCE_ENV_KEYS if key in os.environ},
        "commands": {name: run_command(command, args.timeout) for name, command in commands.items()},
    }

    json_path = Path(args.json)
    text_path = Path(args.text)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    write_text(text_path, data)
    available = [name for name, result in data["commands"].items() if result["available"]]
    missing = [name for name, result in data["commands"].items() if not result["available"]]
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote text: {text_path}")
    print(f"Available probes: {', '.join(available) if available else 'none'}")
    print(f"Missing probes: {', '.join(missing) if missing else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
