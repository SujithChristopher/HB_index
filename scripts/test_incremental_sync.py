#!/usr/bin/env python3
"""
Test script for incremental S3 sync functionality.

This script tests:
1. SyncManifest creation and loading
2. File hash calculation
3. Hybrid sync analysis
4. Manifest persistence
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from upload_to_s3 import SyncManifest


def test_sync_manifest():
    """Test SyncManifest functionality."""
    print("\n" + "=" * 60)
    print("Testing SyncManifest")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = os.path.join(tmpdir, "test_manifest.json")

        # Test 1: Create new manifest
        print("\n[TEST 1] Creating new manifest...")
        manifest = SyncManifest(manifest_path)
        assert manifest.manifest['version'] == '1.0'
        assert manifest.manifest['files'] == {}
        print("  [PASS] New manifest created successfully")

        # Test 2: Create test file and calculate hash
        print("\n[TEST 2] File hash calculation...")
        test_file = os.path.join(tmpdir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("Hello, World!")

        file_hash = manifest.get_file_hash(test_file)
        assert len(file_hash) == 32  # MD5 hex length
        print(f"  [PASS] File hash calculated: {file_hash}")

        # Test 3: Record upload
        print("\n[TEST 3] Recording upload...")
        s3_key = "test/file.txt"
        manifest.record_upload(test_file, s3_key)
        assert s3_key in manifest.manifest['files']
        recorded = manifest.manifest['files'][s3_key]
        assert recorded['md5'] == file_hash
        assert recorded['size'] == os.path.getsize(test_file)
        print(f"  [PASS] Upload recorded: {s3_key}")

        # Test 4: needs_upload returns False for unchanged file
        print("\n[TEST 4] Change detection (unchanged file)...")
        needs_upload = manifest.needs_upload(test_file, s3_key)
        assert not needs_upload
        print("  [PASS] Unchanged file correctly identified")

        # Test 5: Modify file and detect change
        print("\n[TEST 5] Change detection (modified file)...")
        with open(test_file, 'w') as f:
            f.write("Modified content!")
        needs_upload = manifest.needs_upload(test_file, s3_key)
        assert needs_upload
        print("  [PASS] Modified file correctly detected")

        # Test 6: Save and reload manifest
        print("\n[TEST 6] Manifest persistence...")
        manifest.save()
        assert os.path.exists(manifest_path)

        # Load the manifest from disk
        with open(manifest_path, 'r') as f:
            saved_data = json.load(f)

        assert saved_data['version'] == '1.0'
        assert s3_key in saved_data['files']
        print("  [PASS] Manifest saved and loaded successfully")

        # Test 7: Create new manifest instance and load from disk
        print("\n[TEST 7] Loading existing manifest...")
        manifest2 = SyncManifest(manifest_path)
        assert s3_key in manifest2.manifest['files']
        stored_hash = manifest2.manifest['files'][s3_key]['md5']
        # After modification, the hash should be different
        current_hash = manifest2.get_file_hash(test_file)
        assert stored_hash != current_hash
        print("  [PASS] Existing manifest loaded correctly")


def test_file_operations():
    """Test file operations with various sizes."""
    print("\n" + "=" * 60)
    print("Testing File Operations")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = os.path.join(tmpdir, "test_manifest.json")
        manifest = SyncManifest(manifest_path)

        # Test with different file sizes
        test_cases = [
            ("small.txt", 1024),           # 1 KB
            ("medium.bin", 1024 * 1024),  # 1 MB
        ]

        for filename, size in test_cases:
            print(f"\n[FILE TEST] Testing {filename} ({size} bytes)...")
            filepath = os.path.join(tmpdir, filename)

            # Create file with specific size
            with open(filepath, 'wb') as f:
                f.write(os.urandom(size))

            s3_key = f"test/{filename}"

            # Record and verify
            manifest.record_upload(filepath, s3_key)
            recorded = manifest.manifest['files'][s3_key]

            assert recorded['size'] == size
            assert len(recorded['md5']) == 32
            assert 'uploaded_at' in recorded

            print(f"  [PASS] Hash: {recorded['md5']}")
            print(f"  [PASS] Size: {recorded['size']} bytes")


def test_manifest_structure():
    """Test manifest JSON structure."""
    print("\n" + "=" * 60)
    print("Testing Manifest Structure")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = os.path.join(tmpdir, "structure_test.json")
        manifest = SyncManifest(manifest_path)

        # Create multiple test files
        print("\n[STRUCTURE TEST] Creating test files...")
        for i in range(3):
            filepath = os.path.join(tmpdir, f"file_{i}.txt")
            with open(filepath, 'w') as f:
                f.write(f"Content {i}")

            s3_key = f"test/file_{i}.txt"
            manifest.record_upload(filepath, s3_key)

        # Save manifest
        manifest.save()

        # Verify structure
        print("\n[STRUCTURE TEST] Verifying manifest structure...")
        with open(manifest_path, 'r') as f:
            data = json.load(f)

        # Check top-level structure
        assert 'version' in data
        assert 'last_sync' in data
        assert 'files' in data
        assert len(data['files']) == 3

        # Check file entry structure
        for s3_key, file_info in data['files'].items():
            assert 'local_path' in file_info
            assert 'size' in file_info
            assert 'md5' in file_info
            assert 'uploaded_at' in file_info
            print(f"  [PASS] Valid entry: {s3_key}")

        print("\n[STRUCTURE TEST] Manifest structure is valid")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Incremental S3 Sync - Unit Tests")
    print("=" * 60)

    try:
        test_sync_manifest()
        test_file_operations()
        test_manifest_structure()

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n[FAILED] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
