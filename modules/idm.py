# modules/idm.py
import os
import sys
import subprocess
import ctypes
import winreg
import random
import string
import time
import tempfile
import urllib.request
from pathlib import Path

# Constants
IAS_VER = "1.2"
CLSID_PATHS_32 = [r"HKCU\Software\Classes\CLSID"]
CLSID_PATHS_64 = [r"HKCU\Software\Classes\Wow6432Node\CLSID"]

# ---------- Helper Functions ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

def get_user_sid():
    # Get SID of the current user (the one associated with explorer.exe)
    try:
        output = subprocess.check_output(
            ['powershell', '-Command', 
             "$explorerProc = Get-Process -Name explorer | Where-Object {$_.SessionId -eq (Get-Process -Id $pid).SessionId} | Select-Object -First 1; "
             "$sid = (gwmi -Query ('Select * From Win32_Process Where ProcessID=' + $explorerProc.Id)).GetOwnerSid().Sid; $sid"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if output:
            return output
    except:
        pass
    # Fallback: get SID from current user account
    try:
        import win32security
        import win32api
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
        sid, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
        return win32security.ConvertSidToStringSid(sid)
    except:
        return None

def get_architecture():
    # returns "x86" or "x64"
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
        arch, _ = winreg.QueryValueEx(key, "PROCESSOR_ARCHITECTURE")
        winreg.CloseKey(key)
        if arch.lower() == "amd64":
            return "x64"
        else:
            return "x86"
    except:
        return "x86"

def get_idm_path():
    arch = get_architecture()
    if arch == "x64":
        default_path = r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe"
    else:
        default_path = r"C:\Program Files\Internet Download Manager\IDMan.exe"
    # Try to read from registry
    try:
        sid = get_user_sid()
        if sid:
            key = winreg.OpenKey(winreg.HKEY_USERS, rf"{sid}\Software\DownloadManager")
            idm_path, _ = winreg.QueryValueEx(key, "ExePath")
            winreg.CloseKey(key)
            if os.path.exists(idm_path):
                return idm_path
    except:
        pass
    return default_path if os.path.exists(default_path) else None

def kill_idm():
    subprocess.run("taskkill /f /im idman.exe", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

def backup_clsid(backup_dir):
    sid = get_user_sid()
    timestamp = time.strftime("%Y%m%d-%H%M%S%f")[:-3]
    arch = get_architecture()
    if arch == "x86":
        clsid_key = r"HKCU\Software\Classes\CLSID"
    else:
        clsid_key = r"HKCU\Software\Classes\Wow6432Node\CLSID"
    backup_file = os.path.join(backup_dir, f"_Backup_{clsid_key.replace('\\','_')}_{timestamp}.reg")
    subprocess.run(f'reg export "{clsid_key}" "{backup_file}" /y', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sid and not is_hkcu_synced():
        clsid_key2 = rf"HKU\{sid}\Software\Classes\Wow6432Node\CLSID" if arch == "x64" else rf"HKU\{sid}\Software\Classes\CLSID"
        backup_file2 = os.path.join(backup_dir, f"_Backup_{clsid_key2.replace('\\','_')}_{timestamp}.reg")
        subprocess.run(f'reg export "{clsid_key2}" "{backup_file2}" /y', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def is_hkcu_synced():
    # Test if HKCU and HKU\SID are synced by writing a test key
    sid = get_user_sid()
    if not sid:
        return False
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, "IAS_TEST")
        winreg.CreateKey(winreg.HKEY_USERS, f"{sid}\\IAS_TEST")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, "IAS_TEST")
        winreg.DeleteKey(winreg.HKEY_USERS, f"{sid}\\IAS_TEST")
        return True
    except:
        return False

# ---------- Core Registry Manipulation ----------
def delete_idm_registry_values(sid, hkcu_synced):
    # Delete specific values under DownloadManager and the HKLM key
    paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\DownloadManager", ["FName", "LName", "Email", "Serial", "scansk", "tvfrdt", "radxcnt", "LstCheck", "ptrk_scdt", "LastCheckQU"]),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Internet Download Manager" if get_architecture() == "x64" else r"SOFTWARE\Internet Download Manager", [""])  # delete entire key
    ]
    # Delete entire HKLM key
    try:
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, paths[1][1])
        print(f"Deleted - {paths[1][1]}")
    except:
        pass
    # Delete values from HKCU
    for hive, subkey, values in paths[:1]:
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)
            for val in values:
                try:
                    winreg.DeleteValue(key, val)
                    print(f"Deleted - {subkey}\\{val}")
                except:
                    pass
            winreg.CloseKey(key)
        except:
            pass
    if not hkcu_synced and sid:
        try:
            key = winreg.OpenKey(winreg.HKEY_USERS, f"{sid}\\Software\\DownloadManager", 0, winreg.KEY_SET_VALUE)
            for val in ["FName", "LName", "Email", "Serial", "scansk", "tvfrdt", "radxcnt", "LstCheck", "ptrk_scdt", "LastCheckQU"]:
                try:
                    winreg.DeleteValue(key, val)
                    print(f"Deleted - HKU\\{sid}\\Software\\DownloadManager\\{val}")
                except:
                    pass
            winreg.CloseKey(key)
        except:
            pass

