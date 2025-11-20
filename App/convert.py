import os
import platform
import shutil
import tkinter as tk
from QEHelper import warn
import subprocess

def _deduplicate_obj(obj_path):
    """
    Remove duplicate submesh groups from an OBJ file in-place.
    
    EVE's .gr2 files often export with duplicate submeshes (LOD, collision meshes, etc.)
    This function keeps only the first occurrence of each named group.
    
    Optimized for performance:
    - Single pass through file
    - Minimal string operations
    - Buffered I/O
    - Fast set lookups
    
    Args:
        obj_path: Path to .obj file to deduplicate
    
    Returns:
        tuple: (groups_removed, vertices_removed, faces_removed)
    """
    try:
        seen_groups = set()
        skip_current_group = False
        
        # Statistics (only track what we need for reporting)
        groups_removed = 0
        vertices_removed = 0
        faces_removed = 0
        
        # Use temp file for streaming write (faster than building list in memory)
        temp_path = obj_path + '.tmp'
        
        with open(obj_path, 'r', encoding='utf-8', buffering=65536) as f_in, \
             open(temp_path, 'w', encoding='utf-8', buffering=65536) as f_out:
            
            for line in f_in:
                # Fast path: most lines start with these common prefixes
                first_char = line[0] if line else ''
                
                if first_char == 'g':
                    # Group definition - check for duplicates
                    if line.startswith('g '):
                        group_name = line[2:].strip()
                        
                        if group_name in seen_groups:
                            # Duplicate - skip this group
                            skip_current_group = True
                            groups_removed += 1
                        else:
                            # First occurrence - keep it
                            seen_groups.add(group_name)
                            skip_current_group = False
                            f_out.write(line)
                    else:
                        # Not a group line starting with 'g'
                        if not skip_current_group:
                            f_out.write(line)
                
                elif first_char == 'v':
                    # Vertex data (v, vn, vt)
                    if skip_current_group:
                        if line.startswith('v '):
                            vertices_removed += 1
                    else:
                        f_out.write(line)
                
                elif first_char == 'f':
                    # Face data
                    if skip_current_group:
                        if line.startswith('f '):
                            faces_removed += 1
                    else:
                        f_out.write(line)
                
                elif first_char in ('#', '\n', '\r', 's', 'u', 'm', 'o'):
                    # Comments, empty lines, smoothing, materials, objects
                    # Always keep comments and empty lines
                    if first_char in ('#', '\n', '\r'):
                        f_out.write(line)
                    elif not skip_current_group:
                        f_out.write(line)
                
                else:
                    # Any other line type
                    if not skip_current_group:
                        f_out.write(line)
        
        # Atomic replace: remove original and rename temp
        os.replace(temp_path, obj_path)
        
        return (groups_removed, vertices_removed, faces_removed)
        
    except Exception as e:
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        print(f"Warning: Could not deduplicate OBJ file {obj_path}: {e}")
        return (0, 0, 0)

def _log_warning(message, root):
    """Log a warning and update stats if available."""
    print(f"Warning: {message}")
    # Try to update export stats if they exist
    try:
        if hasattr(root, 'exportWindow') and hasattr(root.exportWindow, 'exportStats'):
            root.exportWindow.exportStats['warnings'] += 1
    except:
        pass

def _log_error(message, root):
    """Log an error and update stats if available."""
    print(f"Error: {message}")
    # Try to update export stats if they exist
    try:
        if hasattr(root, 'exportWindow') and hasattr(root.exportWindow, 'exportStats'):
            root.exportWindow.exportStats['errors'] += 1
    except:
        pass

