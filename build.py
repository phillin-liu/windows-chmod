"""
Nuitka build entry point for chmod.exe.
Put this script at the project root (alongside the chmod/ package), then run Nuitka from here.
"""
import sys
import os

# Ensure the project root (where chmod/ lives) is on sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from chmod.cli import main

if __name__ == "__main__":
    main()
