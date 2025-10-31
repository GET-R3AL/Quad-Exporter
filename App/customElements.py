# Some custom elements I've made for this application.
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import filedialog
from fileSys import *
from QEHelper import *
from collections import defaultdict
import json
from convert import convert
import platform

# All extensions - matches conversions.json
extensions = ("ALL FILES", ".gr2", ".black", ".static", ".fsdbinary", ".json", ".xml", ".yaml", ".prs", ".bnk", ".wem", ".jpg", ".dds", ".png", ".webm", ".txt", ".py", ".gsf", ".srt", ".pathdata", ".region", ".pickle", ".css", ".tri", ".mp4", ".mp3")
icons = ("files", "box", "file-digit", "file-digit", "file-digit", "file-code", "file-code", "file-code", "file-input", "music", "music", "image", "image", "image", "youtube", "file-text", "file-code", "file-code", "message-circle", "map", "map", "file-digit", "file-code", "box", "youtube", "music")


def CreateToolTip(widget, text):
    toolTip = ToolTip(widget)

    def enter(event):
        toolTip.showtip(text)

    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)


class ToolTip():
    # Thank you internet for this tooltip function.
    # https://stackoverflow.com/a/56749167
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, borderwidth=1, font=("Arial", "12"))
        label.pack(ipadx=0)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class ExportWindow(tk.Frame):
    def __init__(self, root: tk.Tk, **kwargs):
        super(ExportWindow, self).__init__(**kwargs)
        self.root = root
        # Don't use pack_propagate(False) so the frame can size itself to content
        
        # Load Settings from unified preferences
        from __init__ import loadPreferences
        self.preferences = loadPreferences()
        if self.preferences:
            self.conversionSettings = self.preferences.get("conversions", {})
            self.exportDestination = self.preferences.get("paths", {}).get("exportDest", "")
        else:
            self.conversionSettings = {}
            self.exportDestination = ""
        
        # Main frame with minimum height
        mainFrame = ttk.Frame(self)
        mainFrame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        # Set a minimum height for the export window
        self.config(height=150)
        
        # Export destination section
        destLabel = ttk.Label(mainFrame, text="Export Destination:", font=("Arial", 10, "bold"))
        destLabel.grid(column=0, row=0, sticky="W", pady=(0, 5))
        
        # Destination path display and browse button
        destFrame = ttk.Frame(mainFrame)
        destFrame.grid(column=0, row=1, sticky="EW", pady=(0, 15))
        destFrame.columnconfigure(0, weight=1)
        
        self.destEntry = ttk.Entry(destFrame, width=50)
        self.destEntry.grid(column=0, row=0, sticky="EW", padx=(0, 5))
        if self.exportDestination:
            self.destEntry.insert(0, self.exportDestination)
        
        browseBtn = ttk.Button(destFrame, text="Browse...", command=self.browseDestination)
        browseBtn.grid(column=1, row=0)
        
        # Export Options section
        optionsLabel = ttk.Label(mainFrame, text="Export Options:", font=("Arial", 10, "bold"))
        optionsLabel.grid(column=0, row=2, sticky="W", pady=(0, 5))
        
        # Options frame
        optionsFrame = ttk.Frame(mainFrame)
        optionsFrame.grid(column=0, row=3, sticky="EW", pady=(0, 15))
        
        # Checkbox variables
        self.keepHierarchy = tk.BooleanVar(value=True)
        self.exportFiles = tk.BooleanVar(value=True)
        self.exportSubdirs = tk.BooleanVar(value=True)
        
        # Checkboxes
        hierarchyCheck = ttk.Checkbutton(optionsFrame, text="Keep folder hierarchy", variable=self.keepHierarchy)
        hierarchyCheck.grid(column=0, row=0, sticky="W", padx=(0, 15))
        
        filesCheck = ttk.Checkbutton(optionsFrame, text="Export files", variable=self.exportFiles)
        filesCheck.grid(column=1, row=0, sticky="W", padx=(0, 15))
        
        subdirsCheck = ttk.Checkbutton(optionsFrame, text="Export subdirectories", variable=self.exportSubdirs)
        subdirsCheck.grid(column=2, row=0, sticky="W")
        
        # Export Settings button
        settingsBtn = ttk.Button(mainFrame, text="Export Settings", command=self.openExportSettings)
        settingsBtn.grid(column=0, row=4, sticky="W", pady=(0, 15))
        
        # Export button
        self.exportBtn = ttk.Button(mainFrame, text="Export Selected", command=self.export)
        self.exportBtn.grid(column=0, row=5, sticky="EW")
        
        mainFrame.columnconfigure(0, weight=1)
    
    def _saveExportDestination(self, path):
        """Save export destination to unified preferences."""
        from __init__ import loadPreferences, savePreferences
        preferences = loadPreferences()
        if preferences:
            preferences["paths"]["exportDest"] = path
            savePreferences(preferences)
    
    def browseDestination(self):
        initialdir = self.exportDestination if self.exportDestination and os.path.isdir(self.exportDestination) else "/"
        output_directory = filedialog.askdirectory(parent=self, initialdir=initialdir, 
                                                   title="Select export destination", mustexist=True)
        if output_directory:
            self.exportDestination = output_directory
            self.destEntry.delete(0, tk.END)
            self.destEntry.insert(0, output_directory)
            # Save the destination to unified preferences
            self.exportDestination = output_directory
            self._saveExportDestination(output_directory)
    
    def openExportSettings(self):
        """Open settings window with Conversions tab active."""
        # Call the settings window with tab parameter
        SettingsWindow(self.root, self.root.resPath, self.root.indexPath, 
                      self.root.savePathsCallback, activeTab="Conversions")

    def export(self):
        # Get destination from entry field
        output_directory = self.destEntry.get().strip()
        
        if not output_directory:
            warn(self.root, "Please select an export destination.")
            return
        
        if not os.path.isdir(output_directory):
            warn(self.root, "Export destination does not exist. Please select a valid directory.")
            return
        
        # Update saved destination
        self.exportDestination = output_directory
        self._saveExportDestination(output_directory)
        
        # Go through all of the selected items.
        for item in self.root.selected:
            if isinstance(item, FileItem):
                # Add the file.
                self.exportFile(item, output_directory)
            else:
                self.exportFolder(item, output_directory)

    def exportFile(self, item, output_directory):
        full_item_path = os.path.join(output_directory, item.path)
        # Call our convert.py function to handle file conversion.
        convert(item.truePath, full_item_path, self.conversionSettings, self.root)

    def exportFolder(self, item, output_directory):
        # Get export options from checkboxes
        keep_hierarchy = self.keepHierarchy.get()
        export_files = self.exportFiles.get()
        export_subdirs = self.exportSubdirs.get()
        
        base_path = item.fullPath if keep_hierarchy else ""
        
        def recurse(folder: FileDir):
            if export_files:
                for child in folder.files:
                    rel_path = os.path.join(base_path, os.path.relpath(child.fullPath, item.fullPath))
                    target_dir = os.path.join(output_directory, rel_path)
                    self.exportFile(child, target_dir)

            if export_subdirs:
                for subdir in folder.children:
                    recurse(subdir)

        recurse(item)




