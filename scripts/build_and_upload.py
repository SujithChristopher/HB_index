#!/usr/bin/env python3
"""
Run the HB_index release pipeline.

Steps:
1. Convert XML translations to SQLCipher DB files.
2. Generate bible-translations-index.json metadata.
3. Upload the database folder to S3.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(name: str, command: list[str]) -> None:
    print(f"\n{'=' * 72}")
    print(f"{name}")
    print(f"{'=' * 72}")
    print(f"$ {' '.join(command)}")

    start = time.perf_counter()
    result = subprocess.run(command, cwd=SCRIPT_DIR.parent)
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        raise SystemExit(f"{name} failed with exit code {result.returncode}")

    print(f"{name} completed in {elapsed:.2f}s")


def build_upload_args(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "upload_to_s3.py"),
        "--bucket",
        args.bucket,
        "--path",
        args.path,
        "--prefix",
        args.prefix,
        "--workers",
        str(args.workers),
        "--region",
        args.region,
    ]

    if args.quiet:
        command.append("--quiet")

    if args.no_incremental:
        command.append("--no-incremental")

    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert translations, generate index metadata, then upload to S3."
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip convert_to_db.py and reuse existing database files.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip generate_index.py and reuse existing metadata.",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip upload_to_s3.py.",
    )
    parser.add_argument(
        "--bucket",
        default="ts-db-stream",
        help="S3 bucket name for upload_to_s3.py (default: ts-db-stream).",
    )
    parser.add_argument(
        "--path",
        default="database",
        help="Local path passed to upload_to_s3.py (default: database).",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="S3 prefix passed to upload_to_s3.py (default: root).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Upload worker count passed to upload_to_s3.py (default: 4).",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region passed to upload_to_s3.py (default: us-east-1).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Pass --quiet to upload_to_s3.py.",
    )
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Pass --no-incremental to upload_to_s3.py.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = time.perf_counter()

    if not args.skip_convert:
        run_step(
            "Step 1/3: Convert XML translations to DB",
            [sys.executable, str(SCRIPT_DIR / "convert_to_db.py")],
        )

    if not args.skip_index:
        run_step(
            "Step 2/3: Generate translation index",
            [sys.executable, str(SCRIPT_DIR / "generate_index.py")],
        )

    if not args.skip_upload:
        run_step("Step 3/3: Upload database to S3", build_upload_args(args))

    elapsed = time.perf_counter() - start
    print(f"\nPipeline completed in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