def add_advintdriver_key():
    arch = get_architecture()
    if arch == "x64":
        key_path = r"SOFTWARE\Wow6432Node\Internet Download Manager"
    else:
        key_path = r"SOFTWARE\Internet Download Manager"
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        winreg.SetValueEx(key, "AdvIntDriverEnabled2", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        print(f"Added - HKLM\\{key_path}\\AdvIntDriverEnabled2")
    except Exception as e:
        print(f"Failed - HKLM\\{key_path}\\AdvIntDriverEnabled2 : {e}")

def register_idm(sid, hkcu_synced):
    fname = random.randint(1000, 9999)
    lname = random.randint(1000, 9999)
    email = f"{fname}.{lname}@tonec.com"
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=5)) for _ in range(4))
    print("Applying registration details...")
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\DownloadManager")
        winreg.SetValueEx(k, "FName", 0, winreg.REG_SZ, str(fname))
        winreg.SetValueEx(k, "LName", 0, winreg.REG_SZ, str(lname))
        winreg.SetValueEx(k, "Email", 0, winreg.REG_SZ, email)
        winreg.SetValueEx(k, "Serial", 0, winreg.REG_SZ, key)
        winreg.CloseKey(k)
        print(f"Added - HKCU\\Software\\DownloadManager\\...")
    except Exception as e:
        print(f"Failed to write to HKCU: {e}")
    if not hkcu_synced and sid:
        try:
            k = winreg.CreateKey(winreg.HKEY_USERS, rf"{sid}\Software\DownloadManager")
            winreg.SetValueEx(k, "FName", 0, winreg.REG_SZ, str(fname))
            winreg.SetValueEx(k, "LName", 0, winreg.REG_SZ, str(lname))
            winreg.SetValueEx(k, "Email", 0, winreg.REG_SZ, email)
            winreg.SetValueEx(k, "Serial", 0, winreg.REG_SZ, key)
            winreg.CloseKey(k)
            print(f"Added - HKU\\{sid}\\Software\\DownloadManager\\...")
        except Exception as e:
            print(f"Failed to write to HKU: {e}")

def download_files(idm_path):
    # Downloads three images to trigger IDM registry keys
    download_urls = [
        "https://www.internetdownloadmanager.com/images/idm_box_min.png",
        "https://www.internetdownloadmanager.com/register/IDMlib/images/idman_logos.png",
        "https://www.internetdownloadmanager.com/pictures/idm_about.png"
    ]
    temp_dir = os.environ.get('SystemRoot', 'C:\\Windows') + "\\Temp"
    temp_file = os.path.join(temp_dir, "temp.png")
    print("Triggering downloads to create necessary registry keys...")
    for url in download_urls:
        subprocess.Popen([idm_path, "/n", "/d", url, "/p", temp_dir, "/f", "temp.png"], shell=False)
        time.sleep(1)
        for _ in range(20):  # wait up to 20 seconds
            if os.path.exists(temp_file):
                break
            time.sleep(1)
        kill_idm()
        if os.path.exists(temp_file):
            os.remove(temp_file)
    print("Downloads completed.")

