# Game Covers (covers do repositório)

As covers deste repositório são **baixadas individualmente** do próprio repositório GitHub
por `raw.githubusercontent.com`, uma por jogo, em tempo de download — **não** são instaladas
junto com o app e não são pré-clonadas.

## Como funciona

Com `"repo": "gamecovers"` na configuração, o app tenta baixar a capa nesta ordem:

```
game_covers/<Nome do Jogo>_<TID>/cover.png
game_covers/<TID>/cover.png
game_covers/<TID>.png      (ou .jpg)
game_covers/<HomebrewID>/cover.png   (HomebrewID = TID sintético SHA1 do nome)
```

## Estrutura de pasta aceita pelo downloader

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
  <TID>/               # fallback: apenas TID (ex: 4D5309E7)
  <TID>.png            # fallback: arquivo solto
```

- `<Nome do Jogo>` = nome do jogo (ex: `Halo 3`, `Gears of War`). Caracteres inválidos em nome de pasta (`\ / : * ? " < > |`) são convertidos para `_`. Espaços e unicode são percent-encoded na URL.
- `<TID>` = TitleID do jogo em **8 hex maiúsculos** (ex: `4D5309E7`).
- A busca por nome é case-sensitive em relação ao nome da pasta no repositório (o app usa o nome real vindo do Aurora DB/x360db).

## Fallback local (não distribuído para outros usuários)

A pasta `game_covers/` instalada ao lado do executável é usada como **fallback** quando o
download remoto falha (sem internet, etc.), e como **prioridade máxima** para "capa
personalizada" quando `repo` ≠ `gamecovers`. Estrutura aceita:

1. Pasta `<Nome>_<TID>/`
2. Pasta `<TID>/`
3. Pasta `<HomebrewID>/`
4. Arquivo solto `<TID>.<ext>`
5. Arquivo solto `<Nome>.<ext>` (só capa)

Assets suportados localmente: `cover.png/.jpg`, `background.png/.jpg`, `banner.png`,
`tile.png`, `icon.png`, `screenshots/*.png|.jpg`.

## Log

Quando uma capa é encontrada, aparece no log:
```
[LOG]  360-Game-Art cover for <TID>. (remote: <Nome>_<TID>/cover.png)
[LOG]  capa local (game_covers) para <arquivo>.
```