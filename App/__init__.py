import os
import sys
import tkinter as tk
from tkinter import ttk
from functools import partial
from fileSys import *
from QEHelper import *
from customElements import *

resPath = ""
indexPath = ""
savedPaths = ""
# If enabled is empty, all files are utilized.
# Commenting lines out with # will cause them to be ignored as well.
enabled = []


def getBaseDir():
    """Get the base directory for the application.
    When running as an EXE, this returns the directory containing the EXE.
    When running as a script, this returns the script directory.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.realpath(__file__))


def savePaths():
    global resPath, savedPaths, indexPath
    # Save the data.
    with open(savedPaths, "w") as file:
        file.write(resPath + "\n")
        file.write(indexPath + "\n")


def savePathsFromSettings(newResPath, newIndexPath, root=None):
    """Callback function for settings window to update paths and reload data."""
    global resPath, indexPath, enabled
    oldResPath = resPath
    oldIndexPath = indexPath
    resPath = newResPath
    indexPath = newIndexPath
    savePaths()
    
    # If paths changed and root window is provided, reload the directory tree
    if root and (oldResPath != newResPath or oldIndexPath != newIndexPath):
        try:
            # Reload the directory tree
            rootDir = parseIndex(root, indexPath, resPath, enabled)
            rootDir = rootDir.children[0]
            rootDir.directory = "ResFiles"
            print(f"Reloaded {rootDir.size} bytes")
            root.rootDir = rootDir
            root.selected = []
            
            # Update the directory window if it exists
            if hasattr(root, 'directoryWindow'):
                root.directoryWindow.refreshTree()
        except Exception as e:
            warn(root, f"Failed to reload cache data:\n{str(e)}")


def openSettingsWindow(root: tk.Tk, activeTab: str = "Paths"):
    """Open the settings window."""
    global resPath, indexPath
    # Create a wrapper function that includes the root parameter
    def saveCallback(newResPath, newIndexPath):
        savePathsFromSettings(newResPath, newIndexPath, root)
    
    SettingsWindow(root, resPath, indexPath, saveCallback, activeTab=activeTab)


def main():
    # Some variables for later
    global resPath, savedPaths, indexPath
    baseDir = getBaseDir()
    savedPaths = os.path.join(baseDir, "pref", "savedPaths.txt")
    # Create the main window.
    root = tk.Tk()
    root.title("Quad-Exporter")
    root.minsize(800, 600)
    root.tk.call('tk', 'scaling', 1.3)
    # root.state("zoomed")
    # Load Preferences
    try:
        with open(os.path.join(baseDir, "pref", "enabled.txt")) as file:
            for line in file.readlines():
                line = line.strip()
                if len(line) > 0 and line[0] != "#":
                    enabled.append(line)
        print(f"Enabled File Types: {enabled}")
    except:
        warn(root, "Cannot open 'enabled' preference file")
    # Set default paths
    defaultResPath = r"C:\Program Files\EVE\SharedCache\ResFiles"
    defaultIndexPath = r"C:\Program Files\EVE\SharedCache\tq\resfileindex.txt"
    
    # Ensure pref directory exists
    prefDir = os.path.join(baseDir, "pref")
    if not os.path.exists(prefDir):
        try:
            os.makedirs(prefDir)
        except:
            warn(root, "Cannot create preferences directory.\nWrite privileges may be needed.")
    
    # Load or create savedPaths.txt
    try:
        with open(savedPaths, "r") as file:
            resPath = file.readline().strip()
            indexPath = file.readline().strip()
    except:
        # File doesn't exist, create it with default paths
        resPath = ""
        indexPath = ""
        try:
            with open(savedPaths, "w") as file:
                file.write(defaultResPath + "\n")
                file.write(defaultIndexPath + "\n")
            print("Created new preferences file with default paths.")
        except:
            warn(root, "Cannot create new user preference file.\nWrite privileges may be needed.")
    
    # If we don't have a res cache path yet, use the default
    if resPath == "":
        resPath = defaultResPath
    
    # If we don't have an index path yet, use the default
    if indexPath == "":
        indexPath = defaultIndexPath
    
    # If the cache path doesn't exist, ask to get it (but don't ask for index)
    if not os.path.isdir(resPath):
        resPath = getCachePopUp(root)
        if resPath:  # Only update if user selected something
            savePaths()
    
    # If index path doesn't exist, try to derive it from resPath
    if not os.path.isfile(indexPath):
        # Try to find resfileindex.txt in parent directories
        possibleIndex = os.path.join(os.path.dirname(resPath), "tq", "resfileindex.txt")
        if os.path.isfile(possibleIndex):
            indexPath = possibleIndex
            savePaths()
        else:
            # Use default even if it doesn't exist - user can set it in settings later
            print(f"Warning: Index file not found at {indexPath}. You can set it in Settings.")
    else:
        # Save the data if everything is valid
        savePaths()
    # Check to see if we can open the folder.
    # Open the index file and create our folder.
    rootDir = parseIndex(root, indexPath, resPath, enabled)
    # The first rootDir is a true "root" and is empty, so let's go it its child.
    rootDir = rootDir.children[0]
    rootDir.directory = "ResFiles"
    print(f"Loaded {rootDir.size} bytes")
    root.rootDir = rootDir
    root.selected = []
    
    # Store paths on root for access by ExportWindow
    root.resPath = resPath
    root.indexPath = indexPath
    root.savePathsCallback = savePathsFromSettings

    # Create main horizontal PanedWindow using tk.PanedWindow for better compatibility
    mainPane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
    mainPane.pack(fill=tk.BOTH, expand=True)

    # Directory Window (left pane)
    dW = DirectoryWindow(root)  # Pass root, not mainPane
    dW.pack_propagate(False)
    mainPane.add(dW, minsize=200, width=250)
    root.directoryWindow = dW  # Store reference for refreshing

    # Right side frame
    rightFrame = tk.Frame(mainPane)
    
    # Preview Window (top)
    pW = PreviewWindow(root)  # Pass root, not rightFrame
    pW.pack(side=tk.TOP, fill=tk.BOTH, expand=True, in_=rightFrame)
    root.pwUpdate = pW.update

    # Export Window (bottom) - smaller since we removed the options panes
    eW = ExportWindow(root)  # Pass root, not rightFrame
    eW.pack(side=tk.BOTTOM, fill=tk.X, in_=rightFrame)

    mainPane.add(rightFrame, minsize=400)

    # Menu Commands.
    top = root.winfo_toplevel()
    root.menuBar = tk.Menu(top)
    top['menu'] = root.menuBar

    # Add Settings directly to menu bar
    root.menuBar.add_command(label='Settings', command=partial(openSettingsWindow, root))

    # Finally call the mainloop.
    root.mainloop()


# In case we do multithreading / multiprocessing.
if __name__ == "__main__":
    main()