def convert(truePath: str, fullItemPath: str, settings: dict, root: tk.Tk):
    itemPath, fileExt = os.path.splitext(fullItemPath)
    fileExt = fileExt.lower()  # Normalize case

    # Handle file type based on individual settings
    # Gracefully handle unknown extensions
    if fileExt not in settings:
        _log_warning(f"Unknown file type '{fileExt}' — exporting as-is.", root)
        return _copy(truePath, fullItemPath)

    state = settings[fileExt]["State"]

    if state == "As Is":
        # Always copy as-is
        return _copy(truePath, fullItemPath)

    elif state == "Do Not Export":
        return 1

    elif fileExt == ".gr2":
        if state == ".obj":
            fullItemPath = itemPath + state
            if platform.system() != "Windows":
                warn(root, "Exporting .gr2 files to .obj is currently only supported on Windows!")
                return -1
            # Ensure directory exists
            target_dir = os.path.dirname(fullItemPath)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            tamberToolPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "TamberTool", "evegr2toobj.exe")
            try:
                subprocess.run([tamberToolPath, truePath, fullItemPath], shell=True, capture_output=True)
                
                # Check if OBJ deduplication is enabled in preferences
                deduplicate_obj = False
                try:
                    if hasattr(root, 'preferences') and root.preferences:
                        deduplicate_obj = root.preferences.get("deduplicateOBJ", True)
                except:
                    deduplicate_obj = True  # Default to enabled if preference not found
                
                # Deduplicate the OBJ file if enabled
                if deduplicate_obj and os.path.exists(fullItemPath):
                    groups_removed, vertices_removed, faces_removed = _deduplicate_obj(fullItemPath)
                    if groups_removed > 0:
                        print(f"  Deduplicated OBJ: removed {groups_removed} duplicate groups, {vertices_removed:,} vertices, {faces_removed:,} faces")
                
                return 1
            except Exception as e:
                _log_error(f"Issue with Tamber Tool: {e}", root)
                return -1
        else:
            # Copy as-is for unknown conversion
            return _copy(truePath, fullItemPath)

    # Image conversions
    elif fileExt in [".dds", ".jpg", ".png"]:
        if state in [".png", ".jpg"]:
            fullItemPath = itemPath + state
            return _convertImage(truePath, fullItemPath, fileExt, state, root)
        else:
            # Unknown conversion state, copy as-is
            return _copy(truePath, fullItemPath)

    # Audio conversions  
    elif fileExt in [".wem", ".mp3"]:
        if state in [".wav", ".mp3"]:
            fullItemPath = itemPath + state
            return _convertAudio(truePath, fullItemPath, fileExt, state, root)
        else:
            # Unknown conversion state, copy as-is
            return _copy(truePath, fullItemPath)
    
    # For any other file type with unknown conversion, copy as-is
    else:
        return _copy(truePath, fullItemPath)


def _copy(truePath, fullItemPath):
    """Copy file with efficient directory creation."""
    try:
        target_dir = os.path.dirname(fullItemPath)
        if target_dir:  # Only create if there's a directory component
            os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(truePath, fullItemPath)  # copy2 preserves metadata
        return 1
    except (OSError, PermissionError) as e:
        # Handle permission errors, file already exists, or path too long
        import sys
        if hasattr(sys, '_getframe'):
            # Get the caller's root reference if available
            try:
                frame = sys._getframe(1)
                root = frame.f_locals.get('root')
                if root:
                    _log_error(f"Cannot copy file (permission denied or file locked): {os.path.basename(fullItemPath)}", root)
            except:
                pass
        return -1
    except Exception as e:
        return -1

