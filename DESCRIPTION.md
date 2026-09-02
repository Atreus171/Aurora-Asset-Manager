# Aurora Asset Manager - Description

## Overview
Aurora Asset Manager is a Windows application (Python/Tkinter) for managing Xbox 360 Aurora Dashboard assets. It scans your Aurora game library, downloads covers/artwork from multiple sources, and installs them in the proper Aurora format.

## Version 1.5.0 Highlights

### 🆕 New Game Management
- **Redesigned "Adicionar jogos" dialog**: Auto-detects TID from `.xex` (real TID for retail, synthetic for homebrew), auto-fills name, Title ID moved below Name
- **Batch add via folder**: "Pasta para procurar jogos" scans subfolders with `.xex` (ignores `Media/Managed`, depth ≤ 4)
- **Gerenciar pastas...**: View/remove added scan folders, persists in `aurora_covers_added_folders.json`
- **ICO support**: Import `.ico` files for custom covers/icons → auto-converted to PNG
- **Sort button (A-Z/Z-A)** relocated next to "Adicionar jogos"

### 🔧 Core Improvements
- **GameData auto-creation**: `gamedata_dir(create=True)` creates `Data\GameData` structure if missing
- **Enhanced "Abrir pasta do jogo"**: Tries game folder → GameData → content.db path → common roots (`homebrew`, `jogos`, `emuladores`, `360`, `Games`) → Aurora root
- **Unity covers case fix**: RetroArch (TitleID `00000000`) now works via `CoverInfo.php` (key `Covers` vs `covers`)
- **Search title updates content.db**: "Pesquisar título..." writes renamed game to `content.db` via `db_rename_by_tid`
- **Fixed misleading logs**: Removed "using x360db" messages when using XboxUnity
- **Homebrew names**: Prefers DB `TitleName` over XEX folder basename; auto-fetches Unity names for weak names
- **Case-insensitive dedup**: DB (lowercase) vs XEX (mixed case) homebrews no longer duplicate
- **Container folder fix**: `X:\homebrew` (loose `.xex`) no longer appears as game; internal games restored

## Key Features (All Versions)

### 🎮 Game Library Management
- **Auto-detection**: Scans `Data\GameData` folders or reads directly from Aurora's SQLite database (`content.db`) for real game names
- **Multiple name sources**: x360db, XboxUnity, Aurora database, folder names
- **Homebrew support**: Identifies and names homebrew/XBLA titles
- **Smart sorting**: No-cover first, alphabetical, A-Z/Z-A toggle

### 🖼️ Asset Download & Installation
- **Boxart (covers)**: Landscape/portrait formats
- **Backgrounds**: Full-screen backgrounds
- **Icons & Banners**: 64x64 icons, 420x95 banners
- **Screenshots**: Multiple per game
- **Multiple sources**: x360db (primary), XboxUnity (community covers), Xbox Marketplace
- **Fallback chain**: x360db → XboxUnity → local files

### 📁 Installation Options
- **Aurora format**: `Data\GameData\{TID}_{Name}\{GC|BK|GL|SS}{TID}.asset`
- **Import fallback**: `User\Import\{TID}\*.png` (when GameData not writable)
- **Backup before overwrite**: Optional .bak creation

### 🔧 Advanced Features
- **FTP upload**: Send assets directly to Xbox 360 via FTP
- **Custom covers**: Select local images (PNG/JPG/BMP/WebP/ICO), auto-convert to Aurora format
- **Alternative covers**: Browse XboxUnity community covers with preview
- **Rename games**: Updates display name AND content.db (v1.5.0+)
- **Persistent caches**: x360db index (12h), XboxUnity titles (indefinite)

### 🌐 Internationalization
- 6 languages: Portuguese, English, Spanish, French, Japanese, Russian
- Auto-detects system language
- Runtime language switching (requires restart)

### 🎨 UI/UX
- Dark/Light/System themes
- Adaptive window sizing (works on 720p+)
- Real-time preview panel
- Log panel with connection status
- Compact settings dialog (grid layout)

## Technical Details

### Supported Formats
- **Input**: PNG, JPG, JPEG, BMP, WebP, ICO (v1.5.0+)
- **Output**: Aurora .asset (DXT5 compressed via custom encoder)
- **Preview**: Real-time landscape (900x600) or portrait (900x1233)

### Sources
1. **x360db** (primary): https://github.com/xenia-manager/x360db
   - Game index (~12k titles), artwork, metadata
   - Cached locally for 12 hours
2. **XboxUnity** (community): https://xboxunity.net
   - Community covers, homebrew titles
   - Persistent title cache
   - Fixed case sensitivity for `CoverInfo.php` (v1.5.0+)
3. **Aurora SQLite** (local): `Aurora\Data\Databases\content.db`
   - Real game names as displayed in Aurora
   - Region info, paths, media IDs

### Requirements
- Windows 10/11
- Python 3.10+ (for source)
- Pillow, requests (auto-installed via requirements.txt)

### Build
```bash
pip install -r requirements.txt
python -m py_compile aurora_covers.py
python aurora_covers.py --selftest
python -m PyInstaller --noconfirm --onefile --windowed --name "AuroraAssetManager" --clean --icon "assets/icon.ico" aurora_covers.py
```
Output: `dist\AuroraAssetManager.exe` (~19 MB)

## License
MIT License - see LICENSE file