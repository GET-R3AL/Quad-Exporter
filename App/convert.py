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


def _copy(truePath, fullItemPath):
    if not os.path.exists(os.path.dirname(fullItemPath)):
        os.makedirs(os.path.dirname(fullItemPath))
    shutil.copy(truePath, fullItemPath)
    return 1