# ---------- CLSID Scanning and Manipulation (using PowerShell for simplicity) ----------
# The original script uses a complex PowerShell routine to find and lock/delete specific CLSID keys.
# Here we invoke that same PowerShell script from Python to maintain identical behavior.
def run_regscan_ps(sid, hkcu_synced, lock=False, delete=False, toggle=False):
    # Build the PowerShell command from the original batch's :regscan: block
    # Because it's lengthy and relies on .NET for permissions, we execute it directly.
    ps_script = f'''
$sid = '{sid}'
$HKCUsync = {0 if hkcu_synced else 1}
$lockKey = $(if ($lock) {{1}} else {{$null}})
$deleteKey = $(if ($delete) {{1}} else {{$null}})
$toggle = $(if ($toggle) {{1}} else {{$null}})
$finalValues = @()

$arch = (Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment').PROCESSOR_ARCHITECTURE
if ($arch -eq "x86") {{
  $regPaths = @("HKCU:\\Software\\Classes\\CLSID", "Registry::HKEY_USERS\\$sid\\Software\\Classes\\CLSID")
}} else {{
  $regPaths = @("HKCU:\\Software\\Classes\\WOW6432Node\\CLSID", "Registry::HKEY_USERS\\$sid\\Software\\Classes\\Wow6432Node\\CLSID")
}}

foreach ($regPath in $regPaths) {{
    if (($regPath -match "HKEY_USERS") -and ($HKCUsync -ne $null)) {{ continue }}
    Write-Host "Searching IDM CLSID Registry Keys in $regPath"
    $subKeys = Get-ChildItem -Path $regPath -ErrorAction SilentlyContinue -ErrorVariable lockedKeys | Where-Object {{ $_.PSChildName -match '^\\{{[A-F0-9]{{8}}-[A-F0-9]{{4}}-[A-F0-9]{{4}}-[A-F0-9]{{4}}-[A-F0-9]{{12}}\\}}$' }}
    foreach ($lockedKey in $lockedKeys) {{
        $leafValue = Split-Path -Path $lockedKey.TargetObject -Leaf
        $finalValues += $leafValue
        Write-Output "$leafValue - Found Locked Key"
    }}
    if ($subKeys -eq $null) {{ continue }}
    $subKeysToExclude = "LocalServer32", "InProcServer32", "InProcHandler32"
    $filteredKeys = $subKeys | Where-Object {{ !($_.GetSubKeyNames() | Where-Object {{ $subKeysToExclude -contains $_ }}) }}
    foreach ($key in $filteredKeys) {{
        $fullPath = $key.PSPath
        $keyValues = Get-ItemProperty -Path $fullPath -ErrorAction SilentlyContinue
        $defaultValue = $keyValues.PSObject.Properties | Where-Object {{ $_.Name -eq '(default)' }} | Select-Object -ExpandProperty Value
        if (($defaultValue -match "^\\d+$") -and ($key.SubKeyCount -eq 0)) {{
            $finalValues += $($key.PSChildName)
            Write-Output "$($key.PSChildName) - Found Digit In Default and No Subkeys"
            continue
        }}
        if (($defaultValue -match "\\+|=") -and ($key.SubKeyCount -eq 0)) {{
            $finalValues += $($key.PSChildName)
            Write-Output "$($key.PSChildName) - Found + or = In Default and No Subkeys"
            continue
        }}
        $versionValue = Get-ItemProperty -Path "$fullPath\\Version" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty '(default)' -ErrorAction SilentlyContinue
        if (($versionValue -match "^\\d+$") -and ($key.SubKeyCount -eq 1)) {{
            $finalValues += $($key.PSChildName)
            Write-Output "$($key.PSChildName) - Found Digit In \\Version and No Other Subkeys"
            continue
        }}
        $keyValues.PSObject.Properties | ForEach-Object {{
            if ($_.Name -match "MData|Model|scansk|Therad") {{
                $finalValues += $($key.PSChildName)
                Write-Output "$($key.PSChildName) - Found MData Model scansk Therad"
                continue
            }}
        }}
        if (($key.ValueCount -eq 0) -and ($key.SubKeyCount -eq 0)) {{
            $finalValues += $($key.PSChildName)
            Write-Output "$($key.PSChildName) - Found Empty Key"
            continue
        }}
    }}
}}

$finalValues = @($finalValues | Select-Object -Unique)

if ($finalValues -ne $null) {{
    Write-Host
    if ($lockKey -ne $null) {{ Write-Host "Locking IDM CLSID Registry Keys..." }}
    if ($deleteKey -ne $null) {{ Write-Host "Deleting IDM CLSID Registry Keys..." }}
    Write-Host
}} else {{
    Write-Host "IDM CLSID Registry Keys are not found."
    Exit
}}

if (($finalValues.Count -gt 20) -and ($toggle -ne $null)) {{
    $lockKey = $null
    $deleteKey = 1
    Write-Host "The IDM keys count is more than 20. Deleting them now instead of locking..."
    Write-Host
}}

function Take-Permissions {{
    param($rootKey, $regKey)
    $AssemblyBuilder = [AppDomain]::CurrentDomain.DefineDynamicAssembly(4, 1)
    $ModuleBuilder = $AssemblyBuilder.DefineDynamicModule(2, $False)
    $TypeBuilder = $ModuleBuilder.DefineType(0)
    $TypeBuilder.DefinePInvokeMethod('RtlAdjustPrivilege', 'ntdll.dll', 'Public, Static', 1, [int], @([int], [bool], [bool], [bool].MakeByRefType()), 1, 3) | Out-Null
    9,17,18 | ForEach-Object {{ $TypeBuilder.CreateType()::RtlAdjustPrivilege($_, $true, $false, [ref]$false) | Out-Null }}
    $SID = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
    $IDN = ($SID.Translate([System.Security.Principal.NTAccount])).Value
    $Admin = New-Object System.Security.Principal.NTAccount($IDN)
    $everyone = New-Object System.Security.Principal.SecurityIdentifier('S-1-1-0')
    $none = New-Object System.Security.Principal.SecurityIdentifier('S-1-0-0')
    $key = [Microsoft.Win32.Registry]::$rootKey.OpenSubKey($regkey, 'ReadWriteSubTree', 'TakeOwnership')
    $acl = New-Object System.Security.AccessControl.RegistrySecurity
    $acl.SetOwner($Admin)
    $key.SetAccessControl($acl)
    $key = $key.OpenSubKey('', 'ReadWriteSubTree', 'ChangePermissions')
    $rule = New-Object System.Security.AccessControl.RegistryAccessRule($everyone, 'FullControl', 'ContainerInherit', 'None', 'Allow')
    $acl.ResetAccessRule($rule)
    $key.SetAccessControl($acl)
    if ($lockKey -ne $null) {{
        $acl = New-Object System.Security.AccessControl.RegistrySecurity
        $acl.SetOwner($none)
        $key.SetAccessControl($acl)
        $key = $key.OpenSubKey('', 'ReadWriteSubTree', 'ChangePermissions')
        $rule = New-Object System.Security.AccessControl.RegistryAccessRule($everyone, 'FullControl', 'Deny')
        $acl.ResetAccessRule($rule)
        $key.SetAccessControl($acl)
    }}
}}

foreach ($regPath in $regPaths) {{
    if (($regPath -match "HKEY_USERS") -and ($HKCUsync -ne $null)) {{ continue }}
    foreach ($finalValue in $finalValues) {{
        $fullPath = Join-Path -Path $regPath -ChildPath $finalValue
        if ($fullPath -match 'HKCU:') {{ $rootKey = 'CurrentUser' }} else {{ $rootKey = 'Users' }}
        $position = $fullPath.IndexOf("\\")
        $regKey = $fullPath.Substring($position + 1)
        if ($lockKey -ne $null) {{
            if (-not (Test-Path -Path $fullPath -ErrorAction SilentlyContinue)) {{ New-Item -Path $fullPath -Force -ErrorAction SilentlyContinue | Out-Null }}
            Take-Permissions $rootKey $regKey
            try {{
                Remove-Item -Path $fullPath -Force -Recurse -ErrorAction Stop
                Write-Host -back 'DarkRed' -fore 'white' "Failed - $fullPath"
            }} catch {{
                Write-Host "Locked - $fullPath"
            }}
        }}
        if ($deleteKey -ne $null) {{
            if (Test-Path -Path $fullPath) {{
                Remove-Item -Path $fullPath -Force -Recurse -ErrorAction SilentlyContinue
                if (Test-Path -Path $fullPath) {{
                    Take-Permissions $rootKey $regKey
                    try {{
                        Remove-Item -Path $fullPath -Force -Recurse -ErrorAction Stop
                        Write-Host "Deleted - $fullPath"
                    }} catch {{
                        Write-Host -back 'DarkRed' -fore 'white' "Failed - $fullPath"
                    }}
                }} else {{
                    Write-Host "Deleted - $fullPath"
                }}
            }}
        }}
    }}
}}
'''
    # Inject parameters
    ps_script = ps_script.replace('$lockKey = $(if ($lock) {{1}} else {{$null}})', f'$lockKey = {1 if lock else "$null"}')
    ps_script = ps_script.replace('$deleteKey = $(if ($delete) {{1}} else {{$null}})', f'$deleteKey = {1 if delete else "$null"}')
    ps_script = ps_script.replace('$toggle = $(if ($toggle) {{1}} else {{$null}})', f'$toggle = {1 if toggle else "$null"}')
    subprocess.run(["powershell", "-Command", ps_script], check=False)

