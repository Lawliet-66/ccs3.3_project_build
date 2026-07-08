---
name: ccs3.3-project-build
description: Build or clean CCS3.3 DSP projects using timake (auto-elevated), captured to log files with JSON status output
metadata:
  type: skill
  requires: timake (CCStudio_v3.3PLA), PowerShell 5+
  triggers:
    - ccs3.3_project_build.exe
    - ccs3.3 build
    - timake build
    - DSP project build
---

# ccs3.3-project-build

Build or clean CCS3.3 DSP projects via a Python-wrapped `timake` CLI.

`timake.exe` (CCS3.3) **requires administrator privileges** on Windows.
This skill ships a PowerShell helper, `run_build.ps1`, that auto-elevates
the bundled `ccs3.3_project_build.exe` (showing a UAC prompt) and surfaces
the single JSON result line to the calling console. Use it from any shell
(cmd, PowerShell, bash).

## Usage

### Recommended: `run_build.ps1` (auto-elevates)

```
powershell -ExecutionPolicy Bypass -File run_build.ps1 <project.pjt> [-clean] -log <log_dir>
```

| Argument | Description |
|---|---|
| `project.pjt` | Project file path (supports `*.pjt` glob) |
| `-clean` | Perform a clean instead of a build |
| `-log <dir>` | **Required.** Directory for log output (auto-created) |

**Examples (from cmd):**
```cmd
:: Clean the first .pjt found (UAC prompt appears)
powershell -ExecutionPolicy Bypass -File run_build.ps1 *.pjt -clean -log ./LogFiles

:: Build a specific project
powershell -ExecutionPolicy Bypass -File run_build.ps1 KADD008U2.PJT -log ./LogFiles

:: Build with absolute path
powershell -ExecutionPolicy Bypass -File run_build.ps1 D:/Projects/MyApp/MyApp.pjt -log D:/Logs
```

**Examples (from PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File run_build.ps1 -ProjectPjt KADD008U2.PJT -clean -log ./LogFiles
```

### Direct: `ccs3.3_project_build.exe` (must already be elevated)

```bash
ccs3.3_project_build.exe <project.pjt> [-clean] -log <log_dir>
```
Only works without a UAC prompt when invoked from an already-elevated
(admin) console; otherwise it reports `{"status":"fail","message":"timake
requires administrator privileges..."}`.

## Output

A single JSON line on stdout (echoed by `run_build.ps1` from its
status.json side-channel after the elevated run completes):

- **Success:**
  ```json
  {"status": "success", "log": "D:/Logs/Debug_20260707_102030.log"}
  ```
- **Failure:**
  ```json
  {"status": "fail", "log": "D:/Logs/Debug_20260707_102030.log", "message": "..."}
  ```

Exit code: `0` for success, `1` for failure.

## Log File Naming

`{Clean|Debug}_{YYYYMMDD_HHMMSS}.log`

## How it works

1. `run_build.ps1` launches `ccs3.3_project_build.exe` via `Start-Process -Verb RunAs` (UAC prompt).
2. The elevated exe invokes `timake.exe`, captures its output to the timestamped `.log` file, and writes a `status.json` to the `-log` directory.
3. `run_build.ps1` reads `status.json`, prints the JSON to its stdout (visible to the non-elevated caller), and sets `$LASTEXITCODE`.

## Notes

- When using `*.pjt` glob, the first matching file is used. If no match found in the current directory, it recursively searches subdirectories.
- For automation, pre-elevate the console so `run_build.ps1` does not show a UAC prompt.