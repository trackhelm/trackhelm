from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
import sys
from typing import Final


def setup_logging(log_dir: Path, max_bytes: int, backup_count: int, level: int) -> None:
    """Configure root logging with a stream handler and a rotating file handler.

    The function ensures `log_dir` exists, attaches a `StreamHandler` writing to
    stdout and a `RotatingFileHandler` writing to ``log_dir/pytroller.log`` with the
    provided rotation parameters. Both handlers share the same formatter.

    Args:
            log_dir: Directory where the log file will be placed.
            max_bytes: Maximum size in bytes before rotation.
            backup_count: Number of rotated files to keep.
            level: Logging level for the root logger (e.g. logging.INFO).
    """

    log_dir.mkdir(parents=True, exist_ok=True)

    fmt: Final[str] = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    datefmt: Final[str] = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Stream handler to stdout
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh.setLevel(level)
    root.addHandler(sh)

    # Rotating file handler
    logfile = log_dir / "pytroller.log"
    fh = logging.handlers.RotatingFileHandler(
        filename=str(logfile),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    fh.setLevel(level)
    root.addHandler(fh)
