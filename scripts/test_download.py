#!/usr/bin/env python3
"""
Test Download Script - Download a few translations to verify URLs

This script downloads 1-2 translations from S3 and GitHub to test that
the URLs in the index are working correctly.

Requirements:
    uv pip install boto3 python-dotenv

Usage:
    python scripts/test_download.py
    python scripts/test_download.py --translation english-kjv
    python scripts/test_download.py --count 3

Note:
    - Uses AWS credentials from .env file to download DB files from S3
    - XML files are downloaded directly from GitHub (public)
"""

import os
import sys
import json
import argparse
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def resolve_project_root():
    """Get the project root directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def load_index():
    """Load the Bible translations index."""
    project_root = resolve_project_root()
    index_path = os.path.join(project_root, 'database', 'metadata', 'bible-translations-index.json')

    if not os.path.exists(index_path):
        print(f"❌ Index not found at: {index_path}")
        sys.exit(1)

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


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


def load_aws_credentials():
    """Load AWS credentials from .env file."""
    project_root = resolve_project_root()
    env_file = os.path.join(project_root, '.env')

    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
        print("✓ Loaded credentials from .env file")

        # Set environment variables for boto3
        access_key = os.getenv('ACCESSKEY_ID')
        secret_key = os.getenv('SECRET_ACCESSKEY_ID')

        if access_key and secret_key:
            os.environ['AWS_ACCESS_KEY_ID'] = access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key
            return True
        else:
            print("⚠ .env file found but credentials missing")
            return False
    else:
        print("⚠ .env file not found, will try AWS CLI credentials")
        return False


def init_s3_client(region='ap-south-1'):
    """Initialize S3 client with credentials."""
    try:
        load_aws_credentials()
        s3_client = boto3.client('s3', region_name=region)
        print(f"✓ S3 client initialized (region: {region})")
        return s3_client
    except NoCredentialsError:
        print("❌ AWS credentials not found")
        return None
    except Exception as e:
        print(f"❌ Error initializing S3 client: {e}")
        return None


def download_from_s3(s3_client, bucket, key, output_path, description="file"):
    """Download a file from S3 with progress indication."""
    try:
        print(f"  📥 Downloading {description}...")
        print(f"     S3: s3://{bucket}/{key}")

        # Get file size first
        response = s3_client.head_object(Bucket=bucket, Key=key)
        total_size = response['ContentLength']

        # Download with progress
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        downloaded = 0

        def progress_callback(bytes_amount):
            nonlocal downloaded
            downloaded += bytes_amount
            if total_size > 0:
                progress = (downloaded / total_size) * 100
                print(f"\r     Progress: {progress:.1f}% ({format_size(downloaded)}/{format_size(total_size)})", end='')

        s3_client.download_file(bucket, key, output_path, Callback=progress_callback)
        print()  # New line after progress

        actual_size = os.path.getsize(output_path)
        print(f"  ✓ Downloaded: {output_path} ({format_size(actual_size)})")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"\n  ❌ S3 Error {error_code}: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        return False


def download_file(url, output_path, description="file"):
    """Download a file with progress indication."""
    try:
        print(f"  📥 Downloading {description}...")
        print(f"     URL: {url}")

        # Download with progress
        with urllib.request.urlopen(url, timeout=30) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r     Progress: {progress:.1f}% ({format_size(downloaded)}/{format_size(total_size)})", end='')

            print()  # New line after progress

        actual_size = os.path.getsize(output_path)
        print(f"  ✓ Downloaded: {output_path} ({format_size(actual_size)})")
        return True

    except urllib.error.HTTPError as e:
        print(f"\n  ❌ HTTP Error {e.code}: {e.reason}")
        print(f"     URL: {url}")
        return False
    except urllib.error.URLError as e:
        print(f"\n  ❌ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        return False


def test_download(translation_id=None, count=2, download_xml=False, download_db=True):
    """Download test files."""
    print("\n" + "=" * 70)
    print("Bible Translation Download Test")
    print("=" * 70)

    # Initialize S3 client if downloading DB files
    s3_client = None
    if download_db:
        print("\n🔐 Initializing AWS S3 client...")
        s3_client = init_s3_client(region='ap-south-1')
        if not s3_client:
            print("❌ Cannot download DB files without S3 credentials")
            return False
        print()

    # Load index
    print("📖 Loading index...")
    index = load_index()

    # Collect all translations
    all_translations = []
    for lang in index['languages']:
        for trans in lang['translations']:
            trans['language'] = lang['language']
            all_translations.append(trans)

    print(f"✓ Found {len(all_translations)} translations in index")

    # Select translations to download
    if translation_id:
        # Download specific translation
        translations = [t for t in all_translations if t['id'] == translation_id]
        if not translations:
            print(f"\n❌ Translation '{translation_id}' not found in index")
            print("\nAvailable IDs (first 10):")
            for t in all_translations[:10]:
                print(f"  - {t['id']} ({t['name']})")
            sys.exit(1)
    else:
        # Download first N translations
        translations = all_translations[:count]

    # Create download directory
    project_root = resolve_project_root()
    download_dir = os.path.join(project_root, 'test_downloads')
    os.makedirs(download_dir, exist_ok=True)

    print(f"\n📁 Download directory: {download_dir}")
    print(f"📦 Will download {len(translations)} translation(s)")
    print()

    # Download each translation
    success_count = 0
    fail_count = 0

    for i, trans in enumerate(translations, 1):
        print("=" * 70)
        print(f"Translation {i}/{len(translations)}: {trans['name']}")
        print(f"Language: {trans['language']}")
        print(f"ID: {trans['id']}")
        print("=" * 70)

        translation_success = True

        # Download DB file
        if download_db and 'db_url' in trans:
            db_filename = trans['filename'].replace('.xml', '.db')
            db_path = os.path.join(download_dir, db_filename)

            if os.path.exists(db_path):
                print(f"  ⊘ DB file already exists: {db_path}")
            else:
                # Parse S3 URL to get bucket and key
                # URL format: https://ts-db-stream.s3.ap-south-1.amazonaws.com/translations/AcehBible.db
                db_url = trans['db_url']
                if 's3' in db_url and 'amazonaws.com' in db_url:
                    # Extract bucket and key from S3 URL
                    parts = db_url.split('.s3.')
                    bucket = parts[0].split('://')[-1]  # ts-db-stream
                    key = db_url.split('.amazonaws.com/')[-1]  # translations/AcehBible.db

                    if not download_from_s3(s3_client, bucket, key, db_path, "DB file"):
                        translation_success = False
                else:
                    print(f"  ⚠ Unexpected DB URL format: {db_url}")
                    translation_success = False

        # Download XML file (optional)
        if download_xml:
            xml_path = os.path.join(download_dir, trans['filename'])

            if os.path.exists(xml_path):
                print(f"  ⊘ XML file already exists: {xml_path}")
            else:
                if not download_file(trans['download_url'], xml_path, "XML file"):
                    translation_success = False

        if translation_success:
            success_count += 1
            print(f"  ✅ Translation downloaded successfully\n")
        else:
            fail_count += 1
            print(f"  ❌ Translation download failed\n")

    # Print summary
    print("\n" + "=" * 70)
    print("Download Summary")
    print("=" * 70)
    print(f"✓ Successful: {success_count}/{len(translations)}")
    print(f"✗ Failed:     {fail_count}/{len(translations)}")
    print(f"📁 Location:  {download_dir}")
    print("=" * 70)

    return fail_count == 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test download Bible translations from S3 and GitHub',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download first 2 translations (DB only)
  python scripts/test_download.py

  # Download specific translation
  python scripts/test_download.py --translation english-kjv

  # Download 5 translations
  python scripts/test_download.py --count 5

  # Download both DB and XML files
  python scripts/test_download.py --xml --count 2
        """
    )

    parser.add_argument(
        '--translation',
        help='Specific translation ID to download (e.g., english-kjv)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=2,
        help='Number of translations to download (default: 2)'
    )
    parser.add_argument(
        '--xml',
        action='store_true',
        help='Also download XML files from GitHub (default: DB only)'
    )
    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Skip DB download (XML only)'
    )

    args = parser.parse_args()

    try:
        success = test_download(
            translation_id=args.translation,
            count=args.count,
            download_xml=args.xml,
            download_db=not args.no_db
        )

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
