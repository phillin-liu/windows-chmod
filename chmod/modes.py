# -*- coding: utf-8 -*-
"""
chmod modes — symbolic and numeric mode parsing and application.
"""

import re
from typing import Dict, List, Tuple

from .constants import PERM_READ, PERM_WRITE, PERM_EXEC


# ============================================================
# Symbolic mode clause
# ============================================================

class SymbolicClause:
    """Represents a single symbolic mode clause, e.g., 'u+x', 'go-w', 'a=r'."""

    def __init__(self, who: str, op: str, perms: str):
        self.who = who        # e.g., 'ug', 'o', 'a', ''
        self.op = op          # '+', '-', '='
        self.perms = perms    # e.g., 'rwx', 'rx', 'ugo'

    def apply(self, current_perms: Dict[str, int], is_dir: bool,
              current_special: int = 0) -> Tuple[Dict[str, int], int]:
        """Apply this clause to current permissions. Returns (new_perms, new_special)."""
        perms = dict(current_perms)
        special = current_special

        # Determine which categories to affect
        if not self.who or "a" in self.who:
            categories = ["u", "g", "o"]
        else:
            categories = []
            if "u" in self.who:
                categories.append("u")
            if "g" in self.who:
                categories.append("g")
            if "o" in self.who:
                categories.append("o")

        # Handle reference to other category (u, g, o in perms)
        if self.perms in ("u", "g", "o") and self.op == "=":
            ref_perm = current_perms.get(self.perms, 0)
            for cat in categories:
                perms[cat] = ref_perm
            return perms, special

        # Compute the permission bits to add/remove/set
        target_perm = 0
        has_x_capital = False
        has_special = False
        special_bits = 0

        for ch in self.perms:
            if ch == "r":
                target_perm |= PERM_READ
            elif ch == "w":
                target_perm |= PERM_WRITE
            elif ch == "x":
                target_perm |= PERM_EXEC
            elif ch == "X":
                has_x_capital = True
            elif ch == "s":
                has_special = True
                if "u" in self.who or not self.who or "a" in self.who:
                    special_bits |= 0o4000
                if "g" in self.who or not self.who or "a" in self.who:
                    special_bits |= 0o2000
            elif ch == "t":
                has_special = True
                special_bits |= 0o1000

        for cat in categories:
            if self.op == "+":
                new_perm = perms[cat] | target_perm
                if has_x_capital:
                    if is_dir or (perms[cat] & PERM_EXEC):
                        new_perm |= PERM_EXEC
                perms[cat] = new_perm
            elif self.op == "-":
                new_perm = perms[cat] & ~target_perm
                if has_x_capital:
                    new_perm &= ~PERM_EXEC
                perms[cat] = new_perm
            elif self.op == "=":
                new_perm = target_perm
                if has_x_capital:
                    if is_dir or (perms[cat] & PERM_EXEC):
                        new_perm |= PERM_EXEC
                perms[cat] = new_perm

        if has_special:
            if self.op == "+":
                special |= special_bits
            elif self.op == "-":
                special &= ~special_bits
            elif self.op == "=":
                if "u" in categories or not self.who:
                    if special_bits & 0o4000:
                        special |= 0o4000
                    else:
                        special &= ~0o4000
                if "g" in categories or not self.who:
                    if special_bits & 0o2000:
                        special |= 0o2000
                    else:
                        special &= ~0o2000
                if "o" in categories or not self.who:
                    if special_bits & 0o1000:
                        special |= 0o1000
                    else:
                        special &= ~0o1000

        return perms, special


# ============================================================
# Numeric mode
# ============================================================

class NumericMode:
    """Represents a numeric (octal) mode like 755, 4755, 1755."""

    def __init__(self, mode_str: str):
        padded = mode_str.zfill(4)
        if len(padded) > 4 or not all(c in "01234567" for c in padded):
            raise ValueError(f"invalid numeric mode: '{mode_str}'")

        self.special = int(padded[0])
        self.u = int(padded[1])
        self.g = int(padded[2])
        self.o = int(padded[3])

        self.special_bits = 0
        if self.special & 4:
            self.special_bits |= 0o4000
        if self.special & 2:
            self.special_bits |= 0o2000
        if self.special & 1:
            self.special_bits |= 0o1000

    def apply(self, current_perms: Dict[str, int], is_dir: bool = False,
              current_special: int = 0) -> Tuple[Dict[str, int], int]:
        """Return absolute permissions, preserving admin (root equivalent) rights."""
        perms = {"u": self.u, "g": self.g, "o": self.o,
                 "a": current_perms.get("a", 0)}
        return perms, self.special_bits


# ============================================================
# Symbolic mode (sequence of clauses)
# ============================================================

class SymbolicMode:
    """Represents a symbolic mode like 'u+x,g-w,o=rx'."""

    def __init__(self, mode_str: str):
        self.clauses: List[SymbolicClause] = []
        self._parse(mode_str)

    def _parse(self, mode_str: str):
        """Parse symbolic mode string into clauses."""
        parts = mode_str.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue

            match = re.match(r'^([ugoa]*)([-+=])([rwxXst]*|[ugo])$', part)
            if not match:
                raise ValueError(f"invalid symbolic mode clause: '{part}'")

            who = match.group(1)
            op = match.group(2)
            perms_ = match.group(3)

            if not perms_:
                if op == "=":
                    perms_ = ""
                else:
                    raise ValueError(f"invalid symbolic mode clause: '{part}'")

            self.clauses.append(SymbolicClause(who, op, perms_))

    def apply(self, current_perms: Dict[str, int], is_dir: bool = False,
              current_special: int = 0) -> Tuple[Dict[str, int], int]:
        """Apply all clauses sequentially."""
        perms = dict(current_perms)
        special = current_special
        for clause in self.clauses:
            perms, special = clause.apply(perms, is_dir, special)
        return perms, special


# ============================================================
# Mode parser dispatcher
# ============================================================

def parse_mode(mode_str: str):
    """Parse a mode string and return a NumericMode or SymbolicMode."""
    mode_str = mode_str.strip()

    if re.match(r'^[0-7]+$', mode_str):
        return NumericMode(mode_str)

    return SymbolicMode(mode_str)
