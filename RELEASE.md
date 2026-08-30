# Release Notes

## v1.4.0 (Current) - "SQLite Integration Release"

### ✨ New Features
- **Aurora SQLite Database Reading**: Automatically detects and reads `Aurora\Data\Databases\content.db` for real game names, regions, and paths
- **Homebrew Detection**: Improved identification of homebrew/XBLA titles with XboxUnity fallback
- **XboxUnity Persistent Title Cache**: Local JSON cache (`aurora_covers_unity_titles.json`) for instant homebrew name lookup
- **Multi-language Support**: Portuguese, English, Spanish, French, Japanese, Russian with auto-detection
- **FTP Upload**: Send assets directly to Xbox 360 via FTP (Aurora Asset Editor style)

### 🔧 Improvements
- **Startup Optimization**: Lazy-loading of X360DB/XboxUnity, async config loading, deferred theme
- **UI Responsiveness**: Removed sync HTTP calls from tree refresh, fixed freeze issues
- **Settings Dialog**: Compact two-column grid layout, fixed duplicate buttons
- **Selection Preservation**: Maintains game selection after alt-cover install
- **Auto-scan**: Starts scanning automatically after folder selection

### 🐛 Bug Fixes
- Fixed rename_game to properly handle folder renames
- Fixed alt_covers installing to wrong game when selection changed
- Fixed status_saved log formatting (removed region parameter)
- Fixed duplicate frame in settings dialog
- Fixed cover_missing_both log format
- Fixed locale detection deprecation warning

### 📦 Assets
- `AuroraAssetManager.exe` (~19 MB) - Windows x64 standalone

---

## v1.3.0 - "Multi-source Release"

### ✨ New Features
- **XboxUnity Integration**: Community covers as fallback/alternative source
- **Alternative Covers Dialog**: Browse, preview, and install community covers
- **Screenshot Navigation**: Prev/Next buttons for multi-screenshot games
- **Installed Status**: Based on actual preview (empty/corrupt = Missing)
- **Region Support**: Configurable region (stored for future API support)

### 🔧 Improvements
- Landscape preview default (900x600)
- A-Z/Z-A sort toggle
- Game rename via context menu
- Custom cover with local file picker
- Screenshots per game setting (0-20)

---

## v1.2.0 - "Asset Management Release"

### ✨ New Features
- Background, Icon, Banner download/install
- Screenshots support (multiple per game)
- FTP upload to console
- Asset viewer dialog with per-type status
- Backup before overwrite option

---

## v1.1.0 - "Core Release"

### ✨ New Features
- x360db integration (index + artwork)
- Boxart download/install (portrait/landscape)
- GameData folder scanning
- Theme support (dark/light/system)
- Log panel with connection status

---

## v1.0.0 - Initial Release

Basic Aurora cover downloader with x360db source.