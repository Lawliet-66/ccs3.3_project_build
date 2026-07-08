#!/usr/bin/env python3
"""
CCS3.3 Project Build Tool
Python wrapper for TI CCS3.3 timake command.
Packages as: ccs3.3_project_build.exe <project.pjt> [-clean] -log <log_dir>

NOTE: timake.exe requires administrator privileges on Windows.
Run this script from an elevated (admin) console.
"""

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CCS3.3 Project Build Tool - Wrapper for timake"
    )
    parser.add_argument(
        "project_pjt",
        help="Project file (.pjt), supports glob pattern like *.pjt",
    )
    parser.add_argument(
        "-clean",
        action="store_true",
        help="Perform clean build instead of build",
    )
    parser.add_argument(
        "-log",
        required=True,
        dest="log_dir",
        help="Directory to store log files",
    )
    return parser.parse_args()


def resolve_pjt(pattern: str) -> Optional[str]:
    """Resolve .pjt pattern to an actual file path, or None on failure."""
    if '*' in pattern or '?' in pattern:
        matches = glob.glob(pattern)
        if not matches and '/' not in pattern and '\\' not in pattern:
            recursive_pattern = f"**/{pattern}"
            matches = glob.glob(recursive_pattern, recursive=True)
        if not matches:
            return None
        return os.path.abspath(matches[0])
    else:
        path = os.path.abspath(pattern)
        if not os.path.isfile(path):
            return None
        return path


def build_timake_command(pjt_path: str, clean: bool) -> list[str]:
    """Build the timake command line."""
    cmd = ["timake", pjt_path, "Debug"]
    if clean:
        cmd.append("-clean")
    return cmd


def ensure_log_dir(log_dir: str) -> Optional[str]:
    """Ensure log directory exists, return absolute path, or None on failure."""
    abs_dir = os.path.abspath(log_dir)
    try:
        os.makedirs(abs_dir, exist_ok=True)
    except (PermissionError, OSError):
        return None
    return abs_dir


def generate_log_filename(clean: bool) -> str:
    """Generate log filename: {Clean|Debug}_{YYYYMMDD_HHMMSS}.log"""
    prefix = "Clean" if clean else "Debug"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.log"


def check_build_result(output: str, clean: bool) -> bool:
    """Check timake output to determine build success/failure.

    Build success requires BOTH:
      - The literal "Build Complete" marker, AND
      - Exactly "0 Errors" (matched as a standalone number, so that
        "10 Errors" / "100 Errors" do not falsely match "0 Errors").

    Clean success requires the literal "Build Clean Complete" marker.
    """
    if clean:
        return "Build Clean Complete" in output
    if "Build Complete" not in output:
        return False
    # Match "0 Errors" only when it is the whole error count, not a
    # substring of "10 Errors" / "100 Errors" / "20 Errors".
    return re.search(r"(?<!\d)0 Errors", output) is not None


def run_timake(cmd: list[str], log_path: str, clean: bool) -> tuple[bool, str]:
    """Run timake, capture output to log file.

    Returns (success, message) tuple.
    message is empty on success, or describes the failure reason on failure.

    NOTE: timake.exe requires administrator privileges on Windows
    (WinError 740 when launched from a non-elevated process).
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
    except FileNotFoundError:
        return False, "timake not found"
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 1800 seconds"
    except OSError:
        return False, "timake requires administrator privileges. Run from an elevated (admin) console."

    full_output: str = result.stdout

    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(full_output)
    except (PermissionError, OSError):
        return False, f"Log file not writable: {log_path}"

    ok = check_build_result(full_output, clean)
    if ok:
        return True, ""
    return False, "Build completed with errors"


def write_status_json(log_dir: str, result: dict) -> None:
    """Write result to status.json for elevated-wrapper fallback."""
    status_path = os.path.join(log_dir, "status.json")
    try:
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")
    except (PermissionError, OSError):
        pass  # non-fatal; stdout JSON is the primary channel


def output_result(result: dict) -> None:
    """Print the single JSON result line to stdout."""
    print(json.dumps(result))


def main() -> None:
    args = parse_args()

    # Ensure log directory
    log_dir = ensure_log_dir(args.log_dir)
    if log_dir is None:
        result = {"status": "fail", "log": "", "message": f"Log directory not writable: {os.path.abspath(args.log_dir)}"}
        output_result(result)
        write_status_json("", result)
        sys.exit(1)

    # Resolve .pjt file
    pjt_path = resolve_pjt(args.project_pjt)
    if pjt_path is None:
        result = {"status": "fail", "log": "", "message": f"Project file not found: {args.project_pjt}"}
        output_result(result)
        write_status_json(log_dir, result)
        sys.exit(1)

    # Generate timestamped log file name
    log_filename = generate_log_filename(args.clean)
    log_path = os.path.join(log_dir, log_filename)

    # Build and run timake
    cmd = build_timake_command(pjt_path, args.clean)
    success, message = run_timake(cmd, log_path, args.clean)

    # Build final result
    if success:
        result: dict = {"status": "success", "log": log_path}
    else:
        result = {"status": "fail", "log": log_path, "message": message}

    # Single unified JSON output to stdout
    output_result(result)
    write_status_json(log_dir, result)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()