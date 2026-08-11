# -*- coding: utf-8 -*-
"""
chmod — A full-featured Python implementation of Linux chmod for Windows.

Package structure:
  constants    — Permission bits, Windows account mappings, encoding, admin check
  permissions  — Unix ↔ icacls permission conversion and formatting
  modes        — Symbolic and numeric mode parsing
  acl          — Windows ACL read/write via icacls + PowerShell
  app          — Chmod application orchestration
  cli          — Argument parser, admin check, and main() entry point
"""

from .constants import VERSION, is_admin
from .modes import parse_mode, NumericMode, SymbolicMode, SymbolicClause
from .permissions import (
    perm_to_rwx, perms_to_string, perms_to_octal,
    icacls_to_unix_perm, unix_to_icacls_perm,
)
from .acl import ACLManager
from .app import Chmod
from .cli import main

__version__ = VERSION
__all__ = [
    "main", "Chmod", "ACLManager",
    "parse_mode", "NumericMode", "SymbolicMode", "SymbolicClause",
    "perm_to_rwx", "perms_to_string", "perms_to_octal",
    "icacls_to_unix_perm", "unix_to_icacls_perm",
    "is_admin",
]
