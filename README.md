# Aurora Asset Editor

Aplicativo Windows (Tkinter) para escanear jogos do Aurora (Xbox 360), baixar capas/assets do x360db/XboxUnity e instalar no Aurora.

## Funcionalidades

- **Escaneia** `Data\GameData` do Aurora e lista jogos (TID + nome)
- **Baixa capas** do x360db (principal) e XboxUnity (fallback/alternativas)
- **Instala** assets no formato Aurora: `Data\GameData\{TID}_{Nome}\{GC|BK|GL|SS}{TID}.asset`
- **Fallback** em `User\Import\{TID}\*.png` se GameData não for gravável
- **Preview** em tempo real (paisagem, sem corte)
- **Ordenação**: sem-capa primeiro, alfabético, botão A-Z/Z-A
- **Renomear jogo** via menu de contexto (renomeia pasta GameData)
- **Envio FTP** para o console (estilo Aurora Asset Editor)
- **Navegação** entre screenshots instaladas (◀/▶)
- **Status "Instalado"** baseado em preview real (arquivo vazio/corrompido = Ausente)
- **Temas** claro/escuro
- **Log** visível em monitores 720p (geometria adaptativa)

## Build

```bash
python -m py_compile aurora_covers.py
python aurora_covers.py --selftest
python -m PyInstaller --noconfirm --onefile --windowed --name "AuroraAssetEditor" --clean --icon "assets/icon.ico" aurora_covers.py
```

Exe gerado em `dist\AuroraAssetEditor.exe`.

## Configuração

Arquivos de configuração salvos em `%USERPROFILE%\Documents\Aurora Asset Editor\`:

- `aurora_covers_config.json` — configurações do app
- `aurora_covers_games.json` — cache do índice x360db (12h)
- `aurora_covers_installed.json` — rastreador de assets instalados

Exemplo de `aurora_covers_config.json`:

```json
{
  "theme": "dark",
  "repo": "x360db",
  "cover_format": "paisagem",
  "screenshots": true,
  "lang": "pt",
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

## Fontes de dados

- **x360db** (padrão): índice de jogos + artwork (boxart, background, icon, banner, screenshots)
- **XboxUnity**: capas alternativas + thumbnails

## Requisitos

- Python 3.10+
- `pip install pillow requests`

## Licença

MIT