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

VERSION = "1.2.0"

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
    """Re-launch the current process with administrator privileges via UAC.

    Uses ShellExecuteW with the 'runas' verb (the same mechanism UAC uses).
    Works for both `python chmod/run_chmod.py` and a Nuitka-packaged .exe.
    The elevated copy runs and this process exits.
    """
    if sys.platform != "win32":
        print("chmod: auto-elevation is only supported on Windows.", file=sys.stderr)
        return

    try:
        import os
        import subprocess
        import ctypes

        if getattr(sys, "frozen", False) or sys.argv[0].lower().endswith(".exe"):
            # Packaged executable: elevate the exe itself
            executable = os.path.abspath(sys.argv[0])
            params = subprocess.list2cmdline(sys.argv[1:])
        else:
            # Python script: elevate via the current interpreter
            executable = sys.executable
            params = subprocess.list2cmdline(
                [os.path.abspath(sys.argv[0])] + sys.argv[1:]
            )

        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 1
        )
        if result <= 32:  # ShellExecuteW error codes are <= 32
            raise OSError(f"ShellExecuteW failed with code {result}")
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
