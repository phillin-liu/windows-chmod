# -*- coding: utf-8 -*-
"""
chmod permissions — Unix ↔ icacls permission conversion and formatting.
"""

from typing import Dict, Optional

from .constants import PERM_READ, PERM_WRITE, PERM_EXEC


# ============================================================
# Permission formatting (rwx / octal strings)
# ============================================================

def perm_to_rwx(perm: int) -> str:
    """Convert a 3-bit permission value to rwx string. e.g., 7 -> 'rwx', 5 -> 'r-x'."""
    return (
        ("r" if perm & PERM_READ else "-") +
        ("w" if perm & PERM_WRITE else "-") +
        ("x" if perm & PERM_EXEC else "-")
    )


def perms_to_string(perms: Dict[str, int], special: int = 0) -> str:
    """Convert permission dict to a full rwx string like 'rwxr-xr-x'."""
    u = perms.get("u", 0)
    g = perms.get("g", 0)
    o = perms.get("o", 0)
    a = perms.get("a", 0)

    u_str = perm_to_rwx(u)
    g_str = perm_to_rwx(g)
    o_str = perm_to_rwx(o)
    a_str = perm_to_rwx(a)

    # Setuid: 's' replaces 'x' in owner position if set
    if special & 0o4000:
        u_str = u_str[:2] + ("s" if u & PERM_EXEC else "S")
    # Setgid: 's' replaces 'x' in group position if set
    if special & 0o2000:
        g_str = g_str[:2] + ("s" if g & PERM_EXEC else "S")
    # Sticky: 't' replaces 'x' in others position if set
    if special & 0o1000:
        o_str = o_str[:2] + ("t" if o & PERM_EXEC else "T")

    return f"[a:{a_str}] {u_str}{g_str}{o_str}"


def perms_to_octal(perms: Dict[str, int], special: int = 0) -> str:
    """Convert permission dict to octal string like '0755'."""
    u = perms.get("u", 0)
    g = perms.get("g", 0)
    o = perms.get("o", 0)
    a = perms.get("a", 0)
    special_digit = 0
    if special & 0o4000:
        special_digit |= 4
    if special & 0o2000:
        special_digit |= 2
    if special & 0o1000:
        special_digit |= 1
    return f"{special_digit}{a}{u}{g}{o}"


# ============================================================
# Icacls ↔ Unix permission conversion
# ============================================================

def icacls_to_unix_perm(perm_str: str) -> int:
    """Convert icacls permission string (e.g., 'R', 'W', 'RX', 'M', 'F') to Unix perm bits."""
    perm_str = perm_str.upper().strip()
    unix_perm = 0

    if "F" in perm_str:
        return PERM_READ | PERM_WRITE | PERM_EXEC
    if "M" in perm_str:
        return PERM_READ | PERM_WRITE | PERM_EXEC

    if "R" in perm_str:
        unix_perm |= PERM_READ
    if "W" in perm_str:
        unix_perm |= PERM_WRITE
    if "X" in perm_str:
        unix_perm |= PERM_EXEC

    return unix_perm


def unix_to_icacls_perm(unix_perm: int) -> Optional[str]:
    """Convert Unix permission bits to icacls permission string.

    Prefer predefined icacls combos (F, RX, R, W) because they map cleanly
    to Windows' standard permission checkboxes in the property dialog.
    Combinations that don't match a standard combo are emitted with commas
    (e.g., 'R,W') and will show as "Special permissions" in the GUI.
    """
    if unix_perm == 0:
        return None

    # rwx -> Full control, so 777 shows "完全控制" instead of "特殊权限"
    if unix_perm == (PERM_READ | PERM_WRITE | PERM_EXEC):
        return "F"
    # r-x -> Read & execute
    if unix_perm == (PERM_READ | PERM_EXEC):
        return "RX"
    # r-- -> Read
    if unix_perm == PERM_READ:
        return "R"
    # -w- -> Write
    if unix_perm == PERM_WRITE:
        return "W"

    perms = []
    if unix_perm & PERM_READ:
        perms.append("R")
    if unix_perm & PERM_WRITE:
        perms.append("W")
    if unix_perm & PERM_EXEC:
        perms.append("X")
    return ",".join(perms) if perms else None