# ---------- High-level actions ----------
def reset_activation():
    print("Resetting IDM activation/trial...")
    kill_idm()
    sid = get_user_sid()
    hkcu_synced = is_hkcu_synced()
    backup_dir = os.environ.get('SystemRoot', 'C:\\Windows') + "\\Temp"
    backup_clsid(backup_dir)
    delete_idm_registry_values(sid, hkcu_synced)
    run_regscan_ps(sid, hkcu_synced, delete=True)
    print("Reset completed.")

def activate_idm():
    print("Activating IDM...")
    idm_path = get_idm_path()
    if not idm_path or not os.path.exists(idm_path):
        print("IDM not installed. Please install IDM first.")
        return
    kill_idm()
    sid = get_user_sid()
    hkcu_synced = is_hkcu_synced()
    backup_dir = os.environ.get('SystemRoot', 'C:\\Windows') + "\\Temp"
    backup_clsid(backup_dir)
    delete_idm_registry_values(sid, hkcu_synced)
    add_advintdriver_key()
    run_regscan_ps(sid, hkcu_synced, toggle=True)  # This runs the scanner with toggle (will delete if >20 keys)
    register_idm(sid, hkcu_synced)
    download_files(idm_path)
    run_regscan_ps(sid, hkcu_synced, lock=True)   # Lock keys after download
    print("Activation process completed.")

