#!/usr/bin/env python3
"""
Command router for HB_index translation maintenance.

This keeps the specialized scripts small while giving routine workflows a
single entrypoint:

  python scripts/hb_index.py build
  python scripts/hb_index.py download english-kjv
  python scripts/hb_index.py validate
"""

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
TESTS_DIR = PROJECT_DIR / "tests"


def run(command: list[str]) -> int:
    print(f"$ {' '.join(command)}")
    return subprocess.call(command, cwd=PROJECT_DIR)


def append_common_upload_args(command: list[str], args: argparse.Namespace) -> list[str]:
    command.extend(["--bucket", args.bucket])
    command.extend(["--path", args.path])
    command.extend(["--prefix", args.prefix])
    command.extend(["--workers", str(args.workers)])
    command.extend(["--region", args.region])

    if args.quiet:
        command.append("--quiet")
    if args.no_incremental:
        command.append("--no-incremental")

    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HB_index translation build, upload, download, and validation commands."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="Convert XML to DB, generate index metadata, then upload.",
    )
    build.add_argument("--skip-convert", action="store_true")
    build.add_argument("--skip-index", action="store_true")
    build.add_argument("--skip-upload", action="store_true")
    add_upload_args(build)

    subparsers.add_parser("convert", help="Convert XML files to SQLCipher DB files.")
    subparsers.add_parser("index", help="Generate bible-translations-index.json.")
    subparsers.add_parser("validate", help="Validate and inspect generated index metadata.")

    upload = subparsers.add_parser("upload", help="Upload database/ to S3.")
    add_upload_args(upload)

    download = subparsers.add_parser("download", help="Download a translation by id.")
    download.add_argument("translation", nargs="?", help="Translation id to download.")

    test_download = subparsers.add_parser(
        "test-download",
        help="Download sample translations from S3/GitHub to verify URLs.",
    )
    test_download.add_argument("--translation")
    test_download.add_argument("--count", type=int, default=2)
    test_download.add_argument("--xml", action="store_true")
    test_download.add_argument("--no-db", action="store_true")

    subparsers.add_parser("test-sync", help="Run incremental S3 sync unit checks.")
    subparsers.add_parser("update", help="Update XML submodule and regenerate index.")

    args = parser.parse_args()

    if args.command == "build":
        command = [
            sys.executable,
            str(SCRIPT_DIR / "build_and_upload.py"),
        ]
        for flag in ("skip_convert", "skip_index", "skip_upload"):
            if getattr(args, flag):
                command.append(f"--{flag.replace('_', '-')}")
        return run(append_common_upload_args(command, args))

    if args.command == "convert":
        return run([sys.executable, str(SCRIPT_DIR / "convert_to_db.py")])

    if args.command == "index":
        return run([sys.executable, str(SCRIPT_DIR / "generate_index.py")])

    if args.command == "validate":
        return run([sys.executable, str(SCRIPT_DIR / "validate_index.py")])

    if args.command == "upload":
        return run(append_common_upload_args([sys.executable, str(SCRIPT_DIR / "upload_to_s3.py")], args))

    if args.command == "download":
        command = [sys.executable, str(SCRIPT_DIR / "download_translation.py")]
        if args.translation:
            command.append(args.translation)
        return run(command)

    if args.command == "test-download":
        command = [sys.executable, str(TESTS_DIR / "test_download.py")]
        if args.translation:
            command.extend(["--translation", args.translation])
        command.extend(["--count", str(args.count)])
        if args.xml:
            command.append("--xml")
        if args.no_db:
            command.append("--no-db")
        return run(command)

    if args.command == "test-sync":
        return run([sys.executable, str(TESTS_DIR / "test_incremental_sync.py")])

    if args.command == "update":
        return run([sys.executable, str(SCRIPT_DIR / "update_index.py")])

    parser.error(f"Unknown command: {args.command}")
    return 2


def add_upload_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bucket", default="ts-db-stream")
    parser.add_argument("--path", default="database")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-incremental", action="store_true")


if __name__ == "__main__":
    sys.exit(main())
