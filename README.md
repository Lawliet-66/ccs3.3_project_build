# ccs3.3_project_build

Build or clean Texas Instruments CCS3.3 DSP projects via a Python-wrapped `timake` CLI, with automatic UAC elevation through PowerShell.

`timake.exe` (CCStudio v3.3) **requires administrator privileges** on Windows. This repository provides:

- `ccs3.3_project_build.py` – pure Python wrapper around `timake`.
- `Script/ccs3.3_project_build.exe` – frozen executable built from the Python script.
- `run_build.ps1` – PowerShell helper that auto-elevates the executable (UAC prompt) and surfaces the JSON result back to the non-elevated caller.

## Requirements

- Windows (timake is a Windows-only CCS3.3 tool).
- TI Code Composer Studio v3.3 installed, with `timake.exe` on your system `PATH`.
- PowerShell 5+ (for the auto-elevation wrapper).

## Setting up `timake.exe`

Before running this tool, make sure Windows can find `timake.exe` and that it is allowed to run as administrator.

### 1. Add `timake.exe` to your system `PATH`

Find the folder that contains `timake.exe`. For a default CCS3.3 installation it is usually:

```text
G:\CCStudio_v3.3PLA\cc\bin
```

Add that folder to your system `PATH`:

1. Press `Win + R`, type `sysdm.cpl`, and press Enter.
2. Go to the **Advanced** tab → click **Environment Variables**.
3. Under **System variables**, find and select `Path`, then click **Edit**.
4. Click **New** and add the path to the folder containing `timake.exe`, for example:
   ```text
   G:\CCStudio_v3.3PLA\cc\bin
   ```
5. Click **OK** on all dialogs.
6. Open a new terminal and verify with:
   ```cmd
   where timake
   ```
   It should print the full path to `timake.exe`.

### 2. Set `timake.exe` to always run as administrator

`timake.exe` needs administrator privileges to build CCS3.3 projects. Configure it once:

1. Open File Explorer and navigate to the folder from step 1, e.g.:
   ```text
   G:\CCStudio_v3.3PLA\cc\bin
   ```
2. Right-click `timake.exe` → **Properties**.
3. Go to the **Compatibility** tab.
4. Click **Change settings for all users**.
5. Check **Run this program as an administrator**.
6. Click **OK**.

> **Note:** `run_build.ps1` already tries to elevate the process via UAC. Setting `timake.exe` itself to run as administrator avoids privilege issues when the executable is invoked directly as well.

## Installation

Clone this repository:

```bash
git clone https://github.com/Lawliet-66/ccs3.3_project_build.git
cd ccs3.3_project_build
```

Or download the release package under `Release/ccs3.3_project_build/`.

## Usage

### Recommended: `run_build.ps1` (auto-elevates)

```bash
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

Only works without a UAC prompt when invoked from an already-elevated (admin) console; otherwise it reports:

```json
{"status":"fail","message":"timake requires administrator privileges..."}
```

## Output

A single JSON line on stdout (echoed by `run_build.ps1` from its `status.json` side-channel after the elevated run completes):

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

```text
{Clean|Debug}_{YYYYMMDD_HHMMSS}.log
```

## How It Works

1. `run_build.ps1` launches `ccs3.3_project_build.exe` via `Start-Process -Verb RunAs` (UAC prompt).
2. The elevated executable invokes `timake.exe`, captures its output to a timestamped `.log` file, and writes `status.json` to the `-log` directory.
3. `run_build.ps1` reads `status.json`, prints the JSON to its stdout (visible to the non-elevated caller), and sets `$LASTEXITCODE`.

## Project Layout

```text
ccs3.3_project_build/
├── ccs3.3_project_build.py      # Python source
├── run_build.ps1                # PowerShell auto-elevation wrapper
├── Script/
│   └── ccs3.3_project_build.exe # Frozen executable
├── Release/
│   └── ccs3.3_project_build/    # Packaged release copy
├── docs/                        # Design docs and specs
├── log_files/                   # Example log output (ignored by git)
├── LICENSE                      # MIT License
└── README.md                    # This file
```

## Notes

- When using `*.pjt` glob, the first matching file is used. If no match is found in the current directory, subdirectories are searched recursively.
- For automation, pre-elevate the console so `run_build.ps1` does not show a UAC prompt.
- Logs are written to the directory specified by `-log`; the repository ignores runtime log directories.

## License

This project is licensed under the [MIT License](./LICENSE).

## Author

- **shousidaima** – 2296752208@qq.com
