"""
OBJ File Deduplication Script
Removes duplicate submesh groups from .obj files, keeping only the first occurrence.

EVE Online .gr2 files often export with duplicate submeshes where later occurrences
contain garbage data. This script processes .obj files to remove these duplicates.

Usage:
    python deduplicate_obj.py input.obj output.obj
    python deduplicate_obj.py input.obj  (overwrites input file)
"""

import sys
import os


def deduplicate_obj(input_path, output_path=None):
    """
    Remove duplicate submesh groups from an OBJ file.
    
    Keeps only the first occurrence of each named group (g <name>).
    Later occurrences with the same name are discarded.
    
    Args:
        input_path: Path to input .obj file
        output_path: Path to output .obj file (if None, overwrites input)
    
    Returns:
        tuple: (vertices_removed, faces_removed, groups_removed, groups_kept)
    """
    if output_path is None:
        output_path = input_path
    
    seen_groups = set()
    current_group = None
    skip_current_group = False
    
    # Statistics
    total_vertices = 0
    total_faces = 0
    kept_vertices = 0
    kept_faces = 0
    total_groups = 0
    kept_groups = 0
    
    # Read input file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return (0, 0, 0, 0)
    
    # Process lines
    output_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Handle group definitions
        if stripped.startswith('g '):
            group_name = stripped[2:].strip()
            total_groups += 1
            
            if group_name in seen_groups:
                # Duplicate group - skip it
                skip_current_group = True
                current_group = group_name
                print(f"  Skipping duplicate group: {group_name}")
            else:
                # First occurrence - keep it
                seen_groups.add(group_name)
                skip_current_group = False
                current_group = group_name
                kept_groups += 1
                output_lines.append(line)
                print(f"  Keeping group: {group_name}")
        
        # Handle vertices
        elif stripped.startswith('v '):
            total_vertices += 1
            if not skip_current_group:
                kept_vertices += 1
                output_lines.append(line)
        
        # Handle faces
        elif stripped.startswith('f '):
            total_faces += 1
            if not skip_current_group:
                kept_faces += 1
                output_lines.append(line)
        
        # Handle other data (normals, texture coords, etc.)
        elif stripped.startswith(('vn ', 'vt ', 'usemtl ', 'mtllib ', 's ', 'o ')):
            if not skip_current_group:
                output_lines.append(line)
        
        # Keep comments and empty lines
        elif stripped.startswith('#') or not stripped:
            output_lines.append(line)
        
        # Keep any other lines (material, object definitions, etc.)
        else:
            if not skip_current_group:
                output_lines.append(line)
    
    # Write output file
    try:
        # Write to temp file first
        temp_path = output_path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
        
        # Replace original file
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(temp_path, output_path)
        
        print(f"\n✓ Deduplicated OBJ saved to: {output_path}")
        
    except Exception as e:
        print(f"Error writing file: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return (0, 0, 0, 0)
    
    vertices_removed = total_vertices - kept_vertices
    faces_removed = total_faces - kept_faces
    groups_removed = total_groups - kept_groups
    
    return (vertices_removed, faces_removed, groups_removed, kept_groups)


def process_file(input_path, output_path=None):
    """Process a single OBJ file."""
    print(f"\nProcessing: {input_path}")
    
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        return False
    
    if not input_path.lower().endswith('.obj'):
        print(f"Warning: File doesn't have .obj extension: {input_path}")
    
    # Get file size
    file_size = os.path.getsize(input_path)
    print(f"File size: {file_size:,} bytes")
    
    # Deduplicate
    v_removed, f_removed, g_removed, g_kept = deduplicate_obj(input_path, output_path)
    
    # Print statistics
    print(f"\n--- Statistics ---")
    print(f"Groups kept: {g_kept}")
    print(f"Groups removed: {g_removed}")
    print(f"Vertices removed: {v_removed:,}")
    print(f"Faces removed: {f_removed:,}")
    
    if output_path:
        new_size = os.path.getsize(output_path)
        size_reduction = file_size - new_size
        reduction_pct = (size_reduction / file_size * 100) if file_size > 0 else 0
        print(f"New file size: {new_size:,} bytes")
        print(f"Size reduction: {size_reduction:,} bytes ({reduction_pct:.1f}%)")
    
    return True


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deduplicate_obj.py input.obj [output.obj]")
        print("\nIf output.obj is not specified, input file will be overwritten.")
        print("\nExample:")
        print("  python deduplicate_obj.py ship.obj ship_clean.obj")
        print("  python deduplicate_obj.py ship.obj")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if output_path is None:
        response = input(f"\nThis will overwrite '{input_path}'. Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    success = process_file(input_path, output_path)
    
    if success:
        print("\n✓ Done!")
    else:
        print("\n✗ Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
