# Aurora Asset Manager - Description

## Overview
Aurora Asset Manager is a Windows application (Python/Tkinter) for managing Xbox 360 Aurora Dashboard assets. It scans your Aurora game library, downloads covers/artwork from multiple sources, and installs them in the proper Aurora format.

## Key Features

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
- **Custom covers**: Select local images, auto-convert to Aurora format
- **Alternative covers**: Browse XboxUnity community covers with preview
- **Rename games**: Updates GameData folder name
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
- **Input**: PNG, JPG, JPEG, BMP, WebP
- **Output**: Aurora .asset (DXT5 compressed via custom encoder)
- **Preview**: Real-time landscape (900x600) or portrait (900x1233)

### Sources
1. **x360db** (primary): https://github.com/xenia-manager/x360db
   - Game index (~12k titles), artwork, metadata
   - Cached locally for 12 hours
2. **XboxUnity** (community): https://xboxunity.net
   - Community covers, homebrew titles
   - Persistent title cache
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