# Game Covers (assets locais)

Pasta **não distribuída no executável** — funciona apenas ao rodar por código (`python aurora_covers.py`).

## Estrutura por TID (recomendado)

```
game_covers/
  <TID>/
    cover.jpg      # capa (boxart)
    banner.png     # banner
    tile.png       # tile
    icon.png       # ícone
    background.jpg # fundo
    screenshots/
      1.jpg
      2.jpg
      ...
```

- `<TID>` = TitleID do jogo em **8 hex maiúsculos** (ex: `4D5309E7`).
- Qualquer imagem dentro de `game_covers/<TID>/` é usada como asset do tipo correspondente pelo nome do arquivo.
- Para screenshots, coloque os arquivos em `game_covers/<TID>/screenshots/`.

## Estrutura por nome (só capa)

```
game_covers/
  NomeDoJogo.jpg
  OutroJogo.png
```

- Usado como fallback para **capa** quando não há pasta por TID.
- O app normaliza o nome (remove espaços, pontuação, acentos) e compara com o nome do jogo (`dname`, `folder_name`, `title`).

## Prioridade

1. Pasta `game_covers/<TID>/` (qualquer asset)
2. Arquivo `game_covers/<TID>.jpg/.png`
3. Arquivo `game_covers/<nome>.jpg/.png` (só capa)
4. Fontes remotas (Unity → 360-Game-Art → x360db)

## Log

Quando um asset local é encontrado, aparece no log:
```
[LOG]  game_cover_ok: cover.jpg
```