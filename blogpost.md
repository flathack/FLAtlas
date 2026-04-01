# FL Atlas v0.6.8

v0.6.8 has been released, and this update focuses on workflow polish, safer updating, and making several editor areas much more reliable in day-to-day modding work.

## New in v0.6.8

### Better Zone Population Editing

- The Zone Population editor now follows Freelancer rules much more closely.
- Encounters and factions are validated with better limits and clearer defaults.
- New zones get smarter starting values depending on whether they behave more like patrol zones, trade zones, or field zones.
- The dialog now explains values like encounter level, spawn chance, and faction weight directly in the UI.

### Smarter Links Inside the App

- The Discord link is no longer a hardcoded invite that can expire unnoticed.
- FL Atlas now resolves the Discord invite through the GitHub wiki.
- The old built-in help view has been removed and replaced with a direct link to the FL Atlas wiki.

### Safer Auto Update Behavior

- The Windows self-update flow has been improved.
- Asset selection is now more robust, especially when a release contains multiple downloadable files.
- Invalid downloads are detected more cleanly.
- Error messages for broken update packages are now clearer and less confusing.

### Startup Update Check Is Less Annoying

- The automatic update check no longer jumps in too early during startup.
- It now runs after the app has fully opened, so update dialogs should not get stuck behind the splash screen anymore.

## More Improvements Included

### Base Builder and Base Workflows

- Added parts now refresh more reliably in the Base Builder preview.
- The newest placed part now keeps its position correctly when saving and closing.
- Parent/child handling for base parts has been corrected.
- Child parts now consistently use the correct parent nickname and `visit = 0`.

### Jump Connections

- Jump holes and gates are now much more stable when systems are already open in dirty tabs.
- Several save-order problems that could make newly created jumps disappear have been fixed.

### File Editor Improvements

- The file tree now keeps its expanded state instead of collapsing all the time.
- The path to the selected file is visible and clickable like a breadcrumb/path bar.
- Archetype lines now support opening the related 3D model or jumping to the defining INI entry directly.
- The modified-date column was removed from the tree for a cleaner layout.

### 3D Viewer and Overlay Fixes

- Grid overlays and zones in the 3D viewer now stay visible more reliably.
- They no longer disappear just because another object is in front of them.

### Base NPC Improvements

- Copying NPCs from templates now preserves their actual appearance instead of forcing the benchmark defaults.
- Base creation and editing now include an option to randomize NPC head and body combinations.
- NPC room persistence is now closer to vanilla behavior.

### Cleaner Generated Files

- Generated zone INI files no longer contain unnecessary blank lines.
- Generated base room files were cleaned up as well.

## Overall Direction

This release is not about one giant headline feature. It is more about making FL Atlas behave better in real editing sessions.

That includes:

- fewer situations where newly created content disappears again
- fewer places where generated Freelancer data needs manual cleanup
- better in-editor guidance for values that are otherwise easy to misinterpret
- more reliable links, updates, and startup behavior

FL Atlas is still evolving quickly, and a lot of these changes come directly from building real systems, bases, zones, and file workflows inside the tool and fixing the friction along the way.
