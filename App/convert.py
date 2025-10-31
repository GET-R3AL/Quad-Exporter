import os
import platform
import shutil
import tkinter as tk
from QEHelper import warn
import subprocess

def convert(truePath: str, fullItemPath: str, settings: dict, root: tk.Tk):
    itemPath, fileExt = os.path.splitext(fullItemPath)
    fileExt = fileExt.lower()  # Normalize case
    print(f"Exporting from {truePath} to {fullItemPath}")

    if settings["ALL FILES"]["State"] == "As Is":
        if not os.path.exists(fullItemPath):
            return _copy(truePath, fullItemPath)

    elif settings["ALL FILES"]["State"] == "Do Not Export":
        return 1

    elif settings["ALL FILES"]["State"] == "Follow Individual Options":
        # ✅ Gracefully handle unknown extensions
        if fileExt not in settings:
            print(f"[WARN] Unknown file type '{fileExt}' — exporting as-is.")
            return _copy(truePath, fullItemPath)

        state = settings[fileExt]["State"]

        if state == "As Is":
            if not os.path.exists(fullItemPath):
                return _copy(truePath, fullItemPath)

        elif state == "Do Not Export":
            return 1

        elif fileExt == ".gr2":
            fullItemPath = itemPath + state
            if state == ".obj":
                if platform.system() != "Windows":
                    warn(root, "Exporting .gr2 files to .obj is currently only supported on Windows!")
                    return -1
                if not os.path.exists(os.path.dirname(fullItemPath)):
                    os.makedirs(os.path.dirname(fullItemPath))
                tamberToolPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "TamberTool", "evegr2toobj.exe")
                try:
                    subprocess.run([tamberToolPath, truePath, fullItemPath], shell=True)
                    return 1
                except:
                    warn(root, "Issue with Tamber Tool... Ask Hoed for help.")
                    return -1

        # Image conversions
        elif fileExt in [".dds", ".jpg", ".png"]:
            if state in [".png", ".jpg"]:
                fullItemPath = itemPath + state
                return _convertImage(truePath, fullItemPath, fileExt, state, root)

        # Audio conversions  
        elif fileExt in [".wem", ".mp3"]:
            if state in [".wav", ".mp3"]:
                fullItemPath = itemPath + state
                return _convertAudio(truePath, fullItemPath, fileExt, state, root)


def _copy(truePath, fullItemPath):
    if not os.path.exists(os.path.dirname(fullItemPath)):
        os.makedirs(os.path.dirname(fullItemPath))
    shutil.copy(truePath, fullItemPath)
    return 1

def _convertImage(truePath, fullItemPath, sourceExt, targetExt, root):
    """Convert image files using PIL/Pillow."""
    try:
        from PIL import Image
        
        if not os.path.exists(os.path.dirname(fullItemPath)):
            os.makedirs(os.path.dirname(fullItemPath))
        
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
            except Exception as e:
                print(f"Warning: Could not convert DDS file {truePath}: {e}")
                # Fallback to copying as-is
                return _copy(truePath, fullItemPath)
        
        # Standard image conversions
        else:
            img = Image.open(truePath)
            if targetExt == ".png":
                img.save(fullItemPath, "PNG")
            elif targetExt == ".jpg":
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(fullItemPath, "JPEG", quality=95)
            return 1
            
    except ImportError:
        warn(root, "PIL/Pillow not installed. Cannot convert image files. Installing with: pip install Pillow")
        return _copy(truePath, fullItemPath)
    except Exception as e:
        print(f"Warning: Could not convert image {truePath}: {e}")
        return _copy(truePath, fullItemPath)

def _convertAudio(truePath, fullItemPath, sourceExt, targetExt, root):
    """Convert audio files using ffmpeg or other tools."""
    try:
        if not os.path.exists(os.path.dirname(fullItemPath)):
            os.makedirs(os.path.dirname(fullItemPath))
        
        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            warn(root, "FFmpeg not found. Audio conversion requires FFmpeg to be installed and in PATH.")
            return _copy(truePath, fullItemPath)
        
        # Convert using ffmpeg
        if sourceExt == ".wem":
            if targetExt == ".wav":
                subprocess.run(["ffmpeg", "-i", truePath, "-y", fullItemPath], check=True, capture_output=True)
            elif targetExt == ".mp3":
                subprocess.run(["ffmpeg", "-i", truePath, "-codec:a", "libmp3lame", "-b:a", "192k", "-y", fullItemPath], check=True, capture_output=True)
        elif sourceExt == ".mp3":
            if targetExt == ".wav":
                subprocess.run(["ffmpeg", "-i", truePath, "-y", fullItemPath], check=True, capture_output=True)
        
        return 1
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not convert audio {truePath}: {e}")
        return _copy(truePath, fullItemPath)
    except Exception as e:
        print(f"Warning: Audio conversion failed for {truePath}: {e}")
        return _copy(truePath, fullItemPath)
