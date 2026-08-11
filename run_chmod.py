#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chmod — Windows chmod (portable entry point)
=============================================
Usage:
    python run_chmod.py [OPTION]... MODE FILE...

This script lives inside the chmod/ package directory. It tries two strategies:
  1. Direct import (works after `pip install .`)
  2. Relative import (works when run as `python chmod/run_chmod.py`)

For a proper system-wide install, use:
    pip install .

Then you can simply run:
    chmod 755 file.txt
"""

import sys
import os


def _find_and_import_chmod():
    """Import chmod.cli.main, trying direct import first, then relative path."""
    # Strategy 1: package is installed (pip install .)
    try:
        from chmod.cli import main
        return main
    except ImportError:
        pass

    # Strategy 2: run_chmod.py sits inside chmod/ package dir,
    # so add the PARENT of _script_dir to sys.path
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_script_dir)
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)

    try:
        from chmod.cli import main
        return main
    except ImportError:
        pass

    # Strategy 3: walk up further to find chmod/ package
    _current = _parent_dir
    for _ in range(3):
        _parent = os.path.dirname(_current)
        if _parent == _current:
            break
        _current = _parent
        if _current not in sys.path:
            sys.path.insert(0, _current)
        try:
            from chmod.cli import main
            return main
        except ImportError:
            continue

    sys.exit(0)


if __name__ == "__main__":
    main = _find_and_import_chmod()
    main()
