"""Shared runtime paths for source and bundled builds."""

import sys
from pathlib import Path


def resolve_root_dir(*, frozen=None, meipass=None, executable=None, file_path=None):
    """Resolve the application root for source and PyInstaller bundles."""
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if meipass is None:
        meipass = getattr(sys, "_MEIPASS", None)
    if executable is None:
        executable = getattr(sys, "executable", None)
    if file_path is None:
        file_path = __file__

    if frozen and meipass:
        return Path(meipass).resolve()
    if frozen and executable:
        return Path(executable).resolve().parent
    return Path(file_path).parent.parent


ROOT_DIR = resolve_root_dir()