def freeze_trial():
    print("Freezing IDM trial period...")
    idm_path = get_idm_path()
    if not idm_path or not os.path.exists(idm_path):
        print("IDM not installed. Please install IDM first.")
        return
    kill_idm()
    sid = get_user_sid()
    hkcu_synced = is_hkcu_synced()
    backup_dir = os.environ.get('SystemRoot', 'C:\\Windows') + "\\Temp"
    backup_clsid(backup_dir)
    delete_idm_registry_values(sid, hkcu_synced)
    add_advintdriver_key()
    run_regscan_ps(sid, hkcu_synced, lock=True)   # Lock keys without activation
    print("Trial period freezed successfully.")

def show_main_menu():
    while True:
        print("\n" + "="*60)
        print("IDM Activation Script")
        print("="*60)
        print("1. Freeze Trial")
        print("2. Activate")
        print("3. Reset Activation / Trial")
        print("4. Download IDM")
        print("5. Help")
        print("0. Exit")
        choice = input("Enter your choice [1,2,3,4,5,0]: ").strip()
        if choice == "1":
            freeze_trial()
        elif choice == "2":
            activate_idm()
        elif choice == "3":
            reset_activation()
        elif choice == "4":
            os.startfile("https://www.internetdownloadmanager.com/download.html")
        elif choice == "5":
            os.startfile("https://github.com/WindowsAddict/IDM-Activation-Script")
            os.startfile("https://massgrave.dev/idm-activation-script")
        elif choice == "0":
            break
        else:
            print("Invalid choice, try again.")
        input("\nPress Enter to continue...")
