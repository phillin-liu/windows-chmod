# -*- coding: utf-8 -*-
"""
chmod ACL manager — read / write Windows file ACLs via icacls + PowerShell.
"""

import os
import sys
import re
import stat as stat_module
import subprocess
from typing import Dict, Optional, Tuple

from .constants import (
    ICACLS_ENCODING, PERM_READ, PERM_WRITE, PERM_EXEC,
    GROUP_ACCOUNT, OTHERS_ACCOUNT, ADMIN_ACCOUNT, INHERITANCE_FLAGS,
)
from .permissions import icacls_to_unix_perm, unix_to_icacls_perm


# ============================================================
# ACL Manager
# ============================================================

class ACLManager:
    """Manage Windows file ACLs using icacls and PowerShell."""

    @staticmethod
    def get_file_owner(filepath: str) -> Optional[str]:
        """Get the owner account of a file using PowerShell."""
        try:
            ps_script = f'(Get-Acl -LiteralPath "{filepath}").Owner'
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True,
                encoding=ICACLS_ENCODING, errors="replace", timeout=15
            )
            owner = result.stdout.strip()
            if owner:
                return owner
        except Exception:
            pass
        return None

    @staticmethod
    def get_current_perms(filepath: str) -> Tuple[Dict[str, int], int]:
        """
        Read current permissions from icacls output and convert to Unix-style.
        Returns (perms_dict, special_bits).
        """
        perms = {"u": 0, "g": 0, "o": 0, "a": PERM_READ | PERM_WRITE | PERM_EXEC}
        special = 0

        try:
            result = subprocess.run(
                ["icacls", filepath],
                capture_output=True, text=True,
                encoding=ICACLS_ENCODING, errors="replace", timeout=15
            )

            if result.returncode != 0:
                return ACLManager._get_perms_from_stat(filepath)

            owner = ACLManager.get_file_owner(filepath)

            for line in result.stdout.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if "Successfully" in line or "Failed" in line:
                    continue

                norm_path = os.path.normpath(filepath)
                # icacls may print the path with either slash direction
                for path_variant in (norm_path, norm_path.replace("\\", "/")):
                    if path_variant and path_variant in line:
                        line = line.replace(path_variant, "", 1).strip()
                        break

                groups = re.findall(r"\(([^)]+)\)", line)
                if not groups:
                    continue

                paren_match = re.search(r"\(", line)
                if not paren_match:
                    continue
                principal = line[:paren_match.start()].strip()
                if principal.endswith(":"):
                    principal = principal[:-1].strip()

                perm_letters = ""
                for g in groups:
                    g_upper = g.upper().strip()
                    if g_upper not in INHERITANCE_FLAGS:
                        perm_letters = g_upper
                        break

                if not perm_letters:
                    continue

                perm_val = icacls_to_unix_perm(perm_letters)

                principal_upper = principal.upper()
                if owner and principal_upper == owner.upper():
                    perms["u"] = perm_val
                elif "BUILTIN" in principal_upper and "USERS" in principal_upper \
                        and "ADMINISTRATORS" not in principal_upper:
                    perms["g"] = perm_val
                elif "BUILTIN" in principal_upper and "ADMINISTRATORS" in principal_upper:
                    perms["a"] = perm_val
                elif "EVERYONE" in principal_upper:
                    perms["o"] = perm_val
                elif "AUTHENTICATED" in principal_upper and "USERS" in principal_upper:
                    if perms["o"] == 0:
                        perms["o"] = perm_val

        except FileNotFoundError:
            print("Error: icacls command not found. This tool requires Windows.",
                  file=sys.stderr)
            sys.exit(1)
        except Exception:
            return ACLManager._get_perms_from_stat(filepath)

        return perms, special

    @staticmethod
    def _get_perms_from_stat(filepath: str) -> Tuple[Dict[str, int], int]:
        """Fallback: get permissions from os.stat()."""
        try:
            st = os.stat(filepath)
            mode = st.st_mode
            perms = {
                "u": ((mode & 0o400) and PERM_READ or 0) |
                     ((mode & 0o200) and PERM_WRITE or 0) |
                     ((mode & 0o100) and PERM_EXEC or 0),
                "g": ((mode & 0o040) and PERM_READ or 0) |
                     ((mode & 0o020) and PERM_WRITE or 0) |
                     ((mode & 0o010) and PERM_EXEC or 0),
                "o": ((mode & 0o004) and PERM_READ or 0) |
                     ((mode & 0o002) and PERM_WRITE or 0) |
                     ((mode & 0o001) and PERM_EXEC or 0),
                "a": PERM_READ | PERM_WRITE | PERM_EXEC,
            }
            special = mode & 0o7000
            return perms, special
        except Exception:
            return {"u": 0, "g": 0, "o": 0, "a": PERM_READ | PERM_WRITE | PERM_EXEC}, 0

    @staticmethod
    def set_permissions(filepath: str, perms: Dict[str, int],
                        special: int = 0, verbose: bool = False,
                        quiet: bool = False) -> bool:
        """
        Set Windows ACLs to match the given Unix permissions.
        Returns True if successful, False otherwise.
        """
        owner = ACLManager.get_file_owner(filepath)

        operations = []

        if owner:
            icacls_perm = unix_to_icacls_perm(perms["u"])
            operations.append((owner, icacls_perm))
        else:
            import getpass
            current_user = getpass.getuser()
            icacls_perm = unix_to_icacls_perm(perms["u"])
            operations.append((current_user, icacls_perm))

        icacls_perm_g = unix_to_icacls_perm(perms["g"])
        operations.append((GROUP_ACCOUNT, icacls_perm_g))

        icacls_perm_o = unix_to_icacls_perm(perms["o"])
        operations.append((OTHERS_ACCOUNT, icacls_perm_o))

        # Administrator always gets Full Control (equivalent to root on Linux)
        operations.append((ADMIN_ACCOUNT, "F"))

        remove_accounts = []
        grant_args = []

        for account, icacls_perm in operations:
            remove_accounts.append(account)
            if icacls_perm:
                grant_args.append(f"{account}:({icacls_perm})")

        success = True

        # Step 1: Disable inheritance (convert inherited to explicit)
        try:
            subprocess.run(
                ["icacls", filepath, "/inheritance:d"],
                capture_output=True, text=True,
                encoding=ICACLS_ENCODING, errors="replace", timeout=15
            )
        except Exception:
            pass

        # Step 2: Remove existing ACEs for managed accounts
        if remove_accounts:
            cmd_remove = ["icacls", filepath, "/remove:g"]
            for acc in remove_accounts:
                cmd_remove.append(acc)

            if verbose:
                print(f"  Removing existing ACEs for: {', '.join(remove_accounts)}")

            try:
                result = subprocess.run(cmd_remove, capture_output=True, text=True,
                                        encoding=ICACLS_ENCODING, errors="replace",
                                        timeout=15)
                if result.returncode != 0 and not quiet:
                    stderr = (result.stderr or "").strip()
                    if stderr:
                        print(f"  Warning: {stderr}", file=sys.stderr)
            except Exception as e:
                if not quiet:
                    print(f"  Error removing ACEs: {e}", file=sys.stderr)
                success = False

        # Step 3: Grant new permissions (replace existing ACEs for these accounts)
        if grant_args:
            cmd_grant = ["icacls", filepath, "/grant:r"]
            for arg in grant_args:
                cmd_grant.append(arg)

            if verbose:
                print(f"  Granting: {', '.join(grant_args)}")

            try:
                result = subprocess.run(cmd_grant, capture_output=True, text=True,
                                        encoding=ICACLS_ENCODING, errors="replace",
                                        timeout=15)
                if result.returncode != 0:
                    if not quiet:
                        stderr = (result.stderr or "").strip()
                        stdout = (result.stdout or "").strip()
                        msg = stderr or stdout
                        if msg:
                            print(f"  Error: {msg}", file=sys.stderr)
                    success = False
            except Exception as e:
                if not quiet:
                    print(f"  Error granting permissions: {e}", file=sys.stderr)
                success = False

        # Step 4: Set read-only attribute as supplementary protection
        try:
            if perms["u"] & PERM_WRITE:
                os.chmod(filepath, stat_module.S_IREAD | stat_module.S_IWRITE)
            else:
                os.chmod(filepath, stat_module.S_IREAD)
        except Exception:
            pass

        # Step 5: Warn about special bits (no direct Windows equivalent)
        if special and not quiet:
            special_names = []
            if special & 0o4000:
                special_names.append("setuid")
            if special & 0o2000:
                special_names.append("setgid")
            if special & 0o1000:
                special_names.append("sticky")
            if special_names:
                print(f"WARNING: chmod cannot set special bit(s) "
                      f"({', '.join(special_names)}); "
                      f"they have no direct Windows equivalent.", file=sys.stderr)

        return success
