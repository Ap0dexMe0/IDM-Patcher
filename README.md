# IDM Activation Script

This script allows you to activate, reset, or freeze the trial period of **Internet Download Manager (IDM)**.

> **Important**: The script currently does **NOT** work with the latest IDM versions. Use the **Freeze Trial** option instead of Activation.

## Features

- **Activate IDM** – Attempts to register IDM with a random license.
- **Freeze Trial** – Permanently freezes the 30‑day trial period.
- **Reset Activation / Trial** – Cleans all IDM registry entries and CLSID keys.
- **Download IDM** – Opens the official IDM download page.
- **Help** – Opens the project homepages.
- Supports both **x86** and **x64** Windows.
- Works with **HKCU/HKU** registry redirection and user SID detection.
- Auto‑elevates to administrator privileges.

## Requirements

- Windows 7 / 8 / 8.1 / 10 / 11 (or corresponding Server)
- Python 3.6 or higher
- Administrator rights (script will prompt automatically)
- PowerShell (built‑in on Windows)

## Installation

No installation required – just download the script files.

1. Clone or download this repository:
   ```bash
   git clone https://github.com/Ap0dexMe0/IDM-Patcher.git
   ```
2. Ensure Python is installed and added to `PATH`.
3. Run the script as administrator:
   ```bash
   python main.py
   ```

## Usage

### Interactive Menu

Run the script without arguments to see the interactive menu:

```bash
python main.py
```

Then choose an option by typing the corresponding number.

### Command‑Line Arguments (Unattended Mode)

You can use the following arguments to perform actions directly (no menu):

| Argument | Action                     |
|----------|----------------------------|
| `--active`   | Activate IDM               |
| `--freeze`   | Freeze the trial period    |
| `--reset`   | Reset activation / trial   |

Example:

```bash
python main.py --active
```

The script will run with elevated privileges and exit automatically when finished.

## How It Works

The script performs the following steps:

1. **Checks for admin rights** – re‑launches itself with `runas` if needed.
2. **Detects Windows architecture, user SID, and IDM installation path**.
3. **Kills IDM (`IDMan.exe`) if running**.
4. **Backs up existing CLSID registry keys** to `%SystemRoot%\Temp`.
5. **Deletes IDM‑related registry values** (serial, email, etc.) and the `AdvIntDriverEnabled2` key.
6. **Scans the CLSID hive** for IDM‑generated keys and either:
   - **Locks** them (deny access) – used for trial freeze.
   - **Deletes** them – used for reset.
   - **Deletes if more than 20 keys are found** – to avoid false locking.
7. **If activating**, writes random registration details and triggers a few dummy downloads to force IDM to recreate necessary registry keys, then locks the new CLSID keys.

All registry operations are performed using the Windows API (`winreg`) and, for advanced permission manipulation, a PowerShell snippet (identical to the original batch script).

## Troubleshooting

| Issue                                  | Solution                                                                 |
|----------------------------------------|--------------------------------------------------------------------------|
| Script crashes or Null service error   | Ensure the `Null` service is running (`sc query Null`). Restart if needed. |
| PowerShell language mode restricted    | Undo any PowerShell restrictions (e.g., `ConstrainedLanguage`).          |
| WMI not working                        | Check WMI service and permissions.                                       |
| Cannot write to CLSID registry         | Run as administrator, disable antivirus temporarily.                     |
| Fake serial screen appears after activation | Use the **Freeze Trial** option instead.                             |
| IDM shows popup to register after freeze | Reinstall IDM (keep the frozen trial).                               |

For more help, visit the [official troubleshooting page](https://massgrave.dev/idm-activation-script.html#Troubleshoot).

## Disclaimer

This script is provided for **educational purposes only**. Activating commercial software without a valid license may violate the software's terms of service. Use at your own risk. The original batch script and this Python port are not affiliated with Tonec Inc. (the maker of IDM).

## License

Same as the original project – see [LICENSE](LICENSE) (if provided). Otherwise, feel free to use and modify for personal purposes.
```