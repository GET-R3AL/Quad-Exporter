import os
import sys
import json
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


def getPreferenceDir():
    """Get the directory where preferences should be stored.
    For EXE: Try app directory first, fallback to user AppData.
    For script: Use pref subdirectory in app directory.
    """
    baseDir = getBaseDir()
    
    if getattr(sys, 'frozen', False):
        # Running as EXE - try app directory first
        appPrefDir = os.path.join(baseDir, "pref")
        
        # Test if we can write to the app directory
        try:
            if not os.path.exists(appPrefDir):
                os.makedirs(appPrefDir)
            
            # Test write access
            testFile = os.path.join(appPrefDir, ".write_test")
            with open(testFile, "w") as f:
                f.write("test")
            os.remove(testFile)
            
            # App directory is writable, use it
            return appPrefDir
        except (OSError, PermissionError):
            # App directory not writable, use user AppData
            userDataDir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Quad-Exporter")
            try:
                if not os.path.exists(userDataDir):
                    os.makedirs(userDataDir)
                print(f"Using user data directory for preferences: {userDataDir}")
                return userDataDir
            except Exception as e:
                print(f"Cannot create user data directory: {e}")
                # Final fallback to app directory even if not writable
                return appPrefDir
    else:
        # Running as script - use app directory
        return os.path.join(baseDir, "pref")


def savePaths():
    """Save paths to unified preferences file."""
    global resPath, indexPath
    preferences = loadPreferences()
    if preferences:
        preferences["paths"]["resPath"] = resPath
        preferences["paths"]["indexPath"] = indexPath
        savePreferences(preferences)


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


def loadPreferences():
    """Load preferences from the unified preferences.json file."""
    prefDir = getPreferenceDir()
    preferencesPath = os.path.join(prefDir, "preferences.json")
    
    if os.path.exists(preferencesPath):
        try:
            with open(preferencesPath, "r") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading preferences: {e}")
            return None
    return None

def savePreferences(preferences):
    """Save preferences to the unified preferences.json file."""
    prefDir = getPreferenceDir()
    preferencesPath = os.path.join(prefDir, "preferences.json")
    
    try:
        with open(preferencesPath, "w") as file:
            json.dump(preferences, file, indent=4)
        return True
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return False


def findCacheDirectory(startPath):
    """Find a valid cache directory containing ResFiles and tq folders.
    
    Args:
        startPath: Directory to start searching from
        
    Returns:
        Path to cache directory, or None if not found
    """
    if not os.path.exists(startPath):
        return None
    
    # Check if this directory has both ResFiles and tq (or sisi or thunderdome)
    resFilesPath = os.path.join(startPath, "ResFiles")
    hasTq = os.path.isdir(os.path.join(startPath, "tq"))
    hasSisi = os.path.isdir(os.path.join(startPath, "sisi"))
    hasThunderdome = os.path.isdir(os.path.join(startPath, "thunderdome"))
    
    if os.path.isdir(resFilesPath) and (hasTq or hasSisi or hasThunderdome):
        return startPath
    
    # Search subdirectories one level deep for cache-like folders
    try:
        for item in os.listdir(startPath):
            itemPath = os.path.join(startPath, item)
            if os.path.isdir(itemPath):
                resFilesPath = os.path.join(itemPath, "ResFiles")
                hasTq = os.path.isdir(os.path.join(itemPath, "tq"))
                hasSisi = os.path.isdir(os.path.join(itemPath, "sisi"))
                hasThunderdome = os.path.isdir(os.path.join(itemPath, "thunderdome"))
                if os.path.isdir(resFilesPath) and (hasTq or hasSisi or hasThunderdome):
                    return itemPath
    except (OSError, PermissionError):
        pass
    
    return None


def findIndexFile(cacheDir):
    """Find the resfileindex.txt file in cache directory.
    
    Checks for server folders in order: tq, sisi, thunderdome
    
    Args:
        cacheDir: Path to cache directory
        
    Returns:
        Path to resfileindex.txt, or None if not found
    """
    if not cacheDir or not os.path.exists(cacheDir):
        return None
    
    # Server options in order of preference
    serverOptions = ["tq", "sisi", "thunderdome"]
    
    for server in serverOptions:
        indexPath = os.path.join(cacheDir, server, "resfileindex.txt")
        if os.path.isfile(indexPath):
            return indexPath
    
    return None