class PreviewWindow(tk.Frame):
    # This is the preview window.
    # Todo:
    # A whole lot more preview windows...
    def __init__(self, root: tk.Tk, **kwargs):
        super(PreviewWindow, self).__init__(**kwargs)
        self.root = root
        self.defaultLabel()

    def defaultLabel(self):
        self.mainFrame = ttk.Label(self, text="Preview Window\nDouble Click to Preview Item", anchor=tk.CENTER, compound="top")
        self.mainFrame.imagePath = os.path.join(getBaseDir(), "Images", "Logo.png")
        self.mainFrame.image = loadImage(self.mainFrame.imagePath, (256, 256))
        self.mainFrame.configure(image=self.mainFrame.image)
        self.mainFrame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)

    def defaultPreview(self):
        frame = ttk.Label(self.mainFrame, text=f"Name: {self.selected.path}\nSize: {(self.selected.size / 1000000):.2f} MB", anchor=tk.CENTER, justify=tk.LEFT, font=("Arial", 15))
        frame.name = self.selected.path
        return frame

    def imagePreview(self):
        # TODO: Image transforms like pan, zoom, etc.
        x = self.winfo_width() - 50
        y = self.winfo_height() - 50
        frame = tk.Canvas(self.mainFrame)
        frame.pImage = loadImage(self.selected.truePath, (x, y))
        frame.create_image(x / 2, y / 2, anchor=tk.CENTER, image=frame.pImage)
        frame.name = self.selected.path
        return frame

    def textPreview(self, type: int):
        # TODO: Syntax highlighting and stuff.
        frame = scrolledtext.ScrolledText(self.mainFrame, font=("Arial", 12))
        frame.text = loadText(self.selected.truePath)
        frame.insert(tk.INSERT, frame.text)
        frame.name = self.selected.path
        frame.configure(state=tk.DISABLED)
        return frame

    def folderPreview(self):
        frame = ttk.Label(self.mainFrame, text=f"Folder: {self.selected.directory}\nLocal Items: {self.selected.itemCount}\nTotal Items: {self.selected.totalItems}", anchor=tk.CENTER, justify=tk.LEFT, font=("Arial", 15))
        frame.name = self.selected.directory
        return frame

    def update(self):
        # Take the selected items and display them.
        if (len(self.root.selected) >= 1):
            # For now this only supports single element previews.
            if self.mainFrame is not None:
                self.mainFrame.destroy()
            for child in self.winfo_children():
                child.destroy()
            self.mainFrame = ttk.Notebook(self)
            self.mainFrame.pack(expand=True, fill=tk.BOTH)
            self.frames = []
            for self.selected in self.root.selected:
                if isinstance(self.selected, FileItem):
                    # Image Preview.
                    if isImage(self.selected):
                        self.frames.append(self.imagePreview())
                    # Text preview.
                    # TODO: Add syntax highlighting.
                    elif isText(self.selected):
                        self.frames.append(self.textPreview(isText(self.selected)))
                    # Default (Just display file characteristics).
                    else:
                        self.frames.append(self.defaultPreview())
                else:
                    # Display the statistics of the folder.
                    self.frames.append(self.folderPreview())
            for frame in self.frames:
                frame.pack(fill=tk.BOTH, expand=True)
                self.mainFrame.add(frame, text=frame.name)
        else:
            self.defaultLabel()


