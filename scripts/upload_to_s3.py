#!/usr/bin/env python3
"""
S3 Syncer - Sync database folder to AWS S3

This script syncs the database folder to an S3 bucket with verbose logging,
parallel processing, and progress tracking. Automatically excludes .git,
__pycache__, and other unnecessary files.

Default behavior: Syncs database/ folder to S3 bucket root

Requirements:
    pip install boto3 python-dotenv

Configuration:
    - Bucket name: tdb-bucket-stream
    - AWS credentials: Automatically loads from .env file (ACCESSKEY_ID, SECRET_ACCESSKEY_ID)
    - Fallback: AWS CLI credentials (~/.aws/credentials) or environment variables
"""

import os
import sys
import json
import argparse
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class SyncManifest:
    """Track uploaded files with checksums in local manifest."""

    def __init__(self, manifest_path):
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()

    def _load_manifest(self):
        """Load existing manifest or create new one."""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'version': '1.0', 'last_sync': None, 'files': {}}

    def get_file_hash(self, file_path):
        """Calculate MD5 hash efficiently."""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8388608):  # 8MB chunks
                md5.update(chunk)
        return md5.hexdigest()

    def needs_upload(self, local_path, s3_key):
        """Check if file needs upload based on manifest."""
        file_size = os.path.getsize(local_path)

        if s3_key not in self.manifest['files']:
            return True  # New file

        stored = self.manifest['files'][s3_key]

        # Quick size check first
        if stored.get('size') != file_size:
            return True

        # Then hash check
        file_hash = self.get_file_hash(local_path)
        if stored.get('md5') != file_hash:
            return True

        return False

    def record_upload(self, local_path, s3_key):
        """Record successful upload in manifest."""
        self.manifest['files'][s3_key] = {
            'local_path': str(local_path),
            'size': os.path.getsize(local_path),
            'md5': self.get_file_hash(local_path),
            'uploaded_at': datetime.now().isoformat()
        }

    def save(self):
        """Save manifest to disk."""
        self.manifest['last_sync'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)


