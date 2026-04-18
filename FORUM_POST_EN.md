FL Atlas - Freelancer Modding Suite
===================================

FL Atlas is a desktop tool for Freelancer that brings several common modding workflows together in one application. The goal is not just editing isolated files, but supporting connected workflows directly inside one central editor.

Download links:
- GitHub: https://github.com/flathack/FLAtlas
- ModDB: https://www.moddb.com/games/freelancer/downloads/fl-atlas-visual-freelancer-editor-for-systems-modding-and-ids-workflows

Companion projects:
- FL Lingo: https://www.moddb.com/games/freelancer/downloads/fl-lingo-a-freelancer-translator
- Savegame Editor: https://www.moddb.com/games/freelancer/downloads/flatlas-savegame-editor
- FL Atlas Launcher: https://github.com/flathack/FL-Atlas-Launcher

Project Focus
=============

FL Atlas is aimed at Freelancer modders who want to:

- edit systems and universe data visually
- create or adjust bases, zones, objects, and connections faster
- manage DLL text, infocards, and file references centrally
- stop relying on a plain text editor for large INI files
- inspect 3D models, character assets, and base compositions directly inside the tool

In the current development range from `v0.6.9 -> v0.7.0`, large parts of FL Atlas were expanded, unified, and hardened.

Version Changelog
=================

## v0.6.9 -> v0.7.0

### Highlights
- `File Explorer` and `IDS Editor` were pushed further as core workflows.
- The `Time Machine` now shows real diffs with side-by-side mode, inline mode, minimap markers, a revision timeline, and compact section-based display.
- The new `Clipboard Collector` gathers copied text and file paths, stays open as its own utility window, and can paste selected snippets back into the editor.
- Creation dialogs for objects, weapon platforms, wrecks, depots, and bases now have much stronger embedded 3D previews.
- Base editing now uses a true edit mode with clearer separation between general data and base-loadout content.
- Tool management in the menu bar and settings was reorganized through `Pinned Tools` and `FL Atlas Suite Apps`.

### Resolved GitHub Issues (24)
- `#4` Patrol-zone defaults for path-based encounters
- `#6` New starsphere files were missing from background selection lists
- `#10` Time Machine diff view overhaul
- `#11` Clipboard Collector for the File Editor
- `#12` Wrong `dock_with` links on planetary base edits
- `#13` Base Builder should not be usable on planets / docking rings
- `#16` Newly created systems should open as a separate tab
- `#17` Prefill planet deathzone and atmosphere from planet size
- `#19` Multiple problems in the docking-ring base creation workflow
- `#20` Show `[Zone]` / `[Object]` headers in the 2D object editor
- `#23` 3D previews in creation dialogs
- `#25` Hover artifacts in 2D system and universe views
- `#26` 2D system creation buttons squeezed together on small windows
- `#27` Create `ids_info` directly in the planet creation dialog
- `#28` Tabs could only be dragged one neighbor at a time
- `#32` Linux: wrong orientation for some child parts in 3D
- `#35` 2D object editing should also support `ids_info`
- `#36` Old user configs keep outdated tab names
- `#37` Base edit dialog rework
- `#40` Preserve zoom/camera when switching system tabs
- `#46` Select and copy whole sections in the File Editor
- `#50` Main-tab and suite-tool management in settings
- `#52` Free Cam `A`/`D` mismatch
- `#54` Wrong tradelane ring count after changing endpoints

### Selected Workflow Changes
- `Time Machine`:
  - side-by-side and inline diff
  - word-level highlights
  - diff minimaps with clear markers
  - revision timeline with visible segmentation and date display
  - only changed sections stay expanded while untouched areas are compacted
- `Clipboard Collector`:
  - automatically captures normal editor `Copy`
  - can also store selected file paths from the explorer
  - `Paste`, `Remove`, `Clear all`, `Close`
  - non-modal, always-on-top, semi-transparent when unfocused
- 2D system view:
  - more compact right sidebar
  - more stable hover rendering
  - better object and section editing workflows
  - per-tab zoom and camera state is preserved
- Creation and edit dialogs:
  - larger 3D previews
  - base dialog with a dedicated right-side preview area
  - expanded `ids_info` workflows for planets and objects
- Settings / menus:
  - `IDS Editor` replaces `Name & Info Editor`
  - `Pinned Tools`
  - `FL Atlas Suite Apps`
  - web apps shown in one row with an internet marker

### Short Summary
The step from `v0.6.9` to `v0.7.0` was mainly about strengthening everyday editor workflows: better diffs, better previews, less UI friction, more stable system tabs, and many more direct actions inside the file editor.
