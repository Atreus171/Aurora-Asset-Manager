# Game Covers (assets locais)

Pasta **não distribuída no executável** — funciona apenas ao rodar por código (`python aurora_covers.py`).

## Estrutura recomendada (nome + TID)

```
game_covers/
  <Nome do Jogo>_<TID>/
    cover.png          # capa (boxart)
    background.png     # fundo
    banner.png         # banner
    tile.png           # tile
    icon.png           # ícone
    screenshots/
      1.png
      2.png
      ...
```

- `<Nome do Jogo>` = nome do jogo (ex: `Halo 3`, `Gears of War`). Caracteres inválidos em nome de pasta (`\ / : * ? " < > |`) são convertidos para `_`.
- `<TID>` = TitleID do jogo em **8 hex maiúsculos** (ex: `4D5309E7`).
- O app casa a pasta se o final for `_<TID>` (case-insensitive no TID).

## Estruturas alternativas (fallback)

```
game_covers/
  <TID>/                    # apenas TID (ex: 4D5309E7)
  <HomebrewID>/             # TID sintético SHA1 do nome (para homebrews)
  <NomeDoJogo>.jpg          # arquivo solto por nome (só capa)
  <TID>.png                 # arquivo solto por TID
```

## Prioridade de busca

1. Pasta `<Nome>_<TID>/`
2. Pasta `<TID>/`
3. Pasta `<HomebrewID>/` (TID sintético SHA1 do nome)
4. Arquivo solto `<TID>.<ext>`
5. Arquivo solto `<Nome>.<ext>` (só capa)

## Assets suportados

- `cover.png/.jpg` → capa (boxart)
- `background.png/.jpg` → background
- `banner.png` → banner
- `tile.png` → tile
- `icon.png` → ícone
- `screenshots/*.png|.jpg` → screenshots

## Log

Quando um asset local é encontrado, aparece no log:
```
[LOG]  game_cover_ok: cover.png
```