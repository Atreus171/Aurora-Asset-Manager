# Aurora Asset Manager

Windows (Tkinter) application to scan Aurora games (Xbox 360), download covers/assets from x360db/XboxUnity, and install them into Aurora.

## Features

- **Scans** `Data\GameData` and lists games (TitleID + name)
- **Downloads covers** from x360db (primary) and XboxUnity (fallback/alternatives)
- **Installs** assets in Aurora format: `Data\GameData\{TID}_{Name}\{GC|BK|GL|SS}{TID}.asset`
- **Fallback** to `User\Import\{TID}\*.png` if GameData is not writable
- **Real-time preview** (landscape, no cropping)
- **Sorting**: no-cover first, alphabetical, A-Z/Z-A toggle
- **Rename game** via context menu (renames GameData folder)
- **FTP upload** to console
- **"Installed" status** based on actual preview (empty/corrupt file = Missing)

## Build

```bash
python -m py_compile aurora_covers.py
python aurora_covers.py --selftest
python -m PyInstaller --noconfirm --onefile --windowed --name "AuroraAssetManager" --clean --icon "assets/icon.ico" aurora_covers.py
```

Exe generated at `dist\AuroraAssetManager.exe`.

## Configuration

Config files saved in `%USERPROFILE%\Documents\Aurora Asset Manager\`:

- `aurora_covers_config.json` — app settings
- `aurora_covers_games.json` — x360db index cache (12h TTL)
- `aurora_covers_installed.json` — installed assets tracker

Example `aurora_covers_config.json`:

```json
{
  "theme": "dark",
  "repo": "x360db",
  "cover_format": "landscape",
  "screenshots": true,
  "lang": "en",
  "show_status": true,
  "show_log": true,
  "region": "all",
  "ftp_host": "",
  "ftp_port": 21,
  "ftp_user": "xbox",
  "ftp_pass": "xbox",
  "ftp_base": "Hdd:\\Aurora\\Data\\GameData"
}
```

## Data Sources

- **x360db** (default): game index + artwork (boxart, background, icon, banner, screenshots)
- **XboxUnity**: alternative covers + thumbnails

## Requirements

- Python 3.10+
- `pip install pillow requests`

## License

MIT