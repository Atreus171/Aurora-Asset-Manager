<p align="center">
  <img src="assets/icon.ico" width="128" height="128" alt="Aurora Asset Manager Logo">
</p>

<h1 align="center">Aurora Asset Manager</h1>

<p align="center">
  <strong>Windows tool for managing Xbox 360 Aurora Dashboard assets</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#sources">Data Sources</a> •
  <a href="#building">Building</a> •
  <a href="RELEASE.md">Changelog</a> •
  <a href="LICENSE">License</a>
</p>

---

## 🎯 Overview

**Aurora Asset Manager** is a Windows application that helps you manage artwork for your Xbox 360 Aurora Dashboard game library. It scans your games, downloads high-quality covers and assets from multiple sources, and installs them in the exact format Aurora expects.

Perfect for: **homebrew collectors**, **XBLA enthusiasts**, **Aurora users** wanting complete artwork.

---

## ✨ Features

### 🎮 Game Library
| Feature | Description |
|---------|-------------|
| **Multi-source scanning** | Reads `Data\GameData` folders **or** Aurora's SQLite database (`content.db`) |
| **Real game names** | Uses Aurora's own database for exact display names |
| **Homebrew support** | Detects XBLA/XNA/homebrew via XboxUnity community database |
| **Smart sorting** | No-cover first → alphabetical → A-Z/Z-A toggle |

### 🖼️ Asset Management
| Asset Type | Formats | Sources |
|------------|---------|---------|
| **Boxart (Cover)** | Landscape (900×600) / Portrait (900×1233) | x360db, XboxUnity, Marketplace |
| **Background** | Full-screen | x360db |
| **Icon** | 64×64 | x360db |
| **Banner** | 420×95 | x360db |
| **Screenshots** | Multiple per game (1-20) | x360db |

### ⚡ Installation
- **Aurora native**: `Data\GameData\{TID}_{Name}\{GC|BK|GL|SS}{TID}.asset`
- **Import fallback**: `User\Import\{TID}\*.png` (when GameData not writable)
- **Auto-backup**: Creates `.bak` before overwriting
- **FTP upload**: Send directly to Xbox 360 via FTP

### 🔍 Advanced
- **Alternative covers**: Browse XboxUnity community covers with live preview
- **Custom covers**: Pick any local image (PNG/JPG/BMP/WebP/ICO) → auto-convert to Aurora format
- **Screenshot navigation**: Prev/Next buttons for multi-screenshot games
- **Installed status**: Based on actual preview (empty/corrupt = Missing)

### 🆕 v1.5.0 Highlights
- **Add games dialog redesign**: Detects TID from `.xex` auto, creates GameData folder, adds "Folder to search games" option
- **Folder management**: "Manage folders..." button to view/remove added scan folders
- **ICO support**: Import `.ico` files as custom covers/icons (auto-converted to PNG)
- **Auto GameData creation**: `gamedata_dir(create=True)` creates `Data\GameData` structure if missing
- **Improved "Open folder"**: Tries game folder → GameData → content.db path → common roots (`homebrew`, `jogos`, `emuladores`, `360`, `Games`) → Aurora root
- **Unity covers case fix**: RetroArch (TitleID `00000000`) now works via `CoverInfo.php` (key `Covers` vs `covers`)
- **Search title updates DB**: "Pesquisar título" now writes renamed game to `content.db` via `db_rename_by_tid`
- **Fixed misleading logs**: Removed "using x360db" messages when using XboxUnity
- **Homebrew names**: Prefers DB `TitleName` over XEX folder basename; auto-fetches Unity names for weak/folder-like names
- **Sort button moved**: A-Z/Z-A now sits next to "Adicionar jogos"

---

## 📥 Installation

