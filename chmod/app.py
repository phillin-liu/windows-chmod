# -*- coding: utf-8 -*-
"""
chmod application core — Chmod class that orchestrates permission changes.
"""

import os
import sys
from typing import Dict, List

from .acl import ACLManager
from .permissions import perms_to_octal, perms_to_string


# ============================================================
# Main Chmod Application
# ============================================================

class Chmod:
    """Main application class."""

    def __init__(self, verbose: bool = False, changes_only: bool = False,
                 quiet: bool = False, recursive: bool = False,
                 preserve_root: bool = False):
        self.verbose = verbose
        self.changes_only = changes_only
        self.quiet = quiet
        self.recursive = recursive
        self.preserve_root = preserve_root
        self.changed_count = 0
        self.failed_count = 0

    def _print_verbose(self, filepath: str, old_perms: Dict[str, int],
                       old_special: int, new_perms: Dict[str, int],
                       new_special: int, changed: bool):
        """Print verbose output about permission changes."""
        if self.changes_only and not changed:
            return
        if not self.verbose and not self.changes_only:
            return

        old_octal = perms_to_octal(old_perms, old_special)
        new_octal = perms_to_octal(new_perms, new_special)
        old_str = perms_to_string(old_perms, old_special)
        new_str = perms_to_string(new_perms, new_special)

        if changed:
            print(f"mode of '{filepath}' changed from {old_octal} ({old_str}) "
                  f"to {new_octal} ({new_str})")
        elif self.verbose:
            print(f"mode of '{filepath}' retained as {old_octal} ({old_str})")

    def chmod_one(self, filepath: str, mode) -> bool:
        """
        Apply mode to a single file/directory.
        Returns True if permissions changed, False otherwise.
        """
        if not os.path.exists(filepath):
            if not self.quiet:
                print(f"chmod: cannot access '{filepath}': No such file or directory",
                      file=sys.stderr)
            self.failed_count += 1
            return False

        is_dir = os.path.isdir(filepath)

        old_perms, old_special = ACLManager.get_current_perms(filepath)
        new_perms, new_special = mode.apply(old_perms, is_dir, old_special)

        changed = (old_perms != new_perms or old_special != new_special)

        if changed:
            success = ACLManager.set_permissions(
                filepath, new_perms, new_special,
                verbose=self.verbose, quiet=self.quiet
            )
            if success:
                self.changed_count += 1
            else:
                self.failed_count += 1
                return False
        else:
            success = True

        self._print_verbose(filepath, old_perms, old_special,
                            new_perms, new_special, changed)

        return changed

    def chmod_recursive(self, filepath: str, mode):
        """Recursively apply mode to a directory and all its contents."""
        self.chmod_one(filepath, mode)

        if not os.path.isdir(filepath):
            return

        for root, dirs, files in os.walk(filepath):
            for fname in files:
                fpath = os.path.join(root, fname)
                self.chmod_one(fpath, mode)

            for dname in dirs:
                dpath = os.path.join(root, dname)
                self.chmod_one(dpath, mode)

    def run(self, mode, files: List[str]):
        """Run chmod on all specified files."""
        for filepath in files:
            filepath = os.path.normpath(filepath)

            if self.preserve_root and os.path.abspath(filepath) in ("C:\\", "/", "\\"):
                if not self.quiet:
                    print(f"chmod: it is dangerous to operate recursively on '{filepath}'",
                          file=sys.stderr)
                    print(f"chmod: use --no-preserve-root to override this failsafe",
                          file=sys.stderr)
                self.failed_count += 1
                continue

            if self.recursive and os.path.isdir(filepath):
                self.chmod_recursive(filepath, mode)
            else:
                self.chmod_one(filepath, mode)
