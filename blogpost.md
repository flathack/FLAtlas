# FL Atlas v0.6.7

v0.6.7 has been released, and this update brings a large set of new features, improvements, and bug fixes.

## New in v0.6.7

### 3D Base Builder

- FL Atlas now understands bases and their child objects as connected structures.
- This makes building and editing bases much easier and more visual.
- Base-related workflows have been expanded significantly in both editing and previewing.

### Improved File and Text Editor for Freelancer

- The editor has been heavily upgraded and is becoming a true Freelancer-focused file explorer and text editor.
- It now supports tabs directly inside the explorer.
- Many workflows now feel closer to Visual Studio Code, but tailored for Freelancer modding.
- Changes inside files are highlighted visually.
- After saving, you can inspect the history of each file.
- File history is currently stored inside the mod folder under `.flatlas`.
- The editor is designed to make jumping between related Freelancer files much faster and easier.

### Performance Improvements

- Large parts of the app have been optimized to reduce lag and improve responsiveness.
- Editing large files is now smoother.
- Several UI interactions and preview workflows have been cleaned up for better overall performance.

### 8x8 Grid Layout in 2D and 3D System View

- Both the 2D and 3D system views now support an 8x8 grid layout.
- This makes object placement and system structuring more consistent.

### 3D Character Viewer

- A new 3D Character Viewer has been added.
- This feature was originally created for the Savegame Editor and has now been brought into FL Atlas.

### Many Bug Fixes

- There are also many bug fixes in this release.
- Too many to list individually.
- FL Atlas is still in alpha, so a lot of bug fixing currently comes from actively building systems, bases, and other content and improving things along the way.

## About the Text Editor

I know working with Freelancer text files can be frustrating, especially because so many changes require editing multiple files at once. That is why I want to keep expanding this editor into a full Freelancer-focused editing environment.

The goal is to support workflows like:

- right-clicking lines and jumping directly to related content
- opening referenced files directly from INI entries
- moving through connected game data much faster than with a normal text editor

My aim is to offer an editing experience that feels similar to Visual Studio Code, but optimized specifically for Freelancer modding.

I am not deeply active as a mod creator myself. I understand how the game files and systems work, but I spend more time building tools than making full mods. Because of that, feature requests for the INI/File Editor are very welcome.
