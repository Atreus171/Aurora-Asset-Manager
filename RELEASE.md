# Release Notes

## v1.5.1 (Latest) - "Download Queue Release"

### ✨ New Features
- **Persistent download queue** with background worker thread:
  - Click "Baixar assets" multiple times → jobs stack up and process sequentially
  - Global progress bar shows `[3/12] Game Name (TID)` for current job
  - UI stays fully responsive during downloads
  - "Cancelar" clears pending queue + stops current job
  - Button labels never change (no "Baixando..." text swap)

### 🔧 Improvements
- Sequential processing = zero rate-limit risk (x360db/XboxUnity friendly)
- Each queued job remembers its own asset types (boxart, background, etc.)
- Cancel drains queue instantly without waiting for current file

---

## v1.5.0 - "Game Management & Homebrew Fixes Release"

### ✨ New Features
- **Redesigned "Adicionar jogos" dialog**:
  - Auto-detects Title ID from `.xex` (real TID for XBLA/retail, synthetic for homebrew)
  - Auto-fills game name from folder/XEX filename
  - Title ID field moved below Name (optional when detected)
  - "Criar pasta GameData no HD" checkbox creates folder structure on disk
- **"Pasta para procurar jogos"** (batch add):
  - Select a parent folder (e.g., `X:\homebrew`) → scans subfolders with `.xex`
  - Ignores `Media/Managed` subfolders, depth limit 4
  - One game per subfolder, auto TID + name
- **"Gerenciar pastas..."** button:
  - Lists all folders added via batch add
  - Open folder in Explorer / remove selected (also removes associated games)
  - Persisted in `aurora_covers_added_folders.json`
- **ICO file support**: Import `.ico` files for custom covers/icons → auto-converted to PNG
- **Sort button (A-Z/Z-A)** relocated next to "Adicionar jogos" for quick access

### 🔧 Improvements
- **GameData auto-creation**: `gamedata_dir(create=True)` creates `Data\GameData` if missing when "Criar pasta GameData" checked
- **Enhanced "Abrir pasta do jogo"**: Tries multiple locations in order:
  1. Game's registered folder
  2. GameData subfolder (`TID_Name` or `TID`)
  3. content.db Directory path (resolved via ScanPaths/MountedDevices)
  4. Common game roots: `homebrew`, `jogos`, `emuladores`, `360`, `Games` (case-insensitive)
  5. Aurora root folder fallback
- **Homebrew names**: Merge logic prefers Aurora DB `TitleName` over XEX folder basename; auto-triggers Unity name fetch for weak/folder-like names
- **Unity covers case bug fix**: RetroArch (TitleID `00000000`) now works — `CoverInfo.php` returns key `Covers` (capital C), not `covers`
- **Search title updates content.db**: "Pesquisar título..." writes renamed game to `content.db` via `db_rename_by_tid` (Aurora sees change on rescan)
- **Fixed misleading logs**: Removed "using x360db as fallback" messages when repo=XboxUnity; now shows source-specific messages
- **Case-insensitive dedup**: Homebrews scanned by DB (lowercase paths) and XEX (original case) no longer duplicate
- **Container folder fix**: `X:\homebrew` (loose `.xex` at root) no longer appears as a game; internal games restored

### 🐛 Bug Fixes
- Fixed: "homebres" container game appearing when loose `.xex` at homebrew root
- Fixed: `Media\Managed` assemblies showing as games (e.g., `X:\homebrew\Granny - 1.2.1\Media\Managed`)
- Fixed: Duplicate homebrews from DB (lowercase) vs XEX scan (mixed case) — e.g., `supermariowar` vs `SuperMarioWar`
- Fixed: RetroArch covers not found (Unity `covers()` returned `[]` for `00000000`, fallback key was lowercase `covers`)
- Fixed: Negative/invalid TitleIds from DB (`-3F216667` for Xexmenu) now generate valid synthetic TIDs
- Fixed: `search_title` only updated display name, not `content.db`
- Fixed: `open_game_folder` failed for many games (only checked `g["folder"]`)

### 📦 Assets
- `AuroraAssetManager.exe` (~19.8 MB) - Windows x64 standalone (onefile)
- `AuroraAssetManager/` folder - Windows x64 onedir build (faster startup)
- `AuroraAssetManager_fast.zip` - onefile compressed

---

## v1.4.0 - "SQLite Integration Release"

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