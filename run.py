#!/usr/bin/env python3
"""
Cleanarr - Media Management Tool
Entry point for the application
"""

import sys

from core.cli import handle_cleanup, setup_cli


def main():
    """Main entry point for Cleanarr - directly runs cleanup"""
    parser = setup_cli()
    args = parser.parse_args()

    # Always run cleanup since it's the only command
    return handle_cleanup(args)


if __name__ == "__main__":
    sys.exit(main())