### Pre-built (Recommended)
1. Download latest `AuroraAssetManager.exe` from [Releases](https://github.com/Atreus171/Aurora-Asset-Manager/releases)
2. Run it — no installation needed

### From Source
```bash
# Requirements
pip install -r requirements.txt

# Test
python -m py_compile aurora_covers.py
python aurora_covers.py --selftest

# Run
python aurora_covers.py
```

---

## 🚀 Usage

### First Run
1. Launch `AuroraAssetManager.exe`
2. Click **Procurar...** and select your Aurora root folder (contains `Data\GameData`)
   - **Auto-detects** `Aurora\Data\Databases\content.db` for real names
3. Click **Escanear jogos** — list populates with TID + real names
4. Select games → choose assets → **Baixar e instalar assets**

### Auto-scan
After selecting the Aurora folder, scanning starts automatically.

### Adding Games (v1.5.0+)
**Individual .xex**:
1. Click **Adicionar jogos...** → select `.xex` file
2. TID auto-detected (real TID from XEX, synthetic for homebrew)
3. Name auto-filled from folder/XEX
4. Title ID field now below Name (optional if detected)
5. Check "Criar pasta GameData no HD" to create folder on disk

**Batch via folder**:
1. Click **Adicionar jogos...** → "Pasta para procurar jogos"
2. Select a parent folder (e.g., `X:\homebrew`)
3. App scans subfolders with `.xex` (ignores `Media/Managed`, depth ≤ 4)
4. Each game added with auto TID + name
5. View/remove added folders via **Gerenciar pastas...**

### Alternative Covers
1. Right-click a game → **Capas alternativas online...**
2. Browse community covers with preview
3. Select → **Baixar e instalar esta capa**

### Custom Cover
1. Right-click a game → **Capa personalizada...**
2. Select any image (PNG/JPG/BMP/WebP/ICO)
3. Auto-converts to your chosen format (landscape/portrait)

### FTP to Console
1. Settings → **FTP** → enter Xbox IP (user: `xbox`, pass: `xbox`)
2. In Assets dialog → **Enviar por FTP**
3. Uploads all `.asset` files to `Hdd:\Aurora\Data\GameData\{TID}_{Name}\`

### Search Title (v1.5.0+)
1. Right-click a game → **Pesquisar título...**
2. Searches x360db + XboxUnity
3. If found, updates display name **AND** writes to `content.db` (Aurora sees new name on rescan)

---

## 🌐 Data Sources

| Source | Type | Coverage | Cache |
|--------|------|----------|-------|
| **x360db** | Primary | ~12k titles, official artwork, metadata | 12h (local JSON) |
| **XboxUnity** | Community | Homebrew, XBLA, indie, alt covers | Persistent (local JSON) |
| **Aurora SQLite** | Local | Your exact library with custom names | Real-time |
| **Xbox Marketplace** | Official | Official assets (via x360db links) | On-demand |

### Priority Chain
```
Game name: Aurora DB → x360db → XboxUnity → Folder suffix → TID
Boxart:    x360db → XboxUnity → Marketplace fallback
```

---

## ⚙️ Configuration

Settings saved in `%USERPROFILE%\Documents\Aurora Asset Manager\`:
- `aurora_covers_config.json` — app settings
- `aurora_covers_games.json` — x360db index cache (12h TTL)
- `aurora_covers_unity_titles.json` — XboxUnity title cache (persistent)
- `aurora_covers_installed.json` — asset install tracker
- `aurora_covers_extra_games.json` — manually added TIDs
- `aurora_covers_custom_names.json` — custom display names
- `aurora_covers_hidden.json` — hidden game TIDs
- `aurora_covers_added_folders.json` — folders added via "Pasta para procurar jogos" (v1.5.0+)

### Example Config
```json
{
  "theme": "dark",
  "repo": "x360db",
  "cover_format": "paisagem",
  "screenshots": 6,
  "lang": "pt",
  "show_status": true,
  "show_log": true,
  "ftp_host": "192.168.1.100",
  "ftp_port": 21,
  "ftp_user": "xbox",
  "ftp_pass": "xbox",
  "ftp_base": "Hdd:\\Aurora\\Data\\GameData"
}
```

---

## 🖥️ Requirements

| Component | Version |
|-----------|---------|
| Windows | 10/11 (x64) |
| Python (source) | 3.10+ |
| Pillow | 10+ |
| requests | 2.31+ |

---

## 🏗️ Building

```bash
# Install deps
pip install -r requirements.txt

# Verify
python -m py_compile aurora_covers.py
python aurora_covers.py --selftest

# Build single-file exe (release, slower first start)
python -m PyInstaller --noconfirm --onefile --windowed \
  --name "AuroraAssetManager" --clean \
  --icon "assets/icon.ico" --add-data "assets/icon.ico;." aurora_covers.py
# Output: dist/AuroraAssetManager.exe (~19 MB)

# Build folder build (faster startup, recommended for daily use)
python -m PyInstaller --noconfirm --onedir --windowed \
  --name "AuroraAssetManager" --clean \
  --icon "assets/icon.ico" --add-data "assets/icon.ico;." aurora_covers.py
# Output: dist/AuroraAssetManager/ (exe + _internal folder)
```

---

## 🌍 Languages

| Code | Language | Status |
|------|----------|--------|
| `pt` | Português | ✅ Complete |
| `en` | English | ✅ Complete |
| `es` | Español | ✅ Complete |
| `fr` | Français | ✅ Complete |
| `ja` | 日本語 | ✅ Complete |
| `ru` | Русский | ✅ Complete |

Auto-detects system language on first run (fallback: English).

---

## 📁 Project Structure

```
aurora-x360db-covers/
├── aurora_covers.py        # Main application
├── assets/
│   └── icon.ico            # App icon
├── AuroraCoversX360db.spec # PyInstaller spec
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── DESCRIPTION.md          # Detailed description
├── RELEASE.md              # Changelog
├── LICENSE                 # MIT License
├── aurora_covers_config.json.example
└── .gitignore
```

---

## 🤝 Credits

- **x360db** by [xenia-manager](https://github.com/xenia-manager/x360db) — game database & artwork
- **XboxUnity** by [XboxUnity](https://xboxunity.net) — community covers
- **Aurora Dashboard** by Team Aurora
- **libaustralis** by [jrobiche](https://github.com/jrobiche/libaustralis) — asset format reference
- **Icon** by [Atreus171](https://github.com/Atreus171)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.