def createDefaultPreferences(baseDir):
    """Create default preference files if they don't exist."""
    prefDir = getPreferenceDir()
    
    # Create pref directory if it doesn't exist
    if not os.path.exists(prefDir):
        try:
            os.makedirs(prefDir)
            print("Created preferences directory")
        except Exception as e:
            print(f"Cannot create preferences directory: {e}")
            return False
    
    # Create unified preferences.json if it doesn't exist
    preferencesPath = os.path.join(prefDir, "preferences.json")
    if not os.path.exists(preferencesPath):
        try:
            # Try multiple methods to find a good default export path (EXE-friendly)
            defaultExportPath = None
            
            # Method 1: Try USERPROFILE environment variable (most reliable for EXE)
            user_profile = os.environ.get('USERPROFILE')
            if user_profile and os.path.isdir(user_profile):
                docs_path = os.path.join(user_profile, 'Documents')
                if os.path.isdir(docs_path):
                    defaultExportPath = docs_path
            
            # Method 2: Fallback to expanduser (standard approach)
            if not defaultExportPath:
                try:
                    docs_path = os.path.join(os.path.expanduser("~"), "Documents")
                    if os.path.isdir(docs_path):
                        defaultExportPath = docs_path
                except:
                    pass
            
            # Method 3: Final fallback to application directory
            if not defaultExportPath:
                defaultExportPath = baseDir
                print("Using application directory as export default (could not find Documents folder)")
            
            defaultPreferences = {
                "paths": {
                    "resPath": "",
                    "indexPath": "",
                    "exportDest": defaultExportPath
                },
                "fileTypeVisibility": {
                    ".gr2": True, ".black": True, ".static": True, ".fsdbinary": True,
                    ".json": True, ".xml": True, ".yaml": True, ".prs": True,
                    ".bnk": True, ".wem": True, ".jpg": True, ".dds": True,
                    ".png": True, ".webm": True, ".txt": True, ".py": True,
                    ".gsf": True, ".srt": True, ".pathdata": True, ".region": True,
                    ".pickle": True, ".css": True, ".tri": True, ".mp4": True, ".mp3": True
                },
                "conversions": {
                    "ALL FILES": {
                        "Options": ["As Is", "Follow Individual Options", "Do Not Export"],
                        "State": "As Is"
                    },
                    ".gr2": {
                        "Options": ["As Is", ".obj", "Do Not Export"],
                        "State": "As Is"
                    },
                    ".black": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".static": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".fsdbinary": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".json": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".xml": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".yaml": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".prs": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".bnk": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".wem": {"Options": ["As Is", ".wav", ".mp3", "Do Not Export"], "State": "As Is"},
                    ".jpg": {"Options": ["As Is", ".png", "Do Not Export"], "State": "As Is"},
                    ".dds": {"Options": ["As Is", ".png", ".jpg", "Do Not Export"], "State": "As Is"},
                    ".png": {"Options": ["As Is", ".jpg", "Do Not Export"], "State": "As Is"},
                    ".webm": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".txt": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".py": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".gsf": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".srt": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".pathdata": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".region": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".pickle": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".css": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".tri": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".mp4": {"Options": ["As Is", "Do Not Export"], "State": "As Is"},
                    ".mp3": {"Options": ["As Is", ".wav", "Do Not Export"], "State": "As Is"}
                }
            }
            
            import json
            with open(preferencesPath, "w") as file:
                json.dump(defaultPreferences, file, indent=4)
            print(f"Created default preferences.json with export path: {defaultExportPath}")
        except Exception as e:
            print(f"Cannot create preferences.json: {e}")
    
    return True


