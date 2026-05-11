#!/usr/bin/env python
"""Entry point for `python server.py`; defers to the typer CLI."""

from autopvs1_link.cli import app


def main() -> None:
    """Run the CLI with `server` as the default sub-command."""
    app(["server"])


if __name__ == "__main__":
    main()
