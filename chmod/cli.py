# -*- coding: utf-8 -*-
"""
chmod CLI — argument parsing, admin check, and main entry point.
"""

import os
import sys
import argparse

from .constants import VERSION, is_admin
from .acl import ACLManager
from .modes import parse_mode
from .app import Chmod


# ============================================================
# Argument parser
# ============================================================

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="chmod",
        description="Change file mode bits on Windows (Linux chmod equivalent).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  chmod 755 file.txt            Set permissions to rwxr-xr-x
  chmod 644 file.txt            Set permissions to rw-r--r--
  chmod u+x file.txt            Add execute for owner
  chmod g-w,o-w file.txt        Remove write for group and others
  chmod a=r file.txt            Set read-only for all
  chmod -R 755 directory/       Recursively set permissions
  chmod -v 644 *.txt            Verbose output
  chmod --reference=ref.txt target.txt  Copy permissions from ref

Each MODE is one of:
  [ugoa]*([-+=]([rwxXst]*|[ugo]))+  Symbolic mode (e.g., u+x, go-w, a=r)
  NNNN                               Numeric mode (e.g., 755, 4755)

Windows account mapping:
  u (user/owner)   -> File's actual owner account
  g (group)        -> BUILTIN\\Users (all local users)
  o (others)       -> Everyone
  Administrator    -> BUILTIN\\Administrators (Full Control, equivalent to root)

Note:
  Administrators always retain Full Control (equivalent to Linux root).
  Permission changes may require Administrator privileges — if you are not
  running as admin, chmod will offer to re-launch with elevation.
        """
    )

    parser.add_argument("mode_or_file", nargs="+",
                        help="MODE and FILE(s) to change")
    parser.add_argument("-R", "--recursive", action="store_true",
                        help="change files and directories recursively")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="output a diagnostic for every file processed")
    parser.add_argument("-c", "--changes", action="store_true",
                        help="like verbose but report only when a change is made")
    parser.add_argument("-f", "--silent", "--quiet", action="store_true",
                        help="suppress most error messages")
    parser.add_argument("--reference", metavar="RFILE",
                        help="use RFILE's mode instead of MODE values")
    parser.add_argument("--preserve-root", action="store_true",
                        help="fail to operate recursively on '/'")
    parser.add_argument("--no-preserve-root", action="store_true",
                        help="do not treat '/' specially (default)")
    parser.add_argument("--version", action="version",
                        version=f"chmod {VERSION}")

    return parser


# ============================================================
# Admin check
# ============================================================

def check_admin_and_prompt():
    """Check for admin privileges. If not present, prompt the user to re-launch
    with elevation. Returns True if we should continue (already admin or user
    chose to continue anyway), False if we re-launched with elevation."""
    if is_admin():
        return True

    # If stdin is not a TTY (pipe or redirect), just continue
    if not sys.stdin.isatty():
        print("  Non-interactive mode — continuing without admin rights.", file=sys.stderr)
        print("  Permission changes may fail. Re-run from an elevated prompt if needed.", file=sys.stderr)
        print("", file=sys.stderr)
        return True

    try:
        answer = input("Administrator privileges may be required to change permissions.\n"
                       "Re-launch with administrator privileges? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("", file=sys.stderr)
        print("Continuing without admin rights (changes may fail)...", file=sys.stderr)
        return True

    if answer in ("", "y", "yes"):
        print("Re-launching with administrator privileges...", file=sys.stderr)
        print("(Accept the UAC prompt when it appears.)", file=sys.stderr)
        from .constants import relaunch_as_admin
        relaunch_as_admin()
        # If relaunch_as_admin returns (shouldn't normally), exit
        sys.exit(0)

    print("Continuing without admin rights (changes may fail)...", file=sys.stderr)
    print("", file=sys.stderr)
    return True


# ============================================================
# Main entry point
# ============================================================

def main():
    """Main entry point."""
    parser = create_parser()
    # --help / --version exit here via SystemExit, before any admin prompt
    args = parser.parse_args()

    # Check admin privileges only when we're actually about to change
    # permissions, and skip the prompt entirely in quiet (-f) mode.
    if not args.silent:
        check_admin_and_prompt()

    if args.reference:
        ref_path = args.reference
        if not os.path.exists(ref_path):
            print(f"chmod: cannot access reference file '{ref_path}': "
                  f"No such file or directory", file=sys.stderr)
            sys.exit(1)

        ref_perms, ref_special = ACLManager.get_current_perms(ref_path)

        class ReferenceMode:
            def apply(self, current_perms, is_dir=False, current_special=0):
                return dict(ref_perms), ref_special

        mode = ReferenceMode()
        files = args.mode_or_file
    else:
        if not args.mode_or_file:
            parser.print_help()
            sys.exit(1)

        mode_str = args.mode_or_file[0]
        files = args.mode_or_file[1:]

        if not files:
            print(f"chmod: missing operand after '{mode_str}'", file=sys.stderr)
            print(f"Try 'chmod --help' for more information.", file=sys.stderr)
            sys.exit(1)

        try:
            mode = parse_mode(mode_str)
        except ValueError as e:
            print(f"chmod: invalid mode: '{mode_str}': {e}", file=sys.stderr)
            sys.exit(1)

    if not files:
        print("chmod: missing file operand", file=sys.stderr)
        print("Try 'chmod --help' for more information.", file=sys.stderr)
        sys.exit(1)

    app = Chmod(
        verbose=args.verbose,
        changes_only=args.changes,
        quiet=args.silent,
        recursive=args.recursive,
        preserve_root=args.preserve_root
    )

    app.run(mode, files)

    if app.failed_count > 0:
        sys.exit(1)
    sys.exit(0)