def main():
    # Some variables for later
    global resPath, savedPaths, indexPath
    baseDir = getBaseDir()
    prefDir = getPreferenceDir()
    
    # Create default preferences first, before creating the main window
    prefsCreated = createDefaultPreferences(baseDir)
    
    # Create the main window.
    root = tk.Tk()
    root.title("Quad-Exporter")
    root.minsize(800, 600)
    root.tk.call('tk', 'scaling', 1.3)
    # root.state("zoomed")
    
    # Load unified preferences
    preferences = loadPreferences()
    if preferences:
        # Extract file type visibility (enabled files are those with visibility True)
        fileTypeVisibility = preferences.get("fileTypeVisibility", {})
        for fileType, visible in fileTypeVisibility.items():
            if visible:
                enabled.append(fileType)
        
        if enabled:
            print(f"Visible File Types: {enabled}")
        else:
            print("No file types visible (all hidden)")
        
        # Store preferences globally for access
        root.preferences = preferences
    else:
        print("Warning: Could not load preferences, using defaults")
        root.preferences = None
    # Set default paths - try multiple common EVE installation locations
    possibleEvePaths = [
        r"C:\Program Files\EVE",
        r"C:\EVE",
        r"C:\Program Files (x86)\EVE"
    ]
    
    # Find the first valid cache directory
    defaultCachePath = None
    for evePath in possibleEvePaths:
        if os.path.isdir(evePath):
            # Look for a cache-like folder (has ResFiles and tq/sisi/thunderdome)
            cacheDir = findCacheDirectory(evePath)
            if cacheDir:
                defaultCachePath = cacheDir
                print(f"Found cache directory: {cacheDir}")
                break
    
    # If no cache found, default to a path anyway
    if not defaultCachePath:
        defaultCachePath = r"C:\Program Files\EVE\SharedCache"
    
    # Build default ResFiles path
    defaultResPath = os.path.join(defaultCachePath, "ResFiles")
    
    # Find index file in the cache directory
    defaultIndexPath = findIndexFile(defaultCachePath)
    
    # If no index found, default to TQ path
    if not defaultIndexPath:
        defaultIndexPath = os.path.join(defaultCachePath, "tq", "resfileindex.txt")
    
    # Load paths from preferences
    if preferences and "paths" in preferences:
        resPath = preferences["paths"].get("resPath", defaultResPath)
        indexPath = preferences["paths"].get("indexPath", defaultIndexPath)
    else:
        resPath = defaultResPath
        indexPath = defaultIndexPath
    
    # If paths are empty, use defaults
    if not resPath:
        resPath = defaultResPath
    if not indexPath:
        indexPath = defaultIndexPath
    
    # If the cache path doesn't exist, use default anyway and warn user
    if not os.path.isdir(resPath):
        print(f"Warning: Resource path '{resPath}' does not exist. You can set the correct path in Settings.")
        # Don't show popup - just use the path anyway and let user change it in settings
    
    # If index path doesn't exist, try to find it automatically
    if not os.path.isfile(indexPath):
        # Get the cache directory (parent of ResFiles)
        if resPath.endswith("ResFiles"):
            cacheDir = os.path.dirname(resPath)
        else:
            cacheDir = resPath
        
        # Use helper function to find index file
        foundIndex = findIndexFile(cacheDir)
        if foundIndex:
            indexPath = foundIndex
            print(f"Auto-detected index file: {indexPath}")
            savePaths()
        else:
            # Use default even if it doesn't exist - user can set it in settings later
            print(f"Warning: Index file not found at '{indexPath}'. You can set the correct path in Settings.")
    
    # Always save paths to ensure file exists with current values
    savePaths()
    
    # Check if we can parse the index file
    if os.path.isfile(indexPath) and os.path.isdir(resPath):
        # Both files exist, parse normally
        try:
            rootDir = parseIndex(root, indexPath, resPath, enabled)
            # The first rootDir is a true "root" and is empty, so let's go it its child.
            rootDir = rootDir.children[0]
            rootDir.directory = "ResFiles"
            print(f"Loaded {rootDir.size} bytes")
        except Exception as e:
            print(f"Error parsing index file: {e}")
            # Create empty root directory as fallback
            rootDir = FileDir(resPath=resPath, enabled=enabled)
            rootDir.directory = "ResFiles"
            print("Created empty root directory due to parsing error")
    else:
        # Files don't exist, create empty root directory
        rootDir = FileDir(resPath=resPath, enabled=enabled)
        rootDir.directory = "ResFiles"
        print("Created empty root directory - index file or resource path not found")
    
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

    # Export Window (bottom) with hierarchy options
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