def _convertImage(truePath, fullItemPath, sourceExt, targetExt, root):
    """Convert image files using PIL/Pillow."""
    try:
        from PIL import Image
        
        # Ensure directory exists
        target_dir = os.path.dirname(fullItemPath)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        # Special handling for DDS files
        if sourceExt == ".dds":
            try:
                # Try to open DDS with PIL (requires pillow-dds plugin or similar)
                img = Image.open(truePath)
                if targetExt == ".png":
                    img.save(fullItemPath, "PNG")
                elif targetExt == ".jpg":
                    # Convert to RGB if necessary (JPEG doesn't support transparency)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    img.save(fullItemPath, "JPEG", quality=95)
                return 1
            except (OSError, PermissionError) as e:
                # Permission denied or file access errors
                _log_error(f"Cannot write converted file (permission denied): {os.path.basename(fullItemPath)}", root)
                return -1
            except Exception as e:
                # Unsupported DDS format or other PIL errors
                error_msg = str(e)
                if "Unimplemented pixel format" in error_msg or "cannot identify" in error_msg:
                    # Silently copy unsupported DDS formats as-is (common for EVE)
                    dds_output = fullItemPath.rsplit('.', 1)[0] + '.dds'
                    try:
                        return _copy(truePath, dds_output)
                    except Exception:
                        _log_error(f"Could not copy DDS file: {os.path.basename(truePath)}", root)
                        return -1
                else:
                    _log_warning(f"Could not convert DDS file {os.path.basename(truePath)}: {e}", root)
                    # Fallback to copying as-is
                    try:
                        dds_output = fullItemPath.rsplit('.', 1)[0] + '.dds'
                        return _copy(truePath, dds_output)
                    except Exception:
                        return -1
        
        # Standard image conversions (JPG, PNG)
        else:
            try:
                img = Image.open(truePath)
                if targetExt == ".png":
                    img.save(fullItemPath, "PNG")
                elif targetExt == ".jpg":
                    # Convert to RGB if necessary (JPEG doesn't support transparency)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    img.save(fullItemPath, "JPEG", quality=95)
                else:
                    # Unknown target format, just copy
                    _log_warning(f"Unknown image target format {targetExt}, copying as-is", root)
                    return _copy(truePath, fullItemPath)
                return 1
            except (OSError, PermissionError) as e:
                # Permission denied or file access errors
                _log_error(f"Cannot write converted file (permission denied): {os.path.basename(fullItemPath)}", root)
                return -1
            except Exception as e:
                _log_warning(f"Could not convert image {os.path.basename(truePath)}: {e}", root)
                # Fallback to copying as-is
                try:
                    return _copy(truePath, fullItemPath)
                except Exception:
                    return -1
            
    except ImportError:
        _log_error("PIL/Pillow not installed. Cannot convert image files.", root)
        warn(root, "PIL/Pillow not installed. Cannot convert image files. Installing with: pip install Pillow")
        return _copy(truePath, fullItemPath)
    except Exception as e:
        _log_warning(f"Could not convert image {truePath}: {e}", root)
        return _copy(truePath, fullItemPath)

def _convertAudio(truePath, fullItemPath, sourceExt, targetExt, root):
    """Convert audio files using ffmpeg or other tools."""
    try:
        # Ensure directory exists
        target_dir = os.path.dirname(fullItemPath)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            _log_error("FFmpeg not found. Audio conversion requires FFmpeg to be installed and in PATH.", root)
            warn(root, "FFmpeg not found. Audio conversion requires FFmpeg to be installed and in PATH.")
            return _copy(truePath, fullItemPath)
        
        # Convert using ffmpeg
        if sourceExt == ".wem":
            if targetExt == ".wav":
                subprocess.run(["ffmpeg", "-i", truePath, "-y", fullItemPath], check=True, capture_output=True)
            elif targetExt == ".mp3":
                subprocess.run(["ffmpeg", "-i", truePath, "-codec:a", "libmp3lame", "-b:a", "192k", "-y", fullItemPath], check=True, capture_output=True)
            else:
                _log_warning(f"Unknown audio target format {targetExt} for {sourceExt}, copying as-is", root)
                return _copy(truePath, fullItemPath)
        elif sourceExt == ".mp3":
            if targetExt == ".wav":
                subprocess.run(["ffmpeg", "-i", truePath, "-y", fullItemPath], check=True, capture_output=True)
            else:
                _log_warning(f"Unknown audio target format {targetExt} for {sourceExt}, copying as-is", root)
                return _copy(truePath, fullItemPath)
        else:
            _log_warning(f"Unknown audio source format {sourceExt}, copying as-is", root)
            return _copy(truePath, fullItemPath)
        
        return 1
        
    except subprocess.CalledProcessError as e:
        _log_warning(f"Could not convert audio {truePath}: {e}", root)
        return _copy(truePath, fullItemPath)
    except Exception as e:
        _log_warning(f"Audio conversion failed for {truePath}: {e}", root)
        return _copy(truePath, fullItemPath)