class DirectoryWindow(tk.Frame):
    def __init__(self, root: tk.Tk, **kwargs):
        super(DirectoryWindow, self).__init__(**kwargs)
        self.configure(padx=5, pady=5)

        # Dictionaries
        self.fileDict = {}
        self.dirDict = {}
        self.loaded = []
        self.emptyDict = {}
        self.imageDict = defaultdict(self.defaultDictValue)

        global extensions, icons
        for ext, icon in zip(extensions, icons):
            self.imageDict[ext] = getSVG(os.path.join("Images", "icons", f"{icon}.svg"))

        self.root = root
        self.rootDir = root.rootDir

        # Create Treeview
        self.tree = ttk.Treeview(self, show="tree")
        self.openImg = getSVG(os.path.join("Images", "icons", "folder-open.svg"))
        self.closeImg = getSVG(os.path.join("Images", "icons", "folder.svg"))
        self.errorImg = self.defaultDictValue()
        self.tree.heading('#0', text=self.rootDir.directory, anchor='w')
        self.rootNode = self.tree.insert("", "end", text=self.rootDir.directory, open=True, image=self.openImg)

        # --- Add scrollbars ---
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        # ----------------------

        self.addChildren(self.rootNode, self.rootDir)
        self.addFiles(self.rootNode)

        # Bindings
        self.tree.bind("<<TreeviewOpen>>", self.loadOpen)
        self.tree.bind("<<TreeviewClose>>", self.closeFolder)
        self.tree.bind("<<TreeviewSelect>>", self.updateSelected)
        self.tree.bind("<Double-1>", self.updatePreview)


    def addChildren(self, parent, parentDir: "FileDir"):
        self.fileDict[parent] = parentDir.files
        self.dirDict[parent] = parentDir
        if len(parentDir.children) == 0 or len(parentDir.files) == 0:
            newEmpty = self.tree.insert(parent, "end", open=False, image=self.errorImg, text="")
            self.emptyDict[parent] = newEmpty
        parentDir = sorted(parentDir.children, key=lambda x: x.directory)
        for dir in parentDir:
            # Add all sub directories.
            newParent = self.tree.insert(parent, "end", open=False, image=self.closeImg, text=dir.directory)
            self.addChildren(newParent, dir)

    def addFiles(self, parent):
        self.loaded.append(parent)
        if parent in self.emptyDict:
            self.tree.delete(self.emptyDict[parent])
        files = sorted(self.dirDict[parent].files, key=lambda x: x.path)
        for file in files:
            newNode = self.tree.insert(parent, "end", open=False, image=self.imageDict[file.fileExt], text=file.path)
            self.fileDict[newNode] = file

    def loadOpen(self, event):
        # Load files when we open the subfolders, so we don't take a while to load.
        self.tree.item(self.tree.focus(), image=self.openImg)

        # Only load files if we haven't loaded this yet.
        if self.tree.focus() not in self.loaded:
            self.addFiles(self.tree.focus())

    def closeFolder(self, event):
        self.tree.item(self.tree.focus(), image=self.closeImg)

    def defaultDictValue(self):
        return getSVG(os.path.join("Images", "icons", "alert-octagon.svg"))

    def updatePreview(self, event):
        # This method updates the preview.
        self.updateSelected(event)
        self.root.pwUpdate()

    def updateSelected(self, event):
        # This method updates the selected items (for the export options mostly).
        self.root.selected = self.getSelected(self.tree.selection())

    def getSelected(self, selection):
        # Returns all FileDir and FileItem objects from the selected tuple.
        selectedObjects = []
        for selected in selection:
            if selected in self.dirDict:
                selectedObjects.append(self.dirDict[selected])
            elif selected in self.fileDict:
                selectedObjects.append(self.fileDict[selected])
        return selectedObjects
    
    def refreshTree(self):
        """Refresh the directory tree with new data from root.rootDir."""
        # Clear existing tree
        self.tree.delete(*self.tree.get_children())
        
        # Reset dictionaries
        self.fileDict = {}
        self.dirDict = {}
        self.loaded = []
        self.emptyDict = {}
        
        # Get updated rootDir from root
        self.rootDir = self.root.rootDir
        
        # Update tree heading
        self.tree.heading('#0', text=self.rootDir.directory, anchor='w')
        
        # Recreate root node
        self.rootNode = self.tree.insert("", "end", text=self.rootDir.directory, open=True, image=self.openImg)
        
        # Repopulate tree
        self.addChildren(self.rootNode, self.rootDir)
        self.addFiles(self.rootNode)
        
        # Clear selection
        self.root.selected = []


