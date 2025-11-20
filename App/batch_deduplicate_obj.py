"""
Batch OBJ Deduplication Tool
Recursively processes all .obj files in a directory and its subdirectories,
removing duplicate submesh groups from EVE Online model exports.

Usage:
    python batch_deduplicate_obj.py <directory>
    python batch_deduplicate_obj.py <directory> --dry-run
    python batch_deduplicate_obj.py <directory> --threads 16
    
Examples:
    python batch_deduplicate_obj.py "D:/EVE_Exports"
    python batch_deduplicate_obj.py "C:/Users/Sven/Documents/Ships" --dry-run
    python batch_deduplicate_obj.py "d:/res" --threads 32
"""

import sys
import os
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from convert import _deduplicate_obj


def format_size(bytes):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"


def process_single_file(obj_file, directory, file_num, total_files, dry_run, stats_lock, stats):
    """
    Process a single OBJ file.
    
    Args:
        obj_file: Path to OBJ file
        directory: Root directory (for relative path display)
        file_num: Current file number
        total_files: Total number of files
        dry_run: If True, don't modify files
        stats_lock: Threading lock for statistics
        stats: Dictionary of statistics to update
    
    Returns:
        tuple: (success, message)
    """
    try:
        # Get original size
        size_before = obj_file.stat().st_size
        rel_path = obj_file.relative_to(directory)
        
        # Progress message
        print(f"[{file_num}/{total_files}] Processing: {rel_path}")
        
        if dry_run:
            with stats_lock:
                stats['total_size_before'] += size_before
                stats['total_size_after'] += size_before
                stats['processed_files'] += 1
            print(f"  [DRY RUN] Size: {format_size(size_before)}")
            return (True, f"[DRY RUN] {rel_path}")
        
        # Deduplicate
        groups_removed, vertices_removed, faces_removed = _deduplicate_obj(str(obj_file))
        
        # Get new size
        size_after = obj_file.stat().st_size
        
        # Update statistics
        with stats_lock:
            stats['total_size_before'] += size_before
            stats['total_size_after'] += size_after
            
            if groups_removed > 0:
                size_reduction = size_before - size_after
                reduction_pct = (size_reduction / size_before * 100) if size_before > 0 else 0
                
                stats['total_groups_removed'] += groups_removed
                stats['total_vertices_removed'] += vertices_removed
                stats['total_faces_removed'] += faces_removed
                stats['processed_files'] += 1
                
                msg = f"  ✓ {rel_path} - Removed {groups_removed} groups, {vertices_removed:,} verts, {faces_removed:,} faces ({reduction_pct:.1f}% smaller)"
                print(msg)
                return (True, msg)
            else:
                stats['skipped_files'] += 1
                stats['total_size_after'] += size_before
                msg = f"  ⊘ {rel_path} - Already clean (no duplicates)"
                print(msg)
                return (True, msg)
        
    except Exception as e:
        with stats_lock:
            stats['failed_files'] += 1
            stats['total_size_after'] += size_before
        msg = f"  ✗ {rel_path} - Error: {e}"
        print(msg)
        return (False, msg)


def batch_deduplicate(directory, dry_run=False, max_workers=None):
    """
    Recursively deduplicate all .obj files in a directory using multiple threads.
    
    Args:
        directory: Root directory to search
        dry_run: If True, only scan and report, don't modify files
        max_workers: Maximum number of worker threads (default: CPU count * 4)
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return False
    
    if not directory.is_dir():
        print(f"Error: Not a directory: {directory}")
        return False
    
    # Default to CPU count * 4 for I/O-bound operations
    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 4) * 4)
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Scanning: {directory}")
    print(f"Workers: {max_workers} threads")
    print("=" * 80)
    
    # Find all .obj files recursively
    print("Searching for .obj files...")
    obj_files = list(directory.rglob("*.obj"))
    
    if not obj_files:
        print("No .obj files found.")
        return True
    
    print(f"Found {len(obj_files)} .obj file(s)")
    print("=" * 80)
    print()
    
    # Statistics (thread-safe)
    stats_lock = threading.Lock()
    stats = {
        'processed_files': 0,
        'skipped_files': 0,
        'failed_files': 0,
        'total_groups_removed': 0,
        'total_vertices_removed': 0,
        'total_faces_removed': 0,
        'total_size_before': 0,
        'total_size_after': 0
    }
    
    total_files = len(obj_files)
    start_time = time.perf_counter()
    
    # Process files in parallel
    print(f"Processing {total_files} files with {max_workers} workers...\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_file, 
                obj_file, 
                directory, 
                i, 
                total_files, 
                dry_run, 
                stats_lock, 
                stats
            ): obj_file 
            for i, obj_file in enumerate(obj_files, 1)
        }
        
        # Wait for completion and show progress
        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                future.result()
            except Exception as e:
                print(f"  ✗ Unexpected error: {e}")
            
            # Progress update every 10 files
            if completed % 10 == 0 or completed == total_files:
                with stats_lock:
                    processed = stats['processed_files']
                    skipped = stats['skipped_files']
                    failed = stats['failed_files']
                print(f"\n--- Progress: {completed}/{total_files} ({completed*100//total_files}%) | Processed: {processed} | Clean: {skipped} | Failed: {failed} ---\n")
    
    # Summary
    elapsed = time.perf_counter() - start_time
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files found:      {total_files}")
    print(f"Processed:              {stats['processed_files']}")
    print(f"Already clean:          {stats['skipped_files']}")
    print(f"Failed:                 {stats['failed_files']}")
    print()
    
    if not dry_run and stats['processed_files'] > 0:
        print(f"Groups removed:         {stats['total_groups_removed']:,}")
        print(f"Vertices removed:       {stats['total_vertices_removed']:,}")
        print(f"Faces removed:          {stats['total_faces_removed']:,}")
        print()
        print(f"Total size before:      {format_size(stats['total_size_before'])}")
        print(f"Total size after:       {format_size(stats['total_size_after'])}")
        
        if stats['total_size_before'] > 0:
            total_reduction = stats['total_size_before'] - stats['total_size_after']
            total_reduction_pct = (total_reduction / stats['total_size_before'] * 100)
            print(f"Total size saved:       {format_size(total_reduction)} ({total_reduction_pct:.1f}%)")
    
    print()
    print(f"Time elapsed:           {elapsed:.2f}s")
    print(f"Files per second:       {total_files/elapsed:.2f}")
    print(f"Average per file:       {elapsed/total_files:.3f}s")
    print(f"Workers used:           {max_workers}")
    print("=" * 80)
    
    if dry_run:
        print("\nDRY RUN - No files were modified")
        print("Run without --dry-run to actually deduplicate the files")
    else:
        print("\n✓ Batch deduplication complete!")
    
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    directory = sys.argv[1]
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    # Parse thread count
    max_workers = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--threads", "-t") and i + 1 < len(sys.argv):
            try:
                max_workers = int(sys.argv[i + 1])
                print(f"Using {max_workers} worker threads")
            except ValueError:
                print(f"Warning: Invalid thread count '{sys.argv[i + 1]}', using default")
    
    success = batch_deduplicate(directory, dry_run, max_workers)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