class HybridS3Syncer:
    """Combines manifest, batch listing, and smart comparison."""

    def __init__(self, s3_client, bucket, manifest):
        self.s3_client = s3_client
        self.bucket = bucket
        self.manifest = manifest

    def analyze_sync(self, file_list, s3_prefix=''):
        """
        Perform hybrid sync analysis.
        Returns: (files_to_upload, stats_dict)
        """
        stats = {
            'total': len(file_list),
            'manifest_skips': 0,
            's3_matches': 0,
            'needs_upload': 0
        }

        # Phase 1: Quick manifest check
        candidates = []
        for file_info in file_list:
            if self.manifest.needs_upload(file_info['local_path'], file_info['s3_key']):
                candidates.append(file_info)
            else:
                stats['manifest_skips'] += 1

        if not candidates:
            return [], stats

        # Phase 2: Batch verify against S3
        s3_inventory = self._batch_list_s3(s3_prefix)

        files_to_upload = []
        for file_info in candidates:
            if self._needs_upload_hybrid(file_info, s3_inventory):
                files_to_upload.append(file_info)
                stats['needs_upload'] += 1
            else:
                stats['s3_matches'] += 1

        return files_to_upload, stats

    def _batch_list_s3(self, prefix):
        """Get S3 inventory in one batch."""
        inventory = {}
        paginator = self.s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                inventory[obj['Key']] = {
                    'size': obj['Size'],
                    'modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                }

        return inventory

    def _needs_upload_hybrid(self, file_info, s3_inventory):
        """Smart comparison: size + timestamp + optional MD5."""
        s3_key = file_info['s3_key']
        local_path = file_info['local_path']

        # File doesn't exist in S3
        if s3_key not in s3_inventory:
            return True

        s3_obj = s3_inventory[s3_key]
        local_size = os.path.getsize(local_path)

        # Different size = definitely upload
        if local_size != s3_obj['size']:
            return True

        # Check timestamp
        local_mtime = os.path.getmtime(local_path)
        local_modified = datetime.fromtimestamp(local_mtime, timezone.utc)

        # If local is older or same, skip
        if local_modified <= s3_obj['modified']:
            # Update manifest since we confirmed it matches S3
            self.manifest.record_upload(local_path, s3_key)
            return False

        # Same size, local newer: verify with MD5
        local_md5 = self.manifest.get_file_hash(local_path)
        if local_md5 == s3_obj['etag']:
            # Content matches despite newer timestamp
            self.manifest.record_upload(local_path, s3_key)
            return False

        return True


class S3Uploader:
    """Upload files to S3 with verbose logging and parallel processing."""

    # Directories to exclude from upload
    EXCLUDE_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules', '.env', '.DS_Store'}
    # File extensions to exclude
    EXCLUDE_EXTENSIONS = {'.pyc', '.pyo', '.pyd', '.so', '.o', '.a'}

    def __init__(self, bucket_name, region='us-east-1', max_workers=4, verbose=True, incremental=True):
        """Initialize S3 uploader."""
        self.bucket_name = bucket_name
        self.region = region
        self.max_workers = max_workers
        self.verbose = verbose
        self.uploaded_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.total_bytes_uploaded = 0
        self.file_list = []

        # Initialize incremental sync
        self.incremental = incremental
        self.manifest = None
        self.syncer = None

        try:
            # Load credentials from .env if available
            self._load_credentials()
            self.s3_client = boto3.client('s3', region_name=region)
            self._verify_bucket_exists()
            self.log("✓ S3 client initialized successfully")

            # Initialize incremental sync if enabled
            if incremental:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_dir = os.path.dirname(script_dir)
                manifest_path = os.path.join(project_dir, 'database', '.s3_sync_manifest.json')

                self.manifest = SyncManifest(manifest_path)
                self.syncer = HybridS3Syncer(self.s3_client, bucket_name, self.manifest)
                self.log("✓ Incremental sync enabled")

        except NoCredentialsError:
            self.error("AWS credentials not found. Configure with: aws configure or set up .env file")
            raise
        except Exception as e:
            self.error(f"Failed to initialize S3 client: {e}")
            raise

    def _load_credentials(self):
        """Load AWS credentials from .env file."""
        # Find .env file in project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        env_file = os.path.join(project_dir, '.env')

        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            self.log(f"✓ Loaded credentials from .env file")

            # Set environment variables for boto3
            access_key = os.getenv('ACCESSKEY_ID')
            secret_key = os.getenv('SECRET_ACCESSKEY_ID')

            if access_key and secret_key:
                os.environ['AWS_ACCESS_KEY_ID'] = access_key
                os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key
                self.log("✓ AWS credentials loaded from .env")
            else:
                self.log("⚠ .env file found but credentials missing (ACCESSKEY_ID/SECRET_ACCESSKEY_ID)", level='warning')
        else:
            self.log("ℹ .env file not found, using AWS CLI credentials")

    def _verify_bucket_exists(self):
        """Verify the S3 bucket exists and is accessible."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.log(f"✓ Bucket '{self.bucket_name}' verified")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise Exception(f"Bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                raise Exception(f"Access denied to bucket '{self.bucket_name}'")
            else:
                raise Exception(f"Error accessing bucket: {e}")

    def should_exclude_path(self, path):
        """Check if a path should be excluded from upload."""
        parts = Path(path).parts

        # Check if any directory in path is excluded
        for part in parts:
            if part in self.EXCLUDE_DIRS:
                return True

        # Check file extension
        if Path(path).suffix in self.EXCLUDE_EXTENSIONS:
            return True

        return False

    def collect_files(self, local_path, s3_prefix=''):
        """Collect all files to upload, excluding specified directories."""
        self.log(f"\nCollecting files from: {local_path}")
        collected = 0
        skipped = 0

        for root, dirs, files in os.walk(local_path):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

            for file in files:
                file_path = os.path.join(root, file)

                # Skip excluded files
                if self.should_exclude_path(file_path):
                    skipped += 1
                    continue

                # Calculate S3 key (relative path from local_path)
                rel_path = os.path.relpath(file_path, local_path)
                s3_key = os.path.join(s3_prefix, rel_path).replace('\\', '/')

                file_size = os.path.getsize(file_path)
                self.file_list.append({
                    'local_path': file_path,
                    's3_key': s3_key,
                    'file_size': file_size
                })
                collected += 1

        self.log(f"  → Collected {collected} files ({self.format_size(sum(f['file_size'] for f in self.file_list))})")
        if skipped > 0:
            self.log(f"  → Skipped {skipped} files/directories")

        return collected, skipped

    def upload_file(self, file_info):
        """Upload a single file to S3."""
        local_path = file_info['local_path']
        s3_key = file_info['s3_key']
        file_size = file_info['file_size']

        try:
            # Upload with progress callback
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                Callback=lambda bytes_amount: None  # For large files, could track progress
            )

            self.uploaded_files += 1
            self.total_bytes_uploaded += file_size

            # Update manifest for incremental sync
            if self.manifest:
                self.manifest.record_upload(local_path, s3_key)

            if self.verbose:
                self.log(f"  ✓ {s3_key} ({self.format_size(file_size)})")

            return True

        except Exception as e:
            self.failed_files += 1
            self.log(f"  ✗ Failed to upload {s3_key}: {e}", level='error')
            return False

    def upload_directory(self, local_path, s3_prefix=''):
        """Upload entire directory to S3 with parallel processing."""
        local_path = os.path.abspath(local_path)

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Directory not found: {local_path}")

        self.log("\n" + "=" * 60)
        self.log("S3 Upload Started")
        self.log("=" * 60)
        self.log(f"Bucket: {self.bucket_name}")
        self.log(f"Source: {local_path}")
        self.log(f"S3 Prefix: {s3_prefix or '(root)'}")
        self.log(f"Max Workers: {self.max_workers}")

        # Collect all files
        start_time = datetime.now()
        collected, skipped = self.collect_files(local_path, s3_prefix)

        if collected == 0:
            self.log("No files to upload!")
            return

        # Perform incremental sync analysis
        if self.syncer:
            self.log(f"\n{'='*60}")
            self.log("Analyzing changes (incremental sync)...")
            self.log(f"{'='*60}")

            files_to_upload, stats = self.syncer.analyze_sync(self.file_list, s3_prefix)

            self.log(f"✓ Total files scanned: {stats['total']}")
            self.log(f"✓ Unchanged (manifest): {stats['manifest_skips']}")
            self.log(f"✓ Unchanged (S3 verified): {stats['s3_matches']}")
            self.log(f"✓ Need upload: {stats['needs_upload']}")

            self.file_list = files_to_upload

            if not self.file_list:
                self.log("\n✅ All files are up to date!")
                return

        # Upload files in parallel
        collected = len(self.file_list)
        self.log(f"\nUploading {collected} files with {self.max_workers} parallel workers...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.upload_file, f): f for f in self.file_list}

            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % max(1, collected // 10) == 0 or completed == collected:
                    progress = (completed / collected) * 100
                    self.log(f"Progress: {completed}/{collected} ({progress:.1f}%)")

                try:
                    future.result()
                except Exception as e:
                    self.log(f"Upload error: {e}", level='error')

        # Print summary
        elapsed = datetime.now() - start_time
        self.print_summary(elapsed)

    def print_summary(self, elapsed_time):
        """Print upload summary statistics."""
        self.log("\n" + "=" * 60)
        self.log("Upload Summary")
        self.log("=" * 60)
        self.log(f"✓ Uploaded:  {self.uploaded_files} files ({self.format_size(self.total_bytes_uploaded)})")
        self.log(f"✗ Failed:    {self.failed_files} files")
        self.log(f"⊘ Skipped:   {self.skipped_files} files")
        self.log(f"⏱ Time:      {self._format_time(elapsed_time)}")

        if self.total_bytes_uploaded > 0 and elapsed_time.total_seconds() > 0:
            speed = self.total_bytes_uploaded / elapsed_time.total_seconds()
            self.log(f"⚡ Speed:     {self.format_size(speed)}/s")

        self.log("=" * 60)

        # Save manifest
        if self.manifest:
            self.manifest.save()
            self.log("\n✓ Sync manifest updated")

        if self.failed_files > 0:
            self.log(f"\n⚠ {self.failed_files} file(s) failed to upload. Review errors above.", level='warning')

    @staticmethod
    def format_size(size_bytes):
        """Format bytes to human-readable size."""
        if size_bytes >= 1024**3:
            return f"{size_bytes / (1024**3):.2f} GB"
        elif size_bytes >= 1024**2:
            return f"{size_bytes / (1024**2):.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes} B"

    @staticmethod
    def _format_time(td):
        """Format timedelta to human-readable time."""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def log(self, message, level='info'):
        """Print verbose log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if level == 'error':
            print(f"[{timestamp}] ❌ ERROR: {message}", file=sys.stderr)
        elif level == 'warning':
            print(f"[{timestamp}] ⚠️  WARNING: {message}")
        else:
            print(f"[{timestamp}] ℹ️  {message}")

    def error(self, message):
        """Print error message."""
        self.log(message, level='error')


def main():
    """Main function to handle command-line arguments and upload."""
    parser = argparse.ArgumentParser(
        description='Sync database folder to AWS S3 bucket',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync database folder (default)
  python upload_to_s3.py

  # Sync with custom S3 prefix
  python upload_to_s3.py --prefix my-backup/

  # Use 8 parallel workers for faster upload
  python upload_to_s3.py --workers 8

  # Upload different folder (if needed)
  python upload_to_s3.py --path ./scripts
        """
    )

    parser.add_argument(
        '--bucket',
        default='ts-db-stream',
        help='S3 bucket name (default: ts-db-stream)'
    )
    parser.add_argument(
        '--path',
        default='database',
        help='Local path to upload (default: database folder)'
    )
    parser.add_argument(
        '--prefix',
        default='',
        help='S3 prefix/folder path (default: root)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel upload workers (default: 4)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        default=True,
        help='Use incremental sync (default: True)'
    )
    parser.add_argument(
        '--no-incremental',
        dest='incremental',
        action='store_false',
        help='Force full upload without change detection'
    )

    args = parser.parse_args()

    try:
        # Resolve paths relative to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)

        local_path = args.path
        if not os.path.isabs(local_path):
            local_path = os.path.join(project_dir, local_path)

        # Create uploader and start upload
        uploader = S3Uploader(
            bucket_name=args.bucket,
            region=args.region,
            max_workers=args.workers,
            verbose=not args.quiet,
            incremental=args.incremental
        )

        uploader.upload_directory(local_path, args.prefix)

        # Exit with appropriate code
        sys.exit(0 if uploader.failed_files == 0 else 1)

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
