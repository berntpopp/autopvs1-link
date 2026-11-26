#!/usr/bin/env python
"""Entry point for `python server.py`; defers to the typer CLI."""

import sys

from autopvs1_link.cli import app


def main() -> None:
    """Run the `server` sub-command with the command-line arguments passed on."""
    app(["server", *sys.argv[1:]])


if __name__ == "__main__":
    main()