class SettingsWindow(tk.Toplevel):
    """Settings window for managing application preferences."""
    
    def __init__(self, root: tk.Tk, resPath: str, indexPath: str, saveCallback, activeTab: str = "Paths"):
        super(SettingsWindow, self).__init__(root)
        self.root = root
        self.saveCallback = saveCallback
        self.resPath = resPath
        self.indexPath = indexPath
        
        self.title("Settings")
        self.minsize(650, 500)
        self.resizable(True, True)
        
        # Load unified preferences
        from __init__ import loadPreferences
        self.preferences = loadPreferences()
        if self.preferences:
            self.conversionSettings = self.preferences.get("conversions", {})
            self.fileTypeVisibility = self.preferences.get("fileTypeVisibility", {})
        else:
            self.conversionSettings = {}
            self.fileTypeVisibility = {}
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        pathsTab = ttk.Frame(self.notebook)
        visibilityTab = ttk.Frame(self.notebook)
        conversionsTab = ttk.Frame(self.notebook)
        
        self.notebook.add(pathsTab, text="Paths")
        self.notebook.add(visibilityTab, text="File Type Visibility")
        self.notebook.add(conversionsTab, text="Conversions")
        
        # Set active tab after all tabs are created
        if activeTab == "Conversions":
            self.notebook.select(conversionsTab)
        elif activeTab == "Visibility":
            self.notebook.select(visibilityTab)
        
        # ===== PATHS TAB =====
        pathsFrame = ttk.Frame(pathsTab, padding=10)
        pathsFrame.pack(fill=tk.BOTH, expand=True)
        
        # SharedCache Root Path Section
        sharedCacheLabel = ttk.Label(pathsFrame, text="EVE SharedCache Directory (you can find it in your launcher settings, it will have a ResFiles and tq folder in it):", font=("Arial", 10, "bold"))
        sharedCacheLabel.grid(column=0, row=0, sticky="W", pady=(0, 5))

        # Store the SharedCache root path instead of ResFiles path
        self.sharedCachePathVar = tk.StringVar(value=self.getSharedCacheFromResPath(self.resPath))
        sharedCacheEntry = ttk.Entry(pathsFrame, textvariable=self.sharedCachePathVar, width=60)
        sharedCacheEntry.grid(column=0, row=1, sticky="EW", padx=(0, 5))

        sharedCacheBrowseBtn = ttk.Button(pathsFrame, text="Browse...", command=self.browseSharedCachePath)
        sharedCacheBrowseBtn.grid(column=1, row=1)

        # Help text for SharedCache
        sharedCacheHelp = "Usually here: C:\\Program Files\\EVE\\SharedCache\n         or: C:\\EVE\\SharedCache"
        sharedCacheHelpLabel = ttk.Label(pathsFrame, text=sharedCacheHelp, font=("Arial", 8), foreground="gray")
        sharedCacheHelpLabel.grid(column=0, row=2, columnspan=2, sticky="W", pady=(2, 0))

        # Server Selection Section
        serverLabel = ttk.Label(pathsFrame, text="EVE Server Selection:", font=("Arial", 10, "bold"))
        serverLabel.grid(column=0, row=3, sticky="W", pady=(15, 5))

        # Server radio buttons
        self.serverVar = tk.StringVar(value=self.getServerFromIndexPath(self.indexPath))
        serverFrame = ttk.Frame(pathsFrame)
        serverFrame.grid(column=0, row=4, columnspan=2, sticky="W", pady=(0, 5))
        
        tqRadio = ttk.Radiobutton(serverFrame, text="Tranquility (TQ)", variable=self.serverVar, value="tq", command=self.updatePathsFromSelection)
        tqRadio.pack(side=tk.LEFT, padx=(0, 15))
        
        sisiRadio = ttk.Radiobutton(serverFrame, text="Singularity (Sisi)", variable=self.serverVar, value="sisi", command=self.updatePathsFromSelection)
        sisiRadio.pack(side=tk.LEFT, padx=(0, 15))
        
        thunderdomeRadio = ttk.Radiobutton(serverFrame, text="Thunderdome", variable=self.serverVar, value="thunderdome", command=self.updatePathsFromSelection)
        thunderdomeRadio.pack(side=tk.LEFT)

        # Auto-detected paths display (read-only)
        autoPathsLabel = ttk.Label(pathsFrame, text="Auto-detected paths:", font=("Arial", 9, "bold"))
        autoPathsLabel.grid(column=0, row=5, sticky="W", pady=(15, 5))

        # ResFiles path display
        resFilesDisplayLabel = ttk.Label(pathsFrame, text="ResFiles Path:", font=("Arial", 8))
        resFilesDisplayLabel.grid(column=0, row=6, sticky="W", pady=(2, 0))
        
        self.resPathVar = tk.StringVar(value=self.resPath)
        resPathDisplay = ttk.Entry(pathsFrame, textvariable=self.resPathVar, width=60, state='readonly')
        resPathDisplay.grid(column=0, row=7, sticky="EW", padx=(0, 5), pady=(0, 5))

        # Index path display
        indexDisplayLabel = ttk.Label(pathsFrame, text="Index File Path:", font=("Arial", 8))
        indexDisplayLabel.grid(column=0, row=8, sticky="W", pady=(2, 0))
        
        self.indexPathVar = tk.StringVar(value=self.indexPath)
        indexPathDisplay = ttk.Entry(pathsFrame, textvariable=self.indexPathVar, width=60, state='readonly')
        indexPathDisplay.grid(column=0, row=9, sticky="EW", padx=(0, 5))

        # Grid configuration
        pathsFrame.columnconfigure(0, weight=1)
        
        # Initialize paths based on current selection
        self.updatePathsFromSelection()
        
        # ===== FILE TYPE VISIBILITY TAB =====
        visibilityFrame = ttk.Frame(visibilityTab, padding=10)
        visibilityFrame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        visInstrLabel = ttk.Label(visibilityFrame, text="Show/Hide File Types in Tree:", font=("Arial", 10, "bold"))
        visInstrLabel.pack(anchor="w", pady=(0, 5))
        
        visInstrText = "Select which file types to show in the directory tree. Folders containing only hidden file types will also be hidden."
        visInstrLabel2 = ttk.Label(visibilityFrame, text=visInstrText, font=("Arial", 9))
        visInstrLabel2.pack(anchor="w", pady=(0, 10))
        
        # Buttons for Show All / Hide All
        buttonFrame = ttk.Frame(visibilityFrame)
        buttonFrame.pack(anchor="w", pady=(0, 10))
        
        showAllBtn = ttk.Button(buttonFrame, text="Show All", command=self.showAllFileTypes)
        showAllBtn.pack(side=tk.LEFT, padx=(0, 5))
        
        hideAllBtn = ttk.Button(buttonFrame, text="Hide All", command=self.hideAllFileTypes)
        hideAllBtn.pack(side=tk.LEFT)
        
        # Create canvas with scrollbar for checkboxes
        visCanvasFrame = ttk.Frame(visibilityFrame)
        visCanvasFrame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        visScrollbar = ttk.Scrollbar(visCanvasFrame)
        visScrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas for scrolling
        self.visCanvas = tk.Canvas(visCanvasFrame, yscrollcommand=visScrollbar.set, highlightthickness=0)
        self.visCanvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        visScrollbar.config(command=self.visCanvas.yview)
        
        # Frame inside canvas
        self.visScrollFrame = ttk.Frame(self.visCanvas)
        self.visCanvas.create_window((0, 0), window=self.visScrollFrame, anchor="nw")
        
        # Store checkbox variables
        self.visibilityVars = {}
        
        # Create checkboxes for each file type
        row = 0
        col = 0
        maxCols = 4  # Number of columns for checkbox layout
        
        # Sort file types alphabetically
        sortedFileTypes = sorted(self.fileTypeVisibility.keys())
        
        for fileType in sortedFileTypes:
            var = tk.BooleanVar(value=self.fileTypeVisibility[fileType])
            self.visibilityVars[fileType] = var
            
            cb = ttk.Checkbutton(self.visScrollFrame, text=fileType, variable=var)
            cb.grid(column=col, row=row, sticky="W", padx=10, pady=2)
            
            col += 1
            if col >= maxCols:
                col = 0
                row += 1
        
        # Update scroll region
        self.visScrollFrame.update_idletasks()
        self.visCanvas.config(scrollregion=self.visCanvas.bbox("all"))
        
        # Bind mousewheel
        def on_vis_mousewheel(event):
            if self.visCanvas.winfo_exists():
                self.visCanvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_vis_mousewheel(event):
            self.visCanvas.bind_all("<MouseWheel>", on_vis_mousewheel)
        
        def unbind_vis_mousewheel(event):
            self.visCanvas.unbind_all("<MouseWheel>")
        
        self.visCanvas.bind("<Enter>", bind_vis_mousewheel)
        self.visCanvas.bind("<Leave>", unbind_vis_mousewheel)
        
        # ===== CONVERSIONS TAB =====
        conversionsFrame = ttk.Frame(conversionsTab, padding=10)
        conversionsFrame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instrLabel = ttk.Label(conversionsFrame, text="File Type Export Settings:", font=("Arial", 10, "bold"))
        instrLabel.pack(anchor="w", pady=(0, 5))
        
        instrText = "Select export behavior for each file type."
        instrLabel2 = ttk.Label(conversionsFrame, text=instrText, font=("Arial", 9))
        instrLabel2.pack(anchor="w", pady=(0, 10))
        
        # Create canvas with scrollbar for radio buttons
        canvasFrame = ttk.Frame(conversionsFrame)
        canvasFrame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(canvasFrame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas for scrolling
        self.convCanvas = tk.Canvas(canvasFrame, yscrollcommand=scrollbar.set, highlightthickness=0)
        self.convCanvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.convCanvas.yview)
        
        # Frame inside canvas
        self.convScrollFrame = ttk.Frame(self.convCanvas)
        self.convCanvas.create_window((0, 0), window=self.convScrollFrame, anchor="nw")
        
        # Store radio variables
        self.convRadioVars = {}
        
        # Create radio buttons for each file type - one row per file type
        # Put "ALL FILES" first, then sort the rest
        row = 0
        
        # Sort items but keep "ALL FILES" at the top
        sortedItems = sorted(self.conversionSettings.items())
        orderedItems = []
        
        # Find and add "ALL FILES" first
        for item in sortedItems:
            if item[0] == "ALL FILES":
                orderedItems.insert(0, item)
            else:
                orderedItems.append(item)
        
        for fileType, settings in orderedItems:
            # File type label
            fileLabel = ttk.Label(self.convScrollFrame, text=fileType, font=("Arial", 9, "bold"))
            fileLabel.grid(column=0, row=row, sticky="W", pady=2, padx=(5, 15))
            
            # Create radio variable
            radioVar = tk.StringVar(value=settings["State"])
            self.convRadioVars[fileType] = radioVar
            
            # Create radio buttons for each option in the same row
            col = 1
            for option in settings["Options"]:
                rb = ttk.Radiobutton(self.convScrollFrame, text=option, variable=radioVar, value=option,
                                    command=lambda ft=fileType: self.updateConversionSetting(ft))
                rb.grid(column=col, row=row, sticky="W", padx=5)
                col += 1
            
            row += 1
        
        # Update scroll region
        self.convScrollFrame.update_idletasks()
        self.convCanvas.config(scrollregion=self.convCanvas.bbox("all"))
        
        # Bind mousewheel only when mouse is over the canvas
        def on_mousewheel(event):
            if self.convCanvas.winfo_exists():
                self.convCanvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(event):
            self.convCanvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            self.convCanvas.unbind_all("<MouseWheel>")
        
        self.convCanvas.bind("<Enter>", bind_mousewheel)
        self.convCanvas.bind("<Leave>", unbind_mousewheel)
        
        # Unbind when window closes
        self.protocol("WM_DELETE_WINDOW", lambda: [unbind_mousewheel(None), self.destroy()])
        
        # ===== BOTTOM BUTTONS =====
        buttonFrame = ttk.Frame(self, padding=(10, 0, 10, 10))
        buttonFrame.pack(fill=tk.X)
        
        saveBtn = ttk.Button(buttonFrame, text="Save", command=self.save)
        saveBtn.pack(side=tk.LEFT, padx=5)
        
        cancelBtn = ttk.Button(buttonFrame, text="Cancel", command=self.destroy)
        cancelBtn.pack(side=tk.LEFT, padx=5)
        
        # Center the window
        self.transient(root)
        self.grab_set()
    
    def getSharedCacheFromResPath(self, resPath):
        """Extract SharedCache path from ResFiles path."""
        if resPath and "SharedCache" in resPath:
            # Find SharedCache in the path and get everything up to and including it
            sharedCacheIndex = resPath.find("SharedCache")
            if sharedCacheIndex != -1:
                return resPath[:sharedCacheIndex + len("SharedCache")]
        return ""
    
    def getServerFromIndexPath(self, indexPath):
        """Extract server type from index path."""
        if indexPath:
            if "\\tq\\" in indexPath or "/tq/" in indexPath:
                return "tq"
            elif "\\sisi\\" in indexPath or "/sisi/" in indexPath:
                return "sisi"
            elif "\\thunderdome\\" in indexPath or "/thunderdome/" in indexPath:
                return "thunderdome"
        return "tq"  # Default to TQ
    
    def updatePathsFromSelection(self):
        """Update ResFiles and Index paths based on SharedCache path and server selection."""
        from __init__ import findCacheDirectory, findIndexFile
        
        sharedCachePath = self.sharedCachePathVar.get()
        server = self.serverVar.get()
        
        if sharedCachePath:
            # Try to find a valid cache directory if user selected a parent folder
            cacheDir = findCacheDirectory(sharedCachePath)
            if cacheDir and cacheDir != sharedCachePath:
                # User selected a parent folder, update to the actual cache folder
                sharedCachePath = cacheDir
                self.sharedCachePathVar.set(cacheDir)
                print(f"Auto-detected cache directory: {cacheDir}")
            
            # Update ResFiles path
            resFilesPath = os.path.join(sharedCachePath, "ResFiles")
            self.resPathVar.set(resFilesPath)
            
            # Try to find index file automatically first
            foundIndex = findIndexFile(sharedCachePath)
            if foundIndex:
                self.indexPathVar.set(foundIndex)
                print(f"Auto-detected index file: {foundIndex}")
            else:
                # Fallback to selected server
                indexPath = os.path.join(sharedCachePath, server, "resfileindex.txt")
                self.indexPathVar.set(indexPath)
            
            # Validate paths and show status
            self.validatePaths()

    def validatePaths(self):
        """Validate that the generated paths exist and show status."""
        resPath = self.resPathVar.get()
        indexPath = self.indexPathVar.get()
        
        # Check if paths exist (this could be used for UI feedback in the future)
        resExists = os.path.isdir(resPath) if resPath else False
        indexExists = os.path.isfile(indexPath) if indexPath else False
        
        # For now, just ensure the paths are set
        # Future enhancement: could add status labels to show validation results
        return resExists and indexExists

    def browseSharedCachePath(self):
        """Open file browser for SharedCache directory."""
        path = filedialog.askdirectory(
            parent=self,
            initialdir=self.sharedCachePathVar.get() or "/",
            title="Please select the EVE SharedCache directory.",
            mustexist=True
        )
        if path:
            self.sharedCachePathVar.set(os.path.realpath(path))
            self.updatePathsFromSelection()

    def showAllFileTypes(self):
        """Show all file types."""
        for var in self.visibilityVars.values():
            var.set(True)
    
    def hideAllFileTypes(self):
        """Hide all file types."""
        for var in self.visibilityVars.values():
            var.set(False)
    
    def updateConversionSetting(self, fileType):
        """Update conversion setting when radio button is changed."""
        newState = self.convRadioVars[fileType].get()
        self.conversionSettings[fileType]["State"] = newState
    
    def save(self):
        """Save the settings and close the window."""
        from __init__ import savePreferences
        
        self.resPath = self.resPathVar.get()
        self.indexPath = self.indexPathVar.get()
        
        # Update preferences with all settings
        self.preferences["paths"]["resPath"] = self.resPath
        self.preferences["paths"]["indexPath"] = self.indexPath
        self.preferences["conversions"] = self.conversionSettings
        
        # Update file type visibility from checkboxes
        for fileType, var in self.visibilityVars.items():
            self.preferences["fileTypeVisibility"][fileType] = var.get()
        
        # Save to unified preferences file
        savePreferences(self.preferences)
        
        # Call the callback for path updates (triggers reload if needed)
        self.saveCallback(self.resPath, self.indexPath)
        self.destroy()
