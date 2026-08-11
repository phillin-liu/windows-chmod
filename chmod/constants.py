# -*- coding: utf-8 -*-
"""
chmod constants — permission bits, Windows account mappings, encoding,
and admin privilege detection.
"""

import ctypes
import sys

# ============================================================
# Encoding for subprocess output
# ============================================================

def _get_oem_encoding() -> str:
    """Get the Windows OEM code page encoding for subprocess output."""
    try:
        code_page = ctypes.kernel32.GetOEMCP()
        return f"cp{code_page}"
    except Exception:
        return "utf-8"


ICACLS_ENCODING = _get_oem_encoding()

VERSION = "1.0.1"

# ============================================================
# Admin privilege detection
# ============================================================

def is_admin() -> bool:
    """Check whether the current process has administrator privileges."""
    try:
        if sys.platform != "win32":
            # On non-Windows, assume admin/root is not needed
            return True
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    """Re-launch the current script with administrator privileges via UAC.
    This replaces the current process — code after this call will not execute.
    """
    if sys.platform != "win32":
        print("chmod: auto-elevation is only supported on Windows.", file=sys.stderr)
        return

    try:
        import subprocess

        # Build the full command line from sys.argv
        script_path = sys.argv[0]
        args = sys.argv[1:]

        # Use PowerShell to re-launch with RunAs verb
        ps_script = (
            f'Start-Process -FilePath (Get-Command python).Source '
            f'-ArgumentList \'{script_path} {" ".join(args)}\' '
            f'-Verb RunAs -Wait'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            check=False
        )
    except Exception as e:
        print(f"chmod: failed to re-launch as admin: {e}", file=sys.stderr)


# ============================================================
# Unix permission bits
# ============================================================

PERM_READ  = 4    # r
PERM_WRITE = 2    # w
PERM_EXEC  = 1    # x

# Special bits
S_ISUID = 0o4000  # Set UID
S_ISGID = 0o2000  # Set GID
S_ISVTX = 0o1000  # Sticky bit

# ============================================================
# Windows account mappings
# ============================================================

# u (user/owner)  -> file's actual owner (queried via PowerShell at runtime)
# g (group)       -> BUILTIN\Users (all local users)
# o (others)      -> Everyone
GROUP_ACCOUNT  = "BUILTIN\\Users"
OTHERS_ACCOUNT = "Everyone"
ADMIN_ACCOUNT  = "BUILTIN\\Administrators"   # equivalent to Linux root

# icacls inheritance flags to ignore when parsing permissions
INHERITANCE_FLAGS = {"OI", "CI", "IO", "NP", "ID", "FI", "FC"}
