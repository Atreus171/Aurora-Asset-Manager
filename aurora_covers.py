import io
import json
import hashlib
import os
import re
import sqlite3
import struct
import sys
import threading
import queue
import time
import urllib.error
import urllib.parse
import urllib.request
import ftplib
import concurrent.futures
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from PIL import Image, ImageDraw, ImageOps, ImageTk

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def set_window_icon(root):
    try:
        icon = resource_path("icon.ico")
        if os.path.isfile(icon):
            root.iconbitmap(icon)
    except Exception:
        pass


X360DB_RAW = "https://raw.githubusercontent.com/xenia-manager/x360db/main/"
GAMES_INDEX_URL = X360DB_RAW + "games.json"
GAMES_INDEX_MIRROR = "https://cdn.jsdelivr.net/gh/xenia-manager/x360db@main/games.json"
# 360-Game-Art (Element18592): capas ordenadas por TitleID em Games/<tid>/cover.jpg
GAME_ART_RAW = "https://raw.githubusercontent.com/Element18592/360-Game-Art/main/Games/"
# game_covers remoto (este repo): capas em game_covers/<Nome>_<TID>/cover.png ou game_covers/<TID>/cover.png
GAME_COVERS_REMOTE = "https://raw.githubusercontent.com/Atreus171/Aurora-Asset-Manager/main/game_covers/"
# Pasta de assets locais (game_covers).
# - Rodando por código (python aurora_covers.py): usa a pasta do repo.
# - Rodando compilado (.exe): usa pasta "game_covers" ao lado do executável.
def _get_game_covers_dir():
    if getattr(sys, "frozen", False):  # PyInstaller
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "game_covers")

GAME_COVERS_DIR = _get_game_covers_dir()
USER_AGENT = {"User-Agent": "Mozilla/5.0 (aurora-covers-x360db)"}

MIN_ASSET_SIZE = 24 * 1024
BOXART_W, BOXART_H = 900, 600
COVER_W, COVER_H = 900, 1233
BG_W, BG_H = 1920, 1080
ICON_W, ICON_H = 64, 64
BANNER_W, BANNER_H = 420, 95
SS_W, SS_H = 1280, 720
SS_MAX_DEFAULT = 6

XBOXUNITY_CVERS = "https://www.xboxunity.net/api/Covers/%s"
XBOXUNITY_LIB = "https://www.xboxunity.net/Resources/Lib"
XBOXUNITY_ROOT = "https://www.xboxunity.net/"
X360DB_PING_URL = GAMES_INDEX_URL
PING_INTERVAL = 20
UNITY_OK = "#3fb950"
UNITY_DOWN = "#f85149"
UNITY_WAIT = "#9a9a9a"

# Update checker
GITHUB_REPO = "Atreus171/Aurora-Asset-Manager"
GITHUB_API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_API_RELEASES_ALL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
CURRENT_VERSION = "1.5.2"
UPDATE_CHECK_INTERVAL = 24 * 3600  # 24 hours

ASSET_TYPE_ICON = 0
ASSET_TYPE_BANNER = 1
ASSET_TYPE_BOXART = 2
ASSET_TYPE_BACKGROUND = 4
ASSET_TYPE_SCREENSHOT = 5

ART_SIZE = {
    ASSET_TYPE_BOXART: (BOXART_W, BOXART_H),
    ASSET_TYPE_BACKGROUND: (BG_W, BG_H),
    ASSET_TYPE_ICON: (ICON_W, ICON_H),
    ASSET_TYPE_BANNER: (BANNER_W, BANNER_H),
}

THUMB_W, THUMB_H = 150, 200
PREVIEW_W, PREVIEW_H = 320, 213

THEMES = {
    "claro": {
        "bg": "#f0f0f0",
        "bg2": "#e2e2e2",
        "fg": "#1c1c1c",
        "muted": "#555555",
        "field": "#ffffff",
        "button": "#d9d9d9",
        "active": "#bfbfbf",
        "sel": "#0078d7",
        "sels_fg": "#ffffff",
        "accent": "#0078d7",
        "preview_bg": "#e8e8e8",
    },
    "escuro": {
        "bg": "#1e1e1e",
        "bg2": "#2b2b2b",
        "fg": "#e6e6e6",
        "muted": "#9a9a9a",
        "field": "#252526",
        "button": "#333333",
        "active": "#3f3f46",
        "sel": "#04395e",
        "sels_fg": "#ffffff",
        "accent": "#1f6feb",
        "preview_bg": "#0d0d0d",
    },
}

DEFAULT_CONFIG = {
    "theme": "escuro",
    "repo": "x360db",
    "cover_format": "paisagem",
    "screenshots": SS_MAX_DEFAULT,
    "lang": "pt",
    "show_status": True,
    "show_log": True,
    "auto_search_titles": True,
    "show_game_info": True,
    "show_debug_button": False,
    "download_missing_only": True,
    "auto_update_check": True,
    "ftp_host": "",
    "ftp_port": 21,
    "ftp_user": "xbox",
    "ftp_pass": "xbox",
    "ftp_base": "Hdd:\\Aurora\\Data\\GameData",
}

def detect_system_lang():
    try:
        import locale
        lang_code = locale.getlocale()[0]
        if lang_code:
            lang_code = lang_code.lower().split('_')[0]
            if lang_code in LANGUAGES:
                return lang_code
    except Exception:
        pass
    return "en"


CURRENT_LANG = detect_system_lang()

LANGUAGES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "ja": "日本語",
    "ru": "Русский",
}

TEXT = {
    "pt": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
        "gameart_status": "360-Game-Art:",
        "checking": "verificando...",
        "connected": "conectado",
        "disconnected": "desconectado",
        "aurora_folder": "Pasta do Aurora:",
        "browse": "Procurar...",
        "opt_boxart": "Baixar capa (boxart)",
        "opt_background": "Baixar background",
        "opt_force": "Forçar re-download",
        "opt_backup": "Backup antes de sobrescrever",
        "opt_icon": "Baixar ícone (64x64)",
        "opt_banner": "Baixar banner",
        "opt_screenshots": "Baixar screenshots (até %d)",
        "info_note": "Informações (título/descrição) vêm do x360db e são usadas no painel.",
        "scan": "Escanear jogos",
        "download": "Baixar e instalar assets",
        "custom_cover": "Capa personalizada...",
        "settings": "Configurações...",
        "tip_right_click": "Dica: clique com o botão direito num jogo para ver/alterar assets.",
        "cancel": "Cancelar",
        "col_tid": "TitleID",
        "col_game": "Jogo",
        "col_status": "Estado",
        "preview_title": "Pré-visualização da capa",
        "no_selection": "Sem seleção",
        "no_cover": "Sem capa",
        "no_cover_installed": "Sem capa instalada",
        "cover_installed": "Capa instalada",
        "loading_info": "Carregando informações...",
        "loading_index": "Aguarde, carregando índice do x360db...",
        "index_loaded": "Índice do x360db carregado: %d jogos.",
        "index_fail": "Não foi possível baixar o índice (modo offline: usará o TitleID direto).",
        "warn": "Aviso",
        "info": "Informações",
        "scan_first": "Digitalize os jogos primeiro.",
        "pick_art": "Marque pelo menos um tipo de arte (capa, background, ícone, banner ou screenshots).",
        "pick_aurora": "Escolha a pasta raiz do Aurora primeiro.",
        "not_aurora_folder": "A pasta selecionada não parece ser uma instalação do Aurora (falta Data/GameData ou pasta Aurora).",
        "pick_game": "Selecione um jogo na lista primeiro.",
        "img_open_fail": "Não foi possível abrir a imagem:\n%s",
        "img_write_fail": "Não foi possível gravar:\n%s",
        "save_fail": "Não foi possível salvar:\n%s",
        "warn": "Aviso",
        "error": "Erro",
        "pick_game": "Selecione um jogo na lista primeiro.",
        "custom_cover": "Capa personalizada",
        "m_assets": "Ver/alterar assets deste jogo...",
        "m_alt": "Capas alternativas online...",
        "m_custom": "Capa personalizada...",
        "m_export_assets": "Exportar assets para game_covers...",
        "set_theme": "Tema:",
        "theme_dark": "Escuro",
        "theme_light": "Claro",
        "theme_system": "Seguir o sistema",
        "dest": "Destino",
        "set_lang": "Idioma:",
        "set_show_status": "Mostrar bolinhas de status da Internet no topo",
        "set_repo": "Repositório de capas:",
        "set_format": "Formato da capa:",
        "format_portrait": "Retrato (900x1233)",
        "format_landscape": "Paisagem (900x600)",
        "set_screenshots": "Screenshots por jogo:",
        "status_saved": "Configurações salvas (tema: %s, repositório: %s, capa: %s, screenshots: %d, região: %s).",
        "save": "Salvar",
        "cancel2": "Cancelar",
        "restart_title": "Reiniciar app",
        "restart_lang": "O idioma muda ao reiniciar o app (feche e abra de novo).",
        "assets": "Assets",
        "assets_of": "Assets de",
        "col_kind": "Tipo",
        "col_status": "Estado",
        "dl_online": "Baixar online",
        "dl_all": "Baixar todos",
        "dl_all_start": "Baixando todos os assets deste jogo...",
        "dl_all_log": "Baixando todos os assets de %s (%s)...",
        "change_pc": "Alterar... (PC)",
        "close": "Fechar",
        "assets_hint": "Selecione um tipo e use os botões.",
        "assets_installed": "Instalado",
        "assets_missing": "Ausente",
        "assets_pick": "Selecione um tipo na lista primeiro.",
        "assets_dl_kind": "Baixando %s...",
        "no_preview": "Sem preview",
        "pick_kind": "Escolher %s para %s",
        "kind_boxart": "capa (boxart)",
        "kind_background": "fundo (background)",
        "kind_icon": "ícone",
        "kind_banner": "banner",
        "kind_screenshots": "screenshot",
        "asset_changed": "Asset '%s' alterado para %s (%s).",
        "m_assets": "Ver/alterar assets deste jogo...",
        "m_alt": "Capas alternativas online...",
        "m_custom": "Capa personalizada...",
        "m_export_assets": "Exportar assets para game_covers...",
        "set_title": "Configurações",
        "set_theme": "Tema:",
        "theme_dark": "Escuro",
        "theme_light": "Claro",
        "theme_system": "Seguir o tema do sistema",
        "set_repo": "Repositório de capas:",
        "set_format": "Formato da capa:",
        "format_portrait": "Retrato (900x1233)",
        "format_landscape": "Paisagem (900x600)",
        "set_screenshots": "Screenshots por jogo:",
        "set_lang": "Idioma:",
        "set_show_status": "Mostrar bolinhas de status de conexão",
        "save": "Salvar",
        "cancel2": "Cancelar",
        "restart_title": "Idioma",
        "restart_lang": "Reinicie o aplicativo para aplicar o idioma.",
        "assets_title": "Assets - %s (%s)",
        "assets_header": "Assets de %s (%s)",
        "assets_kind": "Tipo",
        "assets_status": "Estado",
        "assets_pick": "Selecione um tipo e use os botões.",
        "assets_ok": "Instalado",
        "assets_missing": "Ausente",
        "assets_online": "Baixar online",
        "assets_pc": "Alterar... (PC)",
        "assets_close": "Fechar",
        "assets_dl_kind": "Baixar %s...",
        "assets_pick_kind": "Selecione um tipo na lista primeiro.",
        "alt_title": "Capas alternativas - %s (%s)",
        "alt_label": "Capas disponíveis no XboxUnity (escolha uma):",
        "alt_searching": "Buscando capas no XboxUnity...",
        "alt_none": "Nenhuma capa encontrada no XboxUnity para este jogo.",
        "alt_count": "%d capa(s) encontrada(s).",
        "alt_loading": "Carregando visual...",
        "alt_none_found": "Nenhuma capa encontrada no XboxUnity para este jogo.",
        "alt_no_img": "Sem imagem",
        "alt_no_preview": "Sem preview para esta capa.",
        "alt_loaded": "Preview carregado.",
        "alt_noimg": "Sem imagem",
        "alt_preview_ok": "Preview carregado.",
        "alt_preview_none": "Sem preview para esta capa.",
        "alt_sem_preview": "Sem preview",
        "alt_install": "Baixar e instalar esta capa",
        "alt_official": "Capa oficial (x360db)",
        "alt_unity_empty": "Buscado: XboxUnity não tem capa para este jogo; mostrando a capa oficial (x360db).",
        "alt_installed": "Capa instalada com sucesso.",
        "alt_failed": "Falha ao instalar a capa.",
        "alt_select_first": "Selecione uma capa primeiro.",
        "alt_downloading": "Baixando...",
        "status_saved": "Configurações salvas (tema: %s, repositório: %s, capa: %s, screenshots: %d, região: %s).",
        "canceled": "Operação cancelada pelo usuário.",
        "unity_fallback": "XboxUnity sem capa utilizável; usando x360db como alternativa.",
        "unity_no_cover": "XboxUnity sem capas para %s; usando x360db como alternativa.",
        "unity_offline": "XboxUnity fora do ar; usando x360db.",
        "no_games_notice": "Nenhum jogo precisa de download.",
        "done_notice": "Concluído! No Xbox: boot Aurora e aperte Y -> Refresh no jogo (ou use Import).",
        "set_log": "Mostrar log (caixa de texto)",
        "cover_missing_both": "  capa não encontrada em x360db nem XboxUnity.",
        "gameart_cover_ok": "  capa da 360-Game-Art para %s.",
        "game_cover_ok": "  capa local (game_covers) para %s.",
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Pesquisar título...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Buscar títulos automaticamente (XboxUnity)",
        "auto_search_on": "Busca automática de títulos LIGADA.",
        "auto_search_off": "Busca automática de títulos DESLIGADA.",
        "show_game_info": "Mostrar diretor e data de lançamento",
        "show_debug_button": "Mostrar botão Debug DB",
        "auto_update_check": "Verificar atualizações automaticamente",
        "update_available_title": "Atualização disponível",
        "update_available_msg": "Uma nova versão ({0}) está disponível! Versão atual: {1}\n\nDeseja abrir a página de downloads?",
        "download_missing_only": "Baixar só jogos sem capa",
        "m_search": "Pesquisar título...",
        "m_rename": "Renomear jogo",
        "rename_prompt": "Novo nome para %s (%s):",
        "renamed": "Jogo %s renomeado para: %s",
        "ok": "OK",
        "add_game": "Adicionar jogos...",
        "add_game_tid": "Title ID (8 dígitos hex; opcional se detectado):",
        "add_game_xex": "Arquivo .xex (detecta o TID):",
        "add_game_folder": "Pasta para procurar jogos:",
        "add_game_folder_note": "Procura vários jogos (.xex) dentro da pasta escolhida, um por subpasta.",
        "add_game_name": "Nome (opcional):",
        "add_game_mkdir": "Criar pasta GameData no HD",
        "add_game_bad_tid": "Title ID inválido (use 8 dígitos hex, ex.: 5841120F).",
        "add_game_exists": "Este jogo já está na lista.",
        "add_game_need_name": "Informe um nome para criar a pasta.",
        "add_game_added": "Jogo adicionado: %s (%s)",
        "add_game_folder_done": "Pasta escaneada: %d jogo(s) adicionado(s) de %s.",
        "manage_folders": "Gerenciar pastas...",
        "db_editor": "Banco do Aurora (content.db)",
        "db_add": "Adicionar...",
        "db_rename": "Renomear...",
        "db_remove": "Remover...",
        "db_reload": "Atualizar",
        "db_backup": "Backup criado: %s",
        "db_warn1": "Edite apenas com o Aurora fechado e o disco parado (o banco fica travado em uso). Um backup automático (.bak) é criado antes de cada alteração.",
        "db_nodb": "content.db do Aurora não encontrado. Conecte o HD e escaneie antes.",
        "db_need_id": "Selecione uma entrada na lista.",
        "db_new_tid": "Title ID (8 dígitos hex):",
        "db_new_name": "Nome:",
        "db_new_dir": "Pasta relativa (ex.: \\Content\\0000000000000000\\5841120F):",
        "db_added": "Entrada adicionada: %s (%s)",
        "db_renamed": "Entrada renomeada: %s",
        "db_removed": "Entrada removida: %s",
        "db_confirm_remove": "Remover '%s' do registro? O conteúdo em disco NÃO é apagado.",
        "db_only_dlc": "Somente DLC / XBLA / TU",
        "db_filter": "Tipo:",
        "db_all": "Todos",
        "db_search": "Pesquisar nome, TID ou pasta...",
        "filter_games": "Pesquisar jogos: ",
        "db_need_name": "Informe um nome.",
        "rename_ftp_start": "Renomeando a pasta no console via FTP...",
        "rename_ftp_ok": "Pasta renomeada no console: %s",
        "rename_ftp_err": "Não foi possível renomear no console: %s",
        "m_open_folder": "Abrir pasta do jogo",
        "m_remove_cover": "Remover capa instalada",
        "m_remove_game": "Remover da lista",
        "m_restore_hidden": "Restaurar jogos removidos...",
        "remove_cover_confirm": "Remover a capa instalada de '%s' (%s)?\nApaga GC<tid>.asset e a capa da Import.",
        "cover_removed": "Capa removida de %s (%s).",
        "cover_none_found": "Nenhum arquivo de capa encontrado para %s (%s).",
        "remove_game_confirm": "Remover '%s' (%s) da lista? O conteúdo em disco NÃO é apagado.",
        "game_removed": "Jogo %s (%s) removido da lista.",
        "restore_hidden_confirm": "Restaurar %d jogo(s) removido(s) da lista?",
        "restore_hidden_done": "Todos os jogos removidos foram restaurados.",
        "set_ftp": "Enviar por FTP (console):",
        "ftp_host_lbl": "IP do console:",
        "ftp_port_lbl": "Porta:",
        "ftp_user_lbl": "Usuário:",
        "ftp_pass_lbl": "Senha:",
        "ftp_base_lbl": "Pasta remota (GameData):",
        "ftp_send": "Enviar por FTP",
        "ftp_sending": "Enviando para o console via FTP...",
        "ftp_deploy_covers": "Enviar assets do game_covers",
        "ftp_deploying": "Enviando assets do game_covers...",
        "ftp_deploy_ok": "Assets enviados: %d arquivo(s) para %s",
        "ftp_deploy_no_folder": "Nenhuma pasta game_covers encontrada para este jogo.",
        "ftp_sent": "Enviados %d arquivo(s) para %s.",
        "ftp_no_host": "Configure o IP do console em Configurações -> FTP primeiro.",
        "ftp_no_folder": "Este jogo não tem pasta local em Data\\GameData para enviar.",
        "ftp_err": "Erro no FTP: %s",
        "ss_prev": "◀",
        "ss_next": "▶",
        "credits": "Desenvolvido por Atreus171\nhttps://github.com/Atreus171/Aurora-Asset-Manager",
        "release_date": "Lançamento",
        "developer": "Desenvolvedora",
        "genres": "Gêneros",
        "settings_title": "Configurações",
        "db_notfound": "content.db não encontrado",
        "err_generic": "Erro: %s",
        "no_folders": "Nenhuma pasta adicionada ainda.",
        "folders_header": "Pastas adicionadas (via 'Adicionar pasta para procurar jogos'):",
        "col_folder": "Pasta",
        "col_added": "Adicionada em",
        "col_count": "Jogos",
        "col_type": "Tipo",
        "remove_folders_confirm": "Remover %d pasta(s) selecionada(s)?",
        "open_folder": "Abrir pasta",
        "remove_selected": "Remover selecionadas",
        "schema_unknown": "Schema desconhecido (tabela=%s)",
        "folder_not_found": "Pasta não encontrada: %s",
        "folder_open_err": "Erro ao abrir pasta: %s",
        "alt_no_preview": "Sem preview",
        "alt_pick_first": "Selecione uma capa primeiro.",
        "downloading": "Baixando...",
        "no_success": "sem sucesso",
        "logs_unity_names": "Nomes atualizados via XboxUnity.",
        "logs_scanning": "Escaneando: %s",
        "logs_no_index": "Aviso: índice do x360db não carregou; sem filtro de DLC/updates.",
        "logs_ignored_dlc": "Ignorados %d TitleIDs de DLC/update (não constam no índice de jogos).",
        "logs_god_xdlc": "Jogos GOD/XDLC no HD sem pasta GameData: %d (serão tratados via Import)",
        "logs_fetch_names": "Buscando %d nomes no XboxUnity...",
        "logs_title_x360db": "Título encontrado no x360db: %s",
        "logs_title_unity": "Título encontrado no XboxUnity: %s",
        "logs_title_folder": "Usando nome da pasta: %s",
        "logs_title_not_found": "Título não encontrado para %s",
        "logs_title_none_idlike": "Nenhum jogo com nome de TitleID para corrigir.",
        "logs_titles_updated": "Nomes corrigidos: %d.",
        "logs_title_nochange": "Nomes já estão corretos.",
        "logs_updating_db": "Atualizando content.db: TID=%s -> %s",
        "logs_db_err": "Erro ao atualizar content.db: %s",
        "logs_renamed_folder": "Pasta renomeada: %s -> %s",
        "logs_folder_open_err": "Erro ao abrir pasta: %s",
        "logs_gamedata_created": "Pasta GameData criada: %s",
        "logs_queue_started": "Iniciando fila: %d jogo(s)",
        "logs_custom_installed": "Capa personalizada instalada para %s (%s)",
        "logs_assets_exported": "Assets exportados para %s: %s",
        "assets_exported_ok": "Assets exportados para game_covers/%s\n%d arquivo(s) copiado(s).",
        "assets_folder_created_empty": "Pasta criada: game_covers/%s\n%s\n(Nenhum asset instalado encontrado — adicione seus arquivos manualmente).",
        "logs_no_assets_to_export": "Nenhum asset instalado para exportar: %s",
        "no_assets_to_export": "Nenhum asset instalado encontrado para exportar.",
        "logs_ftp_sent": "FTP: %d arquivo(s) enviado(s) para %s.",
        "logs_ftp_err": "Erro no FTP: %s",
        "ftp_inaccessible": "FTP: impossível acessar %s (%s)",
        "logs_downloading": "Baixando %s para %s (%s)...",
        "logs_downloading_assets": "Baixando todos os assets de %s...",
        "logs_rename_folder_err": "Não foi possível renomear a pasta: %s",
        "logs_no_dedicated_gamedata": "Sem pasta GameData dedicada para %s; renomeação salva apenas na lista.",
        "logs_db_titlename_ok": "content.db: TitleName atualizado para '%s'.",
        "logs_db_row_not_found": "content.db: linha %s não encontrada (nome salvo só na configuração).",
        "logs_db_rename_err": "content.db: não foi possível renomear: %s",
        "logs_folders_removed": "%d pasta(s) removida(s)",
        "logs_progress_game": "[%d/%d] %s (%s)",
        "logs_game_err": "Erro neste jogo: %s",
        "logs_cover_fetch_err": "Erro ao buscar capa: %s",
        "logs_hb_tid_by_name": "Homebrew: TID do XboxUnity por nome '%s' = %s",
        "logs_hb_no_cover_by_name": "Homebrew: nenhuma capa por nome no XboxUnity (%s)",
        "logs_unity_offline": "XboxUnity fora do ar (%s)",
        "unity_no_cover": "XboxUnity sem capas para %s",
        "unity_black_cover": "Capa vazia/preta ignorada (bugada) no XboxUnity.",
        "unity_no_usable": "XboxUnity sem capa utilizável (%s)",
        "cover_not_found_repo": "Capa não encontrada no repositório.",
        "background_not_found": "Background não encontrado no x360db.",
        "kind_not_found": "%s não encontrado no x360db.",
        "no_screenshots": "Sem screenshots disponíveis no x360db.",
        "logs_ss_installed": "%d screenshots instaladas.",
        "logs_dl_kind_err": "Erro ao baixar %s: %s",
        "logs_saved": "Gravado %s",
        "logs_alt_import": "Import alternativo em %s",
        "logs_kind_result": "%s: %s",
        "logs_kind_err": "Erro: %s",
        "logs_kind_err_with": "%s: erro: %s",
        "logs_kind_skip": "%s: já instalado (pulando).",
        "unity_fetch_fail": "Falha ao baixar a capa do XboxUnity.",
        "logs_alt_installed": "Capa alternativa instalada para %s (%s).",
        "logs_alt_err": "Erro: %s",
    },
    "en": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
        "gameart_status": "360-Game-Art:",
        "checking": "checking...",
        "connected": "connected",
        "disconnected": "disconnected",
        "aurora_folder": "Aurora folder:",
        "browse": "Browse...",
        "opt_boxart": "Download cover (boxart)",
        "opt_background": "Download background",
        "opt_force": "Force re-download",
        "opt_backup": "Backup before overwriting",
        "opt_icon": "Download icon (64x64)",
        "opt_banner": "Download banner",
        "opt_screenshots": "Download screenshots (up to %d)",
        "info_note": "Info (title/description) comes from x360db and is used in the panel.",
        "scan": "Scan games",
        "download": "Download and install assets",
        "custom_cover": "Custom cover...",
        "settings": "Settings...",
        "tip_right_click": "Tip: right-click a game to view/change assets.",
        "cancel": "Cancel",
        "col_tid": "TitleID",
        "col_game": "Game",
        "col_status": "Status",
        "preview_title": "Cover preview",
        "no_selection": "No selection",
        "no_cover": "No cover",
        "no_cover_installed": "No cover installed",
        "cover_installed": "Cover installed",
        "loading_info": "Loading info...",
        "loading_index": "Loading x360db index, please wait...",
        "index_loaded": "x360db index loaded: %d games.",
        "index_fail": "Could not download the index (offline mode: will use TitleID directly).",
        "warn": "Warning",
        "info": "Info",
        "scan_first": "Scan the games first.",
        "pick_art": "Check at least one art type (cover, background, icon, banner or screenshots).",
        "pick_aurora": "Choose the Aurora root folder first.",
        "not_aurora_folder": "The selected folder does not appear to be an Aurora installation (missing Data/GameData or Aurora folder).",
        "pick_game": "Select a game in the list first.",
        "img_open_fail": "Could not open the image:\n%s",
        "img_write_fail": "Could not write:\n%s",
        "save_fail": "Could not save:\n%s",
        "warn": "Warning",
        "error": "Error",
        "pick_game": "Select a game in the list first.",
        "custom_cover": "Custom cover",
        "m_assets": "View/change this game's assets...",
        "m_alt": "Alternative covers online...",
        "m_custom": "Custom cover...",
        "m_export_assets": "Export assets to game_covers...",
        "set_theme": "Theme:",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_system": "Follow system",
        "dest": "Destination",
        "set_lang": "Language:",
        "set_show_status": "Show internet status dots at the top",
        "set_repo": "Cover repository:",
        "set_format": "Cover format:",
        "format_portrait": "Portrait (900x1233)",
        "format_landscape": "Landscape (900x600)",
        "set_screenshots": "Screenshots per game:",
        "status_saved": "Settings saved (theme: %s, repo: %s, cover: %s, screenshots: %d).",
        "save": "Save",
        "cancel2": "Cancel",
        "restart_title": "Restart app",
        "restart_lang": "The language changes when you restart the app (close and reopen).",
        "assets": "Assets",
        "assets_of": "Assets of",
        "col_kind": "Type",
        "col_status": "Status",
        "dl_online": "Download online",
        "dl_all": "Download all",
        "dl_all_start": "Downloading all assets of this game...",
        "dl_all_log": "Downloading all assets of %s (%s)...",
        "change_pc": "Change... (PC)",
        "close": "Close",
        "assets_hint": "Select a type and use the buttons.",
        "assets_installed": "Installed",
        "assets_missing": "Missing",
        "assets_pick": "Select a type in the list first.",
        "assets_dl_kind": "Downloading %s...",
        "no_preview": "No preview",
        "pick_kind": "Choose %s for %s",
        "kind_boxart": "cover (boxart)",
        "kind_background": "background",
        "kind_icon": "icon",
        "kind_banner": "banner",
        "kind_screenshots": "screenshot",
        "asset_changed": "Asset '%s' changed for %s (%s).",
        "m_assets": "View/change assets of this game...",
        "m_alt": "Alternative covers online...",
        "m_custom": "Custom cover...",
        "m_export_assets": "Export assets to game_covers...",
        "set_title": "Settings",
        "set_theme": "Theme:",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_system": "Follow system theme",
        "set_repo": "Cover repository:",
        "set_format": "Cover format:",
        "format_portrait": "Portrait (900x1233)",
        "format_landscape": "Landscape (900x600)",
        "set_screenshots": "Screenshots per game:",
        "set_lang": "Language:",
        "set_show_status": "Show connection status dots",
        "save": "Save",
        "cancel2": "Cancel",
        "restart_title": "Language",
        "restart_lang": "Restart the app to apply the language.",
        "assets_title": "Assets - %s (%s)",
        "assets_header": "Assets of %s (%s)",
        "assets_kind": "Type",
        "assets_status": "Status",
        "assets_pick": "Select a type and use the buttons.",
        "assets_ok": "Installed",
        "assets_missing": "Missing",
        "assets_online": "Download online",
        "assets_pc": "Change... (PC)",
        "assets_close": "Close",
        "assets_dl_kind": "Downloading %s...",
        "no_preview": "No preview",
        "assets_pick_kind": "Select a type in the list first.",
        "alt_title": "Alternative covers - %s (%s)",
        "alt_label": "Covers available on XboxUnity (pick one):",
        "alt_searching": "Searching covers on XboxUnity...",
        "alt_none": "No covers found on XboxUnity for this game.",
        "alt_count": "%d cover(s) found.",
        "alt_loading": "Loading preview...",
        "alt_none_found": "No covers found on XboxUnity for this game.",
        "alt_no_img": "No image",
        "alt_no_preview": "No preview for this cover.",
        "alt_loaded": "Preview loaded.",
        "alt_noimg": "No image",
        "alt_preview_ok": "Preview loaded.",
        "alt_preview_none": "No preview for this cover.",
        "alt_sem_preview": "No preview",
        "alt_install": "Download and install this cover",
        "alt_official": "Official cover (x360db)",
        "alt_unity_empty": "Searched: XboxUnity has no cover for this game; showing the official cover (x360db).",
        "alt_installed": "Cover installed successfully.",
        "alt_failed": "Failed to install the cover.",
        "alt_select_first": "Select a cover first.",
        "alt_downloading": "Downloading...",
        "status_saved": "Settings saved (theme: %s, repo: %s, cover: %s, screenshots: %d).",
        "canceled": "Operation cancelled by the user.",
        "unity_fallback": "XboxUnity has no usable cover; using x360db as fallback.",
        "unity_no_cover": "XboxUnity has no covers for %s; using x360db as fallback.",
        "unity_offline": "XboxUnity is offline; using x360db.",
        "no_games_notice": "No games need a download.",
        "done_notice": "Done! On the Xbox: boot Aurora and press Y -> Refresh on the game (or use Import).",
        "set_log": "Show log (text box)",
        "cover_missing_both": "  cover not found on x360db or XboxUnity.",
        "gameart_cover_ok": "  360-Game-Art cover for %s.",
        "game_cover_ok": "  local cover (game_covers) for %s.",
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Search title...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Auto-search titles (XboxUnity)",
        "auto_search_on": "Auto title search ENABLED.",
        "auto_search_off": "Auto title search DISABLED.",
        "show_game_info": "Show director and release date",
        "show_debug_button": "Show Debug DB button",
        "auto_update_check": "Check for updates automatically",
        "update_available_title": "Update Available",
        "update_available_msg": "A new version ({0}) is available! Current version: {1}\n\nOpen download page?",
        "download_missing_only": "Download only games without a cover",
        "m_search": "Search title...",
        "m_rename": "Rename game",
        "rename_prompt": "New name for %s (%s):",
        "renamed": "Game %s renamed to: %s",
        "ok": "OK",
        "add_game": "Add games...",
        "add_game_tid": "Title ID (8 hex digits; optional if detected):",
        "add_game_xex": ".xex file (auto-detect TID):",
        "add_game_folder": "Folder to search for games:",
        "add_game_folder_note": "Searches for multiple games (.xex) inside the chosen folder, one per subfolder.",
        "add_game_name": "Name (optional):",
        "add_game_mkdir": "Create GameData folder on HD",
        "add_game_bad_tid": "Invalid Title ID (use 8 hex digits, e.g. 5841120F).",
        "add_game_exists": "This game is already in the list.",
        "add_game_need_name": "Enter a name to create the folder.",
        "add_game_added": "Game added: %s (%s)",
        "add_game_folder_done": "Folder scanned: %d game(s) added from %s.",
        "manage_folders": "Manage folders...",
        "db_editor": "Aurora database (content.db)",
        "db_add": "Add...",
        "db_rename": "Rename...",
        "db_remove": "Remove...",
        "db_reload": "Refresh",
        "db_backup": "Backup created: %s",
        "db_warn1": "Only edit with Aurora closed and the drive idle (the database is locked while in use). An automatic backup (.bak) is created before each change.",
        "db_nodb": "Aurora content.db not found. Connect the HD and scan first.",
        "db_need_id": "Select an entry in the list.",
        "db_new_tid": "Title ID (8 hex digits):",
        "db_new_name": "Name:",
        "db_new_dir": "Relative folder (e.g.: \\Content\\0000000000000000\\5841120F):",
        "db_added": "Entry added: %s (%s)",
        "db_renamed": "Entry renamed: %s",
        "db_removed": "Entry removed: %s",
        "db_confirm_remove": "Remove '%s' from the database? Content on disk is NOT deleted.",
        "db_only_dlc": "Only DLC / XBLA / TU",
        "db_filter": "Type:",
        "db_all": "All",
        "db_search": "Search name, TID or folder...",
        "filter_games": "Search games: ",
        "db_need_name": "Enter a name.",
        "rename_ftp_start": "Renaming folder on the console via FTP...",
        "rename_ftp_ok": "Folder renamed on the console: %s",
        "rename_ftp_err": "Could not rename on the console: %s",
        "m_open_folder": "Open game folder",
        "m_remove_cover": "Remove installed cover",
        "m_remove_game": "Remove from list",
        "m_restore_hidden": "Restore removed games...",
        "remove_cover_confirm": "Remove the installed cover of '%s' (%s)?\nDeletes GC<tid>.asset and the Import cover.",
        "cover_removed": "Cover removed from %s (%s).",
        "cover_none_found": "No cover file found for %s (%s).",
        "remove_game_confirm": "Remove '%s' (%s) from the list? Disk content is NOT deleted.",
        "game_removed": "Game %s (%s) removed from the list.",
        "restore_hidden_confirm": "Restore %d removed game(s) to the list?",
        "restore_hidden_done": "All removed games were restored.",
        "set_ftp": "Send via FTP (console):",
        "ftp_host_lbl": "Console IP:",
        "ftp_port_lbl": "Port:",
        "ftp_user_lbl": "User:",
        "ftp_pass_lbl": "Password:",
        "ftp_base_lbl": "Remote folder (GameData):",
        "ftp_send": "Send via FTP",
        "ftp_sending": "Sending to the console via FTP...",
        "ftp_deploy_covers": "Deploy assets from game_covers",
        "ftp_deploying": "Deploying game_covers assets...",
        "ftp_deploy_ok": "Assets deployed: %d file(s) to %s",
        "ftp_deploy_no_folder": "No game_covers folder found for this game.",
        "ftp_sent": "Sent %d file(s) to %s.",
        "ftp_no_host": "Set the console IP in Settings -> FTP first.",
        "ftp_no_folder": "This game has no local Data\\GameData folder to send.",
        "ftp_err": "FTP error: %s",
        "ss_prev": "◀",
        "ss_next": "▶",
        "credits": "Developed by Atreus171\nhttps://github.com/Atreus171/Aurora-Asset-Manager",
        "release_date": "Release",
        "developer": "Developer",
        "genres": "Genres",
        "settings_title": "Settings",
        "db_notfound": "content.db not found",
        "err_generic": "Error: %s",
        "no_folders": "No folders added yet.",
        "folders_header": "Added folders (via 'Folder to search for games'):",
        "col_folder": "Folder",
        "col_added": "Added on",
        "col_count": "Games",
        "col_type": "Type",
        "remove_folders_confirm": "Remove %d selected folder(s)?",
        "open_folder": "Open folder",
        "remove_selected": "Remove selected",
        "schema_unknown": "Unknown schema (table=%s)",
        "folder_not_found": "Folder not found: %s",
        "folder_open_err": "Error opening folder: %s",
        "alt_no_preview": "No preview",
        "alt_pick_first": "Select a cover first.",
        "downloading": "Downloading...",
        "no_success": "no success",
        "logs_unity_names": "Names updated via XboxUnity.",
        "logs_scanning": "Scanning: %s",
        "logs_no_index": "Warning: x360db index did not load; no DLC/update filter.",
        "logs_ignored_dlc": "Ignored %d DLC/update TitleIDs (not in the games index).",
        "logs_god_xdlc": "GOD/XDLC games on HDD without a GameData folder: %d (will be handled via Import)",
        "logs_fetch_names": "Fetching %d names from XboxUnity...",
        "logs_title_x360db": "Title found on x360db: %s",
        "logs_title_unity": "Title found on XboxUnity: %s",
        "logs_title_folder": "Using folder name: %s",
        "logs_title_not_found": "No title found for %s",
        "logs_title_none_idlike": "No games with a TitleID-like name to fix.",
        "logs_titles_updated": "Names fixed: %d.",
        "logs_title_nochange": "Names are already correct.",
        "logs_updating_db": "Updating content.db: TID=%s -> %s",
        "logs_db_err": "Error updating content.db: %s",
        "logs_renamed_folder": "Folder renamed: %s -> %s",
        "logs_folder_open_err": "Error opening folder: %s",
        "logs_gamedata_created": "GameData folder created: %s",
        "logs_queue_started": "Starting queue: %d game(s)",
        "logs_custom_installed": "Custom cover installed for %s (%s)",
        "logs_assets_exported": "Assets exported to %s: %s",
        "assets_exported_ok": "Assets exported to game_covers/%s\n%d file(s) copied.",
        "assets_folder_created_empty": "Folder created: game_covers/%s\n%s\n(No installed assets found — add your files manually).",
        "logs_no_assets_to_export": "No installed assets to export: %s",
        "no_assets_to_export": "No installed assets found to export.",
        "logs_ftp_sent": "FTP: %d file(s) sent to %s.",
        "logs_ftp_err": "FTP error: %s",
        "ftp_inaccessible": "FTP: cannot access %s (%s)",
        "logs_downloading": "Downloading %s for %s (%s)...",
        "logs_downloading_assets": "Downloading all assets for %s...",
        "logs_rename_folder_err": "Could not rename the folder: %s",
        "logs_no_dedicated_gamedata": "No dedicated GameData folder for %s; rename saved only in the list.",
        "logs_db_titlename_ok": "content.db: TitleName updated to '%s'.",
        "logs_db_row_not_found": "content.db: row %s not found (name saved only in config).",
        "logs_db_rename_err": "content.db: could not rename: %s",
        "logs_folders_removed": "%d folder(s) removed",
        "logs_progress_game": "[%d/%d] %s (%s)",
        "logs_game_err": "Error in this game: %s",
        "logs_cover_fetch_err": "Error fetching cover: %s",
        "logs_hb_tid_by_name": "Homebrew: XboxUnity TID by name '%s' = %s",
        "logs_hb_no_cover_by_name": "Homebrew: no cover by name on XboxUnity (%s)",
        "logs_unity_offline": "XboxUnity is offline (%s)",
        "unity_no_cover": "XboxUnity has no covers for %s",
        "unity_black_cover": "Empty/black cover ignored (buggy) on XboxUnity.",
        "unity_no_usable": "XboxUnity has no usable cover (%s)",
        "cover_not_found_repo": "Cover not found in the repository.",
        "background_not_found": "Background not found on x360db.",
        "kind_not_found": "%s not found on x360db.",
        "no_screenshots": "No screenshots available on x360db.",
        "logs_ss_installed": "%d screenshot(s) installed.",
        "logs_dl_kind_err": "Error downloading %s: %s",
        "logs_saved": "Saved %s",
        "logs_alt_import": "Alternative import at %s",
        "logs_kind_result": "%s: %s",
        "logs_kind_err": "Error: %s",
        "logs_kind_err_with": "%s: error: %s",
        "logs_kind_skip": "%s: already installed (skipping).",
        "unity_fetch_fail": "Failed to download the cover from XboxUnity.",
        "logs_alt_installed": "Alternative cover installed for %s (%s).",
        "logs_alt_err": "Error: %s",
    },
    "es": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
        "gameart_status": "360-Game-Art:",
        "checking": "verificando...",
        "connected": "conectado",
        "disconnected": "desconectado",
        "aurora_folder": "Carpeta de Aurora:",
        "browse": "Examinar...",
        "opt_boxart": "Descargar portada (boxart)",
        "opt_background": "Descargar fondo",
        "opt_force": "Forzar re-descarga",
        "opt_backup": "Copia de seguridad antes de sobrescribir",
        "opt_icon": "Descargar icono (64x64)",
        "opt_banner": "Descargar banner",
        "opt_screenshots": "Descargar screenshots (hasta %d)",
        "info_note": "La información (título/descripción) proviene de x360db y se usa en el panel.",
        "scan": "Escanear juegos",
        "download": "Descargar e instalar assets",
        "custom_cover": "Portada personalizada...",
        "settings": "Configuración...",
        "tip_right_click": "Consejo: clic derecho en un juego para ver/cambiar assets.",
        "cancel": "Cancelar",
        "col_tid": "TitleID",
        "col_game": "Juego",
        "col_status": "Estado",
        "preview_title": "Vista previa de la portada",
        "no_selection": "Sin selección",
        "no_cover": "Sin portada",
        "no_cover_installed": "Sin portada instalada",
        "cover_installed": "Portada instalada",
        "loading_info": "Cargando información...",
        "loading_index": "Cargando índice de x360db, espere...",
        "index_loaded": "Índice de x360db cargado: %d juegos.",
        "index_fail": "No se pudo descargar el índice (modo offline: usará TitleID directamente).",
        "warn": "Advertencia",
        "info": "Información",
        "scan_first": "Escanee los juegos primero.",
        "pick_art": "Marque al menos un tipo de arte (portada, fondo, icono, banner o screenshots).",
        "pick_aurora": "Elija la carpeta raíz de Aurora primero.",
        "not_aurora_folder": "La carpeta seleccionada no parece una instalación de Aurora (falta Data/GameData o carpeta Aurora).",
        "pick_game": "Seleccione un juego en la lista primero.",
        "img_open_fail": "No se pudo abrir la imagen:\n%s",
        "img_write_fail": "No se pudo escribir:\n%s",
        "save_fail": "No se pudo guardar:\n%s",
        "warn": "Advertencia",
        "error": "Error",
        "pick_game": "Seleccione un juego en la lista primero.",
        "custom_cover": "Portada personalizada",
        "m_assets": "Ver/cambiar assets de este juego...",
        "m_alt": "Portadas alternativas online...",
        "m_custom": "Portada personalizada...",
        "m_export_assets": "Exportar assets a game_covers...",
        "set_theme": "Tema:",
        "theme_dark": "Oscuro",
        "theme_light": "Claro",
        "theme_system": "Seguir sistema",
        "dest": "Destino",
        "set_lang": "Idioma:",
        "set_show_status": "Mostrar puntos de estado de Internet arriba",
        "set_repo": "Repositorio de portadas:",
        "set_format": "Formato de portada:",
        "format_portrait": "Retrato (900x1233)",
        "format_landscape": "Paisaje (900x600)",
        "set_screenshots": "Screenshots por juego:",
        "status_saved": "Configuración guardada (tema: %s, repo: %s, portada: %s, screenshots: %d, región: %s).",
        "save": "Guardar",
        "cancel2": "Cancelar",
        "restart_title": "Reiniciar app",
        "restart_lang": "El idioma cambia al reiniciar la app (cierre y abra de nuevo).",
        "assets": "Assets",
        "assets_of": "Assets de",
        "col_kind": "Tipo",
        "col_status": "Estado",
        "dl_online": "Descargar online",
        "dl_all": "Descargar todos",
        "dl_all_start": "Descargando todos los assets de este juego...",
        "dl_all_log": "Descargando todos los assets de %s (%s)...",
        "change_pc": "Cambiar... (PC)",
        "close": "Cerrar",
        "assets_hint": "Seleccione un tipo y use los botones.",
        "assets_installed": "Instalado",
        "assets_missing": "Ausente",
        "assets_pick": "Seleccione un tipo en la lista primero.",
        "assets_dl_kind": "Descargando %s...",
        "no_preview": "Sin vista previa",
        "pick_kind": "Elegir %s para %s",
        "kind_boxart": "portada (boxart)",
        "kind_background": "fondo (background)",
        "kind_icon": "icono",
        "kind_banner": "banner",
        "kind_screenshots": "screenshot",
        "asset_changed": "Asset '%s' cambiado para %s (%s).",
        "m_assets": "Ver/cambiar assets de este juego...",
        "m_alt": "Portadas alternativas online...",
        "m_custom": "Portada personalizada...",
        "m_export_assets": "Exportar assets a game_covers...",
        "set_title": "Configuración",
        "set_theme": "Tema:",
        "theme_dark": "Oscuro",
        "theme_light": "Claro",
        "theme_system": "Seguir tema del sistema",
        "set_repo": "Repositorio de portadas:",
        "set_format": "Formato de portada:",
        "format_portrait": "Retrato (900x1233)",
        "format_landscape": "Paisaje (900x600)",
        "set_screenshots": "Screenshots por juego:",
        "set_lang": "Idioma:",
        "set_show_status": "Mostrar puntos de estado de conexión",
        "save": "Guardar",
        "cancel2": "Cancelar",
        "restart_title": "Idioma",
        "restart_lang": "Reinicie la aplicación para aplicar el idioma.",
        "assets_title": "Assets - %s (%s)",
        "assets_header": "Assets de %s (%s)",
        "assets_kind": "Tipo",
        "assets_status": "Estado",
        "assets_pick": "Seleccione un tipo y use los botones.",
        "assets_ok": "Instalado",
        "assets_missing": "Ausente",
        "assets_online": "Descargar online",
        "assets_pc": "Cambiar... (PC)",
        "assets_close": "Cerrar",
        "assets_dl_kind": "Descargar %s...",
        "no_preview": "Sin vista previa",
        "assets_pick_kind": "Seleccione un tipo en la lista primero.",
        "alt_title": "Portadas alternativas - %s (%s)",
        "alt_label": "Portadas disponibles en XboxUnity (elija una):",
        "alt_searching": "Buscando portadas en XboxUnity...",
        "alt_none": "No se encontraron portadas en XboxUnity para este juego.",
        "alt_count": "%d portada(s) encontrada(s).",
        "alt_loading": "Cargando vista previa...",
        "alt_none_found": "No se encontraron portadas en XboxUnity para este juego.",
        "alt_no_img": "Sin imagen",
        "alt_no_preview": "Sin vista previa para esta portada.",
        "alt_loaded": "Vista previa cargada.",
        "alt_noimg": "Sin imagen",
        "alt_preview_ok": "Vista previa cargada.",
        "alt_preview_none": "Sin vista previa para esta portada.",
        "alt_sem_preview": "Sin vista previa",
        "alt_install": "Descargar e instalar esta portada",
        "alt_official": "Portada oficial (x360db)",
        "alt_unity_empty": "Buscado: XboxUnity no tiene portada para este juego; mostrando la oficial (x360db).",
        "alt_installed": "Portada instalada con éxito.",
        "alt_failed": "Falló la instalación de la portada.",
        "alt_select_first": "Seleccione una portada primero.",
        "alt_downloading": "Descargando...",
        "status_saved": "Configuración guardada (tema: %s, repo: %s, portada: %s, screenshots: %d).",
        "canceled": "Operación cancelada por el usuario.",
        "unity_fallback": "XboxUnity sin portada usable; usando x360db como alternativa.",
        "unity_no_cover": "XboxUnity sin portadas para %s; usando x360db como alternativa.",
        "unity_offline": "XboxUnity fuera de línea; usando x360db.",
        "no_games_notice": "Ningún juego necesita descarga.",
        "done_notice": "¡Hecho! En Xbox: inicie Aurora y pulse Y -> Refresh en el juego (o use Import).",
        "set_log": "Mostrar registro (cuadro de texto)",
        "cover_missing_both": "  portada no encontrada en x360db ni XboxUnity.",
        "gameart_cover_ok": "  portada de 360-Game-Art para %s.",
        "game_cover_ok": "  portada local (game_covers) para %s.",
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Buscar título...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Buscar títulos automaticamente (XboxUnity)",
        "auto_search_on": "Busca automática de títulos LIGADA.",
        "auto_search_off": "Busca automática de títulos DESLIGADA.",
        "show_game_info": "Mostrar director y fecha de lanzamiento",
        "show_debug_button": "Mostrar botón Debug DB",
        "auto_update_check": "Buscar actualizaciones automáticamente",
        "update_available_title": "Actualización disponible",
        "update_available_msg": "Hay una nueva versión ({0}) disponible! Versión actual: {1}\n\n¿Abrir página de descargas?",
        "download_missing_only": "Descargar solo juegos sin portada",
        "m_search": "Buscar título...",
        "m_rename": "Renombrar juego",
        "rename_prompt": "Nuevo nombre para %s (%s):",
        "renamed": "Juego %s renombrado a: %s",
        "ok": "Aceptar",
        "add_game": "Agregar juegos...",
        "add_game_tid": "Title ID (8 dígitos hex; opcional si se detecta):",
        "add_game_xex": "Archivo .xex (detectar TID):",
        "add_game_folder": "Carpeta para buscar juegos:",
        "add_game_folder_note": "Busca varios juegos (.xex) dentro de la carpeta elegida, uno por subcarpeta.",
        "add_game_name": "Nombre (opcional):",
        "add_game_mkdir": "Crear carpeta GameData en el disco",
        "add_game_bad_tid": "Title ID no válido (usa 8 dígitos hex, ej.: 5841120F).",
        "add_game_exists": "Este juego ya está en la lista.",
        "add_game_need_name": "Introduce un nombre para crear la carpeta.",
        "add_game_added": "Juego agregado: %s (%s)",
        "add_game_folder_done": "Carpeta escaneada: %d juego(s) agregado(s) de %s.",
        "manage_folders": "Gestionar carpetas...",
        "db_editor": "Base de datos de Aurora (content.db)",
        "db_add": "Agregar...",
        "db_rename": "Renombrar...",
        "db_remove": "Eliminar...",
        "db_reload": "Actualizar",
        "db_backup": "Copia creada: %s",
        "db_warn1": "Edita solo con Aurora cerrado y disco libre (la BD se bloquea mientras se usa). Se crea una copia automática (.bak) antes de cada cambio.",
        "db_nodb": "No se encontró content.db de Aurora. Conecta el disco y escanea antes.",
        "db_need_id": "Selecciona una entrada de la lista.",
        "db_new_tid": "Title ID (8 dígitos hex):",
        "db_new_name": "Nombre:",
        "db_new_dir": "Carpeta relativa (ej.: \\Content\\0000000000000000\\5841120F):",
        "db_added": "Entrada agregada: %s (%s)",
        "db_renamed": "Entrada renombrada: %s",
        "db_removed": "Entrada eliminada: %s",
        "db_confirm_remove": "¿Eliminar '%s' del registro? El contenido en disco NO se borra.",
        "db_only_dlc": "Solo DLC / XBLA / TU",
        "db_filter": "Tipo:",
        "db_all": "Todos",
        "db_search": "Buscar nombre, TID o carpeta...",
        "filter_games": "Buscar juegos: ",
        "db_need_name": "Introduce un nombre.",
        "rename_ftp_start": "Renombrando carpeta en la consola por FTP...",
        "rename_ftp_ok": "Carpeta renombrada en la consola: %s",
        "rename_ftp_err": "No se pudo renombrar en la consola: %s",
        "m_open_folder": "Abrir carpeta del juego",
        "m_remove_cover": "Eliminar portada instalada",
        "m_remove_game": "Quitar de la lista",
        "m_restore_hidden": "Restaurar juegos eliminados...",
        "remove_cover_confirm": "¿Eliminar la portada instalada de '%s' (%s)?\nBorra GC<tid>.asset y la portada de Import.",
        "cover_removed": "Portada eliminada de %s (%s).",
        "cover_none_found": "No se encontró portada para %s (%s).",
        "remove_game_confirm": "¿Quitar '%s' (%s) de la lista? El contenido en disco NO se borra.",
        "game_removed": "Juego %s (%s) eliminado de la lista.",
        "restore_hidden_confirm": "¿Restaurar %d juego(s) eliminado(s) de la lista?",
        "restore_hidden_done": "Se restauraron todos los juegos eliminados.",
        "set_ftp": "Enviar por FTP (consola):",
        "ftp_host_lbl": "IP de la consola:",
        "ftp_port_lbl": "Puerto:",
        "ftp_user_lbl": "Usuario:",
        "ftp_pass_lbl": "Contraseña:",
        "ftp_base_lbl": "Carpeta remota (GameData):",
        "ftp_send": "Enviar por FTP",
        "ftp_sending": "Enviando a la consola por FTP...",
        "ftp_deploy_covers": "Enviar assets de game_covers",
        "ftp_deploying": "Enviando assets de game_covers...",
        "ftp_deploy_ok": "Assets enviados: %d archivo(s) a %s",
        "ftp_deploy_no_folder": "No se encontró carpeta game_covers para este juego.",
        "ftp_sent": "Enviados %d archivo(s) a %s.",
        "ftp_no_host": "Configure la IP de la consola en Configuración -> FTP primero.",
        "ftp_no_folder": "Este juego no tiene carpeta local en Data\\GameData para enviar.",
        "ftp_err": "Error en FTP: %s",
        "ss_prev": "◀",
        "ss_next": "▶",
        "credits": "Desarrollado por Atreus171\nhttps://github.com/Atreus171/Aurora-Asset-Manager",
        "release_date": "Lanzamiento",
        "developer": "Desarrolladora",
        "genres": "Géneros",
        "settings_title": "Configuración",
        "db_notfound": "content.db no encontrado",
        "err_generic": "Error: %s",
        "no_folders": "Aún no hay carpetas añadidas.",
        "folders_header": "Carpetas añadidas (vía 'Carpeta para buscar juegos'):",
        "col_folder": "Carpeta",
        "col_added": "Añadida el",
        "col_count": "Juegos",
        "col_type": "Tipo",
        "remove_folders_confirm": "¿Eliminar %d carpeta(s) seleccionada(s)?",
        "open_folder": "Abrir carpeta",
        "remove_selected": "Eliminar seleccionadas",
        "schema_unknown": "Esquema desconocido (tabla=%s)",
        "folder_not_found": "Carpeta no encontrada: %s",
        "folder_open_err": "Error al abrir carpeta: %s",
        "alt_no_preview": "Sin vista previa",
        "alt_pick_first": "Seleccione una portada primero.",
        "downloading": "Descargando...",
        "no_success": "sin éxito",
        "logs_unity_names": "Nombres actualizados vía XboxUnity.",
        "logs_scanning": "Escaneando: %s",
        "logs_no_index": "Aviso: el índice de x360db no cargó; sin filtro de DLC/updates.",
        "logs_ignored_dlc": "Ignorados %d TitleIDs de DLC/update (no constan en el índice de juegos).",
        "logs_god_xdlc": "Juegos GOD/XDLC en HDD sin carpeta GameData: %d (se tratarán vía Import)",
        "logs_fetch_names": "Buscando %d nombres en XboxUnity...",
        "logs_title_x360db": "Título encontrado en x360db: %s",
        "logs_title_unity": "Título encontrado en XboxUnity: %s",
        "logs_title_folder": "Usando nombre de carpeta: %s",
        "logs_title_not_found": "Título no encontrado para %s",
        "logs_title_none_idlike": "Ningún juego con nombre tipo TitleID que corregir.",
        "logs_titles_updated": "Nombres corregidos: %d.",
        "logs_title_nochange": "Los nombres ya son correctos.",
        "logs_updating_db": "Actualizando content.db: TID=%s -> %s",
        "logs_db_err": "Error al actualizar content.db: %s",
        "logs_renamed_folder": "Carpeta renombrada: %s -> %s",
        "logs_folder_open_err": "Error al abrir carpeta: %s",
        "logs_gamedata_created": "Carpeta GameData creada: %s",
        "logs_queue_started": "Iniciando cola: %d juego(s)",
        "logs_custom_installed": "Portada personalizada instalada para %s (%s)",
        "logs_assets_exported": "Assets exportados a %s: %s",
        "assets_exported_ok": "Assets exportados a game_covers/%s\n%d archivo(s) copiado(s).",
        "assets_folder_created_empty": "Carpeta creada: game_covers/%s\n%s\n(No se encontraron assets instalados — agregue sus archivos manualmente).",
        "logs_no_assets_to_export": "No hay assets instalados para exportar: %s",
        "no_assets_to_export": "No se encontraron assets instalados para exportar.",
        "logs_ftp_sent": "FTP: %d archivo(s) enviado(s) a %s.",
        "logs_ftp_err": "Error de FTP: %s",
        "ftp_inaccessible": "FTP: no se puede acceder a %s (%s)",
        "logs_downloading": "Descargando %s para %s (%s)...",
        "logs_downloading_assets": "Descargando todos los assets de %s...",
        "logs_rename_folder_err": "No se pudo renombrar la carpeta: %s",
        "logs_no_dedicated_gamedata": "Sin carpeta GameData dedicada para %s; el renombrado se guarda solo en la lista.",
        "logs_db_titlename_ok": "content.db: TitleName actualizado a '%s'.",
        "logs_db_row_not_found": "content.db: fila %s no encontrada (nombre guardado solo en configuración).",
        "logs_db_rename_err": "content.db: no se pudo renombrar: %s",
        "logs_folders_removed": "%d carpeta(s) eliminada(s)",
        "logs_progress_game": "[%d/%d] %s (%s)",
        "logs_game_err": "Error en este juego: %s",
        "logs_cover_fetch_err": "Error al buscar portada: %s",
        "logs_hb_tid_by_name": "Homebrew: TID de XboxUnity por nombre '%s' = %s",
        "logs_hb_no_cover_by_name": "Homebrew: sin portada por nombre en XboxUnity (%s)",
        "logs_unity_offline": "XboxUnity fuera de línea (%s)",
        "unity_no_cover": "XboxUnity sin portadas para %s",
        "unity_black_cover": "Portada vacía/negra ignorada (defectuosa) en XboxUnity.",
        "unity_no_usable": "XboxUnity sin portada utilizable (%s)",
        "cover_not_found_repo": "Portada no encontrada en el repositorio.",
        "background_not_found": "Fondo no encontrado en x360db.",
        "kind_not_found": "%s no encontrado en x360db.",
        "no_screenshots": "Sin capturas disponibles en x360db.",
        "logs_ss_installed": "%d captura(s) instalada(s).",
        "logs_dl_kind_err": "Error al descargar %s: %s",
        "logs_saved": "Guardado %s",
        "logs_alt_import": "Importación alternativa en %s",
        "logs_kind_result": "%s: %s",
        "logs_kind_err": "Error: %s",
        "logs_kind_err_with": "%s: error: %s",
        "logs_kind_skip": "%s: ya instalado (saltando).",
        "unity_fetch_fail": "Fallo al descargar la portada de XboxUnity.",
        "logs_alt_installed": "Portada alternativa instalada para %s (%s).",
        "logs_alt_err": "Error: %s",
    },
    "fr": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
        "gameart_status": "360-Game-Art:",
        "checking": "vérification...",
        "connected": "connecté",
        "disconnected": "déconnecté",
        "aurora_folder": "Dossier Aurora:",
        "browse": "Parcourir...",
        "opt_boxart": "Télécharger la jaquette (boxart)",
        "opt_background": "Télécharger l'arrière-plan",
        "opt_force": "Forcer le re-téléchargement",
        "opt_backup": "Sauvegarde avant d'écraser",
        "opt_icon": "Télécharger l'icône (64x64)",
        "opt_banner": "Télécharger la bannière",
        "opt_screenshots": "Télécharger les captures (jusqu'à %d)",
        "info_note": "Les infos (titre/description) viennent de x360db et sont utilisées dans le panneau.",
        "scan": "Scanner les jeux",
        "download": "Télécharger et installer les assets",
        "custom_cover": "Jaquette personnalisée...",
        "settings": "Paramètres...",
        "tip_right_click": "Astuce: clic droit sur un jeu pour voir/changer les assets.",
        "cancel": "Annuler",
        "col_tid": "TitleID",
        "col_game": "Jeu",
        "col_status": "État",
        "preview_title": "Aperçu de la jaquette",
        "no_selection": "Aucune sélection",
        "no_cover": "Pas de jaquette",
        "no_cover_installed": "Aucune jaquette installée",
        "cover_installed": "Jaquette installée",
        "loading_info": "Chargement des informations...",
        "loading_index": "Chargement de l'index x360db, veuillez patienter...",
        "index_loaded": "Index x360db chargé: %d jeux.",
        "index_fail": "Impossible de télécharger l'index (mode hors ligne: utilisera le TitleID).",
        "warn": "Avertissement",
        "info": "Informations",
        "scan_first": "Scannez les jeux d'abord.",
        "pick_art": "Cochez au moins un type d'art (jaquette, fond, icône, bannière ou captures).",
        "pick_aurora": "Choisissez le dossier racine d'Aurora d'abord.",
        "not_aurora_folder": "Le dossier sélectionné ne semble pas être une installation Aurora (manque Data/GameData ou dossier Aurora).",
        "pick_game": "Sélectionnez un jeu dans la liste d'abord.",
        "img_open_fail": "Impossible d'ouvrir l'image:\n%s",
        "img_write_fail": "Impossible d'écrire:\n%s",
        "save_fail": "Impossible de sauvegarder:\n%s",
        "warn": "Avertissement",
        "error": "Erreur",
        "pick_game": "Sélectionnez un jeu dans la liste d'abord.",
        "custom_cover": "Jaquette personnalisée",
        "m_assets": "Voir/modifier les assets de ce jeu...",
        "m_alt": "Jaquettes alternatives en ligne...",
        "m_custom": "Jaquette personnalisée...",
        "m_export_assets": "Exporter les assets vers game_covers...",
        "set_theme": "Thème:",
        "theme_dark": "Sombre",
        "theme_light": "Clair",
        "theme_system": "Suivre le système",
        "dest": "Destination",
        "set_lang": "Langue:",
        "set_show_status": "Afficher les points d'état Internet en haut",
        "set_repo": "Dépôt de jaquettes:",
        "set_format": "Format de jaquette:",
        "format_portrait": "Portrait (900x1233)",
        "format_landscape": "Paysage (900x600)",
        "set_screenshots": "Captures par jeu:",
        "status_saved": "Paramètres enregistrés (thème: %s, dépôt: %s, jaquette: %s, captures: %d, région: %s).",
        "save": "Enregistrer",
        "cancel2": "Annuler",
        "restart_title": "Redémarrer l'app",
        "restart_lang": "La langue change au redémarrage de l'app (fermez et rouvrez).",
        "assets": "Assets",
        "assets_of": "Assets de",
        "col_kind": "Type",
        "col_status": "État",
        "dl_online": "Télécharger en ligne",
        "dl_all": "Tout télécharger",
        "dl_all_start": "Téléchargement de tous les assets de ce jeu...",
        "dl_all_log": "Téléchargement de tous les assets de %s (%s)...",
        "change_pc": "Changer... (PC)",
        "close": "Fermer",
        "assets_hint": "Sélectionnez un type et utilisez les boutons.",
        "assets_installed": "Installé",
        "assets_missing": "Manquant",
        "assets_pick": "Sélectionnez un type dans la liste d'abord.",
        "assets_dl_kind": "Téléchargement de %s...",
        "no_preview": "Pas d'aperçu",
        "pick_kind": "Choisir %s pour %s",
        "kind_boxart": "jaquette (boxart)",
        "kind_background": "arrière-plan",
        "kind_icon": "icône",
        "kind_banner": "bannière",
        "kind_screenshots": "capture",
        "asset_changed": "Asset '%s' modifié pour %s (%s).",
        "m_assets": "Voir/modifier les assets de ce jeu...",
        "m_alt": "Jaquettes alternatives en ligne...",
        "m_custom": "Jaquette personnalisée...",
        "m_export_assets": "Exporter les assets vers game_covers...",
        "set_title": "Paramètres",
        "set_theme": "Thème:",
        "theme_dark": "Sombre",
        "theme_light": "Clair",
        "theme_system": "Suivre le thème du système",
        "set_repo": "Dépôt de jaquettes:",
        "set_format": "Format de jaquette:",
        "format_portrait": "Portrait (900x1233)",
        "format_landscape": "Paysage (900x600)",
        "set_screenshots": "Captures par jeu:",
        "set_lang": "Langue:",
        "set_show_status": "Afficher les points d'état de connexion",
        "save": "Enregistrer",
        "cancel2": "Annuler",
        "restart_title": "Langue",
        "restart_lang": "Redémarrez l'application pour appliquer la langue.",
        "assets_title": "Assets - %s (%s)",
        "assets_header": "Assets de %s (%s)",
        "assets_kind": "Type",
        "assets_status": "État",
        "assets_pick": "Sélectionnez un type et utilisez les boutons.",
        "assets_ok": "Installé",
        "assets_missing": "Manquant",
        "assets_online": "Télécharger en ligne",
        "assets_pc": "Changer... (PC)",
        "assets_close": "Fermer",
        "assets_dl_kind": "Télécharger %s...",
        "no_preview": "Pas d'aperçu",
        "assets_pick_kind": "Sélectionnez un type dans la liste d'abord.",
        "alt_title": "Jaquettes alternatives - %s (%s)",
        "alt_label": "Jaquettes disponibles sur XboxUnity (choisissez-en une):",
        "alt_searching": "Recherche de jaquettes sur XboxUnity...",
        "alt_none": "Aucune jaquette trouvée sur XboxUnity pour ce jeu.",
        "alt_count": "%d jaquette(s) trouvée(s).",
        "alt_loading": "Chargement de l'aperçu...",
        "alt_none_found": "Aucune jaquette trouvée sur XboxUnity pour ce jeu.",
        "alt_no_img": "Pas d'image",
        "alt_no_preview": "Pas d'aperçu pour cette jaquette.",
        "alt_loaded": "Aperçu chargé.",
        "alt_noimg": "Pas d'image",
        "alt_preview_ok": "Aperçu chargé.",
        "alt_preview_none": "Pas d'aperçu pour cette jaquette.",
        "alt_sem_preview": "Pas d'aperçu",
        "alt_install": "Télécharger et installer cette jaquette",
        "alt_official": "Jaquette officielle (x360db)",
        "alt_unity_empty": "Recherché: XboxUnity n'a pas de jaquette pour ce jeu; affichage de l'officielle (x360db).",
        "alt_installed": "Jaquette installée avec succès.",
        "alt_failed": "Échec de l'installation de la jaquette.",
        "alt_select_first": "Sélectionnez une jaquette d'abord.",
        "alt_downloading": "Téléchargement...",
        "status_saved": "Paramètres enregistrés (thème: %s, dépôt: %s, jaquette: %s, captures: %d).",
        "canceled": "Opération annulée par l'utilisateur.",
        "unity_fallback": "XboxUnity sans jaquette utilisable; utilisation de x360db comme alternative.",
        "unity_no_cover": "XboxUnity sans jaquettes pour %s; utilisation de x360db comme alternative.",
        "unity_offline": "XboxUnity hors ligne; utilisation de x360db.",
        "no_games_notice": "Aucun jeu ne nécessite de téléchargement.",
        "done_notice": "Terminé! Sur Xbox: démarrez Aurora et appuyez Y -> Refresh sur le jeu (ou utilisez Import).",
        "set_log": "Afficher le journal (zone de texte)",
        "cover_missing_both": "  jaquette non trouvée sur x360db ni XboxUnity.",
        "gameart_cover_ok": "  jaquette 360-Game-Art pour %s.",
        "game_cover_ok": "  jaquette locale (game_covers) pour %s.",
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Rechercher titre...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Recherche auto des titres (XboxUnity)",
        "auto_search_on": "Recherche auto des titres ACTIVÉE.",
        "auto_search_off": "Recherche auto des titres DÉSACTIVÉE.",
        "show_game_info": "Afficher le développeur et la date de sortie",
        "show_debug_button": "Afficher bouton Debug DB",
        "auto_update_check": "Vérifier les mises à jour automatiquement",
        "update_available_title": "Mise à jour disponible",
        "update_available_msg": "Une nouvelle version ({0}) est disponible! Version actuelle: {1}\n\nOuvrir la page de téléchargement?",
        "download_missing_only": "Télécharger uniquement les jeux sans jaquette",
        "m_search": "Rechercher titre...",
        "m_rename": "Renommer le jeu",
        "rename_prompt": "Nouveau nom pour %s (%s):",
        "renamed": "Jeu %s renommé en: %s",
        "ok": "OK",
        "add_game": "Ajouter des jeux...",
        "add_game_tid": "Title ID (8 chiffres hex ; optionnel si détecté) :",
        "add_game_xex": "Fichier .xex (détecter le TID) :",
        "add_game_folder": "Dossier pour rechercher des jeux :",
        "add_game_folder_note": "Recherche plusieurs jeux (.xex) dans le dossier choisi, un par sous-dossier.",
        "add_game_name": "Nom (optionnel) :",
        "add_game_mkdir": "Créer le dossier GameData sur le disque",
        "add_game_bad_tid": "Title ID invalide (utilisez 8 chiffres hex, ex. : 5841120F).",
        "add_game_exists": "Ce jeu est déjà dans la liste.",
        "add_game_need_name": "Entrez un nom pour créer le dossier.",
        "add_game_added": "Jeu ajouté : %s (%s)",
        "add_game_folder_done": "Dossier scanné : %d jeu(x) ajouté(s) depuis %s.",
        "manage_folders": "Gérer les dossiers...",
        "db_editor": "Base de données Aurora (content.db)",
        "db_add": "Ajouter...",
        "db_rename": "Renommer...",
        "db_remove": "Supprimer...",
        "db_reload": "Actualiser",
        "db_backup": "Sauvegarde créée : %s",
        "db_warn1": "Éditez uniquement avec Aurora fermé et le disque au repos (la base est verrouillée pendant l'usage). Une sauvegarde automatique (.bak) est créée avant chaque modification.",
        "db_nodb": "content.db d'Aurora introuvable. Connectez le disque et scannez d'abord.",
        "db_need_id": "Sélectionnez une entrée de la liste.",
        "db_new_tid": "Title ID (8 chiffres hex) :",
        "db_new_name": "Nom :",
        "db_new_dir": "Dossier relatif (ex. : \\Content\\0000000000000000\\5841120F) :",
        "db_added": "Entrée ajoutée : %s (%s)",
        "db_renamed": "Entrée renommée : %s",
        "db_removed": "Entrée supprimée : %s",
        "db_confirm_remove": "Supprimer '%s' du registre ? Le contenu sur le disque n'est PAS effacé.",
        "db_only_dlc": "Uniquement DLC / XBLA / TU",
        "db_filter": "Type :",
        "db_all": "Tous",
        "db_search": "Rechercher nom, TID ou dossier...",
        "filter_games": "Rechercher des jeux : ",
        "db_need_name": "Entrez un nom.",
        "rename_ftp_start": "Renommage du dossier sur la console via FTP...",
        "rename_ftp_ok": "Dossier renommé sur la console : %s",
        "rename_ftp_err": "Impossible de renommer sur la console : %s",
        "m_open_folder": "Ouvrir le dossier du jeu",
        "m_remove_cover": "Supprimer la jaquette installée",
        "m_remove_game": "Retirer de la liste",
        "m_restore_hidden": "Restaurer les jeux retirés...",
        "remove_cover_confirm": "Supprimer la jaquette installée de '%s' (%s) ?\nSupprime GC<tid>.asset et la jaquette d'Import.",
        "cover_removed": "Jaquette supprimée de %s (%s).",
        "cover_none_found": "Aucune jaquette trouvée pour %s (%s).",
        "remove_game_confirm": "Retirer '%s' (%s) de la liste ? Le contenu sur disque n'est PAS supprimé.",
        "game_removed": "Jeu %s (%s) retiré de la liste.",
        "restore_hidden_confirm": "Restaurer %d jeu(x) retiré(s) de la liste ?",
        "restore_hidden_done": "Tous les jeux retirés ont été restaurés.",
        "set_ftp": "Envoyer par FTP (console):",
        "ftp_host_lbl": "IP de la console:",
        "ftp_port_lbl": "Port:",
        "ftp_user_lbl": "Utilisateur:",
        "ftp_pass_lbl": "Mot de passe:",
        "ftp_base_lbl": "Dossier distant (GameData):",
        "ftp_send": "Envoyer par FTP",
        "ftp_sending": "Envoi vers la console par FTP...",
        "ftp_deploy_covers": "Déployer assets de game_covers",
        "ftp_deploying": "Déploiement des assets de game_covers...",
        "ftp_deploy_ok": "Assets déployés: %d fichier(s) vers %s",
        "ftp_deploy_no_folder": "Aucun dossier game_covers trouvé pour ce jeu.",
        "ftp_sent": "%d fichier(s) envoyé(s) à %s.",
        "ftp_no_host": "Définissez l'IP de la console dans Paramètres -> FTP d'abord.",
        "ftp_no_folder": "Ce jeu n'a pas de dossier local Data\\GameData à envoyer.",
        "ftp_err": "Erreur FTP: %s",
        "ss_prev": "◀",
        "ss_next": "▶",
        "credits": "Développé par Atreus171\nhttps://github.com/Atreus171/Aurora-Asset-Manager",
        "release_date": "Sortie",
        "developer": "Développeur",
        "genres": "Genres",
        "settings_title": "Paramètres",
        "db_notfound": "content.db introuvable",
        "err_generic": "Erreur : %s",
        "no_folders": "Aucun dossier ajouté pour l'instant.",
        "folders_header": "Dossiers ajoutés (via 'Dossier pour chercher des jeux') :",
        "col_folder": "Dossier",
        "col_added": "Ajouté le",
        "col_count": "Jeux",
        "col_type": "Type",
        "remove_folders_confirm": "Supprimer %d dossier(s) sélectionné(s) ?",
        "open_folder": "Ouvrir le dossier",
        "remove_selected": "Supprimer la sélection",
        "schema_unknown": "Schéma inconnu (table=%s)",
        "folder_not_found": "Dossier introuvable : %s",
        "folder_open_err": "Erreur lors de l'ouverture du dossier : %s",
        "alt_no_preview": "Aucun aperçu",
        "alt_pick_first": "Sélectionnez d'abord une jaquette.",
        "downloading": "Téléchargement...",
        "no_success": "sans succès",
        "logs_unity_names": "Noms mis à jour via XboxUnity.",
        "logs_scanning": "Analyse : %s",
        "logs_no_index": "Attention : l'index x360db n'a pas chargé ; pas de filtre DLC/updates.",
        "logs_ignored_dlc": "%d TitleIDs de DLC/update ignorés (absents de l'index des jeux).",
        "logs_god_xdlc": "Jeux GOD/XDLC sur HDD sans dossier GameData : %d (traités via Import)",
        "logs_fetch_names": "Récupération de %d noms depuis XboxUnity...",
        "logs_title_x360db": "Titre trouvé sur x360db : %s",
        "logs_title_unity": "Titre trouvé sur XboxUnity : %s",
        "logs_title_folder": "Utilisation du nom de dossier : %s",
        "logs_title_not_found": "Aucun titre trouvé pour %s",
        "logs_title_none_idlike": "Aucun jeu avec un nom type TitleID à corriger.",
        "logs_titles_updated": "Noms corrigés : %d.",
        "logs_title_nochange": "Les noms sont déjà corrects.",
        "logs_updating_db": "Mise à jour de content.db : TID=%s -> %s",
        "logs_db_err": "Erreur de mise à jour de content.db : %s",
        "logs_renamed_folder": "Dossier renommé : %s -> %s",
        "logs_folder_open_err": "Erreur lors de l'ouverture du dossier : %s",
        "logs_gamedata_created": "Dossier GameData créé : %s",
        "logs_queue_started": "Démarrage de la file : %d jeu(x)",
        "logs_custom_installed": "Jaquette personnalisée installée pour %s (%s)",
        "logs_assets_exported": "Assets exportés vers %s: %s",
        "assets_exported_ok": "Assets exportés vers game_covers/%s\n%d fichier(s) copié(s).",
        "assets_folder_created_empty": "Dossier créé: game_covers/%s\n%s\n(Aucun asset installé trouvé — ajoutez vos fichiers manuellement).",
        "logs_no_assets_to_export": "Aucun asset installé à exporter: %s",
        "no_assets_to_export": "Aucun asset installé trouvé à exporter.",
        "logs_ftp_sent": "FTP : %d fichier(s) envoyé(s) vers %s.",
        "logs_ftp_err": "Erreur FTP : %s",
        "ftp_inaccessible": "FTP : impossible d'accéder à %s (%s)",
        "logs_downloading": "Téléchargement de %s pour %s (%s)...",
        "logs_downloading_assets": "Téléchargement de tous les assets de %s...",
        "logs_rename_folder_err": "Impossible de renommer le dossier : %s",
        "logs_no_dedicated_gamedata": "Pas de dossier GameData dédié pour %s ; le renommage n'est enregistré que dans la liste.",
        "logs_db_titlename_ok": "content.db : TitleName mis à jour vers '%s'.",
        "logs_db_row_not_found": "content.db : ligne %s introuvable (nom enregistré uniquement dans la config).",
        "logs_db_rename_err": "content.db : impossible de renommer : %s",
        "logs_folders_removed": "%d dossier(s) supprimé(s)",
        "logs_progress_game": "[%d/%d] %s (%s)",
        "logs_game_err": "Erreur dans ce jeu : %s",
        "logs_cover_fetch_err": "Erreur lors de la recherche de la jaquette : %s",
        "logs_hb_tid_by_name": "Homebrew : TID XboxUnity par nom '%s' = %s",
        "logs_hb_no_cover_by_name": "Homebrew : aucune jaquette par nom sur XboxUnity (%s)",
        "logs_unity_offline": "XboxUnity hors ligne (%s)",
        "unity_no_cover": "XboxUnity n'a pas de jaquette pour %s",
        "unity_black_cover": "Jaquette vide/noire ignorée (défectueuse) sur XboxUnity.",
        "unity_no_usable": "XboxUnity n'a pas de jaquette utilisable (%s)",
        "cover_not_found_repo": "Jaquette introuvable dans le dépôt.",
        "background_not_found": "Arrière-plan introuvable sur x360db.",
        "kind_not_found": "%s introuvable sur x360db.",
        "no_screenshots": "Aucune capture disponible sur x360db.",
        "logs_ss_installed": "%d capture(s) installée(s).",
        "logs_dl_kind_err": "Erreur de téléchargement de %s : %s",
        "logs_saved": "Enregistré %s",
        "logs_alt_import": "Import alternatif à %s",
        "logs_kind_result": "%s : %s",
        "logs_kind_err": "Erreur : %s",
        "logs_kind_err_with": "%s : erreur : %s",
        "logs_kind_skip": "%s : déjà installé (ignoré).",
        "unity_fetch_fail": "Échec du téléchargement de la jaquette depuis XboxUnity.",
        "logs_alt_installed": "Jaquette alternative installée pour %s (%s).",
        "logs_alt_err": "Erreur : %s",
    },
    "ja": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
        "gameart_status": "360-Game-Art:",
        "checking": "確認中...",
        "connected": "接続済み",
        "disconnected": "未接続",
        "aurora_folder": "Auroraフォルダ:",
        "browse": "参照...",
        "opt_boxart": "カバー(ボックスアート)をダウンロード",
        "opt_background": "背景をダウンロード",
        "opt_force": "再ダウンロードを強制",
        "opt_backup": "上書き前にバックアップ",
        "opt_icon": "アイコンをダウンロード (64x64)",
        "opt_banner": "バナーをダウンロード",
        "opt_screenshots": "スクリーンショットをダウンロード (最大 %d)",
        "info_note": "情報(タイトル/説明)はx360dbから取得し、パネルで使用されます。",
        "scan": "ゲームをスキャン",
        "download": "アセットをダウンロードしてインストール",
        "custom_cover": "カスタムカバー...",
        "settings": "設定...",
        "tip_right_click": "ヒント: ゲームを右クリックしてアセットを表示/変更。",
        "cancel": "キャンセル",
        "col_tid": "TitleID",
        "col_game": "ゲーム",
        "col_status": "状態",
        "preview_title": "カバープレビュー",
        "no_selection": "選択なし",
        "no_cover": "カバーなし",
        "no_cover_installed": "カバー未インストール",
        "cover_installed": "カバーインストール済み",
        "loading_info": "情報を読み込み中...",
        "loading_index": "x360dbインデックスを読み込み中、お待ちください...",
        "index_loaded": "x360dbインデックス読み込み完了: %d ゲーム。",
        "index_fail": "インデックスをダウンロードできませんでした (オフラインモード: TitleIDを直接使用)。",
        "warn": "警告",
        "info": "情報",
        "scan_first": "まずゲームをスキャンしてください。",
        "pick_art": "アートタイプを少なくとも1つ選択してください (カバー, 背景, アイコン, バナー, スクリーンショット)。",
        "pick_aurora": "まずAuroraのルートフォルダを選択してください。",
        "not_aurora_folder": "選択したフォルダはAuroraのインストールではないようです（Data/GameDataまたはAuroraフォルダがありません）。",
        "pick_game": "まずリストからゲームを選択してください。",
        "img_open_fail": "画像を開けません:\n%s",
        "img_write_fail": "書き込めません:\n%s",
        "save_fail": "保存できません:\n%s",
        "warn": "警告",
        "error": "エラー",
        "pick_game": "まずリストからゲームを選択してください。",
        "custom_cover": "カスタムカバー",
        "m_assets": "このゲームのアセットを表示/変更...",
        "m_alt": "オンラインで代替カバー...",
        "m_custom": "カスタムカバー...",
        "m_export_assets": "game_coversにアセットをエクスポート...",
        "set_theme": "テーマ:",
        "theme_dark": "ダーク",
        "theme_light": "ライト",
        "theme_system": "システムに従う",
        "dest": "保存先",
        "set_lang": "言語:",
        "set_show_status": "上部にインターネット状態ドットを表示",
        "set_repo": "カバーリポジトリ:",
        "set_format": "カバーフォーマット:",
        "format_portrait": "縦向き (900x1233)",
        "format_landscape": "横向き (900x600)",
        "set_screenshots": "ゲームあたりのスクリーンショット数:",
        "status_saved": "設定を保存しました (テーマ: %s, リポジトリ: %s, カバー: %s, スクリーンショット: %d, 地域: %s)。",
        "save": "保存",
        "cancel2": "キャンセル",
        "restart_title": "アプリを再起動",
        "restart_lang": "言語はアプリ再起動時に適用されます (終了して再度開く)。",
        "assets": "アセット",
        "assets_of": "のアセット",
        "col_kind": "種類",
        "col_status": "状態",
        "dl_online": "オンラインでダウンロード",
        "dl_all": "すべてダウンロード",
        "dl_all_start": "このゲームの全アセットをダウンロード中...",
        "dl_all_log": "%s (%s) の全アセットをダウンロード中...",
        "change_pc": "変更... (PC)",
        "close": "閉じる",
        "assets_hint": "種類を選択してボタンを使用します。",
        "assets_installed": "インストール済み",
        "assets_missing": "未インストール",
        "assets_pick": "まずリストから種類を選択してください。",
        "assets_dl_kind": "%s をダウンロード中...",
        "no_preview": "プレビューなし",
        "pick_kind": "%s を %s に選択",
        "kind_boxart": "カバー (ボックスアート)",
        "kind_background": "背景",
        "kind_icon": "アイコン",
        "kind_banner": "バナー",
        "kind_screenshots": "スクリーンショット",
        "asset_changed": "アセット '%s' が %s (%s) で変更されました。",
        "m_assets": "このゲームのアセットを表示/変更...",
        "m_alt": "オンラインで代替カバー...",
        "m_custom": "カスタムカバー...",
        "m_export_assets": "game_coversにアセットをエクスポート...",
        "set_title": "設定",
        "set_theme": "テーマ:",
        "theme_dark": "ダーク",
        "theme_light": "ライト",
        "theme_system": "システムのテーマに従う",
        "set_repo": "カバーリポジトリ:",
        "set_format": "カバーフォーマット:",
        "format_portrait": "縦向き (900x1233)",
        "format_landscape": "横向き (900x600)",
        "set_screenshots": "ゲームあたりのスクリーンショット数:",
        "set_lang": "言語:",
        "set_show_status": "接続状態ドットを表示",
        "save": "保存",
        "cancel2": "キャンセル",
        "restart_title": "言語",
        "restart_lang": "アプリを再起動して言語を適用してください。",
        "assets_title": "アセット - %s (%s)",
        "assets_header": "%s (%s) のアセット",
        "assets_kind": "種類",
        "assets_status": "状態",
        "assets_pick": "種類を選択してボタンを使用します。",
        "assets_ok": "インストール済み",
        "assets_missing": "未インストール",
        "assets_online": "オンラインでダウンロード",
        "assets_pc": "変更... (PC)",
        "assets_close": "閉じる",
        "assets_dl_kind": "%s をダウンロード...",
        "no_preview": "プレビューなし",
        "assets_pick_kind": "まずリストから種類を選択してください。",
        "alt_title": "代替カバー - %s (%s)",
        "alt_label": "XboxUnityで利用可能なカバー (1つ選択):",
        "alt_searching": "XboxUnityでカバーを検索中...",
        "alt_none": "このゲームのカバーがXboxUnityで見つかりませんでした。",
        "alt_count": "%d 個のカバーが見つかりました。",
        "alt_loading": "プレビューを読み込み中...",
        "alt_none_found": "このゲームのカバーがXboxUnityで見つかりませんでした。",
        "alt_no_img": "画像なし",
        "alt_no_preview": "このカバーのプレビューなし。",
        "alt_loaded": "プレビューを読み込みました。",
        "alt_noimg": "画像なし",
        "alt_preview_ok": "プレビューを読み込みました。",
        "alt_preview_none": "このカバーのプレビューなし。",
        "alt_sem_preview": "プレビューなし",
        "alt_install": "このカバーをダウンロードしてインストール",
        "alt_official": "公式カバー (x360db)",
        "alt_unity_empty": "検索結果: XboxUnityにこのゲームのカバーなし; 公式カバーを表示 (x360db)。",
        "alt_installed": "カバーを正常にインストールしました。",
        "alt_failed": "カバーのインストールに失敗しました。",
        "alt_select_first": "まずカバーを選択してください。",
        "alt_downloading": "ダウンロード中...",
        "status_saved": "設定を保存しました (テーマ: %s, リポジトリ: %s, カバー: %s, スクリーンショット: %d)。",
        "canceled": "ユーザーによって操作がキャンセルされました。",
        "unity_fallback": "XboxUnityに使用可能なカバーなし; x360dbを代替として使用。",
        "unity_no_cover": "XboxUnityに%sのカバーなし; x360dbを代替として使用。",
        "unity_offline": "XboxUnityがオフライン; x360dbを使用。",
        "no_games_notice": "ダウンロードが必要なゲームはありません。",
        "done_notice": "完了! Xboxで: Auroraを起動し Y -> Refreshを押す (またはImportを使用)。",
        "set_log": "ログを表示 (テキストボックス)",
        "cover_missing_both": "  x360dbおよびXboxUnityでカバーが見つかりません。",
        "gameart_cover_ok": "  360-Game-Artのカバー %s。",
        "game_cover_ok": "  ローカルカバー (game_covers) で %s。",
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "タイトルを検索...",
        "debug_db": "DB デバッグ",
        "auto_search_titles": "タイトル自動検索 (XboxUnity)",
        "auto_search_on": "タイトル自動検索: オン。",
        "auto_search_off": "タイトル自動検索: オフ。",
        "show_game_info": "開発者と発売日を表示",
        "show_debug_button": "Debug DB ボタンを表示",
        "auto_update_check": "自動的にアップデートを確認",
        "update_available_title": "アップデート利用可能",
        "update_available_msg": "新しいバージョン ({0}) が利用可能です！ 現在のバージョン: {1}\n\nダウンロードページを開きますか？",
        "download_missing_only": "カバーがないゲームのみダウンロード",
        "m_search": "タイトルを検索...",
        "m_rename": "ゲーム名を変更",
        "rename_prompt": "%s (%s) の新しい名前:",
        "renamed": "ゲーム %s を %s にリネームしました。",
        "ok": "OK",
        "add_game": "ゲームを追加...",
        "add_game_tid": "Title ID（8桁の16進数。検出時は省略可）:",
        "add_game_xex": ".xexファイル（TID自動検出）:",
        "add_game_folder": "ゲームを探すフォルダ:",
        "add_game_folder_note": "選択したフォルダ内の複数のゲーム（.xex）をサブフォルダごとに探します。",
        "add_game_name": "名前（任意）:",
        "add_game_mkdir": "HDにGameDataフォルダを作成",
        "add_game_bad_tid": "Title IDが無効です（8桁の16進数、例: 5841120F）。",
        "add_game_exists": "このゲームはすでにリストにあります。",
        "add_game_need_name": "フォルダを作成するには名前を入力してください。",
        "add_game_added": "ゲームを追加しました: %s (%s)",
        "add_game_folder_done": "フォルダをスキャン: %s から %d ゲームを追加しました。",
        "manage_folders": "フォルダを管理...",
        "db_editor": "Auroraデータベース (content.db)",
        "db_add": "追加...",
        "db_rename": "名前変更...",
        "db_remove": "削除...",
        "db_reload": "更新",
        "db_backup": "バックアップ作成: %s",
        "db_warn1": "Auroraを閉じてHDの動きが止まった状態で編集してください（使用中はDBがロックされます）。変更前には自動バックアップ(.bak)が作成されます。",
        "db_nodb": "Auroraのcontent.dbが見つかりません。HDを接続して先にスキャンしてください。",
        "db_need_id": "一覧からエントリを選択してください。",
        "db_new_tid": "Title ID（8桁の16進数）:",
        "db_new_name": "名前:",
        "db_new_dir": "相対フォルダ（例: \\Content\\0000000000000000\\5841120F）:",
        "db_added": "エントリを追加: %s (%s)",
        "db_renamed": "エントリ名を変更: %s",
        "db_removed": "エントリを削除: %s",
        "db_confirm_remove": "'%s' を登録から削除しますか？ ディスク上のコンテンツは消去されません。",
        "db_only_dlc": "DLC / XBLA / TU のみ",
        "db_filter": "種類:",
        "db_all": "すべて",
        "db_search": "名前・TID・フォルダを検索...",
        "filter_games": "ゲームを検索: ",
        "db_need_name": "名前を入力してください。",
        "rename_ftp_start": "FTPで本体のフォルダ名を変更しています...",
        "rename_ftp_ok": "本体のフォルダ名を変更しました: %s",
        "rename_ftp_err": "本体でフォルダ名を変更できませんでした: %s",
        "m_open_folder": "ゲームフォルダを開く",
        "m_remove_cover": "インストール済みカバーを削除",
        "m_remove_game": "リストから削除",
        "m_restore_hidden": "削除したゲームを復元...",
        "remove_cover_confirm": "'%s' (%s) のインストール済みカバーを削除しますか?\nGC<tid>.asset とインポートのカバーを削除します。",
        "cover_removed": "%s (%s) のカバーを削除しました。",
        "cover_none_found": "%s (%s) のカバーファイルが見つかりません。",
        "remove_game_confirm": "'%s' (%s) をリストから削除しますか? ディスク上の内容は削除されません。",
        "game_removed": "%s (%s) をリストから削除しました。",
        "restore_hidden_confirm": "削除した %d 件のゲームをリストに復元しますか?",
        "restore_hidden_done": "削除したゲームをすべて復元しました。",
        "set_ftp": "FTPで送信 (コンソール):",
        "ftp_host_lbl": "コンソールIP:",
        "ftp_port_lbl": "ポート:",
        "ftp_user_lbl": "ユーザー:",
        "ftp_pass_lbl": "パスワード:",
        "ftp_base_lbl": "リモートフォルダ (GameData):",
        "ftp_send": "FTPで送信",
        "ftp_sending": "コンソールにFTPで送信中...",
        "ftp_deploy_covers": "game_coversのアセットを配布",
        "ftp_deploying": "game_coversのアセットを配布中...",
        "ftp_deploy_ok": "アセットを配布しました: %d 個のファイルを %s へ",
        "ftp_deploy_no_folder": "このゲームの game_covers フォルダが見つかりません。",
        "ftp_sent": "%d ファイルを %s に送信しました。",
        "ftp_no_host": "設定 -> FTP でコンソールIPを設定してください。",
        "ftp_no_folder": "このゲームにローカルData\\GameDataフォルダがありません。",
        "ftp_err": "FTPエラー: %s",
        "ss_prev": "◀",
        "ss_next": "▶",
        "credits": "Atreus171によって開発\nhttps://github.com/Atreus171/Aurora-Asset-Manager",
        "release_date": "発売日",
        "developer": "開発元",
        "genres": "ジャンル",
        "settings_title": "設定",
        "db_notfound": "content.db が見つかりません",
        "err_generic": "エラー: %s",
        "no_folders": "まだフォルダが追加されていません。",
        "folders_header": "追加済みフォルダ（「ゲームを探すフォルダ」経由）:",
        "col_folder": "フォルダ",
        "col_added": "追加日",
        "col_count": "ゲーム数",
        "col_type": "種類",
        "remove_folders_confirm": "選択した %d 個のフォルダを削除しますか？",
        "open_folder": "フォルダを開く",
        "remove_selected": "選択を削除",
        "schema_unknown": "不明なスキーマ (table=%s)",
        "folder_not_found": "フォルダが見つかりません: %s",
        "folder_open_err": "フォルダを開けません: %s",
        "alt_no_preview": "プレビューなし",
        "alt_pick_first": "先にカバーを選択してください。",
        "downloading": "ダウンロード中...",
        "no_success": "失敗",
        "logs_unity_names": "XboxUnity から名前を更新しました。",
        "logs_scanning": "スキャン中: %s",
        "logs_no_index": "警告: x360db のインデックスが読み込めませんでした。DLC/アップデートのフィルタなし。",
        "logs_ignored_dlc": "%d 個の DLC/アップデート TitleID を無視しました（ゲーム索引にありません）。",
        "logs_god_xdlc": "GameData フォルダのない GOD/XDLC ゲーム: %d（Import で処理されます）",
        "logs_fetch_names": "XboxUnity から %d 個の名前を取得中...",
        "logs_title_x360db": "x360db でタイトルが見つかりました: %s",
        "logs_title_unity": "XboxUnity でタイトルが見つかりました: %s",
        "logs_title_folder": "フォルダ名を使用: %s",
        "logs_title_not_found": "%s のタイトルが見つかりません",
        "logs_title_none_idlike": "修正対象の TitleID 形式の名前を持つゲームはありません。",
        "logs_titles_updated": "修正した名前: %d 件。",
        "logs_title_nochange": "名前はすでに正しいです。",
        "logs_updating_db": "content.db を更新: TID=%s -> %s",
        "logs_db_err": "content.db の更新に失敗: %s",
        "logs_renamed_folder": "フォルダ名を変更: %s -> %s",
        "logs_folder_open_err": "フォルダを開けません: %s",
        "logs_gamedata_created": "GameData フォルダを作成: %s",
        "logs_queue_started": "キューを開始: %d ゲーム",
        "logs_custom_installed": "%s (%s) にカスタムカバーをインストールしました",
        "logs_assets_exported": "%s にアセットをエクスポートしました: %s",
        "assets_exported_ok": "game_covers/%s にアセットをエクスポートしました\n%d 個のファイルをコピーしました。",
        "assets_folder_created_empty": "フォルダを作成しました: game_covers/%s\n%s\n(インストール済みアセットが見つかりません — 手動でファイルを追加してください)。",
        "logs_no_assets_to_export": "エクスポートするインストール済みアセットがありません: %s",
        "no_assets_to_export": "エクスポートするインストール済みアセットが見つかりません。",
        "logs_ftp_sent": "FTP: %d 個のファイルを %s に送信しました。",
        "logs_ftp_err": "FTP エラー: %s",
        "ftp_inaccessible": "FTP: %s にアクセスできません (%s)",
        "logs_downloading": "%s を %s (%s) にダウンロード中...",
        "logs_downloading_assets": "%s の全アセットをダウンロード中...",
        "logs_rename_folder_err": "フォルダ名を変更できません: %s",
        "logs_no_dedicated_gamedata": "%s に専用の GameData フォルダがありません。リスト内のみで名前を保存します。",
        "logs_db_titlename_ok": "content.db: TitleName を '%s' に更新しました。",
        "logs_db_row_not_found": "content.db: 行 %s が見つかりません（設定のみに保存）。",
        "logs_db_rename_err": "content.db: 名前を変更できません: %s",
        "logs_folders_removed": "%d 個のフォルダを削除しました",
        "logs_progress_game": "[%d/%d] %s (%s)",
        "logs_game_err": "このゲームでエラー: %s",
        "logs_cover_fetch_err": "カバーの取得に失敗: %s",
        "logs_hb_tid_by_name": "ホームブルー: 名前 '%s' の XboxUnity TID = %s",
        "logs_hb_no_cover_by_name": "ホームブルー: XboxUnity に名前のカバーなし (%s)",
        "logs_unity_offline": "XboxUnity がオフラインです (%s)",
        "unity_no_cover": "XboxUnity に %s のカバーがありません",
        "unity_black_cover": "XboxUnity で空/黒のカバーを無視しました（不良）。",
        "unity_no_usable": "XboxUnity に使用できるカバーがありません (%s)",
        "cover_not_found_repo": "リポジトリにカバーが見つかりません。",
        "background_not_found": "x360db に背景が見つかりません。",
        "kind_not_found": "x360db に %s が見つかりません。",
        "no_screenshots": "x360db にスクリーンショットがありません。",
        "logs_ss_installed": "%d 枚のスクリーンショットをインストールしました。",
        "logs_dl_kind_err": "%s のダウンロードに失敗: %s",
        "logs_saved": "%s を保存しました",
        "logs_alt_import": "%s への代替インポート",
        "logs_kind_result": "%s: %s",
        "logs_kind_err": "エラー: %s",
        "logs_kind_err_with": "%s: エラー: %s",
        "logs_kind_skip": "%s: インストール済み（スキップ）。",
        "unity_fetch_fail": "XboxUnity からカバーのダウンロードに失敗しました。",
        "logs_alt_installed": "%s (%s) に代替カバーをインストールしました。",
        "logs_alt_err": "エラー: %s",
    },
    "ru": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
        "gameart_status": "360-Game-Art:",
        "checking": "проверка...",
        "connected": "подключено",
        "disconnected": "отключено",
        "aurora_folder": "Папка Aurora:",
        "browse": "Обзор...",
        "opt_boxart": "Скачать обложку (boxart)",
        "opt_background": "Скачать фон",
        "opt_force": "Принудительно скачать повторно",
        "opt_backup": "Резервная копия перед перезаписью",
        "opt_icon": "Скачать иконку (64x64)",
        "opt_banner": "Скачать баннер",
        "opt_screenshots": "Скачать скриншоты (до %d)",
        "info_note": "Информация (название/описание) берется из x360db и используется в панели.",
        "scan": "Сканировать игры",
        "download": "Скачать и установить ассеты",
        "custom_cover": "Пользовательская обложка...",
        "settings": "Настройки...",
        "tip_right_click": "Совет: правый клик по игре для просмотра/изменения ассетов.",
        "cancel": "Отмена",
        "col_tid": "TitleID",
        "col_game": "Игра",
        "col_status": "Статус",
        "preview_title": "Предпросмотр обложки",
        "no_selection": "Ничего не выбрано",
        "no_cover": "Нет обложки",
        "no_cover_installed": "Обложка не установлена",
        "cover_installed": "Обложка установлена",
        "loading_info": "Загрузка информации...",
        "loading_index": "Загрузка индекса x360db, пожалуйста подождите...",
        "index_loaded": "Индекс x360db загружен: %d игр.",
        "index_fail": "Не удалось скачать индекс (офлайн-режим: будет использоваться TitleID).",
        "warn": "Предупреждение",
        "info": "Информация",
        "scan_first": "Сначала отсканируйте игры.",
        "pick_art": "Выберите хотя бы один тип арта (обложка, фон, иконка, баннер или скриншоты).",
        "pick_aurora": "Сначала выберите корневую папку Aurora.",
        "not_aurora_folder": "Выбранная папка не похожа на установку Aurora (нет Data/GameData или папки Aurora).",
        "pick_game": "Сначала выберите игру в списке.",
        "img_open_fail": "Не удалось открыть изображение:\n%s",
        "img_write_fail": "Не удалось записать:\n%s",
        "save_fail": "Не удалось сохранить:\n%s",
        "warn": "Предупреждение",
        "error": "Ошибка",
        "pick_game": "Сначала выберите игру в списке.",
        "custom_cover": "Пользовательская обложка",
        "m_assets": "Просмотреть/изменить ассеты этой игры...",
        "m_alt": "Альтернативные обложки онлайн...",
        "m_custom": "Пользовательская обложка...",
        "m_export_assets": "Экспортировать ассеты в game_covers...",
        "set_theme": "Тема:",
        "theme_dark": "Тёмная",
        "theme_light": "Светлая",
        "theme_system": "По системе",
        "dest": "Назначение",
        "set_lang": "Язык:",
        "set_show_status": "Показывать точки статуса интернета сверху",
        "set_repo": "Репозиторий обложек:",
        "set_format": "Формат обложки:",
        "format_portrait": "Портрет (900x1233)",
        "format_landscape": "Альбом (900x600)",
        "set_screenshots": "Скриншотов на игру:",
        "status_saved": "Настройки сохранены (тема: %s, репозиторий: %s, обложка: %s, скриншоты: %d, регион: %s).",
        "save": "Сохранить",
        "cancel2": "Отмена",
        "restart_title": "Перезапуск приложения",
        "restart_lang": "Язык меняется при перезапуске приложения (закройте и откройте снова).",
        "assets": "Ассеты",
        "assets_of": "Ассеты",
        "col_kind": "Тип",
        "col_status": "Статус",
        "dl_online": "Скачать онлайн",
        "dl_all": "Скачать всё",
        "dl_all_start": "Скачивание всех ассетов этой игры...",
        "dl_all_log": "Скачивание всех ассетов %s (%s)...",
        "change_pc": "Изменить... (ПК)",
        "close": "Закрыть",
        "assets_hint": "Выберите тип и используйте кнопки.",
        "assets_installed": "Установлено",
        "assets_missing": "Отсутствует",
        "assets_pick": "Сначала выберите тип в списке.",
        "assets_dl_kind": "Загрузка %s...",
        "no_preview": "Нет превью",
        "pick_kind": "Выбрать %s для %s",
        "kind_boxart": "обложка (boxart)",
        "kind_background": "фон (background)",
        "kind_icon": "иконка",
        "kind_banner": "баннер",
        "kind_screenshots": "скриншот",
        "asset_changed": "Ассет '%s' изменен для %s (%s).",
        "m_assets": "Просмотреть/изменить ассеты этой игры...",
        "m_alt": "Альтернативные обложки онлайн...",
        "m_custom": "Пользовательская обложка...",
        "m_export_assets": "Экспортировать ассеты в game_covers...",
        "set_title": "Настройки",
        "set_theme": "Тема:",
        "theme_dark": "Тёмная",
        "theme_light": "Светлая",
        "theme_system": "Следовать теме системы",
        "set_repo": "Репозиторий обложек:",
        "set_format": "Формат обложки:",
        "format_portrait": "Портрет (900x1233)",
        "format_landscape": "Альбом (900x600)",
        "set_screenshots": "Скриншотов на игру:",
        "set_lang": "Язык:",
        "set_show_status": "Показывать точки статуса подключения",
        "save": "Сохранить",
        "cancel2": "Отмена",
        "restart_title": "Язык",
        "restart_lang": "Перезапустите приложение для применения языка.",
        "assets_title": "Ассеты - %s (%s)",
        "assets_header": "Ассеты %s (%s)",
        "assets_kind": "Тип",
        "assets_status": "Статус",
        "assets_pick": "Выберите тип и используйте кнопки.",
        "assets_ok": "Установлено",
        "assets_missing": "Отсутствует",
        "assets_online": "Скачать онлайн",
        "assets_pc": "Изменить... (ПК)",
        "assets_close": "Закрыть",
        "assets_dl_kind": "Скачать %s...",
        "no_preview": "Нет превью",
        "assets_pick_kind": "Сначала выберите тип в списке.",
        "alt_title": "Альтернативные обложки - %s (%s)",
        "alt_label": "Доступные обложки на XboxUnity (выберите одну):",
        "alt_searching": "Поиск обложек на XboxUnity...",
        "alt_none": "Обложки не найдены на XboxUnity для этой игры.",
        "alt_count": "Найдено обложек: %d.",
        "alt_loading": "Загрузка превью...",
        "alt_none_found": "Обложки не найдены на XboxUnity для этой игры.",
        "alt_no_img": "Нет изображения",
        "alt_no_preview": "Нет превью для этой обложки.",
        "alt_loaded": "Превью загружено.",
        "alt_noimg": "Нет изображения",
        "alt_preview_ok": "Превью загружено.",
        "alt_preview_none": "Нет превью для этой обложки.",
        "alt_sem_preview": "Нет превью",
        "alt_install": "Скачать и установить эту обложку",
        "alt_official": "Официальная обложка (x360db)",
        "alt_unity_empty": "Поиск: на XboxUnity нет обложки для этой игры; показываем официальную (x360db).",
        "alt_installed": "Обложка успешно установлена.",
        "alt_failed": "Ошибка установки обложки.",
        "alt_select_first": "Сначала выберите обложку.",
        "alt_downloading": "Загрузка...",
        "status_saved": "Настройки сохранены (тема: %s, репозиторий: %s, обложка: %s, скриншоты: %d).",
        "canceled": "Операция отменена пользователем.",
        "unity_fallback": "На XboxUnity нет подходящей обложки; используется x360db как запасной.",
        "unity_no_cover": "На XboxUnity нет обложек для %s; используется x360db как запасной.",
        "unity_offline": "XboxUnity недоступен; используется x360db.",
        "no_games_notice": "Нет игр, требующих загрузки.",
        "done_notice": "Готово! На Xbox: запустите Aurora и нажмите Y -> Refresh в игре (или используйте Import).",
        "set_log": "Показать лог (текстовое поле)",
        "cover_missing_both": "  обложка не найдена ни в x360db, ни в XboxUnity.",
        "gameart_cover_ok": "  обложка 360-Game-Art для %s.",
        "game_cover_ok": "  локальная обложка (game_covers) для %s.",
        "sort_asc": "А-Я",
        "sort_desc": "Я-А",
        "search_title": "Поиск названия...",
        "debug_db": "Отладка БД",
        "auto_search_titles": "Автопоиск названий (XboxUnity)",
        "auto_search_on": "Автопоиск названий: ВКЛ.",
        "auto_search_off": "Автопоиск названий: ВЫКЛ.",
        "show_game_info": "Показывать разработчика и дату релиза",
        "show_debug_button": "Показать кнопку Debug DB",
        "auto_update_check": "Автоматически проверять обновления",
        "update_available_title": "Доступно обновление",
        "update_available_msg": "Доступна новая версия ({0})! Текущая версия: {1}\n\nОткрыть страницу загрузки?",
        "download_missing_only": "Скачивать только игры без обложки",
        "m_search": "Поиск названия...",
        "m_rename": "Переименовать игру",
        "rename_prompt": "Новое имя для %s (%s):",
        "renamed": "Игра %s переименована в: %s",
        "ok": "OK",
        "add_game": "Добавить игры...",
        "add_game_tid": "Title ID (8 шестнадцатеричных цифр; необязательно, если определено):",
        "add_game_xex": "Файл .xex (автоопределение TID):",
        "add_game_folder": "Папка для поиска игр:",
        "add_game_folder_note": "Ищет несколько игр (.xex) внутри выбранной папки, по одной на каждую подпапку.",
        "add_game_name": "Название (необязательно):",
        "add_game_mkdir": "Создать папку GameData на диске",
        "add_game_bad_tid": "Неверный Title ID (используйте 8 шестнадцатеричных цифр, напр. 5841120F).",
        "add_game_exists": "Эта игра уже есть в списке.",
        "add_game_need_name": "Введите название, чтобы создать папку.",
        "add_game_added": "Игра добавлена: %s (%s)",
        "add_game_folder_done": "Папка просканирована: добавлено %d игр(ы) из %s.",
        "manage_folders": "Управление папками...",
        "db_editor": "База данных Aurora (content.db)",
        "db_add": "Добавить...",
        "db_rename": "Переименовать...",
        "db_remove": "Удалить...",
        "db_reload": "Обновить",
        "db_backup": "Создана резервная копия: %s",
        "db_warn1": "Редактируйте только при закрытой Aurora и свободном диске (БД блокируется при использовании). Перед каждым изменением создаётся резервная копия (.bak).",
        "db_nodb": "content.db Aurora не найден. Подключите диск и выполните сканирование.",
        "db_need_id": "Выберите запись в списке.",
        "db_new_tid": "Title ID (8 шестнадцатеричных цифр):",
        "db_new_name": "Название:",
        "db_new_dir": "Относительная папка (напр.: \\Content\\0000000000000000\\5841120F):",
        "db_added": "Запись добавлена: %s (%s)",
        "db_renamed": "Запись переименована: %s",
        "db_removed": "Запись удалена: %s",
        "db_confirm_remove": "Удалить '%s' из реестра? Содержимое на диске НЕ удаляется.",
        "db_only_dlc": "Только DLC / XBLA / TU",
        "db_filter": "Тип:",
        "db_all": "Все",
        "db_search": "Поиск по имени, TID или папке...",
        "filter_games": "Поиск игр: ",
        "db_need_name": "Введите название.",
        "rename_ftp_start": "Переименование папки на консоли по FTP...",
        "rename_ftp_ok": "Папка на консоли переименована в: %s",
        "rename_ftp_err": "Не удалось переименовать на консоли: %s",
        "m_open_folder": "Открыть папку игры",
        "m_remove_cover": "Удалить установленную обложку",
        "m_remove_game": "Убрать из списка",
        "m_restore_hidden": "Восстановить удалённые игры...",
        "remove_cover_confirm": "Удалить установленную обложку для '%s' (%s)?\nУдаляет GC<tid>.asset и обложку из Import.",
        "cover_removed": "Обложка удалена: %s (%s).",
        "cover_none_found": "Файл обложки не найден для %s (%s).",
        "remove_game_confirm": "Убрать '%s' (%s) из списка? Содержимое на диске НЕ удаляется.",
        "game_removed": "Игра %s (%s) убрана из списка.",
        "restore_hidden_confirm": "Восстановить %d удалённую(ые) игру(ы) в список?",
        "restore_hidden_done": "Все удалённые игры восстановлены.",
        "set_ftp": "Отправить по FTP (консоль):",
        "ftp_host_lbl": "IP консоли:",
        "ftp_port_lbl": "Порт:",
        "ftp_user_lbl": "Пользователь:",
        "ftp_pass_lbl": "Пароль:",
        "ftp_base_lbl": "Удаленная папка (GameData):",
        "ftp_send": "Отправить по FTP",
        "ftp_sending": "Отправка на консоль по FTP...",
        "ftp_deploy_covers": "Развернуть ассеты из game_covers",
        "ftp_deploying": "Развертывание ассетов из game_covers...",
        "ftp_deploy_ok": "Ассеты развернуты: %d файл(ов) в %s",
        "ftp_deploy_no_folder": "Папка game_covers для этой игры не найдена.",
        "ftp_sent": "Отправлено %d файл(ов) в %s.",
        "ftp_no_host": "Настройте IP консоли в Настройки -> FTP сначала.",
        "ftp_no_folder": "У этой игры нет локальной папки Data\\GameData для отправки.",
        "ftp_err": "Ошибка FTP: %s",
        "ss_prev": "◀",
        "ss_next": "▶",
        "credits": "Разработано Atreus171\nhttps://github.com/Atreus171/Aurora-Asset-Manager",
        "release_date": "Релиз",
        "developer": "Разработчик",
        "genres": "Жанры",
        "settings_title": "Настройки",
        "db_notfound": "content.db не найден",
        "err_generic": "Ошибка: %s",
        "no_folders": "Папки ещё не добавлены.",
        "folders_header": "Добавленные папки (через «Папка для поиска игр»):",
        "col_folder": "Папка",
        "col_added": "Добавлена",
        "col_count": "Игры",
        "col_type": "Тип",
        "remove_folders_confirm": "Удалить %d выбранную(ых) папку(и)?",
        "open_folder": "Открыть папку",
        "remove_selected": "Удалить выбранные",
        "schema_unknown": "Неизвестная схема (table=%s)",
        "folder_not_found": "Папка не найдена: %s",
        "folder_open_err": "Ошибка открытия папки: %s",
        "alt_no_preview": "Нет предпросмотра",
        "alt_pick_first": "Сначала выберите обложку.",
        "downloading": "Загрузка...",
        "no_success": "неудачно",
        "logs_unity_names": "Названия обновлены через XboxUnity.",
        "logs_scanning": "Сканирование: %s",
        "logs_no_index": "Внимание: индекс x360db не загрузился; без фильтра DLC/обновлений.",
        "logs_ignored_dlc": "Пропущено %d TitleID DLC/обновлений (нет в индексе игр).",
        "logs_god_xdlc": "Игры GOD/XDLC на HDD без папки GameData: %d (будут обработаны через Import)",
        "logs_fetch_names": "Получение %d названий из XboxUnity...",
        "logs_title_x360db": "Название найдено в x360db: %s",
        "logs_title_unity": "Название найдено в XboxUnity: %s",
        "logs_title_folder": "Используется имя папки: %s",
        "logs_title_not_found": "Название не найдено для %s",
        "logs_title_none_idlike": "Нет игр с именем в виде TitleID для исправления.",
        "logs_titles_updated": "Исправлено имён: %d.",
        "logs_title_nochange": "Имена уже корректны.",
        "logs_updating_db": "Обновление content.db: TID=%s -> %s",
        "logs_db_err": "Ошибка обновления content.db: %s",
        "logs_renamed_folder": "Папка переименована: %s -> %s",
        "logs_folder_open_err": "Ошибка открытия папки: %s",
        "logs_gamedata_created": "Папка GameData создана: %s",
        "logs_queue_started": "Запуск очереди: %d игра(ы)",
        "logs_custom_installed": "Пользовательская обложка установлена для %s (%s)",
        "logs_assets_exported": "Ассеты экспортированы в %s: %s",
        "assets_exported_ok": "Ассеты экспортированы в game_covers/%s\n%d файл(ов) скопировано.",
        "assets_folder_created_empty": "Папка создана: game_covers/%s\n%s\n(Установленные ассеты не найдены — добавьте файлы вручную).",
        "logs_no_assets_to_export": "Нет установленных ассетов для экспорта: %s",
        "no_assets_to_export": "Не найдено установленных ассетов для экспорта.",
        "logs_ftp_sent": "FTP: %d файл(ов) отправлено в %s.",
        "logs_ftp_err": "Ошибка FTP: %s",
        "ftp_inaccessible": "FTP: невозможно получить доступ к %s (%s)",
        "logs_downloading": "Загрузка %s для %s (%s)...",
        "logs_downloading_assets": "Загрузка всех ассетов для %s...",
        "logs_rename_folder_err": "Не удалось переименовать папку: %s",
        "logs_no_dedicated_gamedata": "Нет выделенной папки GameData для %s; переименование сохранено только в списке.",
        "logs_db_titlename_ok": "content.db: TitleName обновлён на '%s'.",
        "logs_db_row_not_found": "content.db: строка %s не найдена (имя сохранено только в конфигурации).",
        "logs_db_rename_err": "content.db: не удалось переименовать: %s",
        "logs_folders_removed": "%d папка(и) удалена(ы)",
        "logs_progress_game": "[%d/%d] %s (%s)",
        "logs_game_err": "Ошибка в этой игре: %s",
        "logs_cover_fetch_err": "Ошибка получения обложки: %s",
        "logs_hb_tid_by_name": "Хоумбрю: TID XboxUnity по имени '%s' = %s",
        "logs_hb_no_cover_by_name": "Хоумбрю: нет обложки по имени на XboxUnity (%s)",
        "logs_unity_offline": "XboxUnity недоступен (%s)",
        "unity_no_cover": "На XboxUnity нет обложек для %s",
        "unity_black_cover": "Пустая/чёрная обложка проигнорирована (бракованная) на XboxUnity.",
        "unity_no_usable": "На XboxUnity нет подходящей обложки (%s)",
        "cover_not_found_repo": "Обложка не найдена в репозитории.",
        "background_not_found": "Фон не найден в x360db.",
        "kind_not_found": "%s не найден в x360db.",
        "no_screenshots": "Нет скриншотов в x360db.",
        "logs_ss_installed": "Установлено скриншотов: %d.",
        "logs_dl_kind_err": "Ошибка загрузки %s: %s",
        "logs_saved": "Сохранено %s",
        "logs_alt_import": "Альтернативный импорт в %s",
        "logs_kind_result": "%s: %s",
        "logs_kind_err": "Ошибка: %s",
        "logs_kind_err_with": "%s: ошибка: %s",
        "logs_kind_skip": "%s: уже установлено (пропуск).",
        "unity_fetch_fail": "Не удалось загрузить обложку с XboxUnity.",
        "logs_alt_installed": "Альтернативная обложка установлена для %s (%s).",
        "logs_alt_err": "Ошибка: %s",
    },
}


def tr(key, *args):
    s = TEXT.get(CURRENT_LANG, TEXT["en"]).get(key)
    if s is None:
        s = TEXT["en"].get(key, key)
    if args:
        try:
            return s % args
        except Exception:
            return s
    return s


def detect_system_theme():
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "claro" if val else "escuro"
        except Exception:
            pass
    return "escuro"

ASSET_KINDS = [
    ("boxart", "Capa (Boxart)", "GC", ASSET_TYPE_BOXART, "cover.png"),
    ("background", "Fundo (Background)", "BK", ASSET_TYPE_BACKGROUND, "background.png"),
    ("icon", "Ícone (64x64)", "GL", ASSET_TYPE_ICON, "icon.png"),
    ("banner", "Banner (420x95)", "GL", ASSET_TYPE_BANNER, "banner.png"),
    ("screenshots", "Screenshots", "SS", ASSET_TYPE_SCREENSHOT, "screenshot1.png"),
]


def config_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    # Use Documents\Aurora Asset Manager folder
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Aurora Asset Manager")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, "aurora_covers_config.json")


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def log(*args):
    print(*args)


# HTTP connection pooling for faster repeated requests
class _HTTPPool:
    def __init__(self):
        self._opener = None
        self._lock = threading.Lock()

    def _get_opener(self):
        if self._opener is None:
            with self._lock:
                if self._opener is None:
                    handlers = [
                        urllib.request.HTTPCookieProcessor(),
                        urllib.request.HTTPRedirectHandler(),
                        urllib.request.HTTPHandler(),
                        urllib.request.HTTPSHandler(),
                    ]
                    self._opener = urllib.request.build_opener(*handlers)
        return self._opener

    def open(self, req, timeout=40):
        opener = self._get_opener()
        return opener.open(req, timeout=timeout)


_HTTP_POOL = _HTTPPool()


def fetch_bytes(url, timeout=40, attempts=2):
    for _ in range(attempts):
        try:
            req = urllib.request.Request(url, headers=USER_AGENT)
            with _HTTP_POOL.open(req, timeout=timeout) as resp:
                data = resp.read()
                if getattr(resp, "status", 200) == 200 and len(data) > 0:
                    return data
        except Exception:
            time.sleep(1.0)
    return None


def download_json(url, timeout=40):
    data = fetch_bytes(url, timeout=timeout)
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def display_path(path):
    try:
        return os.path.relpath(path)
    except ValueError:
        return os.path.abspath(path)


def poke_url(url, timeout=8, method="GET"):
    try:
        req = urllib.request.Request(url, headers=USER_AGENT, method=method)
        with _HTTP_POOL.open(req, timeout=timeout) as resp:
            resp.read(1024)
            return True
    except Exception:
        return False


class X360DB:
    def __init__(self):
        self.titles = {}
        self.alt_ids = {}
        self.info_cache = {}
        self.ready = threading.Event()
        self.index_file = os.path.join(os.path.dirname(config_path()), "aurora_covers_games.json")
        self._loaded = False
        self._load_lock = threading.Lock()

    def _ensure_loaded(self):
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            self.load_index()
            self._loaded = True

    def _read_cache(self):
        try:
            if os.path.isfile(self.index_file):
                if time.time() - os.path.getmtime(self.index_file) < 12 * 3600:
                    with open(self.index_file, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception:
            pass
        return None

    def _write_cache(self, raw):
        try:
            tmp = self.index_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)
            os.replace(tmp, self.index_file)
        except Exception:
            pass

    def load_index(self):
        raw = self._read_cache()
        if not raw:
            raw = download_json(GAMES_INDEX_URL)
            if not raw:
                raw = download_json(GAMES_INDEX_MIRROR)
            if not raw:
                try:
                    with open(self.index_file, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                except Exception:
                    raw = None
            elif raw:
                self._write_cache(raw)
        if not isinstance(raw, list) or not raw:
            return False
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            tid = (entry.get("id") or "").upper()
            if not tid:
                continue
            self.titles[tid] = {
                "title": entry.get("title") or tid,
                "boxart_url": entry.get("boxart"),
            }
            for alt in entry.get("alternative_id") or []:
                self.alt_ids[alt.upper()] = tid
        self.ready.set()
        return True

    def canonical(self, tid):
        self._ensure_loaded()
        return self.alt_ids.get(tid.upper(), tid.upper())

    def title_name(self, tid):
        self._ensure_loaded()
        info = self.titles.get(tid.upper())
        if info:
            return info["title"]
        return tid.upper()

    def artwork_url(self, tid, kind):
        self._ensure_loaded()
        return X360DB_RAW + "titles/" + self.canonical(tid) + "/artwork/" + kind + ".jpg"

    def info(self, tid):
        self._ensure_loaded()
        tid = self.canonical(tid)
        if tid in self.info_cache:
            return self.info_cache[tid]
        info = download_json(X360DB_RAW + "titles/" + tid + "/info.json")
        self.info_cache[tid] = info or {}
        return self.info_cache[tid]

    def download_artwork(self, tid, kind):
        self._ensure_loaded()
        data = fetch_bytes(self.artwork_url(tid, kind))
        if data is not None:
            return data
        info = self.info(tid)
        if info:
            fallback = (info.get("artwork") or {}).get(kind)
            if fallback:
                data = fetch_bytes(fallback)
                if data is not None:
                    return data
        return None

    def gallery_urls(self, tid):
        info = self.info(tid)
        if not info:
            return []
        return [u for u in (info.get("artwork") or {}).get("gallery") or [] if u]


class XboxUnity:
    def __init__(self):
        self.cache = {}
        self._down_until = 0.0
        self._title_cache = {}
        self._title_cache_file = os.path.join(os.path.dirname(config_path()), "aurora_covers_unity_titles.json")
        self._load_title_cache()

    def _load_title_cache(self):
        try:
            if os.path.isfile(self._title_cache_file):
                with open(self._title_cache_file, "r", encoding="utf-8") as f:
                    self._title_cache = json.load(f)
        except Exception:
            self._title_cache = {}

    def _save_title_cache(self):
        try:
            tmp = self._title_cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._title_cache, f, ensure_ascii=False)
            os.replace(tmp, self._title_cache_file)
        except Exception:
            pass

    def covers(self, tid, force=False):
        if not force and tid in self.cache:
            return self.cache[tid]
        if not force and time.time() < self._down_until:
            self.cache[tid] = []
            return []
        items = []
        got = False
        b = fetch_bytes(XBOXUNITY_CVERS % tid, timeout=12, attempts=1)
        if b:
            got = True
            try:
                data = json.loads(b.decode("utf-8"))
            except Exception:
                data = None
            if isinstance(data, list):
                items = [it for it in data if isinstance(it, dict)]
        if not items:
            b2 = fetch_bytes(
                XBOXUNITY_LIB + "/CoverInfo.php?titleid=" + tid, timeout=12, attempts=1
            )
            if b2:
                got = True
                try:
                    data2 = json.loads(b2.decode("utf-8"))
                except Exception:
                    data2 = None
                if isinstance(data2, dict) and isinstance(data2.get("Covers") or data2.get("covers"), list):
                    covers_list = data2.get("Covers") or data2.get("covers")
                    items = [it for it in covers_list if isinstance(it, dict)]
        if got:
            self._down_until = 0.0
        elif time.time() >= self._down_until:
            self._down_until = time.time() + 30
        self.cache[tid] = items
        return items

    def get_best_title(self, tid):
        """Retorna o melhor nome disponível no XboxUnity para o TID (usa cache persistente)."""
        tid = tid.upper()
        if tid in self._title_cache:
            return self._title_cache[tid]
        items = self.covers(tid, force=False)
        for it in items:
            name = it.get("name") or it.get("title")
            if name and name.strip():
                self._title_cache[tid] = name.strip()
                self._save_title_cache()
                return name.strip()
        return None

    def search_titles(self, query, count=25):
        """Busca títulos no XboxUnity por nome (TitleList.php). Retorna lista de dicts."""
        params = urllib.parse.urlencode({
            "page": "0",
            "count": str(count),
            "search": query,
            "sort": "0",
            "direction": "0",
            "category": "0",
            "filter": "0",
        })
        b = fetch_bytes(XBOXUNITY_LIB + "/TitleList.php?" + params, timeout=12, attempts=2)
        if not b:
            return []
        try:
            data = json.loads(b.decode("utf-8", "replace"))
        except Exception:
            return []
        items = data.get("Items") or []
        if not isinstance(items, list):
            return []
        return [it for it in items if isinstance(it, dict)]

    def resolve_title_tid(self, query):
        """Acha o TitleID (interno) que o XboxUnity usa para um homebrew, pesquisando por nome.
        Só aceita entradas do tipo HomeBrew para não pegar capa de outro jogo."""
        qkey = "nameidx|" + re.sub(r"\s+", " ", (query or "")).strip().lower()
        if qkey in self._title_cache:
            return self._title_cache[qkey] or None
        found = None
        items = self.search_titles(query)
        ql = (query or "").strip().lower()
        hb = [it for it in items if "brew" in str(it.get("TitleType") or "").lower()]
        if hb:
            exact = [it for it in hb if str(it.get("Name") or "").strip().lower() == ql]
            if len(exact) == 1:
                found = exact[0]
            else:
                contains = [it for it in hb if ql and ql in str(it.get("Name") or "").strip().lower()]
                if contains:
                    if len(contains) == 1:
                        found = contains[0]
                    else:
                        found = sorted(contains, key=lambda it: len(str(it.get("Name") or "")))[0]
        if found:
            tid = str(found.get("TitleID") or "").strip().upper()
            if len(tid) < 8:
                try:
                    tid = ("%08X" % int(tid, 16))
                except ValueError:
                    tid = tid.zfill(8)
            if tid:
                self._title_cache[qkey] = tid
                self._save_title_cache()
                return tid
        self._title_cache[qkey] = None
        self._save_title_cache()
        return None

    def cover_bytes(self, item, small=False):
        if small:
            order = ["thumbnail", "front", "url", "large"]
        else:
            order = ["url", "large", "thumbnail", "front"]
        for key in order:
            if key == "large":
                cid = item.get("cover_id") or item.get("cid")
                if cid:
                    b = fetch_bytes(XBOXUNITY_LIB + "/Cover.php?size=large&cid=" + str(cid), timeout=12, attempts=1)
                    if b:
                        return b
                continue
            u = item.get(key)
            if u:
                b = fetch_bytes(u, timeout=12, attempts=1)
                if b:
                    return b
        return None

    def label(self, item):
        name = item.get("name") or item.get("title") or ""
        rating = item.get("rating")
        official = bool(item.get("official"))
        tag = "Oficial" if official else "Comunidade"
        s = (name or tag) + "  [%s]" % tag
        if rating:
            s += "  (nota %s)" % rating
        w = item.get("width")
        h = item.get("height")
        if w and h:
            s += "  %sx%s" % (w, h)
        return s


def unity_rating(item):
    try:
        return int(item.get("rating") or 0)
    except (TypeError, ValueError):
        return 0


def is_black_cover(data):
    """Detecta capas 'bugadas' do XboxUnity que são imagens totalmente pretas/vazias
    (aparecem no automodelista sem arte). Retorna True se a imagem for basicamente preta."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img = img.resize((32, 32), Image.BILINEAR)
        px = list(img.getdata())
    except Exception:
        return False
    total = len(px)
    if total == 0:
        return False
    darkness = sum((r + g + b) for r, g, b in px) / (total * 3)
    return darkness < 12


def cover_fill(image, target_w, target_h):
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    scale = max(target_w / image.width, target_h / image.height)
    nw = max(target_w, round(image.width * scale))
    nh = max(target_h, round(image.height * scale))
    image = image.resize((nw, nh), Image.BILINEAR)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return image.crop((left, top, left + target_w, top + target_h))


def cover_fit(image, target_w, target_h):
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    image.thumbnail((target_w, target_h), Image.BILINEAR)
    return image


def box_render(image, cover_format):
    if cover_format == "retrato":
        return cover_fill(image, COVER_W, COVER_H)
    return cover_fill(image, BOXART_W, BOXART_H)


def encode_texture(image):
    img = image.convert("RGBA")
    w, h = img.size
    pw = ((w + 31) // 32) * 32
    ph = ((h + 31) // 32) * 32
    canvas = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    data = bytearray(canvas.tobytes())

    for i in range(0, len(data) - 1, 2):
        data[i], data[i + 1] = data[i + 1], data[i]

    pitch = (w + 31) // 32
    c0 = (pitch << 22) | 2
    c1 = (1 << 6) | 6
    c2 = ((h - 1) << 13) | (w - 1)
    c3 = (3 << 10) | (2 << 7) | (1 << 4)
    c4 = 0
    c5 = (1 << 11) | (1 << 9)
    return bytes(data), (c0, c1, c2, c3, c4, c5)


def make_multi_asset_bytes(textures):
    payload = bytearray()
    entries = bytearray(25 * 64)
    flags = 0
    ss_count = 0
    for slot, image in textures:
        data, c = encode_texture(image)
        entry = struct.pack(
            ">III7I6I",
            len(payload),
            len(data),
            0,
            3,
            1,
            0,
            0,
            0,
            0xFFFF0000,
            0xFFFF0000,
            c[0],
            c[1],
            c[2],
            c[3],
            c[4],
            c[5],
        )
        entries[slot * 64 : slot * 64 + 64] = entry
        payload.extend(data)
        flags |= 1 << slot
        if slot >= ASSET_TYPE_SCREENSHOT:
            ss_count += 1

    header = struct.pack(">IIII", 0x52584541, 1, len(payload), flags)
    header += struct.pack(">I", ss_count)
    header += bytes(entries)
    padding = 2048 - len(header)
    header += b"\x00" * padding
    return header + bytes(payload)


def make_asset_bytes(image, asset_type):
    return make_multi_asset_bytes([(asset_type, image)])


def color565(value):
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31, 255)


def decompress_bc3(data, w, h):
    out = bytearray(w * h * 4)
    blocks_x = (w + 3) // 4
    blocks_y = (h + 3) // 4
    for by in range(blocks_y):
        for bx in range(blocks_x):
            block = by * blocks_x + bx
            off = block * 16
            a0 = data[off]
            a1 = data[off + 1]
            atab = [0] * 8
            atab[0] = a0
            atab[1] = a1
            if a0 > a1:
                for i in range(6):
                    atab[i + 2] = ((6 - i) * a0 + (i + 1) * a1 + 3) // 7
            else:
                for i in range(4):
                    atab[i + 2] = ((4 - i) * a0 + (i + 1) * a1 + 2) // 5
                atab[6] = 0
                atab[7] = 255
            bits_alpha = int.from_bytes(data[off + 2 : off + 8], "little")
            c0 = int.from_bytes(data[off + 8 : off + 10], "little")
            c1 = int.from_bytes(data[off + 10 : off + 12], "little")
            bits_color = int.from_bytes(data[off + 12 : off + 16], "little")
            p0 = color565(c0)
            p1 = color565(c1)
            if c0 > c1:
                table = [
                    p0,
                    p1,
                    ((2 * p0[0] + p1[0]) // 3, (2 * p0[1] + p1[1]) // 3, (2 * p0[2] + p1[2]) // 3, 255),
                    ((p0[0] + 2 * p1[0]) // 3, (p0[1] + 2 * p1[1]) // 3, (p0[2] + 2 * p1[2]) // 3, 255),
                ]
            else:
                table = [
                    p0,
                    p1,
                    ((p0[0] + p1[0]) // 2, (p0[1] + p1[1]) // 2, (p0[2] + p1[2]) // 2, 255),
                    (0, 0, 0, 0),
                ]
            for py in range(4):
                for px in range(4):
                    ix = bx * 4 + px
                    iy = by * 4 + py
                    if ix >= w or iy >= h:
                        continue
                    pos = py * 4 + px
                    ai = (bits_alpha >> (3 * pos)) & 7
                    ci = (bits_color >> (2 * pos)) & 3
                    r, g, b, a = table[ci]
                    a = atab[ai]
                    o = (iy * w + ix) * 4
                    out[o] = r
                    out[o + 1] = g
                    out[o + 2] = b
                    out[o + 3] = a
    return bytes(out)


def decode_texture(data, fmt, endian, swizzle, padded_w, padded_h):
    if endian == 1:
        for i in range(0, len(data) - 1, 2):
            data[i], data[i + 1] = data[i + 1], data[i]
    elif endian == 2:
        for i in range(0, len(data) - 3, 4):
            data[i], data[i + 3] = data[i + 3], data[i]
            data[i + 1], data[i + 2] = data[i + 2], data[i + 1]
    elif endian == 3:
        for i in range(0, len(data) - 3, 4):
            data[i], data[i + 2] = data[i + 2], data[i]
            data[i + 1], data[i + 3] = data[i + 3], data[i + 1]
    if fmt == 6:
        rgba = bytes(data)
    elif fmt == 20:
        rgba = decompress_bc3(data, padded_w, padded_h)
    else:
        return None
    buf = bytearray(rgba)
    sx, sy, sz, sw = swizzle
    if sx != 0 or sy != 1 or sz != 2 or sw != 3:
        for i in range(0, len(buf) - 3, 4):
            x = buf[i + sx]
            y = buf[i + sy]
            z = buf[i + sz]
            w = buf[i + sw]
            buf[i] = x
            buf[i + 1] = y
            buf[i + 2] = z
            buf[i + 3] = w
    return bytes(buf)


def decode_asset(blob, asset_type):
    if not blob or len(blob) < 2048:
        return None
    try:
        magic, ver, datalen, flags, sshots = struct.unpack(">IIIII", blob[:20])
    except Exception:
        return None
    if flags & (1 << asset_type) == 0:
        return None
    base = 0x14 + asset_type * 0x40
    idx, size, ext = struct.unpack(">III", blob[base : base + 12])
    th = struct.unpack(">13I", blob[base + 12 : base + 64])
    c = th[7:13]
    tiled = (c[0] & 0x80000000) >> 31
    dimension = (c[5] & 0x600) >> 9
    if tiled or dimension != 1:
        return None
    pitch = (c[0] & 0x7FC00000) >> 22
    fmt = c[1] & 0x3F
    endian = (c[1] & 0xC0) >> 6
    real_w = (c[2] & 0x1FFF) + 1
    real_h = ((c[2] & 0x03FFE000) >> 13) + 1
    swx = (c[3] & 0x0C) >> 2
    swy = (c[3] & 0x70) >> 4
    swz = (c[3] & 0x380) >> 7
    sww = (c[3] & 0x1C00) >> 10
    if pitch == 0 or size == 0 or idx + size > len(blob) - 2048:
        return None
    padded_w = pitch * 32
    bpp = 4 if fmt == 6 else 1
    padded_h = size // (padded_w * bpp)
    if padded_h <= 0:
        return None
    data = bytearray(blob[2048 + idx : 2048 + idx + size])
    rgba = decode_texture(data, fmt, endian, (swx, swy, swz, sww), padded_w, padded_h)
    if rgba is None:
        return None
    img = Image.frombytes("RGBA", (padded_w, padded_h), rgba)
    return img.crop((0, 0, real_w, real_h))


def _read_file(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def _decode_asset_safe(blob, asset_type):
    try:
        return decode_asset(blob, asset_type)
    except Exception:
        return None


def _open_image(path):
    try:
        return Image.open(path)
    except Exception:
        return None


def installed_path():
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Aurora Asset Manager")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, "aurora_covers_installed.json")


def custom_names_path():
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Aurora Asset Manager")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, "aurora_covers_names.json")


def load_custom_names():
    try:
        with open(custom_names_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_custom_names(data):
    try:
        tmp = custom_names_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, custom_names_path())
    except Exception:
        pass


def extra_games_path():
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Aurora Asset Manager")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, "aurora_covers_extra_games.json")


def load_extra_games():
    try:
        with open(extra_games_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [t.strip().upper() for t in data if isinstance(t, str) and t.strip()]
    except Exception:
        pass
    return []


def save_extra_games(tids):
    try:
        tmp = extra_games_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tids, f, indent=2)
        os.replace(tmp, extra_games_path())
    except Exception:
        pass


def added_folders_path():
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Aurora Asset Manager")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, "aurora_covers_added_folders.json")


def load_added_folders():
    """Carrega pastas adicionadas via 'Adicionar pasta para procurar jogos'.
    Retorna lista de dicts: {'folder': path, 'added': timestamp, 'count': n}"""
    try:
        with open(added_folders_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_added_folders(folders):
    try:
        tmp = added_folders_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(folders, f, indent=2, ensure_ascii=False)
        os.replace(tmp, added_folders_path())
    except Exception:
        pass


def hidden_games_path():
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Aurora Asset Manager")
    os.makedirs(docs, exist_ok=True)
    return os.path.join(docs, "aurora_covers_hidden.json")


def load_hidden_games():
    try:
        with open(hidden_games_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [t.strip().upper() for t in data if isinstance(t, str) and t.strip()]
    except Exception:
        pass
    return []


def save_hidden_games(tids):
    try:
        tmp = hidden_games_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(list(set(tids)), f, indent=2)
        os.replace(tmp, hidden_games_path())
    except Exception:
        pass


def mark_installed(tid, kind):
    try:
        data = {}
        p = installed_path()
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.setdefault(tid, {})[kind] = True
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    except Exception:
        pass


def is_installed(tid, kind):
    try:
        with open(installed_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool((data.get(tid) or {}).get(kind))
    except Exception:
        return False


def scan_aurora_db(root, logger=None):
    """Lê o content.db do Aurora para obter nomes reais dos jogos (inclui homebrews)."""
    def _log(msg):
        if logger:
            logger(msg)
        else:
            print(msg)
    games = []
    # Tenta vários caminhos comuns do content.db
    db_paths = [
        os.path.join(root, "Aurora", "Data", "Databases", "content.db"),
        os.path.join(root, "Data", "Databases", "content.db"),
        os.path.join(root, "Aurora", "Data", "content.db"),
    ]
    db_path = None
    for p in db_paths:
        if os.path.isfile(p):
            db_path = p
            break
    if not db_path:
        return games

    def _cols(conn, table):
        try:
            return [r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)]
        except sqlite3.Error:
            return []

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        _log(f"  [DB] Tabelas encontradas: {tables}")

        content_table = None
        for t in ["ContentItems", "Content", "Games", "GameList", "Titles", "ContentList"]:
            if t in tables:
                content_table = t
                _log(f"  [DB] Usando tabela: {content_table}")
                break
        if not content_table:
            _log("  [DB] Nenhuma tabela conhecida encontrada")
            conn.close()
            return games

        cols = _cols(conn, content_table)
        cv = lambda *names: next((c for c in cols if c.lower() in names), None)
        col_tid = cv("titleid", "tid", "title_id")
        col_title = cv("title", "name", "titlename", "gamename", "displayname")
        col_dir = cv("path", "gamepath", "location", "directory", "dir")
        col_sp = cv("scanpathid")
        col_exe = cv("executable", "exe")
        _log(f"  [DB] Mapeamento: tid={col_tid}, title={col_title}, dir={col_dir}")

        # ScanPaths + MountedDevices: resolve pastas absolutas no PC
        dev_map = {}
        if "MountedDevices" in tables:
            try:
                mcols = _cols(conn, "MountedDevices")
                mdev_id = next((c for c in mcols if c.lower() in ("deviceid", "device_id", "id")), None)
                mdev_mnt = next((c for c in mcols if "mountpoint" in c.lower() or c.lower() in ("path", "root")), None)
                if mdev_id and mdev_mnt:
                    for r in conn.execute('SELECT "%s","%s" FROM "MountedDevices"' % (mdev_id, mdev_mnt)):
                        dev_map[r[0]] = r[1] or ""
            except sqlite3.Error:
                pass
        sp_map = {}
        if "ScanPaths" in tables:
            try:
                scols = _cols(conn, "ScanPaths")
                sp_id = next((c for c in scols if c.lower() in ("id", "scanpathid", "pathid")), None)
                sp_path = next((c for c in scols if c.lower() in ("path", "contentpath", "location", "dir")), None)
                sp_dev = next((c for c in scols if "deviceid" in c.lower() or "device" in c.lower()), None)
                if sp_id and sp_path:
                    for r in conn.execute('SELECT * FROM "ScanPaths"'):
                        devid = r[sp_dev] if sp_dev else None
                        sp_map[r[sp_id]] = (dev_map.get(devid, "") if devid is not None else "", r[sp_path] or "")
            except sqlite3.Error:
                pass

        sel_cols = [c for c in (col_tid, col_title, col_dir, col_sp, col_exe) if c]
        sel_cols += [c for c in cols if c.lower() in ("mediaid", "contenttype", "filetype")]
        qcols = ", ".join('"%s"' % c for c in sel_cols) if sel_cols else "*"
        query = 'SELECT %s FROM "%s"' % (qcols, content_table)
        _log(f"  [DB] Query: {query}")
        count = 0
        for row in conn.execute(query):
            count += 1
            tid_raw = row[col_tid] if col_tid else None
            if tid_raw is None:
                tid = ""
            elif isinstance(tid_raw, int):
                # TitleId guardado como inteiro. Valores negativos ou fora do
                # intervalo de 32 bits (comuns em homebrews com TID inválido)
                # não formam um TID válido -> trata como homebrew.
                if 0 <= tid_raw <= 0xFFFFFFFF:
                    tid = "%08X" % tid_raw
                else:
                    tid = ""
            else:
                tid = (str(tid_raw) or "").strip().upper()
            title = (str(row[col_title] or "")).strip() if col_title else ""
            directory = (str(row[col_dir] or "")).strip() if col_dir else ""
            scanpath = row[col_sp] if col_sp else None
            mount, spbase = sp_map.get(scanpath, ("", "")) if scanpath is not None else ("", "")
            folder = None
            rel = re.sub(r"^(?:[A-Za-z]+:)?[\\/]*", "", (mount or "") + (spbase or "") + directory)
            rel = rel.replace("/", os.sep).replace("\\", os.sep)
            rel = re.sub(r"^[\\/]+", "", rel)
            if rel:
                # O Directory no content.db é relativo à RAIZ do drive (ex: \homebrew\...,
                # \jogos\...), não a \Aurora. Resolve contra a raiz do drive primeiro.
                drive_root = os.path.splitdrive(os.path.abspath(root))[0] + os.sep
                for _base in (drive_root, root, os.path.join(root, "Aurora")):
                    _cand = os.path.join(_base, rel)
                    if os.path.isdir(_cand):
                        folder = _cand
                        break
            # Homebrews (TitleId zerado/vazio) recebem TID pela pasta ou TID sintético
            if not tid or tid == "00000000":
                m = re.match(r"^([0-9A-F]{8})[_\s]?", os.path.basename(folder)) if folder else None
                if m:
                    tid = m.group(1)
                elif folder:
                    tid = "%08X" % (int(hashlib.sha1(rel.encode("utf-8", "replace")).hexdigest()[:8], 16) & 0xFFFFFFFF)
                elif title:
                    tid = "%08X" % (int(hashlib.sha1(title.encode("utf-8", "replace")).hexdigest()[:8], 16) & 0xFFFFFFFF)
                else:
                    continue
            if not title and folder:
                title = os.path.basename(folder)
            if not title:
                title = tid
            has_cover = bool(folder and find_cover_file(folder, tid))
            games.append({
                "folder": folder,
                "tid": tid,
                "folder_name": os.path.basename(folder) if folder else tid,
                "dname": title,
                "has_cover": has_cover,
            })
        conn.close()
        _log(f"  [DB] Total jogos carregados: {len(games)} (de {count} linhas)")
    except Exception as e:
        _log(f"  [DB] Erro ao ler banco: {e}")
    return games


def find_content_db(root):
    for p in (
        os.path.join(root, "Aurora", "Data", "Databases", "content.db"),
        os.path.join(root, "Data", "Databases", "content.db"),
        os.path.join(root, "Aurora", "Data", "content.db"),
    ):
        if os.path.isfile(p):
            return p
    return None


def db_backup(db_path):
    bak = db_path + ".bak"
    with open(db_path, "rb") as f:
        data = f.read()
    with open(bak, "wb") as f:
        f.write(data)
    return bak


def db_schema(conn):
    """Descobre a tabela e colunas principais do content.db do Aurora."""
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    table = next(
        (t for t in ("ContentItems", "Content", "Games", "GameList", "Titles", "ContentList") if t in tables),
        None,
    )
    if table is None:
        return None, None
    cols = [r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)]
    col_types = {}
    for row in conn.execute('PRAGMA table_info("%s")' % table):
        col_types[row[1]] = row[2] or ""
    col_id = next((c for c in cols if c.lower() in ("id", "contentitemid", "gameid")), None)
    col_tid = next((c for c in cols if c.lower() in ("titleid", "tid", "title_id")), None)
    col_title = next((c for c in cols if c.lower() in ("title", "name", "titlename", "gamename", "displayname")), None)
    col_dir = next((c for c in cols if c.lower() in ("path", "gamepath", "location", "directory", "dir")), None)
    return table, {
        "cols": cols,
        "col_types": col_types,
        "id": col_id,
        "tid": col_tid,
        "title": col_title,
        "dir": col_dir,
    }


def db_row_kind(directory):
    """Classifica pelo CÓDIGO DE PASTA exato (segmento de 8 hex), não por substring
    (evita TIDs/pastas conterem códigos e marcarem jogo normal como DLC/TU/XBLA).
    Mapeamento real do 360/Aurora:
      00000000 -> jogo (base), GAMEDATA -> jogo
      00000002 -> DLC
      00004000 -> XBLA (Arcade)
      00007000 -> GOD (Games on Demand -> é um JOGO)
      00008000 -> Avatar
      000B0000 -> Title Update
      000D0000 -> Dados instalados/save
    """
    segs = [s for s in re.split(r"[\\/]", (directory or "").upper()) if s]
    codes = {
        "00000002": "dlc",
        "00004000": "xbla",
        "00007000": "god",
        "00008000": "avatar",
        "000B0000": "tu",
        "000D0000": "data",
    }
    for s in segs:
        if s in codes:
            return codes[s]
    if not segs:
        return "other"
    if "00000000" in segs or "GAMEDATA" in segs:
        return "game"
    # sem código explícito, mas a última pasta é um TID (rip direto na pasta de scan)
    return "game" if re.match(r"^[0-9A-F]{8}$", segs[-1]) else "other"


def db_kind_label(kind):
    lang = CURRENT_LANG
    m = {
        "dlc": {"pt": "DLC", "en": "DLC", "es": "DLC", "fr": "DLC", "ja": "DLC", "ru": "DLC"},
        "xbla": {"pt": "XBLA", "en": "XBLA", "es": "XBLA", "fr": "XBLA", "ja": "XBLA", "ru": "XBLA"},
        "god": {"pt": "Jogo GOD", "en": "Games on Demand", "es": "Juego GOD", "fr": "Jeu GoD", "ja": "GODゲーム", "ru": "Игра GOD"},
        "avatar": {"pt": "Avatar", "en": "Avatar", "es": "Avatar", "fr": "Avatar", "ja": "アバター", "ru": "Аватар"},
        "tu": {"pt": "TU/Update", "en": "Title Update", "es": "TU/Update", "fr": "Màj titre", "ja": "TU/アップデート", "ru": "TU/Обновление"},
        "data": {"pt": "Dados", "en": "Data", "es": "Datos", "fr": "Données", "ja": "データ", "ru": "Данные"},
        "game": {"pt": "Jogo", "en": "Game", "es": "Juego", "fr": "Jeu", "ja": "ゲーム", "ru": "Игра"},
        "other": {"pt": "Outro", "en": "Other", "es": "Otro", "fr": "Autre", "ja": "その他", "ru": "Другое"},
    }
    return m.get(kind, m["other"]).get(lang, "Other")


def db_rows(conn, table, sc, only_special=False, kinds=None, text=""):
    conn.row_factory = sqlite3.Row
    out = []
    text = (text or "").strip().lower()
    kw = set()
    if only_special:
        kw = {"dlc", "xbla", "tu"}
    elif kinds:
        kw = set(kinds)
    for row in conn.execute('SELECT * FROM "%s"' % table):
        tid = row[sc["tid"]]
        if isinstance(tid, int):
            tid = "%08X" % tid
        else:
            tid = (str(tid) or "").strip().upper()
        directory = str(row[sc["dir"]] or "").strip() if sc["dir"] else ""
        kind = db_row_kind(directory)
        if kw and kind not in kw:
            continue
        name = str(row[sc["title"]] or "").strip()
        if text and text not in " ".join((tid, name, directory)).lower():
            continue
        out.append({
            "id": row[sc["id"]],
            "tid": tid,
            "name": name,
            "dir": directory,
            "kind": kind,
            "label": db_kind_label(kind),
        })
    return out


def db_add_row(conn, table, sc, tid, name, directory):
    fields = {}
    if sc["tid"]:
        ctype = (sc["col_types"].get(sc["tid"]) or "").upper()
        fields[sc["tid"]] = int(tid, 16) if "INT" in ctype else tid
    if sc["title"]:
        fields[sc["title"]] = name
    if sc["dir"]:
        fields[sc["dir"]] = directory
    for cn in sc["cols"]:
        lcn = cn.lower()
        if cn in fields:
            continue
        if lcn in ("scanpathid", "databaseid", "dbid"):
            scanpath = 1
            try:
                for row in conn.execute('SELECT "%s" FROM "%s" LIMIT 1' % (cn, table)):
                    scanpath = row[0]
                    break
            except sqlite3.Error:
                pass
            fields[cn] = scanpath
        elif lcn == "mediaid":
            fields[cn] = 0
        elif lcn == "contenttype":
            fields[cn] = 0
        elif lcn == "filetype":
            fields[cn] = 0
        elif lcn in ("executable", "exe"):
            fields[cn] = "default.xex"
    if not fields:
        return False
    cols_str = ", ".join('"%s"' % c for c in fields)
    ph = ", ".join("?" * len(fields))
    conn.execute('INSERT INTO "%s" (%s) VALUES (%s)' % (table, cols_str, ph), list(fields.values()))
    return True


def db_update_title(conn, table, sc, rowid, newtitle):
    conn.execute(
        'UPDATE "%s" SET "%s" = ? WHERE "%s" = ?' % (table, sc["title"], sc["id"]),
        (newtitle, rowid),
    )


def db_rename_by_tid(root, tid, newtitle):
    """Atualiza o TitleName de um jogo diretamente no content.db pelo seu TID.
    Retorna True se encontrou e atualizou."""
    db_path = find_content_db(root)
    if not db_path:
        return False
    try:
        conn = sqlite3.connect(db_path)
        table, sc = db_schema(conn)
        if table is None or not sc["id"] or not sc["tid"] or not sc["title"]:
            conn.close()
            return False
        target = ("%08X" % int(tid, 16)) if re.match(r"^[0-9A-F]{8}$", tid) else tid
        conn.row_factory = sqlite3.Row
        found = False
        for row in conn.execute('SELECT "%s" FROM "%s"' % (sc["id"], table)):
            rowid = row[0]
            raw = None
            try:
                raw = conn.execute('SELECT "%s" FROM "%s" WHERE "%s" = ?' % (sc["tid"], table, sc["id"]), (rowid,)).fetchone()
            except sqlite3.Error:
                raw = None
            if raw is None:
                continue
            rawv = raw[0]
            if isinstance(rawv, int):
                cur = "%08X" % rawv
            else:
                cur = (str(rawv) or "").strip().upper()
            if cur in (target, tid):
                conn.execute(
                    'UPDATE "%s" SET "%s" = ? WHERE "%s" = ?' % (table, sc["title"], sc["id"]),
                    (newtitle, rowid),
                )
                found = True
                break
        conn.commit()
        conn.close()
        return found
    except sqlite3.Error:
        return False


def db_delete_row(conn, table, sc, rowid):
    conn.execute('DELETE FROM "%s" WHERE "%s" = ?' % (table, sc["id"]), (rowid,))


def parse_xex2(filepath):
    """Extrai o TitleID e MediaID de um executável XEX2 (Xbox 360) lendo o header.
    Retorna dict com 'title_id','media_id' (None se for homebrew/sem Execution Info)."""
    info = {"title_id": None, "media_id": None}
    try:
        with open(filepath, "rb") as f:
            head = f.read(12)
        if len(head) < 12 or head[0:4] != b"XEX2":
            return info
        if len(head) >= 12:
            n_headers = int.from_bytes(head[8:12], "big")
        else:
            n_headers = 0
        off = 12
        with open(filepath, "rb") as f:
            f.seek(off)
            for _ in range(n_headers):
                hs = f.read(4)
                if len(hs) < 4:
                    break
                hsize = int.from_bytes(hs, "big")
                ht = f.read(4)
                if len(ht) < 4:
                    break
                htype = int.from_bytes(ht, "big")
                data = f.read(hsize - 8)
                if htype == 0x00010196:  # Execution Info
                    if len(data) >= 0x14:
                        media_id = int.from_bytes(data[0x04:0x08], "big")
                        title_id = int.from_bytes(data[0x10:0x14], "big")
                        info["media_id"] = media_id
                        info["title_id"] = title_id
                    break
    except Exception:
        pass
    return info


def locate_xex_in_folder(folder):
    """Procura o .xex principal de um jogo (default.xex ou o único .xex na pasta)."""
    if not folder or not os.path.isdir(folder):
        return None
    defxex = os.path.join(folder, "default.xex")
    if os.path.isfile(defxex):
        return defxex
    try:
        for fn in sorted(os.listdir(folder)):
            if fn.lower().endswith(".xex") and os.path.isfile(os.path.join(folder, fn)):
                return os.path.join(folder, fn)
    except OSError:
        pass
    return None


def scan_homebrew_xex(root, known_folders=None):
    """Descobre homebrews do mesmo jeito que o Aurora/Unity: pela presença de um
    executável (.xex) dentro dos scan paths (360, homebrew e os ScanPaths do content.db).
    Homebrews não têm TitleId válido, então recebem um TID sintético estável."""
    known = set(os.path.normpath(f) for f in (known_folders or []) if f)
    known_norm = set(os.path.normcase(f) for f in known)
    bases = []
    db_path = find_content_db(root)
    if db_path:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "ScanPaths" in tables:
                dev_map = {}
                if "MountedDevices" in tables:
                    try:
                        mcols = [r[1] for r in conn.execute('PRAGMA table_info("MountedDevices")')]
                        mdev_id = next((c for c in mcols if c.lower() in ("deviceid", "device_id", "id")), None)
                        mdev_mnt = next((c for c in mcols if "mountpoint" in c.lower() or c.lower() in ("path", "root")), None)
                        if mdev_id and mdev_mnt:
                            for r in conn.execute('SELECT "%s","%s" FROM "MountedDevices"' % (mdev_id, mdev_mnt)):
                                dev_map[r[0]] = r[1] or ""
                    except sqlite3.Error:
                        pass
                try:
                    scols = [r[1] for r in conn.execute('PRAGMA table_info("ScanPaths")')]
                    sp_id = next((c for c in scols if c.lower() in ("id", "scanpathid", "pathid")), None)
                    sp_path = next((c for c in scols if c.lower() in ("path", "contentpath", "location", "dir")), None)
                    sp_dev = next((c for c in scols if "deviceid" in c.lower() or "device" in c.lower()), None)
                    for r in conn.execute('SELECT * FROM "ScanPaths"'):
                        devid = r[sp_dev] if sp_dev else None
                        mount = dev_map.get(devid, "") if devid is not None else ""
                        seg = re.sub(r"^(?:[A-Za-z]+:)?[\\/]*", "", (mount or "") + (r[sp_path] or "") if sp_path else "")
                        seg = seg.replace("/", os.sep).replace("\\", os.sep).rstrip("\\")
                        if not seg or not os.path.isdir(os.path.join(root, seg)):
                            continue
                        low = seg.lower()
                        if low.startswith(os.path.join("content", "")) or low == "content" or "gamedata" in low:
                            continue  # os jogos reais/DLC já vêm do DB
                        bases.append(os.path.join(root, seg))
                except sqlite3.Error:
                    pass
            conn.close()
        except sqlite3.Error:
            pass
    bases += [os.path.join(root, "360"), os.path.join(root, "homebrew")]
    # Homebrews/ILA XBLA costumam ficar em Content\\0000000000000000\\<TID>\\...
    # (mesmo endereço dos jogos do sistema), então incluímos a raiz de conteúdo e
    # filtramos no walk pelos códigos de subpasta que NÃO são o jogo em si.
    content_root = os.path.join(root, "Content", "0000000000000000")
    if os.path.isdir(content_root):
        bases.append(content_root)
    bases = list(dict.fromkeys(b for b in bases if os.path.isdir(b)))
    norm_bases = set(os.path.normcase(b) for b in bases)

    out = []
    hex8 = re.compile(r"^([0-9A-F]{8})$")
    # Códigos de subpasta de conteúdo que NÃO representam o jogo/base (DLC, TU, dados)
    skip_seg = {"00000002", "000B0000", "000D0000", "00008000"}
    for base in bases:
        for dirpath, dirnames, filenames in os.walk(base):
            depth = 0
            relpath = dirpath
            if base != root:
                try:
                    relpath = os.path.relpath(dirpath, base)
                    depth = 0 if relpath == "." else len(relpath.split(os.sep))
                except ValueError:
                    pass
            if depth > 4:
                dirnames[:] = []
                continue
            # Poda subpastas de conteúdo que não são o jogo/base (DLC/TU/dados)
            parts = re.split(r"[\\/]", dirpath)
            if any(p.upper() in skip_seg for p in parts):
                dirnames[:] = []
                continue
            # Subpastas Media/Managed contêm assemblies/.NET, não são jogos
            if any(p.lower() in ("media", "managed") for p in parts):
                dirnames[:] = []
                continue
            if not any(fn.lower().endswith(".xex") for fn in filenames):
                continue
            folder = os.path.normpath(dirpath)
            # A raiz de um scan path é um CONTÊINER de jogos (ex.: \\homebrew),
            # não um jogo em si: nunca tratá-la como jogo (evita "homebres" na lista).
            if os.path.normcase(folder) in norm_bases:
                continue
            if os.path.normcase(folder) in known_norm:
                continue
            known_norm.add(os.path.normcase(folder))
            known.add(folder)
            rel = os.path.relpath(dirpath, root).replace("/", os.sep)
            # TID: usar um TID hex de 8 dígitos encontrado na árvore do caminho
            # (a pasta do jogo, ou a pasta TID em Content\\...\\<TID>\\...).
            # Códigos de subpasta de conteúdo (00007000, 00000002, etc) não são TIDs.
            non_tid = {"00000000", "0000000000000000", "00000002", "00007000", "00004000", "000B0000", "000D0000", "00008000"}
            try:
                rel_parts = os.path.relpath(dirpath, base).split(os.sep)
            except ValueError:
                rel_parts = parts
            candidate_tid = None
            for seg in (os.path.basename(dirpath), os.path.basename(os.path.dirname(dirpath))):
                if hex8.match(seg) and seg not in non_tid:
                    candidate_tid = seg
                    break
            if candidate_tid is None:
                for seg in rel_parts:
                    if hex8.match(seg) and seg not in non_tid:
                        candidate_tid = seg
                        break
            m = candidate_tid
            src = rel if rel else os.path.basename(dirpath)
            tid = m if m else "%08X" % (int(hashlib.sha1(src.encode("utf-8", "replace")).hexdigest()[:8], 16) & 0xFFFFFFFF)
            # Nome legível: primeiro segmento que não seja código de conteúdo nem TID
            def _bad_seg(s):
                u = (s or "").upper()
                return (not s) or u in non_tid or u in ("CONTENT",) or hex8.match(s)
            name = os.path.basename(dirpath)
            if _bad_seg(name):
                name = next(
                    (s for s in reversed(rel_parts) if not _bad_seg(s)),
                    tid,
                )
            has_cover = bool(find_cover_file(dirpath, tid))
            out.append({
                "folder": folder,
                "tid": tid,
                "folder_name": os.path.basename(folder),
                "dname": name,
                "has_cover": has_cover,
            })
    return out


def scan_aurora(root):
    # Carrega nomes customizados salvos
    custom_names = load_custom_names()
    log(f"  [SCAN] Nomes customizados carregados: {len(custom_names)}")

    # Primeiro tenta ler do SQLite do Aurora (nomes reais)
    games = scan_aurora_db(root, logger=lambda m: log(m))
    if not games:
        log("  [DB] Falhou ou vazio, tentando fallback por pastas...")
    
    # Fallback: escaneia pastas GameData
    gamedata = os.path.join(root, "Data", "GameData")
    if os.path.isdir(gamedata):
        folder_games = []
        # Suporta pastas "<TID>_<Nome>" e também "<TID>" sozinho (sem underline),
        # pra pegar mais jogos (GOD/XDLC/pastas só com o TitleID).
        pattern = re.compile(r"^([0-9A-Fa-f]{8})(?:_(.+))?$")
        for name in sorted(os.listdir(gamedata)):
            m = pattern.match(name)
            if not m:
                continue
            tid = m.group(1).upper()
            if tid == "00000000":
                continue
            dname = (m.group(2) or "").strip() or tid
            # Aplica nome customizado se existir
            if tid in custom_names:
                dname = custom_names[tid]
            folder = os.path.join(gamedata, name)
            if not os.path.isdir(folder):
                continue
            has_cover = False
            has_cover = bool(find_cover_file(folder, tid))
            folder_games.append({
                "folder": folder,
                "tid": tid,
                "folder_name": name,
                "dname": dname,
                "has_cover": has_cover,
            })
        # Merge: jogos do DB têm prioridade, pastas preenchem faltantes
        existing_tids = {g["tid"] for g in games}
        for fg in folder_games:
            if fg["tid"] not in existing_tids:
                games.append(fg)
                continue
            dbg = next(g for g in games if g["tid"] == fg["tid"])
            if not dbg.get("folder"):
                dbg["folder"] = fg["folder"]
                dbg["folder_name"] = fg["folder_name"]
                dbg["has_cover"] = bool(dbg.get("has_cover")) or bool(fg["has_cover"])

    # Também escaneia pasta Import para homebrews sem GameData
    # (checa User\Import na raiz do drive E dentro de \Aurora, onde versões
    # antigas do app gravavam capas baixadas)
    for import_dir in import_dirs_existing(root):
        for tid_dir in os.listdir(import_dir):
            if not re.match(r"^[0-9A-Fa-f]{8}$", tid_dir):
                continue
            tid = tid_dir.upper()
            if tid == "00000000":
                continue
            # Tenta pegar nome customizado
            dname = custom_names.get(tid, tid)
            import_path = os.path.join(import_dir, tid_dir)
            has_cover = False
            if os.path.isdir(import_path):
                for fn in os.listdir(import_path):
                    upper = fn.upper()
                    # Aurora: capa de Import é cover.png / cover.jpg / cover.dds (ou GC*.asset legado)
                    if (
                        upper.startswith("COVER") and fn.lower().endswith((".png", ".jpg", ".jpeg", ".dds"))
                    ) or (upper.startswith("GC") and fn.lower().endswith((".png", ".asset"))):
                        if has_cover_image(os.path.join(import_path, fn)):
                            has_cover = True
                            break
            # Se o jogo já veio do DB/pastas (ex: homebrew via .xex), aproveita o
            # título e só enriquece a capa de Import que o scan anterior não achou.
            existing = next((g for g in games if g["tid"] == tid), None)
            if existing is None:
                # Reconcile: versões antigas do app gravavam capas de homebrew sob
                # um TID sintético = SHA1 do NOME do jogo (ex: Sonic Mania = FA5F679D).
                # Se o TID do Import bater com esse hash, usa o jogo correspondente.
                legacy = next(
                    (g for g in games if legacy_tid_for(g.get("dname")) == tid),
                    None,
                )
                if legacy is not None:
                    existing = legacy
            if existing is not None:
                if not existing.get("dname") and dname != tid:
                    existing["dname"] = dname
                if has_cover and not existing["has_cover"]:
                    existing["has_cover"] = True
                    existing["import_cover"] = import_path
                continue
            games.append({
                "folder": None,
                "tid": tid,
                "folder_name": tid,
                "dname": dname,
                "has_cover": has_cover,
                "import_cover": import_path if has_cover else None,
            })

    # Varredura física de homebrews (identificação por executável, como o Aurora/Unity)
    homebrew = scan_homebrew_xex(
        root,
        known_folders=[g.get("folder") for g in games if g.get("folder")],
    )
    if homebrew:
        log(f"  [SCAN] Homebrews encontrados por .xex: {len(homebrew)}")
        games.extend(homebrew)

    # Aplica nomes customizados aos jogos (rename do usuário tem prioridade
    # sobre o nome do DB/auto-detetado; se não aplicar, o nome volta ao antigo
    # no próximo scan quando o content.db não foi alterado).
    for g in games:
        if g["tid"] in custom_names:
            g["dname"] = custom_names[g["tid"]]

    # Deduplicação — por TID e também por pasta (case-insensitive), para evitar
    # duplicar homebrews que o DB encontra numa capitalização e o scan de .xex
    # encontra noutra (ex.: \\homebrew\\supermariowar vs \\homebrew\\SuperMarioWar).
    seen = {}
    deduped = []
    for g in games:
        key = g["tid"]
        if key not in seen:
            seen[key] = g
            deduped.append(g)
        elif not seen[key]["has_cover"] and g["has_cover"]:
            i = deduped.index(seen[key])
            deduped[i] = g
            seen[key] = g
    # Merge por pasta normalizada (mantém a entrada com TID real/dname, descarta duplicata)
    folder_seen = {}
    merged = []
    for g in deduped:
        f = g.get("folder")
        if not f:
            merged.append(g)
            continue
        nf = os.path.normcase(os.path.normpath(f))
        if nf not in folder_seen:
            folder_seen[nf] = g
            merged.append(g)
            continue
        keep = g
        other = folder_seen[nf]
        # Prefere a entrada com TID hex "real" (8 dígitos) e nome legível
        def _real_tid(x):
            t = str(x.get("tid") or "")
            return bool(re.fullmatch(r"[0-9A-F]{8}", t)) and t not in ("00000000",)
        if _real_tid(other) and not _real_tid(keep):
            continue
        if _real_tid(keep) and not _real_tid(other):
            i = merged.index(other)
            merged[i] = keep
            folder_seen[nf] = keep
            continue
        if not keep.get("dname") and other.get("dname"):
            keep["dname"] = other["dname"]
        elif keep.get("dname") and other.get("dname"):
            # Prefere nome do DB (content.db TitleName) sobre nome de pasta do XEX scan
            # Heurística: nomes do DB não parecem caminhos de pasta
            if ("\\" in keep["dname"] or "/" in keep["dname"]) and not ("\\" in other["dname"] or "/" in other["dname"]):
                keep["dname"] = other["dname"]
        if not keep["has_cover"] and other["has_cover"]:
            keep["has_cover"] = True
    log(f"  [SCAN] Total de jogos encontrados: {len(merged)}")
    return merged


def scan_hdd_content(root):
    tids = []
    pattern = re.compile(r"^[0-9A-Fa-f]{8}$")
    for drive_entry in os.listdir(root):
        content = os.path.join(root, drive_entry, "Content", "0000000000000000")
        if os.path.isdir(content):
            ids = [d for d in os.listdir(content) if pattern.match(d)]
            ids.sort()
            tids.extend(ids)
    root_content = os.path.join(root, "Content", "0000000000000000")
    if os.path.isdir(root_content):
        for d in os.listdir(root_content):
            if pattern.match(d) and d not in tids:
                tids.append(d)
    return [t for t in tids if t != "00000000"]


def import_bases(root):
    """Pastas User\\Import onde o Aurora (e o app) guardam capas baixadas.

    O Aurora lê as capas de Import a partir da RAIZ do drive (\\User\\Import).
    Versões antigas do app gravavam em \\Aurora\\User\\Import quando o caminho
    selecionado era a pasta do Aurora; por isso checamos as duas localizações,
    priorizando a raiz do drive (localização oficial), para nunca perder capas."""
    bases = []
    r = (root or "").strip().strip('"')
    roots = [r] if r else []
    drive = os.path.splitdrive(os.path.abspath(r or os.getcwd()))[0] + os.sep
    if drive and drive not in roots:
        roots.append(drive)
    # Prioridade: raiz do drive primeiro, depois o caminho selecionado.
    ordered = []
    for rr in (["%s" % drive] if drive else []) + roots:
        for p in (os.path.join(rr, "User", "Import"), os.path.join(rr, "Aurora", "User", "Import")):
            p = os.path.normpath(p)
            if p not in ordered:
                ordered.append(p)
    return ordered


def import_dirs_existing(root):
    return [d for d in import_bases(root) if os.path.isdir(d)]


def legacy_tid_for(name):
    """TID sintético que versões antigas do app usavam para homebrews: SHA1 do NOME."""
    if not name:
        return None
    return "%08X" % (int(hashlib.sha1(name.encode("utf-8", "replace")).hexdigest()[:8], 16) & 0xFFFFFFFF)


def homebrew_search_queries(g):
    """Gera queries para buscar capa de homebrew no XboxUnity (TitleList.php).
    A Unity indexa homebrews por um TitleID interno pequeno + nome, não pelo TID do XEX
    (o HBTitleID é só informativo). O fallback procura pelo nome do jogo (DB e pasta)."""
    seen = set()
    out = []

    def _add(q):
        q = re.sub(r"\s+", " ", (q or "")).strip()
        if not q:
            return
        low = q.lower()
        if low in seen:
            return
        seen.add(low)
        out.append(q)

    for key in ("dname", "folder_name"):
        raw = str(g.get(key) or "").strip()
        if not raw or raw.lower() == str(g.get("tid") or "").lower():
            continue
        _add(raw)
        toks = [t for t in re.split(r"[\s_\-\.\(\)\[\]]+", raw) if t]
        if toks:
            _add(toks[0])
            if len(toks) >= 2:
                _add("%s %s" % (toks[0], toks[1]))
    return out[:6]


def cover_exts():
    return (".png", ".jpg", ".jpeg", ".dds")


def iter_cover_names(folder, tid=None):
    """Gera os nomes de arquivos de capa que o Aurora reconhece dentro da pasta do jogo:
    GC*.asset (container AURORA/COM do app e do Aurora) e boxart/cover em PNG/JPEG/DDS
    (usados pelo Aurora para capas de homebrews e jogos). Ordena priorizando o GC do TID."""
    try:
        names = os.listdir(folder)
    except OSError:
        return
    exts = cover_exts()
    tid = (tid or "").upper()
    # Primeiro o GC exatamente do TID do jogo (evita pegar capa de OUTRO jogo
    # quando vários jogos dividem a mesma pasta, ex.: XBLA em \xbox 360 dvd).
    if tid:
        for name in sorted(names):
            base, ext = os.path.splitext(name)
            if base.upper() == "GC" + tid and ext.lower() in (".asset",) + exts:
                if has_cover_image(os.path.join(folder, name)):
                    yield name
                    return
    for name in sorted(names):
        up = name.upper()
        if up.startswith("GC") and name.lower().endswith((".asset",) + exts):
            yield name
    for name in sorted(names):
        up = name.upper()
        if (up.startswith("BOXART") or up.startswith("COVER")) and name.lower().endswith(exts):
            yield name


def find_cover_file(folder, tid=None):
    """Encontra a capa de um jogo na pasta, igual ao Aurora: além do GC*.asset,
    aceita boxart.* e cover.* (PNG/JPEG/DDS) que ficam dentro da pasta do jogo.
    Quando `tid` é informado, prioriza o GC<TID>.asset exato do jogo, para não
    mostrar a capa de outro jogo que compartilha a mesma pasta."""
    if not folder or not os.path.isdir(folder):
        return None
    for name in iter_cover_names(folder, tid):
        path = os.path.join(folder, name)
        if has_cover_image(path):
            return path
    return None


def open_cover_image(path):
    """Abre uma capa instalada: container RXEA do app, JPEG/PNG puro ou
    JPEG/PNG com header proprio embutido (como alguns arquivos do Aurora)."""
    blob = _read_file(path)
    if blob is None:
        return None
    img = _decode_asset_safe(blob, ASSET_TYPE_BOXART)
    if img is not None:
        return img
    img = _open_image(path)
    if img is not None:
        return img
    for marker in (b"\xFF\xD8\xFF", b"\x89PNG\r\n\x1a\n"):
        idx = blob.find(marker)
        if idx > 0:
            try:
                return Image.open(io.BytesIO(blob[idx:])).convert("RGBA")
            except Exception:
                pass
    return None


def has_cover_image(path):
    """Detecta de forma leve se um arquivo contém uma imagem de capa real:
    container RXEA do app, JPEG/PNG puro ou JPEG embutido após um header."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return False
    return head[:4] == b"RXEA" or b"\xFF\xD8\xFF" in head or b"\x89PNG\r\n\x1a\n" in head


def selftest():
    img = Image.new("RGBA", (900, 600), (200, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((100, 100, 500, 300), fill=(0, 200, 0, 255))
    blob = make_asset_bytes(img, ASSET_TYPE_BOXART)
    assert blob[:4] == b"RXEA", blob[:4].hex()
    assert len(blob) >= 2048
    header_len = struct.unpack(">I", blob[8:12])[0]
    assert header_len == len(blob) - 2048
    flags = struct.unpack(">I", blob[12:16])[0]
    assert flags & (1 << ASSET_TYPE_BOXART)
    back = decode_asset(blob, ASSET_TYPE_BOXART)
    assert back is not None
    assert back.size == (900, 600)
    assert back.getpixel((200, 200)) == (0, 200, 0, 255)
    assert back.getpixel((700, 100)) == (200, 30, 30, 255)
    print("selftest OK: %d bytes, decode round-trip OK" % len(blob))

    icon = Image.new("RGBA", (ICON_W, ICON_H), (10, 20, 30, 255))
    banner = Image.new("RGBA", (BANNER_W, BANNER_H), (40, 50, 60, 255))
    gl = make_multi_asset_bytes([(ASSET_TYPE_ICON, icon), (ASSET_TYPE_BANNER, banner)])
    gl_flags = struct.unpack(">I", gl[12:16])[0]
    assert gl_flags == (1 << ASSET_TYPE_ICON) | (1 << ASSET_TYPE_BANNER)
    assert decode_asset(gl, ASSET_TYPE_ICON).getpixel((10, 10)) == (10, 20, 30, 255)
    assert decode_asset(gl, ASSET_TYPE_BANNER).getpixel((10, 10)) == (40, 50, 60, 255)

    ss1 = Image.new("RGBA", (SS_W, SS_H), (100, 110, 120, 255))
    ss2 = Image.new("RGBA", (SS_W, SS_H), (200, 210, 220, 255))
    ss = make_multi_asset_bytes(
        [(ASSET_TYPE_SCREENSHOT, ss1), (ASSET_TYPE_SCREENSHOT + 1, ss2)]
    )
    ss_flags = struct.unpack(">I", ss[12:16])[0]
    ss_count = struct.unpack(">I", ss[16:20])[0]
    assert ss_flags == (1 << ASSET_TYPE_SCREENSHOT) | (1 << (ASSET_TYPE_SCREENSHOT + 1))
    assert ss_count == 2
    assert decode_asset(ss, ASSET_TYPE_SCREENSHOT).getpixel((10, 10)) == (100, 110, 120, 255)
    assert decode_asset(ss, ASSET_TYPE_SCREENSHOT + 1).getpixel((10, 10)) == (200, 210, 220, 255)
    print("selftest OK: GL (ícone+banner) e SS (screenshots) OK")

    retrato = box_render(Image.new("RGBA", (300, 400), (9, 9, 9, 255)), "retrato")
    paisagem = box_render(Image.new("RGBA", (300, 400), (8, 8, 8, 255)), "paisagem")
    assert retrato.size == (COVER_W, COVER_H)
    assert paisagem.size == (BOXART_W, BOXART_H)
    print("selftest OK: box_render (retrato 900x1233 e paisagem 900x600) OK")

    cfg = {
        "theme": "escuro",
        "repo": "x360db",
        "cover_format": "paisagem",
        "screenshots": SS_MAX_DEFAULT,
        "lang": "pt",
        "show_status": True,
        "show_log": True,
        "auto_search_titles": True,
        "show_game_info": True,
        "show_debug_button": False,
        "download_missing_only": True,
        "auto_update_check": True,
        "ftp_host": "",
        "ftp_port": 21,
        "ftp_user": "xbox",
        "ftp_pass": "xbox",
        "ftp_base": "Hdd:\\Aurora\\Data\\GameData",
    }
    assert dict(DEFAULT_CONFIG) == cfg
    _old_lang = globals()["CURRENT_LANG"]
    globals()["CURRENT_LANG"] = "pt"
    assert tr("warn") == "Aviso"
    globals()["CURRENT_LANG"] = "en"
    assert tr("warn") == "Warning"
    assert tr("alt_count", 3) == "3 cover(s) found."
    globals()["CURRENT_LANG"] = "pt"
    assert tr("warn") == "Aviso"
    assert tr("alt_count", 3) == "3 capa(s) encontrada(s)."
    globals()["CURRENT_LANG"] = "es"
    assert tr("warn") == "Advertencia"
    assert tr("alt_count", 2) == "2 portada(s) encontrada(s)."
    globals()["CURRENT_LANG"] = "fr"
    assert tr("warn") == "Avertissement"
    assert tr("alt_count", 5) == "5 jaquette(s) trouvée(s)."
    globals()["CURRENT_LANG"] = "ja"
    assert tr("warn") == "警告"
    assert tr("alt_count", 1) == "1 個のカバーが見つかりました。"
    globals()["CURRENT_LANG"] = "ru"
    assert tr("warn") == "Предупреждение"
    assert tr("alt_count", 4) == "Найдено обложек: 4."
    globals()["CURRENT_LANG"] = _old_lang
    en_keys = set(TEXT["en"].keys())
    for lang_code in LANGUAGES:
        missing = en_keys - set(TEXT[lang_code].keys())
        assert not missing, "translations missing in %s: %s" % (lang_code, sorted(missing))
    assert tr("m_rename") != "m_rename"
    assert [k for k, *_ in ASSET_KINDS] == ["boxart", "background", "icon", "banner", "screenshots"]
    assert THEMES["escuro"]["fg"] == "#e6e6e6"
    print("selftest OK: configurações e temas OK")


class App:
    def __init__(self, root):
        self.root = root
        self.queue = queue.Queue()
        self._db = None
        self._unity = None
        self.cfg = {}
        self.theme = "escuro"
        self.repo = "x360db"
        self.cover_format = "paisagem"
        self.ss_max = SS_MAX_DEFAULT
        self.lang = "pt"
        global CURRENT_LANG
        CURRENT_LANG = "pt"
        # Aplica o idioma salvo ANTES de construir a interface, senão os textos
        # são criados com o idioma do sistema e a interface fica em português mesmo
        # com outro idioma configurado.
        try:
            _early_cfg = load_config()
            if _early_cfg.get("lang") in TEXT:
                self.lang = _early_cfg["lang"]
                CURRENT_LANG = self.lang
        except Exception:
            pass
        self.show_status = True
        self.show_log = True
        self.ftp_host = ""
        self.ftp_port = 21
        self.ftp_user = "xbox"
        self.ftp_pass = "xbox"
        self.ftp_base = "Hdd:\\Aurora\\Data\\GameData"
        self.sort_asc = True
        self.cancel_event = threading.Event()
        self.unity_status = "checking"
        self.x360db_status = "checking"
        self.gameart_status = "checking"
        self._applied_theme = ""
        self.aurora_path = tk.StringVar()
        self.opt_boxart = tk.BooleanVar(value=True)
        self.opt_background = tk.BooleanVar(value=True)
        self.opt_force = tk.BooleanVar(value=False)
        self.opt_backup = tk.BooleanVar(value=True)
        self.opt_icon = tk.BooleanVar(value=True)
        self.opt_banner = tk.BooleanVar(value=True)
        self.opt_screenshots = tk.BooleanVar(value=True)
        self.opt_missing_only = tk.BooleanVar(value=True)
        self.opt_auto_search = tk.BooleanVar(value=True)
        self.games = []
        self.hidden_tids = set(load_hidden_games())
        self.worker = None
        self.busy = False
        self._last_assets_kind = None
        # Download queue: each item = (games_list, path, kinds_dict)
        self.download_queue = queue.Queue()
        self.download_worker_thread = None
        self.current_download_job = None
        # Update checker
        self.update_check_thread = None
        self.last_update_check = 0
        self.latest_version = None
        self.update_available = False
        self.item_to_game = {}
        self.search_var = tk.StringVar()
        self._photo = None
        self.preview_cache = {}
        self._preview_cache_lock = threading.Lock()
        self._preview_cache_max = 100
        self._assets_dlg = None
        self._assets_tree = None
        self._assets_kinds = {}
        self._assets_g = None
        self._assets_path = ""
        self._assets_msg = None
        self._assets_ss_index = 0
        self._assets_prev = None
        self._assets_next = None
        self._alt_dlg = None
        self._alt_lb = None
        self._alt_msg = None
        self._alt_preview = None
        self._alt_items = []
        self._alt_photo = None
        self._alt_preview_item = (0, None)
        self.unity_status = "checking"

        root.title(tr("title"))
        try:
            screen_h = root.winfo_screenheight()
            screen_w = root.winfo_screenwidth()
        except tk.TclError:
            screen_h, screen_w = 768, 1366
        geo_h = max(620, min(760, screen_h - 90))
        geo_w = max(900, min(1040, screen_w - 40))
        self.txt_rows = 5 if screen_h <= 720 else 8
        root.geometry("%dx%d" % (geo_w, geo_h))
        if screen_h <= 720:
            root.state("zoomed")
        root.minsize(860, 560)

        frm = ttk.Frame(root, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        self._build_ui(frm)
        self._load_config_async()
        self.root.after(100, self.poll_queue)
        threading.Thread(target=self.load_db, daemon=True).start()
        threading.Thread(target=self.status_loop, daemon=True).start()
        threading.Thread(target=self.theme_loop, daemon=True).start()
        # Persistent download worker
        self.download_worker_thread = threading.Thread(target=self._download_queue_worker, daemon=True)
        self.download_worker_thread.start()
        self.root.after(0, self.apply_theme)

    @property
    def db(self):
        if self._db is None:
            self._db = X360DB()
        return self._db

    @property
    def unity(self):
        if self._unity is None:
            self._unity = XboxUnity()
        return self._unity

    def _build_ui(self, frm):

        self.status_row = ttk.Frame(frm)
        ttk.Label(self.status_row, text=tr("unity_status")).pack(side=tk.LEFT)
        self.unity_dot = tk.Label(self.status_row, text="●", width=1, fg=UNITY_WAIT)
        self.unity_dot.pack(side=tk.LEFT, padx=(4, 2))
        self.unity_lbl = ttk.Label(self.status_row, text=tr("checking"))
        self.unity_lbl.pack(side=tk.LEFT)
        ttk.Label(self.status_row, text=tr("x360db_status")).pack(side=tk.LEFT, padx=(16, 0))
        self.x360db_dot = tk.Label(self.status_row, text="●", width=1, fg=UNITY_WAIT)
        self.x360db_dot.pack(side=tk.LEFT, padx=(4, 2))
        self.x360db_lbl = ttk.Label(self.status_row, text=tr("checking"))
        self.x360db_lbl.pack(side=tk.LEFT)
        ttk.Label(self.status_row, text=tr("gameart_status")).pack(side=tk.LEFT, padx=(16, 0))
        self.gameart_dot = tk.Label(self.status_row, text="●", width=1, fg=UNITY_WAIT)
        self.gameart_dot.pack(side=tk.LEFT, padx=(4, 2))
        self.gameart_lbl = ttk.Label(self.status_row, text=tr("checking"))
        self.gameart_lbl.pack(side=tk.LEFT)

        self.path_row = ttk.Frame(frm)
        self.path_row.pack(fill=tk.X)
        ttk.Label(self.path_row, text=tr("aurora_folder")).pack(side=tk.LEFT)
        self.entry_path = ttk.Entry(self.path_row, textvariable=self.aurora_path)
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(self.path_row, text=tr("browse"), command=self.browse).pack(side=tk.LEFT)

        opts = ttk.Frame(frm)
        opts.pack(fill=tk.X, pady=(8, 0))
        ttk.Checkbutton(opts, text=tr("opt_boxart"), variable=self.opt_boxart).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(opts, text=tr("opt_background"), variable=self.opt_background).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(opts, text=tr("opt_force"), variable=self.opt_force).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(opts, text=tr("opt_backup"), variable=self.opt_backup).pack(
            side=tk.LEFT
        )

        opts2 = ttk.Frame(frm)
        opts2.pack(fill=tk.X, pady=(4, 0))
        ttk.Checkbutton(opts2, text=tr("opt_icon"), variable=self.opt_icon).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(opts2, text=tr("opt_banner"), variable=self.opt_banner).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        self.chk_screenshots = ttk.Checkbutton(
            opts2, text=tr("opt_screenshots", self.ss_max), variable=self.opt_screenshots
        )
        self.chk_screenshots.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(
            opts2, text=tr("info_note"), fg=UNITY_WAIT,
        ).pack(side=tk.LEFT)

        filter_row = ttk.Frame(frm)
        filter_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(filter_row, text=tr("filter_games")).pack(side=tk.LEFT)
        e_filter = ttk.Entry(filter_row, textvariable=self.search_var, width=40)
        e_filter.pack(side=tk.LEFT, padx=(6, 0))
        self.search_var.trace_add("write", lambda *_: self.root.after_idle(self.refresh_tree))

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        self.btn_scan = ttk.Button(btn_row, text=tr("scan"), command=self.start_scan)
        self.btn_scan.pack(side=tk.LEFT)
        self.btn_add = ttk.Button(btn_row, text=tr("add_game"), command=self.add_game)
        self.btn_add.pack(side=tk.LEFT, padx=(8, 0))
        # Botão para gerenciar pastas adicionadas (ver/remover)
        self.btn_folders = ttk.Button(
            btn_row, text=tr("manage_folders"), command=self.manage_added_folders
        )
        self.btn_folders.pack(side=tk.LEFT, padx=(8, 0))
        # Botão AZ (ordenar) ao lado do Adicionar jogos
        self.btn_sort = ttk.Button(
            btn_row, text=tr("sort_asc"), command=self.toggle_sort
        )
        self.btn_sort.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_db = ttk.Button(btn_row, text=tr("db_editor"), command=self.db_editor)
        self.btn_db.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_dl = ttk.Button(
            btn_row, text=tr("download"), command=self.start_download, state=tk.DISABLED
        )
        self.btn_dl.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_custom = ttk.Button(
            btn_row, text=tr("custom_cover"), command=self.install_custom, state=tk.DISABLED
        )
        self.btn_custom.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_row, text=tr("settings"), command=self.open_settings).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.btn_search = ttk.Button(
            btn_row, text=tr("search_title"), command=self.search_title, state=tk.DISABLED
        )
        self.btn_search.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_debug_db = ttk.Button(
            btn_row, text=tr("debug_db"), command=self.debug_database, state=tk.DISABLED
        )
        # Initially hidden (show_debug_button defaults to False)
        self.btn_cancel = ttk.Button(btn_row, text=tr("cancel"), command=self.cancel_worker, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(
            btn_row, text=tr("tip_right_click"), fg=UNITY_WAIT,
        ).pack(side=tk.LEFT, padx=(10, 0))

        body = ttk.Frame(frm)
        body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        tree_frame = ttk.Frame(body)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        cols = ("tid", "title", "status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("tid", text=tr("col_tid"))
        self.tree.heading("title", text=tr("col_game"))
        self.tree.heading("status", text=tr("col_status"))
        self.tree.column("tid", width=90, stretch=False)
        self.tree.column("status", width=110, stretch=False)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Button-3>", self.on_tree_menu)
        self.tree.bind("<Control-Button-1>", self.on_tree_menu)

        preview_panel = ttk.Frame(body, width=340)
        preview_panel.grid(row=0, column=1, sticky="ns", padx=(12, 0))
        preview_panel.grid_propagate(False)
        ttk.Label(preview_panel, text=tr("preview_title")).pack(pady=(0, 4))
        self._preview_frame = tk.Frame(
            preview_panel, width=PREVIEW_W + 8, height=PREVIEW_H + 8, bd=1,
            relief=tk.SUNKEN, bg="#222",
        )
        self._preview_frame.pack_propagate(False)
        self._preview_frame.pack()
        self.preview_lbl = tk.Label(
            self._preview_frame, text=tr("no_selection"), bg="#222", fg="#9a9a9a"
        )
        self.preview_lbl.pack(fill=tk.BOTH, expand=True)
        # Drag-and-drop / double-click para importar capa
        self.preview_lbl.bind("<Double-Button-1>", lambda e: self.import_cover_from_file())
        self.preview_lbl.bind("<Button-3>", self._preview_context_menu)
        self.preview_lbl.configure(cursor="hand2")
        self.preview_title = ttk.Label(preview_panel, text="", wraplength=320)
        self.preview_title.pack(pady=(6, 0))
        self.preview_info = ttk.Label(
            preview_panel, text="", wraplength=320, justify=tk.LEFT, foreground=UNITY_WAIT
        )
        self.preview_info.pack(pady=(4, 0), fill=tk.X)
        self.preview_status = ttk.Label(preview_panel, text="")
        self.preview_status.pack()

        self.progress = ttk.Progressbar(frm, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(8, 0))

        log_frame = self.log_frame = ttk.Frame(frm)
        self.txt = tk.Text(log_frame, height=self.txt_rows, state=tk.DISABLED, wrap="word")
        log_sb = ttk.Scrollbar(log_frame, command=self.txt.yview)
        self.txt.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.apply_show_status()
        self.apply_show_log()
        self._paint_status()
        self.post(tr("loading_index"))
        self.root.after(100, self.poll_queue)
        threading.Thread(target=self.load_db, daemon=True).start()
        threading.Thread(target=self.status_loop, daemon=True).start()
        threading.Thread(target=self.theme_loop, daemon=True).start()

    def _load_config_async(self):
        def _run():
            cfg = load_config()
            self.cfg = cfg
            self.theme = cfg.get("theme", "escuro")
            self.repo = cfg.get("repo", "x360db")
            self.cover_format = cfg.get("cover_format", "paisagem")
            self.ss_max = int(cfg.get("screenshots", SS_MAX_DEFAULT))
            self.lang = cfg.get("lang", "pt")
            global CURRENT_LANG
            CURRENT_LANG = self.lang if self.lang in TEXT else "pt"
            self.show_status = bool(cfg.get("show_status", True))
            self.show_log = bool(cfg.get("show_log", True))
            self.ftp_host = str(cfg.get("ftp_host", ""))
            self.ftp_port = int(cfg.get("ftp_port", 21))
            self.ftp_user = str(cfg.get("ftp_user", "xbox"))
            self.ftp_pass = str(cfg.get("ftp_pass", "xbox"))
            self.ftp_base = str(cfg.get("ftp_base", "Hdd:\\Aurora\\Data\\GameData"))
            self.opt_missing_only.set(bool(cfg.get("download_missing_only", True)))
            self.queue.put("__config_loaded__")
        threading.Thread(target=_run, daemon=True).start()

    def _on_config_loaded(self):
        self.apply_theme()
        self.apply_show_status()
        self.apply_show_log()
        self._paint_status()
        self.opt_auto_search.set(bool(self.cfg.get("auto_search_titles", True)))
        self.chk_screenshots.configure(text=tr("opt_screenshots", self.ss_max))
        if self.cfg.get("show_debug_button", False):
            self.btn_debug_db.pack(side=tk.LEFT, padx=(8, 0))
        else:
            self.btn_debug_db.pack_forget()
        self.root.after(0, self.apply_theme)

    def log(self, message):
        self.queue.put(message)

    def post(self, message):
        try:
            self.txt.configure(state=tk.NORMAL)
            self.txt.insert(tk.END, message + "\n")
            self.txt.see(tk.END)
            self.txt.configure(state=tk.DISABLED)
        except tk.TclError:
            pass

    def poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "__config_loaded__":
                    self._on_config_loaded()
                elif msg == "__refresh_tree__":
                    self.refresh_tree()
                elif msg == "__done__":
                    self.set_busy(False)
                elif msg == "__theme_check__":
                    self.apply_theme()
                elif isinstance(msg, str) and msg.startswith("__unity_status__:"):
                    self.unity_status = "ok" if msg.split(":", 1)[1] == "ok" else "down"
                    self._paint_status()
                elif isinstance(msg, str) and msg.startswith("__x360db_status__:"):
                    self.x360db_status = "ok" if msg.split(":", 1)[1] == "ok" else "down"
                    self._paint_status()
                elif isinstance(msg, str) and msg.startswith("__gameart_status__:"):
                    self.gameart_status = "ok" if msg.split(":", 1)[1] == "ok" else "down"
                    self._paint_status()
                elif isinstance(msg, str) and msg.startswith("__update_available__:"):
                    self._show_update_dialog(msg.split(":", 1)[1])
                elif isinstance(msg, str) and msg.startswith("__preview_info__:"):
                    self._preview_info_show(msg.split(":", 1)[1])
                elif msg == "__alt_preview__":
                    self._alt_preview_show()
                elif msg == "__assets_refresh__":
                    self.refresh_assets_dlg()
                elif isinstance(msg, str) and msg.startswith("__assets_msg__:"):
                    self._assets_msg_show(msg.split(":", 1)[1])
                elif msg == "__preview_refresh__":
                    g = self.selected_game()
                    if g is not None:
                        self.show_preview(g)
                elif msg == "__alt_populate__":
                    self._alt_populate()
                elif isinstance(msg, str) and msg.startswith("__alt_installed__:") :
                    ok = msg.split(":")[1] == "t"
                    if self._alt_dlg is not None and self._alt_dlg.winfo_exists():
                        self._alt_msg.configure(text=tr("alt_installed") if ok else tr("alt_failed"))
                    self.set_busy(False)
                    # Preserve selection across refresh
                    sel_tid = None
                    g = self.selected_game()
                    if g:
                        sel_tid = g["tid"]
                    self.queue.put("__refresh_tree__")
                    self.queue.put("__preview_refresh__")
                    if sel_tid:
                        def _restore_sel():
                            for item, gg in self.item_to_game.items():
                                if gg.get("tid") == sel_tid:
                                    self.tree.selection_set(item)
                                    self.tree.focus(item)
                                    self.tree.see(item)
                                    break
                        self.root.after(50, _restore_sel)
                elif isinstance(msg, str) and msg.startswith("__progress__:"):
                    parts = msg.split(":")
                    self.progress.configure(maximum=int(parts[2]) or 1, value=int(parts[1]))
                elif msg == "__busy_true__":
                    self.set_busy(True)
                else:
                    self.post(msg)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def load_db(self):
        try:
            ok = self.db.load_index()
        except Exception:
            ok = False
        if ok:
            self.log(tr("index_loaded", len(self.db.titles)))
        else:
            self.log(tr("index_fail"))
        self.queue.put("__refresh_tree__")

    def _fetch_unity_names(self, games):
        """Busca nomes no XboxUnity para jogos sem nome no x360db."""
        updated = False
        for g in games:
            if self.cancel_event.is_set():
                break
            tid = g["tid"]
            name = self.unity.get_best_title(tid)
            if name:
                g["dname"] = name
                updated = True
        if updated:
            self.queue.put("__refresh_tree__")
            self.log(tr("logs_unity_names"))

    def _paint_status(self):
        th = THEMES.get(detect_system_theme() if self.theme == "sistema" else self.theme, THEMES["escuro"])
        for status, dot, lbl in (
            (self.unity_status, self.unity_dot, self.unity_lbl),
            (self.x360db_status, self.x360db_dot, self.x360db_lbl),
            (self.gameart_status, self.gameart_dot, self.gameart_lbl),
        ):
            color = {"ok": UNITY_OK, "down": UNITY_DOWN}.get(status, UNITY_WAIT)
            text = tr("connected") if status == "ok" else (
                tr("disconnected") if status == "down" else tr("checking")
            )
            dot.configure(bg=th["bg"], fg=color)
            lbl.configure(text=text)

    def apply_show_status(self):
        if self.show_status:
            self.status_row.pack(fill=tk.X, pady=(0, 4), before=self.path_row)
        else:
            self.status_row.pack_forget()

    def apply_show_log(self):
        if self.show_log:
            self.log_frame.pack(fill=tk.BOTH, pady=(8, 0))
        else:
            self.log_frame.pack_forget()

    def status_loop(self):
        while True:
            if self.show_status:
                self.queue.put("__unity_status__:" + ("ok" if poke_url(XBOXUNITY_ROOT) else "down"))
                self.queue.put("__x360db_status__:" + ("ok" if poke_url(X360DB_PING_URL, method="HEAD") else "down"))
                # Ping numa capa real conhecida do 360-Game-Art (valida conexão e estrutura).
                self.queue.put("__gameart_status__:" + ("ok" if poke_url(GAME_ART_RAW + "315a07d2/cover.jpg") else "down"))
            time.sleep(PING_INTERVAL)

    def theme_loop(self):
        while True:
            time.sleep(15)
            if self.theme == "sistema":
                eff = detect_system_theme()
                if eff != self._applied_theme:
                    self.queue.put("__theme_check__")

    def update_check_loop(self):
        while True:
            if self.cfg.get("auto_update_check", True):
                now = time.time()
                if now - self.last_update_check >= UPDATE_CHECK_INTERVAL:
                    self.last_update_check = now
                    self.check_for_updates()
            time.sleep(3600)  # Check every hour

    def check_for_updates(self):
        try:
            data = fetch_bytes(GITHUB_API_RELEASES, timeout=15)
            if not data:
                return
            release = json.loads(data.decode("utf-8"))
            tag = release.get("tag_name", "").lstrip("v")
            if tag and self._version_greater(tag, CURRENT_VERSION):
                self.latest_version = tag
                self.update_available = True
                self.queue.put("__update_available__:" + tag)
        except Exception:
            pass

    def _version_greater(self, v1, v2):
        try:
            return tuple(map(int, v1.split("."))) > tuple(map(int, v2.split(".")))
        except Exception:
            return v1 > v2

    def browse(self):
        # Permite selecionar unidade (drive) ou pasta
        path = filedialog.askdirectory(title=tr("aurora_folder"))
        if not path:
            return
        # Se for a raiz de uma unidade, mantém a raiz: o content.db guarda caminhos
        # relativos à raiz (\homebrew, \jogos, \content...), então apontar para X:\
        # permite resolver as pastas físicas das capas junto com a base do Aurora.
        if os.path.splitdrive(path)[1] in ("\\", "/"):
            self.aurora_path.set(path)
            self.root.after(100, self.start_scan)
            return
        # Caso contrário (pasta manual), tenta detectar a estrutura Aurora
        for p in (
            os.path.join(path, "Aurora"),
            os.path.join(path, "Data", "GameData"),
        ):
            if os.path.isdir(p):
                path = p
                break
        self.aurora_path.set(path)
        self.root.after(100, self.start_scan)

    def set_busy(self, busy):
        self.busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_scan.configure(state=state)
        self.btn_dl.configure(state=state if self.games else tk.DISABLED)
        self.btn_cancel.configure(state=tk.NORMAL if busy else tk.DISABLED)

    def cancel_worker(self):
        self.cancel_event.set()
        try:
            while True:
                self.download_queue.get_nowait()
                self.download_queue.task_done()
        except queue.Empty:
            pass
        self.log(tr("canceled"))

    def start_scan(self):
        if self.busy:
            return
        path = self.aurora_path.get().strip().strip('"')
        if not path or not os.path.isdir(path):
            messagebox.showerror(tr("warn"), tr("pick_aurora"))
            return
        # Valida se é estrutura Aurora (tem Data/GameData ou pasta Aurora)
        aurora_root = path
        if not (os.path.isdir(os.path.join(path, "Data", "GameData")) or os.path.isdir(os.path.join(path, "Aurora"))):
            # Se for raiz de drive, permite (pode ter estrutura na raiz)
            drive, tail = os.path.splitdrive(path)
            if tail not in ("\\", "/"):
                messagebox.showerror(tr("warn"), tr("not_aurora_folder"))
                return
        self.cancel_event.clear()
        self.set_busy(True)
        threading.Thread(target=self.scan_worker, args=(path,), daemon=True).start()

    def scan_worker(self, path):
        try:
            self.log(tr("logs_scanning", path))
            if not self.db.ready.wait(timeout=30):
                self.log(tr("logs_no_index"))
            if self.cancel_event.is_set():
                self.log(tr("canceled"))
                return
            self.games = scan_aurora(path)
            hdd_ids = scan_hdd_content(path)
            known_tids = {g["tid"] for g in self.games}
            extra = [t for t in hdd_ids if t not in known_tids]
            if extra and not self.cancel_event.is_set():
                known_games = set(self.db.titles) | set(self.db.alt_ids)
                dlc_ids, game_ids = [], []
                for t in sorted(extra):
                    (game_ids if (t in known_games or not known_games) else dlc_ids).append(t)
                if dlc_ids:
                    self.log(tr("logs_ignored_dlc", len(dlc_ids)))
                if game_ids:
                    self.log(tr("logs_god_xdlc", len(game_ids)))
                    for t in game_ids:
                        self.games.append(
                            {
                                "folder": None,
                                "tid": t,
                                "folder_name": t,
                                "has_cover": False,
                            }
                        )
            # Jogos adicionados manualmente (persistidos) não são perdidos no rescan
            existing = {g["tid"] for g in self.games}
            for t in sorted(load_extra_games()):
                if t not in existing:
                    self.games.append(
                        {
                            "folder": None,
                            "tid": t,
                            "folder_name": t,
                            "dname": "",
                            "has_cover": False,
                        }
                    )
            # Capas já baixadas/instaladas (tracker) contam como "têm capa", mesmo
            # quando o arquivo não é encontrado no disco num re-scan (ex.: capa de
            # homebrew guardada em local que a varredura física não alcança).
            try:
                _inst = json.load(open(installed_path(), "r", encoding="utf-8"))
            except Exception:
                _inst = {}
            for _g in self.games:
                if not _g["has_cover"] and bool((_inst.get(_g["tid"]) or {}).get("boxart")):
                    _g["has_cover"] = True
            
            # Busca nomes faltando/no XboxUnity em background (se habilitado)
            # Só procura quando o nome está vazio, é um TitleID (8 hex) ou parece
            # caminho de pasta — NÃO para todo nome "minúsculo", pra não varrer
            # todos os jogos e queimar performance em busca desnecessária.
            def _weak_name(dname):
                if not dname:
                    return True
                d = dname.strip()
                if "\\" in d or "/" in d:
                    return True
                if re.fullmatch(r"[0-9A-F]{8}", d.upper()) and d == d.upper():
                    return True
                return False
            
            if self.cfg.get("auto_search_titles", True):
                missing = [g for g in self.games if _weak_name(g.get("dname"))]
                if missing:
                    self.log(tr("logs_fetch_names", len(missing)))
                    threading.Thread(target=self._fetch_unity_names, args=(missing,), daemon=True).start()
            self.queue.put("__refresh_tree__")
        except Exception as exc:
            self.queue.put("Erro no scan: %s" % exc)
        finally:
            self.queue.put("__done__")

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.item_to_game.clear()
        text = self.search_var.get().strip().lower()
        games = [g for g in self.games if g["tid"].upper() not in self.hidden_tids]
        if text:
            games = [
                g for g in games
                if text in self.game_title(g).lower()
                or text in g["tid"].lower()
                or text in (g.get("dname") or "").lower()
            ]
        order = sorted(
            games,
            key=lambda g: (
                g.get("has_cover") is True,
                (self.game_title(g) or "").lower(),
            ),
        )
        if not self.sort_asc:
            order.reverse()
        for g in order:
            title = self.game_title(g)
            status = "Capa OK" if g["has_cover"] else "Sem capa"
            item = self.tree.insert("", tk.END, values=(g["tid"], title, status))
            self.item_to_game[item] = g
        self.preview_cache.clear()
        self.show_no_preview()

    def game_title(self, g):
        tid = g["tid"]
        name = self.db.title_name(tid)
        if name != tid:
            return name
        return (g.get("dname") or "").strip() or tid

    def toggle_sort(self):
        self.sort_asc = not self.sort_asc
        try:
            self.btn_sort.configure(text=tr("sort_asc") if self.sort_asc else tr("sort_desc"))
        except tk.TclError:
            pass
        self.refresh_tree()

    def _looks_like_id(self, dname):
        """Nome que é um TID/pasta (não um nome humano): vazio, com separadores,
        ou exatamente 8 hex (TitleID) no lugar do título."""
        if not dname:
            return True
        d = dname.strip()
        if d == d.upper() and re.fullmatch(r"[0-9A-F]{8}", d):
            return True
        return "\\" in d or "/" in d

    def _best_title_for(self, g):
        tid = g["tid"]
        try:
            name = self.db.title_name(tid)
            if name and name != tid:
                return ("db", name)
            unity_name = self.unity.get_best_title(tid)
            if unity_name:
                return ("unity", unity_name)
        except Exception:
            pass
        return (None, None)

    def search_title(self):
        # Como vários jogos podem ter nomes "fracos" (TID/pasta) ao mesmo tempo,
        # este botão percorre TODOS (não só o selecionado) e tenta renomear os que
        # estão salvos como TitleID em vez de nome. Roda em thread p/ não travar a UI.
        if not self.games:
            return
        targets = [g for g in self.games if self._looks_like_id(g.get("dname"))]
        if not targets:
            sel = self.selected_game()
            targets = [sel] if sel else []
        if not targets:
            self.log(tr("logs_title_none_idlike"))
            return
        self.set_busy(True)

        def _run(items):
            changed = 0
            try:
                for g in items:
                    if self.cancel_event.is_set():
                        break
                    tid = g["tid"]
                    src, name = self._best_title_for(g)
                    if not name:
                        self.log(tr("logs_title_not_found", tid))
                        continue
                    if g.get("dname") == name:
                        continue
                    g["dname"] = name
                    self._update_content_db_name(tid, name)
                    custom_names = load_custom_names()
                    custom_names[tid] = name
                    save_custom_names(custom_names)
                    changed += 1
                    if src == "db":
                        self.log(tr("logs_title_x360db", name))
                    else:
                        self.log(tr("logs_title_unity", name))
            finally:
                if changed:
                    self.log(tr("logs_titles_updated", changed))
                else:
                    self.log(tr("logs_title_nochange"))
                self.queue.put("__refresh_tree__")
                self.queue.put("__done__")

        threading.Thread(target=_run, args=(targets,), daemon=True).start()

    def _update_content_db_name(self, tid, new_name):
        """Atualiza o TitleName no content.db para o TID informado."""
        try:
            path = self.aurora_path.get().strip().strip('"')
            if not path or not os.path.isdir(path):
                return
            db_path = find_content_db(path)
            if not db_path:
                return
            self.log(tr("logs_updating_db", tid, new_name))
            db_rename_by_tid(path, tid, new_name)
        except Exception as e:
            self.log(tr("logs_db_err", e))

    def debug_database(self):
        path = self.aurora_path.get().strip().strip('"')
        if not path or not os.path.isdir(path):
            messagebox.showerror(tr("warn"), tr("pick_aurora"))
            return
        import sqlite3
        db_paths = [
            os.path.join(path, "Aurora", "Data", "Databases", "content.db"),
            os.path.join(path, "Data", "Databases", "content.db"),
            os.path.join(path, "Aurora", "Data", "content.db"),
        ]
        db_path = None
        for p in db_paths:
            if os.path.isfile(p):
                db_path = p
                break
        if not db_path:
            messagebox.showerror(tr("debug_db"), tr("db_notfound"))
            return
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            info = f"DB: {db_path}\n\nTabelas:\n"
            for t in tables:
                cols = [row[1] for row in conn.execute(f"PRAGMA table_info({t})")]
                info += f"\n{t}: {cols}"
                # Sample data
                try:
                    sample = conn.execute(f"SELECT * FROM {t} LIMIT 3").fetchall()
                    if sample:
                        info += f"\n  Exemplo: {sample}"
                except:
                    pass
            conn.close()
            # Show in a scrollable dialog
            dlg = tk.Toplevel(self.root)
            dlg.title(tr("debug_db"))
            dlg.geometry("800x600")
            txt = tk.Text(dlg, wrap="word")
            txt.pack(fill=tk.BOTH, expand=True)
            txt.insert("1.0", info)
            txt.configure(state=tk.DISABLED)
            sb = ttk.Scrollbar(dlg, command=txt.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            txt.configure(yscrollcommand=sb.set)
        except Exception as e:
            messagebox.showerror(tr("debug_db"), tr("err_generic", e))

    def find_gamedata_folder(self, tid):
        path = self.aurora_path.get().strip().strip('"')
        if not path or not os.path.isdir(path):
            return None
        cands = [
            os.path.join(path, "Data", "GameData"),
            os.path.join(path, "Aurora", "Data", "GameData"),
            os.path.join(path, "GameData"),
            path,
        ]
        prefix = tid + "_"
        seen = set()
        for base in cands:
            if base in seen or not os.path.isdir(base):
                continue
            seen.add(base)
            try:
                names = sorted(os.listdir(base))
            except OSError:
                continue
            for name in names:
                if name.startswith(prefix):
                    full = os.path.join(base, name)
                    if os.path.isdir(full):
                        return full
        return None

    def rename_game(self, g):
        current = self.game_title(g)
        name = simpledialog.askstring(
            tr("m_rename"),
            tr("rename_prompt", current, g["tid"]),
            initialvalue=current,
            parent=self.root,
        )
        if not name:
            return
        clean = re.sub(r'[\\/:*?"<>|]+', "_", name.strip())
        clean = re.sub(r"\s+", " ", clean).strip()
        if not clean:
            return
        if clean == current:
            return
        # Só renomeia a pasta quando for uma pasta GameData dedicada do jogo
        # (pasta própria <tid>_<nome>). NUNCA renomeia pastas compartilhadas
        # (ex.: \jogos\xbox 360 dvd com vários XBLA) nem pastas do jogo no HD,
        # para não quebrar outros jogos nem perder a capa importada.
        folder = self.find_gamedata_folder(g["tid"])
        renamed_any = False
        if folder:
            parent = os.path.dirname(folder)
            new_folder = os.path.join(parent, "%s_%s" % (g["tid"], clean))
            if os.path.normpath(new_folder) != os.path.normpath(folder):
                try:
                    os.rename(folder, new_folder)
                    g["folder"] = new_folder
                    g["folder_name"] = os.path.basename(new_folder)
                    renamed_any = True
                    self.log(tr("logs_renamed_folder", os.path.basename(folder), os.path.basename(new_folder)))
                except OSError as exc:
                    self.log(tr("logs_rename_folder_err", exc))
        if not renamed_any:
            self.log(tr("logs_no_dedicated_gamedata", g["tid"]))
        g["dname"] = clean
        # Salva nome customizado permanentemente
        custom_names = load_custom_names()
        custom_names[g["tid"]] = clean
        save_custom_names(custom_names)
        # Renomeia diretamente no content.db (TitleName), para refletir no Aurora
        try:
            db_path = find_content_db(self.aurora_path.get().strip().strip('"'))
            if db_path:
                # Cria backup uma única vez antes de escrever
                if not os.path.exists(db_path + ".bak"):
                    db_backup(db_path)
            if db_rename_by_tid(self.aurora_path.get().strip().strip('"'), g["tid"], clean):
                self.log(tr("logs_db_titlename_ok", clean))
            else:
                self.log(tr("logs_db_row_not_found", g["tid"]))
        except Exception as exc:
            self.log(tr("logs_db_rename_err", exc))
        # Se o console estiver configurado (FTP), renomeia a pasta no Aurora também
        if self.ftp_host.strip():
            new_folder_name = "%s_%s" % (g["tid"], clean)
            threading.Thread(
                target=self._ftp_rename_game,
                args=(g["tid"], new_folder_name),
                daemon=True,
            ).start()
        self.log(tr("renamed", self.db.title_name(g["tid"]), clean))
        self.refresh_tree()
        try:
            self.tree.selection_set(
                next((i for i, gg in self.item_to_game.items() if gg is g), "")
            )
        except tk.TclError:
            pass

    def _ftp_rename_game(self, tid, new_folder_name):
        try:
            self.log(tr("rename_ftp_start"))
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_host, int(self.ftp_port), timeout=30)
            ftp.login(self.ftp_user, self.ftp_pass)
            remote = self._ftp_ensure_dir(ftp, self.ftp_base)
            try:
                names = ftp.nlst(remote)
            except ftplib.error_perm:
                names = []
            prefix = tid + "_"
            found = None
            for entry in names:
                base = os.path.basename(entry)
                if base.startswith(prefix):
                    found = base
                    break
            if found is None:
                self.log(tr("rename_ftp_err", "pasta não encontrada no console"))
                return
            if found == new_folder_name:
                self.log(tr("rename_ftp_ok", new_folder_name))
                return
            try:
                ftp.rename(found, new_folder_name)
            except ftplib.error_perm as exc:
                self.log(tr("rename_ftp_err", str(exc)))
                return
            self.log(tr("rename_ftp_ok", new_folder_name))
            try:
                ftp.quit()
            except Exception:
                pass
        except Exception as exc:
            self.log(tr("rename_ftp_err", str(exc)))

    def open_game_folder(self, g):
        """Tenta abrir a pasta do jogo em várias localizações possíveis."""
        folder = g.get("folder")
        tid = g.get("tid")
        
        candidates = []
        if folder:
            candidates.append(folder)
        
        # GameData folder (criada pelo add_game ou pelo Aurora)
        gamedata = self.gamedata_dir()
        if gamedata and tid:
            # Procura pasta no formato TID_Nome ou apenas TID
            for name in os.listdir(gamedata) if os.path.isdir(gamedata) else []:
                if name.upper().startswith(tid.upper() + "_") or name.upper() == tid.upper():
                    candidates.append(os.path.join(gamedata, name))
                    break
        
        # Pasta original do scan (para homebrews do DB)
        if tid:
            # Busca no content.db
            try:
                path = self.aurora_path.get().strip().strip('"')
                if path and os.path.isdir(path):
                    db_path = find_content_db(path)
                    if db_path:
                        import sqlite3
                        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                        try:
                            cur = conn.execute(
                                'SELECT "Directory" FROM "ContentItems" WHERE "TitleId"=? LIMIT 1',
                                (int(tid, 16) if all(c in "0123456789ABCDEF" for c in tid.upper()) else 0,)
                            )
                            row = cur.fetchone()
                            if row and row[0]:
                                directory = str(row[0]).strip()
                                if directory:
                                    # Resolve contra raiz do drive
                                    drive_root = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
                                    for base in (drive_root, path, os.path.join(path, "Aurora")):
                                        cand = os.path.join(base, directory.lstrip("\\/"))
                                        if os.path.isdir(cand):
                                            candidates.append(cand)
                                            break
                        finally:
                            conn.close()
            except Exception:
                pass
        
        # Tenta abrir a primeira que existir
        for c in candidates:
            if os.path.isdir(c):
                try:
                    os.startfile(c)
                    return
                except Exception:
                    continue
        
        # Fallback: tenta abrir pastas raiz conhecidas de jogos baseado no tipo/caminho
        path = self.aurora_path.get().strip().strip('"')
        if path and os.path.isdir(path):
            # Determina pasta raiz provável baseada no folder do jogo
            game_folder = g.get("folder", "")
            root_folders = []
            
            if game_folder:
                # Se o jogo tem folder conhecido, acha a raiz (ex: X:\homebrew\... -> X:\homebrew)
                parts = game_folder.split(os.sep)
                if len(parts) >= 3:  # X:\homebrew\game
                    root_folders.append(os.sep.join(parts[:3]))  # X:\homebrew
                    root_folders.append(os.sep.join(parts[:2]))  # X:\
            
            # Pastas comuns de jogos no Aurora/RGH
            common_roots = [
                os.path.join(path, "homebrew"),
                os.path.join(path, "Homebrew"),
                os.path.join(path, "jogos"),
                os.path.join(path, "Jogos"),
                os.path.join(path, "360"),
                os.path.join(path, "emuladores"),
                os.path.join(path, "Emuladores"),
                os.path.join(path, "Games"),
                os.path.join(path, "games"),
            ]
            for r in root_folders + common_roots:
                if os.path.isdir(r):
                    try:
                        os.startfile(r)
                        return
                    except Exception:
                        continue
            
            # Último fallback: abre a pasta Aurora
            try:
                os.startfile(path)
            except Exception as e:
                self.log(tr("logs_folder_open_err", e))

    def remove_cover(self, g):
        if self.busy:
            return
        tid = g["tid"]
        if not messagebox.askyesno(tr("warn"), tr("remove_cover_confirm", self.game_title(g), tid)):
            return
        removed = False
        folder = g.get("folder")
        if folder:
            for name in ("GC%s.asset" % tid, "boxart.png", "boxart.jpg", "boxart.jpeg",
                         "cover.png", "cover.jpg", "cover.jpeg", "cover.dds"):
                p = os.path.join(folder, name)
                if os.path.isfile(p):
                    try:
                        os.remove(p)
                        removed = True
                    except OSError:
                        pass
        # Remove a capa da Import (todas as bases: raiz do drive e pasta do Aurora)
        path = self.aurora_path.get().strip().strip('"')
        for base in import_bases(path):
            d = os.path.join(base, tid)
            if os.path.isdir(d):
                for name in ("cover.png", "cover.jpg", "cover.jpeg", "cover.dds"):
                    p = os.path.join(d, name)
                    if os.path.isfile(p):
                        try:
                            os.remove(p)
                            removed = True
                        except OSError:
                            pass
                try:
                    if not os.listdir(d):
                        os.rmdir(d)
                except OSError:
                    pass
        # Limpa o marcador 'instalado' para boxart
        try:
            p = installed_path()
            data = {}
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            if tid in data:
                data[tid].pop("boxart", None)
                if not data[tid]:
                    data.pop(tid, None)
                tmp = p + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp, p)
        except Exception:
            pass
        g["has_cover"] = False
        self.preview_cache.pop(tid + "|" + (g["folder"] or "import"), None)
        if removed:
            self.log(tr("cover_removed", self.game_title(g), tid))
        else:
            self.log(tr("cover_none_found", self.game_title(g), tid))
        self.refresh_tree()

    def remove_game(self, g):
        if self.busy:
            return
        tid = g["tid"]
        if not messagebox.askyesno(tr("warn"), tr("remove_game_confirm", self.game_title(g), tid)):
            return
        self.hidden_tids.add(tid.upper())
        save_hidden_games(sorted(self.hidden_tids))
        self.log(tr("game_removed", self.game_title(g), tid))
        self.refresh_tree()

    def restore_hidden_games(self):
        if self.busy:
            return
        if not self.hidden_tids:
            return
        if not messagebox.askyesno(tr("warn"), tr("restore_hidden_confirm", len(self.hidden_tids))):
            return
        self.hidden_tids = set()
        save_hidden_games([])
        self.log(tr("restore_hidden_done"))
        self.refresh_tree()

    def manage_added_folders(self):
        """Dialog para ver e remover pastas adicionadas via 'Adicionar pasta para procurar jogos'."""
        folders = load_added_folders()
        if not folders:
            messagebox.showinfo(tr("info"), tr("no_folders"))
            return

        dlg = tk.Toplevel(self.root)
        dlg.title(tr("manage_folders"))
        dlg.transient(self.root)
        dlg.resizable(True, True)
        dlg.geometry("700x400")

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text=tr("folders_header")).pack(anchor="w", pady=(0, 6))

        # Treeview
        cols = ("folder", "added", "count")
        tree = ttk.Treeview(frm, columns=cols, show="headings", selectmode="extended")
        tree.heading("folder", text=tr("col_folder"))
        tree.heading("added", text=tr("col_added"))
        tree.heading("count", text=tr("col_count"))
        tree.column("folder", width=400, stretch=True)
        tree.column("added", width=150, stretch=False)
        tree.column("count", width=60, stretch=False)

        sb = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for f in folders:
            tree.insert("", "end", values=(f.get("folder", ""), f.get("added", ""), f.get("count", 0)))

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(10, 0))

        def remove_selected():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno(tr("warn"), tr("remove_folders_confirm", len(sel))):
                return
            folders_set = {tree.item(item, "values")[0] for item in sel}
            remaining = [f for f in folders if f.get("folder") not in folders_set]
            save_added_folders(remaining)
            # Também remove os jogos dessas pastas da lista
            if folders_set:
                self.games = [g for g in self.games if g.get("folder") not in folders_set]
                self.refresh_tree()
            # Atualiza tree
            for item in sel:
                tree.delete(item)
            self.log(tr("logs_folders_removed", len(sel)))

        def open_selected():
            sel = tree.selection()
            if not sel:
                return
            folder = tree.item(sel[0], "values")[0]
            if os.path.isdir(folder):
                try:
                    os.startfile(folder)
                except Exception as e:
                    self.log(tr("folder_open_err", e))

        ttk.Button(btn_row, text=tr("open_folder"), command=open_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text=tr("remove_selected"), command=remove_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text=tr("ok"), command=dlg.destroy).pack(side=tk.RIGHT)

        dlg.grab_set()
        self.root.wait_window(dlg)

    def db_editor(self):
        root = self.aurora_path.get().strip().strip('"')
        db_path = find_content_db(root)
        if not db_path:
            messagebox.showwarning(tr("warn"), tr("db_nodb"))
            return
        try:
            conn = sqlite3.connect(db_path)
        except sqlite3.Error as exc:
            messagebox.showerror(tr("error"), str(exc))
            return
        table, sc = db_schema(conn)
        if table is None or not sc["id"] or not sc["tid"] or not sc["title"]:
            conn.close()
            messagebox.showerror(tr("error"), tr("schema_unknown", table))
            return
        backed_up = [False]

        def ensure_backup():
            if backed_up[0]:
                return
            try:
                bak = db_backup(db_path)
                backed_up[0] = True
                self.log(tr("db_backup", os.path.basename(bak)))
            except OSError as exc:
                messagebox.showerror(tr("error"), str(exc))

        dlg = tk.Toplevel(self.root)
        dlg.title("%s - %s" % (tr("db_editor"), os.path.basename(db_path)))
        dlg.transient(self.root)
        dlg.geometry("820x500")
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text=tr("db_warn1")).pack(anchor="w")
        bar = ttk.Frame(frm)
        bar.pack(fill=tk.X, pady=(6, 4))
        kind_map = [None, "game", "god", "dlc", "xbla", "avatar", "tu", "data", "other"]
        kind_opts = [
            tr("db_all"),
            db_kind_label("game"),
            db_kind_label("god"),
            db_kind_label("dlc"),
            db_kind_label("xbla"),
            db_kind_label("avatar"),
            db_kind_label("tu"),
            db_kind_label("data"),
            db_kind_label("other"),
        ]
        kind_var = tk.StringVar(value=kind_opts[0])
        search_var = tk.StringVar()

        try:
            all_rows = db_rows(conn, table, sc)
        except sqlite3.Error as exc:
            conn.close()
            messagebox.showerror(tr("error"), str(exc))
            dlg.destroy()
            return

        def reload_rows():
            for item in tree.get_children():
                tree.delete(item)
            kkind = kind_map[kind_opts.index(kind_var.get())]
            text = search_var.get().strip()
            for r in all_rows:
                if kkind is not None and r["kind"] != kkind:
                    continue
                if text and text.lower() not in " ".join((r["tid"], r["name"], r["dir"])).lower():
                    continue
                tree.insert("", tk.END, values=(r["id"], r["tid"], r["name"], r["dir"], r["label"]))

        ttk.Label(bar, text=tr("db_filter")).pack(side=tk.LEFT)
        kind_cb = ttk.Combobox(
            bar, textvariable=kind_var, values=kind_opts, state="readonly", width=14
        )
        kind_cb.pack(side=tk.LEFT, padx=(4, 10))
        kind_cb.bind("<<ComboboxSelected>>", lambda _e: reload_rows())
        ttk.Label(bar, text=tr("db_search")).pack(side=tk.LEFT)
        e_search = ttk.Entry(bar, textvariable=search_var, width=30)
        e_search.pack(side=tk.LEFT, padx=(4, 8))
        search_var.trace_add("write", lambda *_: reload_rows())
        ttk.Button(bar, text=tr("db_reload"), command=reload_rows).pack(side=tk.LEFT)

        sel = {"row": None}

        def on_select(_e=None):
            cur = tree.selection()
            r = tree.item(cur[0], "values") if cur else None
            sel["row"] = r

        holder = ttk.Frame(frm)
        holder.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        tree = ttk.Treeview(holder, columns=("id", "tid", "title", "dir", "type"), show="headings", height=16)
        tree.heading("id", text="ID")
        tree.heading("tid", text="TID")
        tree.heading("title", text=tr("db_new_name"))
        tree.heading("dir", text=tr("col_folder"))
        tree.heading("type", text=tr("col_type"))
        tree.column("id", width=50, anchor="center")
        tree.column("tid", width=90, anchor="center")
        tree.column("title", width=270)
        tree.column("dir", width=310)
        tree.column("type", width=100)
        vsb = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.bind("<<TreeviewSelect>>", on_select)
        reload_rows()

        act = ttk.Frame(frm)
        act.pack(fill=tk.X)
        ttk.Button(act, text=tr("db_add"), command=lambda: self._db_add(conn, table, sc, ensure_backup, reload_rows, dlg)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(act, text=tr("db_rename"), command=lambda: self._db_rename(conn, table, sc, ensure_backup, reload_rows, sel, dlg)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(act, text=tr("db_remove"), command=lambda: self._db_remove(conn, table, sc, ensure_backup, reload_rows, sel, dlg)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(act, text=tr("close"), command=dlg.destroy).pack(side=tk.RIGHT)

        def on_close():
            try:
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", on_close)
        dlg.grab_set()
        self.root.wait_window(dlg)
        self.refresh_tree()

    def _db_add(self, conn, table, sc, ensure_backup, reload_rows, parent):
        dlg = tk.Toplevel(parent)
        dlg.title(tr("db_add"))
        dlg.transient(parent)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        def add_row(label_text, entry_var, width, row):
            ttk.Label(frm, text=label_text).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 12))
            e = ttk.Entry(frm, textvariable=entry_var, width=width)
            e.grid(row=row, column=1, sticky="w", pady=4)
            return e

        v_tid = tk.StringVar()
        v_name = tk.StringVar()
        v_dir = tk.StringVar()
        add_row(tr("db_new_tid"), v_tid, 20, 0)
        add_row(tr("db_new_name"), v_name, 36, 1)
        add_row(tr("db_new_dir"), v_dir, 60, 2)
        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(8, 0))
        res = {"ok": False}

        def _ok(_e=None):
            res["tid"] = v_tid.get().strip().upper()
            res["name"] = v_name.get().strip()
            d = v_dir.get().strip()
            d = re.sub(r"^(?:[A-Za-z]+:)?[\\/]*", "", d)
            if d and not d.startswith("\\"):
                d = "\\" + d
            res["dir"] = d
            res["ok"] = True
            dlg.destroy()

        ttk.Button(btns, text=tr("ok"), command=_ok).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text=tr("cancel"), command=dlg.destroy).pack(side=tk.LEFT)
        dlg.bind("<Return>", _ok)
        dlg.grab_set()
        parent.wait_window(dlg)
        if not res["ok"]:
            return
        tid, name, directory = res["tid"], res["name"], res["dir"]
        if not re.match(r"^[0-9A-F]{8}$", tid):
            messagebox.showerror(tr("warn"), tr("add_game_bad_tid"))
            return
        if not name:
            messagebox.showwarning(tr("warn"), tr("db_need_name"))
            return
        ensure_backup()
        try:
            db_add_row(conn, table, sc, tid, name, directory)
            conn.commit()
        except sqlite3.Error as exc:
            messagebox.showerror(tr("error"), str(exc))
            return
        self.log(tr("db_added", name, tid))
        reload_rows()

    def _db_rename(self, conn, table, sc, ensure_backup, reload_rows, sel, parent):
        r = sel["row"]
        if not r:
            messagebox.showwarning(tr("warn"), tr("db_need_id"))
            return
        rc_id, rc_name = r[0], r[2]
        newname = simpledialog.askstring(tr("db_rename"), tr("db_new_name"), initialvalue=rc_name, parent=parent)
        if newname is None:
            return
        newname = newname.strip()
        if not newname:
            return
        ensure_backup()
        try:
            db_update_title(conn, table, sc, rc_id, newname)
            conn.commit()
        except sqlite3.Error as exc:
            messagebox.showerror(tr("error"), str(exc))
            return
        self.log(tr("db_renamed", newname))
        reload_rows()

    def _db_remove(self, conn, table, sc, ensure_backup, reload_rows, sel, parent):
        r = sel["row"]
        if not r:
            messagebox.showwarning(tr("warn"), tr("db_need_id"))
            return
        rc_id, rc_name = r[0], r[2]
        if not messagebox.askyesno(tr("db_remove"), tr("db_confirm_remove", rc_name)):
            return
        ensure_backup()
        try:
            db_delete_row(conn, table, sc, rc_id)
            conn.commit()
        except sqlite3.Error as exc:
            messagebox.showerror(tr("error"), str(exc))
            return
        self.log(tr("db_removed", rc_name))
        reload_rows()

    def gamedata_dir(self, create=False):
        """Retorna a pasta GameData do Aurora. Se create=True, cria a estrutura se não existir."""
        path = self.aurora_path.get().strip().strip('"')
        if not path or not os.path.isdir(path):
            return None
        for cand in (
            os.path.join(path, "Data", "GameData"),
            os.path.join(path, "Aurora", "Data", "GameData"),
            os.path.join(path, "GameData"),
        ):
            if os.path.isdir(cand):
                return cand
        if create:
            # Cria a estrutura padrão Data\GameData
            gamedata = os.path.join(path, "Data", "GameData")
            try:
                os.makedirs(gamedata, exist_ok=True)
                return gamedata
            except OSError:
                return None
        return None

    def add_game(self):
        dlg = tk.Toplevel(self.root)
        dlg.title(tr("add_game"))
        dlg.transient(self.root)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Linha 0: arquivo .xex
        ttk.Label(frm, text=tr("add_game_xex")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        v_xex = tk.StringVar()
        e_xex = ttk.Entry(frm, textvariable=v_xex, width=36)
        e_xex.grid(row=0, column=1, sticky="w", pady=(0, 6), padx=(0, 4))

        # Linha 1: pasta para procurar jogos (vários .xex de uma vez)
        ttk.Label(frm, text=tr("add_game_folder")).grid(row=1, column=0, sticky="w", pady=(0, 6))
        v_folder = tk.StringVar()
        e_folder = ttk.Entry(frm, textvariable=v_folder, width=36)
        e_folder.grid(row=1, column=1, sticky="w", pady=(0, 6), padx=(0, 4))
        ttk.Label(
            frm, text=tr("add_game_folder_note"), foreground="#888888"
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 6))

        # Linha 3: nome (opcional)
        ttk.Label(frm, text=tr("add_game_name")).grid(row=3, column=0, sticky="w", pady=(0, 6))
        v_name = tk.StringVar()
        e_name = ttk.Entry(frm, textvariable=v_name, width=24)
        e_name.grid(row=3, column=1, sticky="w", pady=(0, 6))

        # Linha 4: Title ID (agora abaixo do nome)
        ttk.Label(frm, text=tr("add_game_tid")).grid(row=4, column=0, sticky="w", pady=(0, 6))
        v_tid = tk.StringVar()

        def _fill_from_xex(fn):
            v_xex.set(fn)
            info = parse_xex2(fn) or {}
            tid = ("%08X" % info["title_id"]) if info.get("title_id") else None
            base = os.path.basename(os.path.dirname(fn) or fn)
            if base.lower().endswith(".xex"):
                base = os.path.basename(fn)
            base = os.path.splitext(base)[0]
            default_name = base.strip()
            if not tid and default_name:
                tid = legacy_tid_for(default_name)
            if tid:
                v_tid.set(tid)
            if not e_name.get().strip() and default_name:
                e_name.delete(0, tk.END)
                e_name.insert(0, default_name)

        def _browse_xex():
            fn = filedialog.askopenfilename(
                title=tr("add_game_xex"),
                filetypes=[("XEX", "*.xex"), ("Todos", "*.*")],
            )
            if fn:
                _fill_from_xex(fn)

        def _browse_folder():
            fd = filedialog.askdirectory(title=tr("add_game_folder"), mustexist=True)
            if fd:
                v_folder.set(fd)

        ttk.Button(frm, text=tr("browse"), command=_browse_xex).grid(row=0, column=2, sticky="w", pady=(0, 6))
        ttk.Button(frm, text=tr("browse"), command=_browse_folder).grid(row=1, column=2, sticky="w", pady=(0, 6))

        e_tid = ttk.Entry(frm, textvariable=v_tid, width=16)
        e_tid.grid(row=4, column=1, sticky="w", pady=(0, 6))
        v_mkdir = tk.BooleanVar(value=self.gamedata_dir() is not None)
        ttk.Checkbutton(frm, text=tr("add_game_mkdir"), variable=v_mkdir).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=3, sticky="e")
        res = {"ok": False, "tid": None, "name": None, "mkdir": False, "xex": None, "folder": None}

        def stage_done(tid, name, folder=None):
            res["tid"] = tid
            res["name"] = name
            res["folder"] = folder
            res["ok"] = True
            dlg.destroy()

        # Confirmação do fluxo de pasta: adiciona todos os jogos encontrados na pasta
        def _apply_folder_selection():
            raw = v_folder.get().strip().strip('"')
            if not raw:
                messagebox.showwarning(tr("warn"), tr("add_game_bad_tid"))
                return
            if not os.path.isdir(raw):
                messagebox.showerror(tr("warn"), tr("folder_not_found", raw))
                return
            folder = os.path.normpath(raw)
            games_found = self.probe_folder_games(folder)
            count = 0
            for t in games_found:
                if any(g["tid"] == t["tid"] for g in self.games):
                    continue
                g = {
                    "folder": t["folder"],
                    "tid": t["tid"],
                    "folder_name": os.path.basename(t["folder"]) if t["folder"] else t["tid"],
                    "dname": t["name"],
                    "has_cover": False,
                }
                custom_names = load_custom_names()
                custom_names[t["tid"]] = t["name"]
                save_custom_names(custom_names)
                extra = load_extra_games()
                if t["tid"] not in extra:
                    extra.append(t["tid"])
                    save_extra_games(extra)
                self.games.append(g)
                count += 1
            if count:
                targets = [g for g in self.games if g["tid"] in {t["tid"] for t in games_found}]
                threading.Thread(target=self._fetch_unity_names, args=(targets,), daemon=True).start()
            self.log(tr("add_game_folder_done", count, folder))
            # Salva a pasta na lista de pastas gerenciadas
            if count:
                added = load_added_folders()
                # Evita duplicata
                if not any(f.get("folder") == folder for f in added):
                    added.append({
                        "folder": folder,
                        "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "count": count,
                    })
                    save_added_folders(added)
            self.refresh_tree()
            res["ok"] = True
            res["folder"] = folder
            dlg.destroy()

        def _ok(_event=None):
            tid = v_tid.get().strip().upper()
            name = v_name.get().strip()
            if not tid:
                # Sem TID informado: gera sintético a partir do nome (para homebrew)
                src = name or os.path.splitext(os.path.basename(v_xex.get().strip() or ""))[0]
                if src:
                    tid = legacy_tid_for(src)
            if v_folder.get().strip():
                _apply_folder_selection()
                return
            stage_done(tid, name)

        ttk.Button(btns, text=tr("ok"), command=_ok).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text=tr("cancel"), command=dlg.destroy).pack(side=tk.LEFT)
        e_name.focus_set()
        dlg.bind("<Return>", _ok)
        dlg.grab_set()
        self.root.wait_window(dlg)
        if not res["ok"]:
            return
        if res["folder"]:
            return  # fluxo de pasta já tratado
        tid = res["tid"]
        if not re.match(r"^[0-9A-F]{8}$", tid):
            messagebox.showerror(tr("warn"), tr("add_game_bad_tid"))
            return
        if any(g["tid"] == tid for g in self.games):
            messagebox.showwarning(tr("warn"), tr("add_game_exists"))
            return
        name = res["name"] or tid
        g = {"folder": None, "tid": tid, "folder_name": tid, "dname": name, "has_cover": False}
        if res["mkdir"]:
            gamedata = self.gamedata_dir(create=True)
            if not gamedata:
                gamedata = os.path.join(self.aurora_path.get().strip().strip('"'), "Data", "GameData")
            try:
                os.makedirs(gamedata, exist_ok=True)
                fld = os.path.join(gamedata, "%s_%s" % (tid, name))
                os.makedirs(fld, exist_ok=True)
                g["folder"] = fld
                g["folder_name"] = os.path.basename(fld)
                self.log(tr("logs_gamedata_created", g["folder_name"]))
            except OSError as exc:
                messagebox.showerror(tr("error"), str(exc))
                return
        custom_names = load_custom_names()
        custom_names[tid] = name
        save_custom_names(custom_names)
        extra = load_extra_games()
        if tid not in extra:
            extra.append(tid)
            save_extra_games(extra)
        self.games.append(g)
        self.log(tr("add_game_added", name or tid, tid))
        threading.Thread(target=self._fetch_unity_names, args=([g],), daemon=True).start()
        self.refresh_tree()

    def probe_folder_games(self, folder):
        """Enumera jogos dentro de uma pasta escolhida (um por subpasta com .xex),
        retornando uma lista de dicts {'tid','name','folder'}. Não trata a própria
        pasta como um jogo e ignora subpastas Media/Managed."""
        out = []
        folder = os.path.normpath(folder)
        max_depth = 4
        for dirpath, dirnames, filenames in os.walk(folder):
            rel = os.path.relpath(dirpath, folder)
            depth = 0 if rel == "." else len(rel.split(os.sep))
            if depth > max_depth:
                dirnames[:] = []
                continue
            parts = [p.lower() for p in re.split(r"[\\/]", dirpath)]
            if "media" in parts or "managed" in parts:
                dirnames[:] = []
                continue
            xexs = sorted(fn for fn in filenames if fn.lower().endswith(".xex"))
            if not xexs:
                continue
            if depth == 0:
                # A própria pasta raiz tem um .xex solto: não tratar a pasta inteira como jogo
                continue
            xex = os.path.join(dirpath, xexs[0])
            name = os.path.basename(dirpath).strip()
            tid = None
            info = parse_xex2(xex)
            if info and info.get("title_id"):
                tid = "%08X" % info["title_id"]
            if name:
                if tid is None:
                    tid = legacy_tid_for(name)
            if not tid or not re.match(r"^[0-9A-F]{8}$", tid):
                continue
            if any(o["tid"] == tid for o in out):
                continue
            out.append({"tid": tid, "name": name, "folder": dirpath})
        return out

    def selected_game(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.item_to_game.get(sel[0])

    def get_selected_games(self):
        sel = self.tree.selection()
        return [self.item_to_game[item] for item in sel if item in self.item_to_game]

    def on_select(self, _event=None):
        g = self.selected_game()
        if g is None:
            self.btn_custom.configure(state=tk.DISABLED)
            self.btn_search.configure(state=tk.DISABLED)
            self.btn_debug_db.configure(state=tk.DISABLED)
            self.show_no_preview()
            return
        self.btn_custom.configure(state=tk.NORMAL)
        self.btn_search.configure(state=tk.NORMAL)
        self.btn_debug_db.configure(state=tk.NORMAL)
        self.show_preview(g)

    def load_cover(self, g):
        key = g["tid"] + "|" + (g["folder"] or "import")
        with self._preview_cache_lock:
            if key in self.preview_cache:
                return self.preview_cache[key]
        img = None
        cover_file = find_cover_file(g["folder"], g["tid"])
        if cover_file:
            img = open_cover_image(cover_file)
        if img is None:
            for import_dir in import_dirs_existing(self.aurora_path.get()):
                cand = os.path.join(import_dir, g["tid"])
                if not os.path.isdir(cand):
                    continue
                for fn in sorted(os.listdir(cand)):
                    if (
                        fn.lower().startswith("cover")
                        and fn.lower().endswith((".png", ".jpg", ".jpeg", ".dds"))
                    ):
                        try:
                            img = Image.open(os.path.join(cand, fn)).convert("RGBA")
                        except Exception:
                            img = None
                        if img is not None:
                            break
                if img is not None:
                    break
        if img is None:
            with self._preview_cache_lock:
                self._preview_cache_put(key, None)
                return None
        thumb = cover_fit(img, PREVIEW_W, PREVIEW_H)
        with self._preview_cache_lock:
            self._preview_cache_put(key, thumb)
        return thumb

    def _preview_cache_put(self, key, value):
        if len(self.preview_cache) >= self._preview_cache_max:
            oldest = next(iter(self.preview_cache))
            del self.preview_cache[oldest]
        self.preview_cache[key] = value

    def show_preview(self, g):
        img = self.load_cover(g)
        title = self.game_title(g)
        self.preview_title.configure(text="%s (%s)" % (title, g["tid"]))
        self.preview_info.configure(text=tr("loading_info"))
        tid = g["tid"]
        threading.Thread(target=self._preview_info_thread, args=(tid,), daemon=True).start()
        if img is None:
            self.preview_lbl.configure(image="", text=tr("no_cover"))
            self.preview_status.configure(text=tr("no_cover_installed"))
            self._photo = None
            return
        thumb = cover_fit(img, PREVIEW_W, PREVIEW_H)
        self._photo = ImageTk.PhotoImage(thumb)
        self.preview_lbl.configure(image=self._photo, text="")
        self.preview_status.configure(text=tr("cover_installed"))

    def import_cover_from_file(self):
        """Importa capa via arquivo (double-click no preview ou menu de contexto)."""
        g = self.selected_game()
        if g is None:
            return
        filetypes = [("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp *.ico"), ("Todos", "*.*")]
        file_name = filedialog.askopenfilename(
            title=tr("custom_cover") + " (%s)" % self.db.title_name(g["tid"]),
            filetypes=filetypes,
        )
        if not file_name:
            return
        try:
            img = box_render(Image.open(file_name), self.cover_format)
        except Exception as exc:
            messagebox.showerror(tr("warn"), tr("img_open_fail", exc))
            return
        path = self.aurora_path.get().strip().strip('"')
        try:
            self.install_cover_img(path, g, img)
        except Exception as exc:
            messagebox.showerror(tr("warn"), tr("img_write_fail", exc))
            return
        self.log(tr("logs_custom_installed", self.db.title_name(g["tid"]), g["tid"]))
        self.show_preview(g)
        self.update_tree_row(g)

    def _preview_context_menu(self, event):
        """Menu de contexto no preview (botão direito)."""
        g = self.selected_game()
        if g is None:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=tr("custom_cover"), command=self.import_cover_from_file)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _preview_info_thread(self, tid):
        try:
            self.db.info(tid)
        except Exception:
            pass
        self.queue.put("__preview_info__:" + tid)

    def _preview_info_show(self, tid):
        g = self.selected_game()
        if g is None or g["tid"] != tid:
            return
        parts = self._format_info(self.db.info(tid) or {})
        self.preview_info.configure(text=parts)

    def _show_update_dialog(self, version):
        if messagebox.askyesno(tr("update_available_title"),
                                tr("update_available_msg", version, CURRENT_VERSION)):
            # Open GitHub releases page
            import webbrowser
            webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/tag/v{version}")

    def _format_info(self, info):
        genres = ", ".join(info.get("genre") or [])[:60]
        dev = info.get("developer") or ""
        desc = (info.get("description") or {}).get("short") or ""
        if len(desc) > 180:
            desc = desc[:177] + "..."
        parts = []
        show_info = self.cfg.get("show_game_info", True)
        if show_info and info.get("release_date"):
            rd = info["release_date"]
            if CURRENT_LANG in ("pt", "es"):
                # Formato dia/mês/ano para PT e ES
                try:
                    # Tenta parsear vários formatos comuns
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            dt = datetime.strptime(str(rd), fmt)
                            rd = dt.strftime("%d/%m/%Y")
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            parts.append(tr("release_date") + ": " + str(rd))
        if show_info and dev:
            parts.append(tr("developer") + ": " + dev)
        if genres:
            parts.append(tr("genres") + ": " + genres)
        if desc:
            parts.append(desc)
        return "\n".join(parts)

    def show_no_preview(self):
        self.preview_lbl.configure(image="", text=tr("no_selection"))
        self.preview_title.configure(text="")
        self.preview_info.configure(text="")
        self.preview_status.configure(text="")
        self._photo = None

    def update_tree_row(self, g):
        status = "Capa OK" if g["has_cover"] else "Sem capa"
        for item, game in self.item_to_game.items():
            if game is g or game.get("tid") == g.get("tid"):
                self.tree.item(
                    item,
                    values=(g["tid"], self.game_title(g), status),
                )
                return

    def start_download(self):
        if not self.games:
            messagebox.showwarning(tr("warn"), tr("scan_first"))
            return
        if not (
            self.opt_boxart.get()
            or self.opt_background.get()
            or self.opt_icon.get()
            or self.opt_banner.get()
            or self.opt_screenshots.get()
        ):
            messagebox.showwarning(tr("warn"), tr("pick_art"))
            return
        selected = self.get_selected_games()
        if not selected:
            selected = self.games
        path = self.aurora_path.get().strip().strip('"')
        targets = [g for g in selected if self.needs_download(g, path)]
        if not targets:
            self.log(tr("no_games_notice"))
            return
        kinds = {
            "boxart": self.opt_boxart.get(),
            "background": self.opt_background.get(),
            "icon": self.opt_icon.get(),
            "banner": self.opt_banner.get(),
            "screenshots": self.opt_screenshots.get(),
        }
        self.download_queue.put((targets, path, kinds))
        if not self.busy:
            self.cancel_event.clear()
            self.set_busy(True)

    def _download_queue_worker(self):
        while True:
            targets, path, kinds = self.download_queue.get()
            self.current_download_job = (targets, path, kinds)
            self.cancel_event.clear()
            self.queue.put("__busy_true__")
            try:
                total = len(targets)
                if total == 0:
                    self.log(tr("no_games_notice"))
                else:
                    self.log(tr("logs_queue_started", total))
                done = 0
                for g in targets:
                    if self.cancel_event.is_set():
                        self.log(tr("canceled"))
                        break
                    done += 1
                    remaining = self.download_queue.qsize()
                    self.queue.put("__progress__:%d:%d" % (done, total))
                    self.log(tr("logs_progress_game", done, total, self.db.title_name(g["tid"]), g["tid"]))
                    try:
                        self.download_one(path, g, kinds)
                    except Exception as exc:
                        self.log(tr("logs_game_err", exc))
                    time.sleep(0.3)
                self.log(tr("done_notice"))
                self.queue.put("__refresh_tree__")
            except Exception as exc:
                self.queue.put(tr("err_generic", exc))
            finally:
                self.current_download_job = None
                self.queue.put("__done__")
            self.download_queue.task_done()

    def _kind_exists(self, g, path, kind):
        folder = g["folder"]
        bases = ([folder] if folder else [])
        for import_dir in import_dirs_existing(path):
            bases.append(os.path.join(import_dir, g["tid"]))
        if not bases:
            bases.append(os.path.join(path, "User", "Import", g["tid"]))
        def _has(name_ok):
            return any(any(os.path.exists(os.path.join(b, f)) for f in name_ok) for b in bases)
        if kind == "boxart":
            return _has(["GC%s.asset" % g["tid"]] if folder else ["cover.png", "cover.jpg", "cover.jpeg", "cover.dds"])
        if kind == "background":
            return _has(["BK%s.asset" % g["tid"]] if folder else ["background.png"])
        if kind in ("icon", "banner"):
            return _has(["GL%s.asset" % g["tid"]] if folder else ["icon.png"])
        if kind == "screenshots":
            return _has(["SS%s.asset" % g["tid"]] if folder else ["screenshot1.png"])
        return False

    def needs_download(self, g, path):
        if self.opt_force.get():
            return True
        if self.opt_missing_only.get():
            # Padrão: só joga sem CAPA. (Se uma capa existe, o jogo não é alvo.)
            return not self._kind_exists(g, path, "boxart")
        folder = g["folder"]
        bases = ([folder] if folder else [])
        for import_dir in import_dirs_existing(path):
            bases.append(os.path.join(import_dir, g["tid"]))
        if not bases:
            bases.append(os.path.join(path, "User", "Import", g["tid"]))
        def _has(name_ok):
            return any(any(os.path.exists(os.path.join(b, f)) for f in name_ok) for b in bases)
        checks = []
        if self.opt_boxart.get():
            checks.append(_has(["GC%s.asset" % g["tid"]] if folder else ["cover.png", "cover.jpg", "cover.jpeg", "cover.dds"]))
        if self.opt_background.get():
            checks.append(_has(["BK%s.asset" % g["tid"]] if folder else ["background.png"]))
        if self.opt_icon.get() or self.opt_banner.get():
            checks.append(_has(["GL%s.asset" % g["tid"]] if folder else ["icon.png"]))
        if self.opt_screenshots.get():
            checks.append(_has(["SS%s.asset" % g["tid"]] if folder else ["screenshot1.png"]))
        return not all(checks)

    def download_one(self, path, g, kinds):
        tid = g["tid"]
        if self.opt_force.get():
            skip = lambda kind: False
        else:
            skip = lambda kind: self._kind_exists(g, path, kind)
        got = False

        # Download different asset types in parallel
        download_tasks = []
        if kinds.get("boxart") and not skip("boxart"):
            download_tasks.append(("boxart", lambda: self.download_kind(path, g, "boxart")))
        if kinds.get("background") and not skip("background"):
            download_tasks.append(("background", lambda: self.download_kind(path, g, "background")))
        if kinds.get("icon") and not skip("icon"):
            download_tasks.append(("icon", lambda: self.download_kind(path, g, "icon")))
        if kinds.get("banner") and not skip("banner"):
            download_tasks.append(("banner", lambda: self.download_kind(path, g, "banner")))
        if kinds.get("screenshots") and not skip("screenshots"):
            download_tasks.append(("screenshots", lambda: self.download_kind(path, g, "screenshots")))

        if download_tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(download_tasks)) as executor:
                futures = {executor.submit(fn): kind for kind, fn in download_tasks}
                for future in concurrent.futures.as_completed(futures):
                    kind = futures[future]
                    try:
                        result = future.result()
                        if kind == "boxart" and result:
                            got = True
                    except Exception as exc:
                        self.log(tr("logs_dl_kind_err", kind, exc))
        if got:
            g["has_cover"] = True

    def get_cover_blob(self, tid, g=None):
        try:
            # Se repo for gamecovers, busca do REMOTO (GitHub raw) + fallback local
            if self.repo == "gamecovers":
                b = self._gamecovers_remote(tid, g)
                if b:
                    return b
                # Fallback local se remoto falhar
                if g:
                    b = self._local_asset(tid, g)
                    if b:
                        return b
                self.log(tr("cover_missing_both"))
                return None

            # Capa personalizada local (pasta game_covers/ neste repo, não distribuída)
            # tem a maior prioridade: é o asset explícito do usuário para esse jogo.
            if g:
                b = self._local_asset(tid, g)
                if b:
                    return b
            # Na COVER, o x360db NUNCA vem primeiro (ele só tem a arte da frente), mesmo que
            # seja o repositório selecionado. A seleção (self.repo) apenas decide se a Unity
            # (caixa completa 900x600) ou a 360-Game-Art (capa frontal por TitleID) tenta
            # primeiro; o x360db fica sempre como último fallback.
            def _unity():
                return self._unity_cover(tid, g)

            def _gameart():
                b = fetch_bytes(GAME_ART_RAW + tid.lower() + "/cover.jpg")
                if b:
                    self.log(tr("gameart_cover_ok", tid))
                return b

            def _x360():
                return self.db.download_artwork(tid, "boxart")

            primary = self.repo if self.repo in ("xboxunity", "gameart") else "xboxunity"
            order = [primary]
            if primary == "xboxunity":
                order.append("gameart")
            else:
                order.insert(0, "xboxunity")
            order.append("x360db")
            for src in order:
                b = {"xboxunity": _unity, "gameart": _gameart, "x360db": _x360}[src]()
                if b:
                    return b
            self.log(tr("cover_missing_both"))
            return None
        except Exception as exc:
            self.log(tr("logs_cover_fetch_err", exc))
            return None

    def _local_asset(self, tid, g=None):
        """Busca asset na pasta local `game_covers/` deste repositório (não distribuída).
        Estrutura suportada:
          game_covers/<Nome do Jogo>_<TID>/cover.png | background.png | banner.png | tile.png | icon.png | screenshots/
          game_covers/<TID>/...
          game_covers/<HomebrewID>/...  (TID sintético SHA1 do nome)
        Prioridade: pasta com padrão <Nome>_<TID> > pasta por TID > pasta por HomebrewID > arquivo solto por TID > arquivo solto por nome."""
        base = GAME_COVERS_DIR
        if not os.path.isdir(base):
            return None
        ok = (".jpg", ".jpeg", ".png", ".dds", ".webp")
        tid = (tid or "").upper()

        def _try(path):
            try:
                if os.path.isfile(path):
                    self.log(tr("game_cover_ok", os.path.basename(path)))
                    return open(path, "rb").read()
            except (OSError, IOError):
                pass
            return None

        def _scan_folder(folder):
            if not os.path.isdir(folder):
                return None
            try:
                for name in sorted(os.listdir(folder)):
                    if name.lower().endswith(ok):
                        b = _try(os.path.join(folder, name))
                        if b:
                            return b
            except OSError:
                pass
            return None

        # 1) Pasta com padrão <Nome>_<TID> (case-insensitive no TID)
        if g:
            for key in ("dname", "folder_name", "title"):
                raw = str(g.get(key) or "").strip()
                if raw and raw.lower() != tid.lower():
                    # normaliza o nome para uso em pasta (remove caracteres problemáticos)
                    safe_name = re.sub(r'[\\/:*?"<>|]', "_", raw)
                    # procura pasta <safe_name>_<tid> ou <safe_name>_<tid_lower>
                    for suffix in (tid, tid.lower()):
                        folder_name = f"{safe_name}_{suffix}"
                        folder = os.path.join(base, folder_name)
                        b = _scan_folder(folder)
                        if b:
                            return b
                        # também tenta case-insensitive listando o diretório
                        try:
                            for entry in os.listdir(base):
                                if os.path.isdir(os.path.join(base, entry)) and entry.lower() == folder_name.lower():
                                    b = _scan_folder(os.path.join(base, entry))
                                    if b:
                                        return b
                        except OSError:
                            pass

        # 2) Pasta por TID (case-insensitive)
        for sub in (os.path.join(base, tid), os.path.join(base, tid.lower())):
            b = _scan_folder(sub)
            if b:
                return b

        # 3) Pasta por HomebrewID (TID sintético SHA1 do nome)
        if g:
            for key in ("dname", "folder_name", "title"):
                raw = str(g.get(key) or "").strip()
                if raw and raw.lower() != tid.lower():
                    hb_tid = legacy_tid_for(raw)
                    if hb_tid:
                        for sub in (os.path.join(base, hb_tid), os.path.join(base, hb_tid.lower())):
                            b = _scan_folder(sub)
                            if b:
                                return b

        # 4) Arquivo solto por TID
        for ext in ok:
            b = _try(os.path.join(base, tid + ext))
            if b:
                return b

        # 5) Arquivo solto por nome (só capa)
        if g:
            names = {}
            for key in ("dname", "folder_name", "title"):
                raw = str(g.get(key) or "").strip()
                if raw and raw.lower() != tid.lower():
                    slug = re.sub(r"[^a-z0-9]", "", raw.lower())
                    if slug:
                        names[slug] = raw
            if names:
                try:
                    for name in os.listdir(base):
                        if not name.lower().endswith(ok):
                            continue
                        slug = re.sub(r"[^a-z0-9]", "", os.path.splitext(name)[0].lower())
                        if slug in names:
                            self.log(tr("game_cover_ok", name))
                            return open(os.path.join(base, name), "rb").read()
                except OSError:
                    pass
        return None

    def _gamecovers_remote(self, tid, g=None):
        """Busca capa no repositório remoto game_covers (GitHub raw).
        Tenta múltiplos padrões de URL:
        - game_covers/<Nome>_<TID>/cover.png
        - game_covers/<TID>/cover.png
        - game_covers/<TID>.png
        - game_covers/<TID>.jpg
        - game_covers/<HomebrewID>/cover.png"""
        # Tenta com nome do jogo + TID
        if g:
            for key in ("dname", "folder_name", "title"):
                raw = str(g.get(key) or "").strip()
                if raw and raw.lower() != tid.lower():
                    safe_name = re.sub(r'[\\/:*?"<>|]', "_", raw)
                    for suffix in (tid, tid.lower()):
                        folder_name = f"{safe_name}_{suffix}"
                        # Tenta cover.png
                        url = GAME_COVERS_REMOTE + folder_name + "/cover.png"
                        b = fetch_bytes(url)
                        if b:
                            self.log(tr("gameart_cover_ok", tid) + f" (remote: {folder_name}/cover.png)")
                            return b
        # Tenta apenas TID
        for suffix in (tid, tid.lower()):
            url = GAME_COVERS_REMOTE + suffix + "/cover.png"
            b = fetch_bytes(url)
            if b:
                self.log(tr("gameart_cover_ok", tid) + f" (remote: {suffix}/cover.png)")
                return b
            # Tenta arquivo solto
            for ext in (".png", ".jpg", ".jpeg"):
                url = GAME_COVERS_REMOTE + suffix + ext
                b = fetch_bytes(url)
                if b:
                    self.log(tr("gameart_cover_ok", tid) + f" (remote: {suffix}{ext})")
                    return b
        # Tenta HomebrewID (TID sintético SHA1 do nome)
        if g:
            for key in ("dname", "folder_name", "title"):
                raw = str(g.get(key) or "").strip()
                if raw and raw.lower() != tid.lower():
                    hb_tid = legacy_tid_for(raw)
                    if hb_tid:
                        url = GAME_COVERS_REMOTE + hb_tid + "/cover.png"
                        b = fetch_bytes(url)
                        if b:
                            self.log(tr("gameart_cover_ok", tid) + f" (remote: {hb_tid}/cover.png)")
                            return b
        return None

    def _unity_cover(self, tid, g=None):
        items = self.unity.covers(tid)
        # Homebrews: a Unity indexa a capa por um TitleID interno (pequeno) achado
        # pela busca por NOME (TitleList), não pelo TID sintético/SHA1 nem pelo TID do XEX.
        if not items and g:
            for q in homebrew_search_queries(g):
                real = self.unity.resolve_title_tid(q)
                if real and real.upper() != tid.upper():
                    self.log(tr("logs_hb_tid_by_name", q, real))
                    items = self.unity.covers(real, force=True)
                    if items:
                        break
            if not items:
                self.log(tr("logs_hb_no_cover_by_name", self.game_title(g)))
        if not items:
            if self.unity._down_until > time.time():
                self.log(tr("logs_unity_offline", tid))
            else:
                self.log(tr("unity_no_cover", tid))
            return None
        ordered = sorted(
            items,
            key=lambda i: (0 if i.get("official") else 1, -unity_rating(i)),
        )
        for item in ordered[:8]:
            b = self.unity.cover_bytes(item)
            if b:
                if is_black_cover(b):
                    self.log(tr("unity_black_cover"))
                    continue
                return b
        self.log(tr("unity_no_usable", tid))
        return None

    def download_kind(self, path, g, kind):
        tid = g["tid"]
        try:
            if kind == "boxart":
                blob = self.get_cover_blob(tid, g)
                if blob:
                    img = box_render(Image.open(io.BytesIO(blob)), self.cover_format)
                    if g["folder"]:
                        self.write_asset(g["folder"], tid, "GC", img, ASSET_TYPE_BOXART)
                    self.write_import(path, tid, "cover.png", img)
                    mark_installed(tid, "boxart")
                    return True
                self.log(tr("cover_not_found_repo"))
                return False
            if kind == "background":
                blob = self._local_asset(tid, g)
                if not blob:
                    blob = self.db.download_artwork(tid, "background")
                if blob:
                    img = cover_fill(Image.open(io.BytesIO(blob)), BG_W, BG_H)
                    if g["folder"]:
                        self.write_asset(g["folder"], tid, "BK", img, ASSET_TYPE_BACKGROUND)
                    self.write_import(path, tid, "background.png", img)
                    mark_installed(tid, "background")
                    return True
                self.log(tr("background_not_found"))
                return False
            if kind in ("icon", "banner"):
                slot = ASSET_TYPE_ICON if kind == "icon" else ASSET_TYPE_BANNER
                size = (ICON_W, ICON_H) if kind == "icon" else (BANNER_W, BANNER_H)
                name = "icon" if kind == "icon" else "banner"
                blob = self._local_asset(tid, g)
                if not blob:
                    blob = self.db.download_artwork(tid, kind)
                if not blob:
                    self.log(tr("kind_not_found", name))
                    return False
                new_img = cover_fill(Image.open(io.BytesIO(blob)), *size)
                ok = self.apply_gl_slot(path, g, slot, new_img, name + ".png")
                if ok:
                    mark_installed(tid, kind)
                return ok
            if kind == "screenshots":
                # Local screenshots: pasta game_covers/<tid>/screenshots/ com arquivos *.jpg/*.png
                grabs = []
                local_ss_dir = os.path.join(GAME_COVERS_DIR, tid, "screenshots")
                if os.path.isdir(local_ss_dir):
                    for fname in sorted(os.listdir(local_ss_dir)):
                        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                            try:
                                img = cover_fill(Image.open(os.path.join(local_ss_dir, fname)), SS_W, SS_H)
                                grabs.append(img)
                                if len(grabs) >= self.ss_max:
                                    break
                            except Exception:
                                pass
                if not grabs:
                    for url in self.db.gallery_urls(tid)[: self.ss_max]:
                        data = fetch_bytes(url)
                        if not data:
                            continue
                        try:
                            grabs.append(cover_fill(Image.open(io.BytesIO(data)), SS_W, SS_H))
                        except Exception:
                            continue
                if not grabs:
                    self.log(tr("no_screenshots"))
                    return False
                textures = [(ASSET_TYPE_SCREENSHOT + i, s) for i, s in enumerate(grabs[: self.ss_max])]
                if g["folder"]:
                    self.write_multi_asset(g["folder"], tid, "SS", textures)
                for i, s in enumerate(textures):
                    self.write_import(path, tid, "screenshot%d.png" % (i + 1), s[1])
                mark_installed(tid, "screenshots")
                self.log(tr("logs_ss_installed", len(textures)))
                return True
        except Exception as exc:
            self.log(tr("logs_dl_kind_err", kind, exc))
            return False

    def apply_gl_slot(self, path, g, slot, new_img, import_name):
        tid = g["tid"]
        parts = {ASSET_TYPE_ICON: None, ASSET_TYPE_BANNER: None}
        if g["folder"]:
            gl_file = os.path.join(g["folder"], "GL%s.asset" % tid)
            if os.path.isfile(gl_file):
                try:
                    with open(gl_file, "rb") as f:
                        blob = f.read()
                    for s in parts:
                        parts[s] = decode_asset(blob, s)
                except Exception:
                    pass
        parts[slot] = new_img
        textures = [(s, im) for s, im in parts.items() if im is not None]
        if g["folder"]:
            self.write_multi_asset(g["folder"], tid, "GL", textures)
        self.write_import(path, tid, import_name, new_img)
        return True

    def write_asset(self, folder, tid, prefix, img, asset_type):
        self.write_multi_asset(folder, tid, prefix, [(asset_type, img)])

    def write_multi_asset(self, folder, tid, prefix, textures):
        target = os.path.join(folder, "%s%s.asset" % (prefix, tid))
        if os.path.exists(target) and self.opt_backup.get():
            backup = target + ".bak"
            try:
                if not os.path.exists(backup):
                    os.replace(target, backup)
            except OSError:
                pass
        blob = make_multi_asset_bytes(textures)
        with open(target, "wb") as f:
            f.write(blob)
        self.log(tr("logs_saved", display_path(target)))

    def write_import(self, root, tid, name, img):
        # Grava na raiz do drive (\\User\\Import, onde o Aurora lê) e também na
        # pasta do Aurora (onde versões antigas do app gravavam), para a capa
        # ficar visível em qualquer configuração de caminho.
        bases = []
        for p in (os.path.join(root, "User", "Import"),) + tuple(import_bases(root)):
            p = os.path.normpath(p)
            if p not in bases:
                bases.append(p)
        for import_dir in bases:
            import_dir = os.path.join(import_dir, tid)
            try:
                os.makedirs(import_dir, exist_ok=True)
            except OSError:
                continue
            target = os.path.join(import_dir, name)
            try:
                img.save(target, "PNG")
            except OSError:
                continue
            self.log(tr("logs_alt_import", display_path(target)))

    def install_custom(self, g=None):
        if self.busy:
            return
        if g is None:
            g = self.selected_game()
        if g is None:
            messagebox.showwarning(tr("warn"), tr("pick_game"))
            return
        filetypes = [("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp *.ico"), ("Todos", "*.*")]
        file_name = filedialog.askopenfilename(
            title=tr("custom_cover") + " (%s)" % self.db.title_name(g["tid"]),
            filetypes=filetypes,
        )
        if not file_name:
            return
        try:
            img = box_render(Image.open(file_name), self.cover_format)
        except Exception as exc:
            messagebox.showerror(tr("warn"), tr("img_open_fail", exc))
            return
        path = self.aurora_path.get().strip().strip('"')
        try:
            self.install_cover_img(path, g, img)
        except Exception as exc:
            messagebox.showerror(tr("warn"), tr("img_write_fail", exc))
            return
        self.log(tr("logs_custom_installed", self.db.title_name(g["tid"]), g["tid"]))
        self.show_preview(g)
        self.update_tree_row(g)

    def install_cover_img(self, path, g, img):
        if g["folder"]:
            self.write_asset(g["folder"], g["tid"], "GC", img, ASSET_TYPE_BOXART)
        self.write_import(path, g["tid"], "cover.png", img)
        mark_installed(g["tid"], "boxart")
        g["has_cover"] = True
        self.preview_cache.pop(g["tid"] + "|" + (g["folder"] or "import"), None)

    def export_assets(self, g):
        """Exporta assets do jogo para a pasta game_covers/<Nome>_<TID>/.
        Baixa assets faltando dos repositórios online antes de exportar."""
        tid = g.get("tid", "").upper()
        if not tid:
            return
        # Determina o nome da pasta: <Nome>_<TID>
        name = self.game_title(g)
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", name)
        folder_name = f"{safe_name}_{tid}"
        target_dir = os.path.join(GAME_COVERS_DIR, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(os.path.join(target_dir, "screenshots"), exist_ok=True)

        # Primeiro, garante que todos os assets estão baixados localmente
        self.log(tr("logs_downloading_assets", name))
        path = self.aurora_path.get().strip().strip('"')
        kinds = {
            "boxart": True,
            "background": True,
            "icon": True,
            "banner": True,
            "screenshots": True,
        }
        self.download_one(path, g, kinds)

        exported = []
        aurora_root = self.aurora_path.get().strip().strip('"')
        
        # Usa as mesmas bases de Import que o write_import usa
        import_bases_list = import_bases(aurora_root)
        import_candidates = [os.path.join(base, tid) for base in import_bases_list]
        
        def find_and_copy(filename, dst_name):
            for base in import_candidates:
                src = os.path.join(base, filename)
                if os.path.isfile(src):
                    dst = os.path.join(target_dir, dst_name)
                    shutil.copy2(src, dst)
                    exported.append(dst_name)
                    self.log(f"[EXPORT] Copiado: {src} -> {dst}")
                    return True
            return False

        # 1) Arquivos principais do Import - tenta vários nomes possíveis
        def find_and_copy_multi(patterns, dst_name):
            for base in import_candidates:
                if not os.path.isdir(base):
                    continue
                try:
                    for fname in os.listdir(base):
                        low = fname.lower()
                        for pat in patterns:
                            if low == pat or low.startswith(pat.rstrip("*")):
                                src = os.path.join(base, fname)
                                dst = os.path.join(target_dir, dst_name)
                                shutil.copy2(src, dst)
                                exported.append(dst_name)
                                self.log(f"[EXPORT] Copiado: {src} -> {dst}")
                                return True
                except OSError:
                    pass
            return False

        find_and_copy_multi(["cover.png", "cover.jpg", "cover.jpeg", "boxart.png", "boxart.jpg"], "cover.png")
        find_and_copy_multi(["background.png", "background.jpg", "background.jpeg", "bg.png"], "background.png")
        find_and_copy_multi(["banner.png", "banner.jpg", "banner.jpeg"], "banner.png")
        find_and_copy_multi(["tile.png", "tile.jpg", "tile.jpeg"], "tile.png")
        find_and_copy_multi(["icon.png", "icon.jpg", "icon.jpeg", "icon.ico"], "icon.png")

        # 2) Preview cache (PIL.Image) - salva cover se não exportou
        if "cover.png" not in exported:
            for cache_key in (f"{tid}|{g.get('folder') or 'import'}", f"{tid}|import"):
                if cache_key in self.preview_cache:
                    img = self.preview_cache[cache_key]
                    if isinstance(img, Image.Image):
                        img.save(os.path.join(target_dir, "cover.png"), "PNG")
                        exported.append("cover.png")
                        self.log(f"[EXPORT] Cover salvo do preview_cache: {cache_key}")
                        break

        # 3) Screenshots - procura em todos os Import candidatos
        for base in import_candidates:
            if os.path.isdir(base):
                try:
                    for fname in sorted(os.listdir(base)):
                        if fname.lower().startswith("screenshot") and fname.lower().endswith((".png", ".jpg", ".jpeg")):
                            src = os.path.join(base, fname)
                            dst_name = f"screenshots/{fname}"
                            dst = os.path.join(target_dir, dst_name)
                            shutil.copy2(src, dst)
                            exported.append(dst_name)
                            self.log(f"[EXPORT] Screenshot copiado: {src} -> {dst}")
                except OSError:
                    pass

        # 4) Tenta também a pasta do jogo (GameData) - copia assets se existirem como arquivos soltos
        folder = g.get("folder")
        if folder and os.path.isdir(folder):
            try:
                for fname in os.listdir(folder):
                    full = os.path.join(folder, fname)
                    up = fname.upper()
                    low = fname.lower()
                    if up.startswith(f"GC{tid}") and low.endswith(".asset"):
                        self.log(f"[EXPORT] Container GC na pasta do jogo: {fname} (não extraído)")
                    # Tenta copiar assets soltos na pasta do jogo (qualquer extensão de imagem)
                    if low.startswith("cover") and low.endswith((".png", ".jpg", ".jpeg")):
                        shutil.copy2(full, os.path.join(target_dir, "cover.png"))
                        exported.append("cover.png")
                        self.log(f"[EXPORT] Cover copiado da pasta do jogo: {fname}")
                    elif low.startswith("background") and low.endswith((".png", ".jpg", ".jpeg")):
                        shutil.copy2(full, os.path.join(target_dir, "background.png"))
                        exported.append("background.png")
                        self.log(f"[EXPORT] Background copiado da pasta do jogo: {fname}")
                    elif low.startswith("banner") and low.endswith((".png", ".jpg", ".jpeg")):
                        shutil.copy2(full, os.path.join(target_dir, "banner.png"))
                        exported.append("banner.png")
                        self.log(f"[EXPORT] Banner copiado da pasta do jogo: {fname}")
                    elif low.startswith("tile") and low.endswith((".png", ".jpg", ".jpeg")):
                        shutil.copy2(full, os.path.join(target_dir, "tile.png"))
                        exported.append("tile.png")
                        self.log(f"[EXPORT] Tile copiado da pasta do jogo: {fname}")
                    elif low.startswith("icon") and low.endswith((".png", ".jpg", ".jpeg")):
                        shutil.copy2(full, os.path.join(target_dir, "icon.png"))
                        exported.append("icon.png")
                        self.log(f"[EXPORT] Icon copiado da pasta do jogo: {fname}")
                    elif low.startswith("screenshot") and low.endswith((".png", ".jpg", ".jpeg")):
                        dst = os.path.join(target_dir, "screenshots", fname)
                        shutil.copy2(full, dst)
                        exported.append(f"screenshots/{fname}")
                        self.log(f"[EXPORT] Screenshot copiado da pasta do jogo: {fname}")
            except OSError:
                pass

        # 5) EXTRAI DO CONTAINER GC (RXEA) - contém TODOS os assets: boxart, background, icon, banner, screenshots
        gc_asset_types = [
            (ASSET_TYPE_BOXART, "cover.png"),
            (ASSET_TYPE_BACKGROUND, "background.png"),
            (ASSET_TYPE_ICON, "icon.png"),
            (ASSET_TYPE_BANNER, "banner.png"),
        ]
        # Screenshots: extrai todos (count dinâmico)
        # será processado separadamente após
        for base in scan_dirs:
            if not os.path.isdir(base):
                continue
            try:
                for fname in os.listdir(base):
                    if fname.upper().startswith(f"GC{tid}") and fname.lower().endswith(".asset"):
                        gc_path = os.path.join(base, fname)
                        self.log(f"[EXPORT] Lendo container GC: {fname}")
                        blob = _read_file(gc_path)
                        if blob and blob[:4] == b"RXEA":
                            for atype, dst_name in gc_asset_types:
                                if dst_name in exported:
                                    continue
                                img = decode_asset(blob, atype)
                                if img is not None:
                                    dst = os.path.join(target_dir, dst_name)
                                    if dst_name.startswith("screenshots/"):
                                        os.makedirs(os.path.join(target_dir, "screenshots"), exist_ok=True)
                                    img.save(dst, "PNG")
                                    exported.append(dst_name)
                                    self.log(f"[EXPORT GC] Extraído {dst_name} ({img.size[0]}x{img.size[1]}) do container")
                        # Extrai TODAS as screenshots do container GC
                        i = 0
                        while True:
                            ss_name = f"screenshots/screenshot{i+1}.png"
                            if ss_name in exported:
                                i += 1
                                continue
                            img = decode_asset(blob, ASSET_TYPE_SCREENSHOT + i)
                            if img is None:
                                break
                            dst = os.path.join(target_dir, ss_name)
                            os.makedirs(os.path.join(target_dir, "screenshots"), exist_ok=True)
                            img.save(dst, "PNG")
                            exported.append(ss_name)
                            self.log(f"[EXPORT GC] Extraído {ss_name} ({img.size[0]}x{img.size[1]}) do container")
                            i += 1
            except OSError:
                pass

        # 6) DEEP SCAN: encontra TODAS as imagens nos diretórios relevantes e classifica por tamanho/nome
        # Isso pega assets mesmo com nomes não padrão
        scan_dirs = import_candidates + ([folder] if folder and os.path.isdir(folder) else [])
        for base in scan_dirs:
            if not os.path.isdir(base):
                continue
            try:
                for fname in os.listdir(base):
                    full = os.path.join(base, fname)
                    if not os.path.isfile(full):
                        continue
                    low = fname.lower()
                    if not low.endswith((".png", ".jpg", ".jpeg")):
                        continue
                    # Tenta abrir e classificar por dimensões
                    try:
                        with Image.open(full) as im:
                            w, h = im.size
                        # DEBUG log every image found
                        self.log(f"[EXPORT DEEP SCAN] {fname} ({w}x{h}) in {base}")
                        # Classifica por proporção/tamanho
                        if low.startswith("screenshot") or (w >= 1000 and h >= 500 and w/h > 1.5):
                            # Screenshot ou banner largo
                            if w/h > 2.0:
                                dst_name = f"screenshots/{fname}"
                            else:
                                dst_name = "banner.png"
                        elif h > w * 1.3:  # Retrato alto = cover
                            dst_name = "cover.png"
                        elif w == h and w <= 256:  # Quadrado pequeno = icon/tile
                            dst_name = "icon.png"
                        elif w >= h * 1.5:  # Paisagem = background
                            dst_name = "background.png"
                        else:
                            dst_name = fname  # mantém nome original
                        
                        dst = os.path.join(target_dir, dst_name) if not dst_name.startswith("screenshots/") else os.path.join(target_dir, dst_name)
                        if dst_name.startswith("screenshots/"):
                            os.makedirs(os.path.join(target_dir, "screenshots"), exist_ok=True)
                        shutil.copy2(full, dst)
                        if dst_name not in exported:
                            exported.append(dst_name)
                        self.log(f"[EXPORT DEEP] {fname} ({w}x{h}) -> {dst_name}")
                    except Exception as e:
                        self.log(f"[EXPORT DEEP ERR] {fname}: {e}")
                        pass
            except OSError:
                pass

        # 6) DEBUG: lista o que tem no Import para diagnóstico
        for base in import_candidates:
            if os.path.isdir(base):
                try:
                    files = os.listdir(base)
                    self.log(f"[EXPORT DEBUG] Import folder {base}: {files}")
                except OSError:
                    pass

        # SEMPRE mostra resultado - pasta foi criada
        if exported:
            self.log(tr("logs_assets_exported", folder_name, ", ".join(exported)))
            messagebox.showinfo(tr("info"), tr("assets_exported_ok", folder_name, len(exported)))
        else:
            self.log(tr("logs_no_assets_to_export", tid))
            # A pasta foi criada vazia - avisa o usuário
            messagebox.showinfo(tr("info"), tr("assets_folder_created_empty", folder_name, target_dir))

    def on_tree_menu(self, event):
        if self.busy:
            return
        if not self.games:
            return
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        g = self.item_to_game.get(row)
        if g is None:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=tr("m_assets"), command=lambda: self.open_assets(g))
        menu.add_command(label=tr("m_alt"), command=lambda: self.alt_covers(g))
        menu.add_command(label=tr("m_custom"), command=lambda: self.install_custom(g))
        menu.add_command(label=tr("m_export_assets"), command=lambda: self.export_assets(g))
        menu.add_separator()
        menu.add_command(label=tr("m_rename"), command=lambda: self.rename_game(g))
        if g.get("folder"):
            menu.add_command(label=tr("m_open_folder"), command=lambda: self.open_game_folder(g))
        menu.add_separator()
        menu.add_command(label=tr("m_remove_cover"), command=lambda: self.remove_cover(g))
        menu.add_command(label=tr("m_remove_game"), command=lambda: self.remove_game(g))
        if self.hidden_tids:
            menu.add_separator()
            menu.add_command(label=tr("m_restore_hidden"), command=self.restore_hidden_games)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def apply_theme(self):
        eff = detect_system_theme() if self.theme == "sistema" else self.theme
        self._applied_theme = eff
        th = THEMES.get(eff, THEMES["escuro"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=th["bg"], foreground=th["fg"], fieldbackground=th["field"])
        style.configure("TFrame", background=th["bg"])
        style.configure("TLabel", background=th["bg"], foreground=th["fg"])
        style.configure("TEntry", fieldbackground=th["field"], foreground=th["fg"], insertcolor=th["fg"])
        style.configure("TSpinbox", fieldbackground=th["field"], foreground=th["fg"], buttonbackground=th["button"])
        style.configure("TButton", background=th["button"], foreground=th["fg"], bordercolor=th["bg2"])
        style.map("TButton", background=[("active", th["active"]), ("pressed", th["active"])], foreground=[("disabled", th["muted"])])
        style.configure("TCheckbutton", background=th["bg"], foreground=th["fg"])
        style.map("TCheckbutton", background=[("active", th["bg"])])
        style.configure("TRadiobutton", background=th["bg"], foreground=th["fg"])
        style.map("TRadiobutton", background=[("active", th["bg"])])
        style.configure("Treeview", background=th["field"], fieldbackground=th["field"], foreground=th["fg"])
        style.map("Treeview", background=[("selected", th["sel"])], foreground=[("selected", th["sels_fg"])])
        style.configure("Treeview.Heading", background=th["button"], foreground=th["fg"])
        style.configure("TProgressbar", background=th["accent"], troughcolor=th["bg2"])
        style.configure("TScrollbar", background=th["button"], troughcolor=th["bg"])
        self._recolor_all(self.root, th)
        self._paint_status()

    def _recolor_all(self, widget, th):
        try:
            cls = widget.winfo_class()
        except tk.TclError:
            return
        if cls == "Label":
            try:
                widget.configure(bg=th["bg"], fg=th["fg"])
            except tk.TclError:
                pass
        elif cls == "Frame":
            try:
                widget.configure(bg=th["bg"])
            except tk.TclError:
                pass
        elif cls == "Text":
            try:
                widget.configure(bg=th["field"], fg=th["fg"], insertbackground=th["fg"])
            except tk.TclError:
                pass
        elif cls == "Listbox":
            try:
                widget.configure(bg=th["field"], fg=th["fg"], selectbackground=th["sel"])
            except tk.TclError:
                pass
        for child in widget.winfo_children():
            self._recolor_all(child, th)

    def open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title(tr("settings_title"))
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.minsize(520, 0)
        th = THEMES.get(self.theme, THEMES["escuro"])
        dlg.configure(bg=th["bg"])
        outer = ttk.Frame(dlg, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        # Two-column grid: label (col 0), control (col 1)
        row_idx = 0

        def add_row(label_text, widget, colspan=1):
            nonlocal row_idx
            ttk.Label(outer, text=label_text).grid(row=row_idx, column=0, sticky="w", pady=4, padx=(0, 12))
            if colspan == 1:
                widget.grid(row=row_idx, column=1, sticky="w", pady=4)
            else:
                widget.grid(row=row_idx, column=1, columnspan=colspan, sticky="ew", pady=4)
            row_idx += 1

        def add_section(title):
            nonlocal row_idx
            if row_idx > 0:
                ttk.Separator(outer, orient=tk.HORIZONTAL).grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=(8, 4))
                row_idx += 1
            ttk.Label(outer, text=title, font=("Segoe UI", 9, "bold")).grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(0, 4))
            row_idx += 1

        outer.columnconfigure(1, weight=1)

        # General
        add_section(tr("set_title"))

        theme_var = tk.StringVar(value=self.theme)
        tf = ttk.Frame(outer)
        ttk.Radiobutton(tf, text=tr("theme_dark"), variable=theme_var, value="escuro").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(tf, text=tr("theme_light"), variable=theme_var, value="claro").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(tf, text=tr("theme_system"), variable=theme_var, value="sistema").pack(side=tk.LEFT, padx=6)
        add_row(tr("set_theme"), tf)

        lang_var = tk.StringVar(value=CURRENT_LANG)
        lf = ttk.Frame(outer)
        for code, name in LANGUAGES.items():
            ttk.Radiobutton(lf, text=name, variable=lang_var, value=code).pack(side=tk.LEFT, padx=6)
        add_row(tr("set_lang"), lf)

        show_status_var = tk.BooleanVar(value=self.show_status)
        show_log_var = tk.BooleanVar(value=self.show_log)
        sf2 = ttk.Frame(outer)
        ttk.Checkbutton(sf2, text=tr("set_show_status"), variable=show_status_var).pack(anchor="w")
        ttk.Checkbutton(sf2, text=tr("set_log"), variable=show_log_var).pack(anchor="w")
        add_row(tr("set_show_status"), sf2)

        # Covers
        add_section(tr("set_repo"))

        repo_var = tk.StringVar(value=self.repo)
        rf = ttk.Frame(outer)
        ttk.Radiobutton(rf, text="x360db", variable=repo_var, value="x360db").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(rf, text="XboxUnity", variable=repo_var, value="xboxunity").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(rf, text="360-Game-Art", variable=repo_var, value="gameart").pack(side=tk.LEFT, padx=6)
        add_row(tr("set_repo"), rf)

        f_var = tk.StringVar(value=self.cover_format)
        cf = ttk.Frame(outer)
        ttk.Radiobutton(cf, text=tr("format_portrait"), variable=f_var, value="retrato").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(cf, text=tr("format_landscape"), variable=f_var, value="paisagem").pack(side=tk.LEFT, padx=6)
        add_row(tr("set_format"), cf)

        sf = ttk.Frame(outer)
        spin = ttk.Spinbox(sf, from_=0, to=20, width=4)
        spin.set(str(self.ss_max))
        spin.pack(anchor="w")
        add_row(tr("set_screenshots"), sf)

        auto_search_var = tk.BooleanVar(value=self.cfg.get("auto_search_titles", True))
        add_row(tr("auto_search_titles"), ttk.Checkbutton(outer, text=tr("auto_search_titles"), variable=auto_search_var))

        show_game_info_var = tk.BooleanVar(value=self.cfg.get("show_game_info", True))
        add_row(tr("show_game_info"), ttk.Checkbutton(outer, text=tr("show_game_info"), variable=show_game_info_var))

        show_debug_var = tk.BooleanVar(value=self.cfg.get("show_debug_button", False))
        add_row(tr("show_debug_button"), ttk.Checkbutton(outer, text=tr("show_debug_button"), variable=show_debug_var))

        missing_only_var = tk.BooleanVar(value=self.opt_missing_only.get())
        add_row(tr("download_missing_only"), ttk.Checkbutton(outer, text=tr("download_missing_only"), variable=missing_only_var))

        auto_update_var = tk.BooleanVar(value=self.cfg.get("auto_update_check", True))
        add_row(tr("auto_update_check"), ttk.Checkbutton(outer, text=tr("auto_update_check"), variable=auto_update_var))

        # FTP
        add_section(tr("set_ftp"))

        ftp_host_ent = ttk.Entry(outer, width=16)
        ftp_host_ent.insert(0, self.ftp_host)
        add_row(tr("ftp_host_lbl"), ftp_host_ent)

        ftp_port_ent = ttk.Entry(outer, width=6)
        ftp_port_ent.insert(0, str(self.ftp_port))
        add_row(tr("ftp_port_lbl"), ftp_port_ent)

        ftp_user_ent = ttk.Entry(outer, width=10)
        ftp_user_ent.insert(0, self.ftp_user)
        add_row(tr("ftp_user_lbl"), ftp_user_ent)

        ftp_pass_ent = ttk.Entry(outer, width=10, show="*")
        ftp_pass_ent.insert(0, self.ftp_pass)
        add_row(tr("ftp_pass_lbl"), ftp_pass_ent)

        ftp_base_ent = ttk.Entry(outer)
        ftp_base_ent.insert(0, self.ftp_base)
        add_row(tr("ftp_base_lbl"), ftp_base_ent)

        # Credits
        ttk.Separator(outer, orient=tk.HORIZONTAL).grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=(12, 4))
        row_idx += 1
        tk.Label(
            outer,
            text=tr("credits"),
            justify=tk.CENTER,
            fg=th.get("fg", "#ffffff"),
            bg=th["bg"],
            font=("Segoe UI", 8),
        ).grid(row=row_idx, column=0, columnspan=2, pady=(0, 8))
        row_idx += 1

        # Buttons
        bf = ttk.Frame(outer)
        bf.grid(row=row_idx, column=0, columnspan=2, pady=(8, 0))

        def _save():
            try:
                self.theme = theme_var.get()
                self.repo = repo_var.get()
                self.cover_format = f_var.get()
                new_lang = lang_var.get()
                new_show = bool(show_status_var.get())
                new_log = bool(show_log_var.get())
                try:
                    self.ss_max = max(0, min(20, int(spin.get().strip() or self.ss_max)))
                except ValueError:
                    pass
                changed_show = new_show != self.show_status
                changed_lang = new_lang != CURRENT_LANG
                self.show_status = new_show
                self.show_log = new_log
                self.ftp_host = ftp_host_ent.get().strip()
                try:
                    self.ftp_port = max(1, int(ftp_port_ent.get().strip() or 21))
                except ValueError:
                    self.ftp_port = 21
                self.ftp_user = ftp_user_ent.get().strip() or "xbox"
                self.ftp_pass = ftp_pass_ent.get()
                self.ftp_base = ftp_base_ent.get().strip() or "Hdd:\\Aurora\\Data\\GameData"
                self.opt_missing_only.set(bool(missing_only_var.get()))
                self.cfg.update(
                    theme=self.theme,
                    repo=self.repo,
                    cover_format=self.cover_format,
                    screenshots=self.ss_max,
                    lang=new_lang,
                    show_status=self.show_status,
                    show_log=self.show_log,
                    auto_search_titles=bool(auto_search_var.get()),
                    show_game_info=bool(show_game_info_var.get()),
                    show_debug_button=bool(show_debug_var.get()),
                    download_missing_only=bool(missing_only_var.get()),
                    auto_update_check=bool(auto_update_var.get()),
                    ftp_host=self.ftp_host,
                    ftp_port=self.ftp_port,
                    ftp_user=self.ftp_user,
                    ftp_pass=self.ftp_pass,
                    ftp_base=self.ftp_base,
                )
                save_config(self.cfg)
                self.chk_screenshots.configure(text=tr("opt_screenshots", self.ss_max))
                self.apply_show_status()
                self.apply_show_log()
                self.apply_theme()
                self.log(
                    tr(
                        "status_saved",
                        self.theme,
                        self.repo,
                        self.cover_format,
                        self.ss_max,
                    )
                )
                dlg.destroy()
                if changed_lang:
                    messagebox.showinfo(tr("restart_title"), tr("restart_lang"))
            except Exception as exc:
                messagebox.showerror(tr("warn"), tr("save_fail", exc))

        ttk.Button(bf, text=tr("save"), command=_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("cancel2"), command=dlg.destroy).pack(side=tk.LEFT, padx=4)
        dlg.grab_set()

    def asset_present(self, g, kind, path):
        targets = {
            "boxart": ("GC%s.asset", "cover.png"),
            "background": ("BK%s.asset", "background.png"),
            "icon": ("GL%s.asset", "icon.png"),
            "banner": ("GL%s.asset", "banner.png"),
            "screenshots": ("SS%s.asset", "screenshot1.png"),
        }
        a, b = targets[kind]
        cands = []
        if g["folder"]:
            cands.append(os.path.join(g["folder"], a % g["tid"]))
        cands.append(os.path.join(path, "User", "Import", g["tid"], b))
        return any(os.path.isfile(c) for c in cands)

    def open_assets(self, g):
        if self.busy:
            return
        path = self.aurora_path.get().strip().strip('"')
        dlg = tk.Toplevel(self.root)
        dlg.title("%s - %s (%s)" % (tr("assets"), self.game_title(g), g["tid"]))
        dlg.transient(self.root)
        dlg.resizable(False, False)
        th = THEMES.get(self._applied_theme, THEMES["escuro"])
        dlg.configure(bg=th["bg"])
        ttk.Label(
            dlg, text="%s %s (%s)" % (tr("assets_of"), self.game_title(g), g["tid"])
        ).pack(pady=(10, 4))
        body = ttk.Frame(dlg)
        body.pack(fill=tk.BOTH, expand=True, padx=10)
        tree = ttk.Treeview(body, columns=("item", "kind", "status"), show="headings", height=5)
        tree.heading("item", text="")
        tree.heading("kind", text=tr("col_kind"))
        tree.heading("status", text=tr("col_status"))
        tree.column("item", width=24, stretch=False)
        tree.column("kind", width=170)
        tree.column("status", width=90)
        tree.pack(side=tk.LEFT, fill=tk.Y)
        kinds = {}
        for i, (kind, label, _p, _s, _imp) in enumerate(ASSET_KINDS):
            item = tree.insert("", tk.END, values=(i + 1, label, "?"))
            kinds[item] = kind
        right = ttk.Frame(body, width=160)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self._assets_kindlbl = ttk.Label(right, text="")
        self._assets_kindlbl.pack(pady=(0, 4))
        pframe = tk.Frame(
            right, width=160, height=200, bd=1, relief=tk.SUNKEN, bg=th["field"]
        )
        pframe.pack_propagate(False)
        pframe.pack(fill=tk.BOTH)
        self._assets_preview = tk.Label(
            pframe, text=tr("no_preview"), bg=th["field"], fg=th["muted"]
        )
        self._assets_preview.pack(fill=tk.BOTH, expand=True)
        nav = ttk.Frame(right)
        nav.pack(pady=(4, 0))
        self._assets_prev = ttk.Button(
            nav, text=tr("ss_prev"), width=4, command=self._assets_ss_prev, state=tk.DISABLED
        )
        self._assets_prev.pack(side=tk.LEFT, padx=(0, 4))
        self._assets_next = ttk.Button(
            nav, text=tr("ss_next"), width=4, command=self._assets_ss_next, state=tk.DISABLED
        )
        self._assets_next.pack(side=tk.LEFT)
        bf = ttk.Frame(dlg)
        bf.pack(pady=(4, 0))
        ttk.Button(bf, text=tr("dl_online"), command=self.download_selected_kind).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dl_all"), command=self.download_all_assets).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("change_pc"), command=self.pick_selected_kind).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("ftp_send"), command=self.ftp_send_assets).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("ftp_deploy_covers"), command=self.ftp_deploy_covers).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("close"), command=self._close_assets_dlg).pack(side=tk.LEFT, padx=4)
        msg = tk.Label(dlg, text=tr("assets_hint"), bg=th["bg"], fg=th["muted"])
        msg.pack(pady=(6, 8))
        tree.bind("<<TreeviewSelect>>", self._assets_on_select)
        self._assets_tree = tree
        self._assets_kinds = kinds
        self._assets_g = g
        self._assets_path = path
        self._assets_msg = msg
        self._assets_dlg = dlg
        self._assets_photo = None
        self._assets_ss_index = 0
        dlg.protocol("WM_DELETE_WINDOW", self._close_assets_dlg)
        self.refresh_assets_dlg()
        if kinds:
            first = list(kinds)[0]
            tree.selection_set(first)
            tree.focus(first)
        dlg.grab_set()

    def _close_assets_dlg(self):
        if self._assets_dlg is not None:
            try:
                self._assets_dlg.destroy()
            except tk.TclError:
                pass
        self._assets_dlg = None
        self._assets_tree = None
        self._assets_kinds = {}
        self._assets_msg = None
        self._assets_preview = None
        self._assets_kindlbl = None
        self._assets_photo = None
        self._assets_ss_index = 0
        self._assets_prev = None
        self._assets_next = None

    def refresh_assets_dlg(self):
        dlg = self._assets_dlg
        if dlg is None or not dlg.winfo_exists():
            return
        for item, kind in self._assets_kinds.items():
            img = self.load_kind_image(self._assets_g, kind, self._assets_path)
            st = (
                tr("assets_installed")
                if img is not None
                else tr("assets_missing")
            )
            self._assets_tree.set(item, "status", st)
        self._assets_on_select()

    def _assets_on_select(self, _event=None):
        if self._assets_dlg is None or not self._assets_dlg.winfo_exists():
            return
        kind = self._selected_kind()
        if kind is None:
            if self._assets_preview is not None:
                self._assets_preview.configure(image="", text=tr("no_preview"))
            return
        label = dict((k, l) for k, l, *_ in ASSET_KINDS).get(kind, kind)
        imgs = self.load_kind_images(self._assets_g, kind, self._assets_path)
        ss_kind = kind == "screenshots"
        for b in (self._assets_prev, self._assets_next):
            if b is not None:
                try:
                    b.configure(state=tk.NORMAL if (ss_kind and len(imgs) > 1) else tk.DISABLED)
                except tk.TclError:
                    pass
        # Reset screenshot index when switching to screenshots kind
        if ss_kind and self._last_assets_kind != "screenshots":
            self._assets_ss_index = 0
        self._last_assets_kind = kind
        if ss_kind:
            if imgs:
                self._assets_ss_index = max(0, min(self._assets_ss_index, len(imgs) - 1))
                label = "%s (%d/%d)" % (
                    label,
                    self._assets_ss_index + 1,
                    len(imgs),
                )
            else:
                self._assets_ss_index = 0
        else:
            self._assets_ss_index = 0
        if self._assets_kindlbl is not None:
            self._assets_kindlbl.configure(text=label)
        if not imgs:
            if self._assets_preview is not None:
                self._assets_preview.configure(image="", text=tr("no_preview"))
            return
        img = imgs[min(self._assets_ss_index, len(imgs) - 1)]
        thumb = cover_fit(img, 150, 190)
        try:
            self._assets_photo = ImageTk.PhotoImage(thumb)
            self._assets_preview.configure(image=self._assets_photo, text="")
        except Exception:
            self._assets_preview.configure(image="", text=tr("no_preview"))

    def _assets_ss_prev(self):
        if self._assets_ss_index > 0:
            self._assets_ss_index -= 1
        self._assets_on_select()

    def _assets_ss_next(self):
        self._assets_ss_index += 1
        self._assets_on_select()

    def _import_paths(self, tid, path):
        dirs = [os.path.join(d, tid) for d in import_dirs_existing(path)]
        if not dirs:
            dirs.append(os.path.join(path, "User", "Import", tid))
        return dirs

    def _open_import_image(self, tid, path, name):
        for d in self._import_paths(tid, path):
            im = _open_image(os.path.join(d, name))
            if im is not None:
                return im
        return None

    def load_kind_images(self, g, kind, path):
        imgs = []
        tid = g["tid"]
        folder = g["folder"]
        import_paths = self._import_paths(tid, path)
        if kind == "screenshots":
            if folder:
                asset = os.path.join(folder, "SS%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        try:
                            count = max(1, struct.unpack(">I", raw[16:20])[0])
                        except Exception:
                            count = 1
                        for i in range(count):
                            im = _decode_asset_safe(raw, ASSET_TYPE_SCREENSHOT + i)
                            if im is None:
                                break
                            imgs.append(im)
            i = 1
            while True:
                found = None
                for import_path in import_paths:
                    im = _open_image(os.path.join(import_path, "screenshot%d.png" % i))
                    if im is not None:
                        found = im
                        break
                if found is None:
                    break
                imgs.append(found)
                i += 1
            return imgs
        im = self.load_kind_image(g, kind, path)
        if im is not None:
            imgs.append(im)
        return imgs

    def load_kind_image(self, g, kind, path):
        tid = g["tid"]
        folder = g["folder"]
        raw = None
        if kind == "boxart":
            if folder:
                asset = os.path.join(folder, "GC%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, ASSET_TYPE_BOXART)
                        if im:
                            return im
            return self._open_import_image(tid, path, "cover.png")
        if kind == "background":
            if folder:
                asset = os.path.join(folder, "BK%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, ASSET_TYPE_BACKGROUND)
                        if im:
                            return im
            return self._open_import_image(tid, path, "background.png")
        if kind == "icon" or kind == "banner":
            at = ASSET_TYPE_ICON if kind == "icon" else ASSET_TYPE_BANNER
            name = "icon.png" if kind == "icon" else "banner.png"
            if folder:
                asset = os.path.join(folder, "GL%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, at)
                        if im:
                            return im
            return self._open_import_image(tid, path, name)
        if kind == "screenshots":
            if folder:
                asset = os.path.join(folder, "SS%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, ASSET_TYPE_SCREENSHOT)
                        if im:
                            return im
            return self._open_import_image(tid, path, "screenshot1.png")
        return None

    def _selected_kind(self):
        if self._assets_tree is None:
            return None
        sel = self._assets_tree.selection()
        if not sel:
            return None
        return self._assets_kinds.get(sel[0])

    def download_selected_kind(self):
        kind = self._selected_kind()
        if kind is None:
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("assets_pick"))
            return
        if self._assets_msg is not None:
            self._assets_msg.configure(text=tr("assets_dl_kind", kind))
        self.thread_download_kind(self._assets_path, self._assets_g, kind)

    def ftp_send_assets(self):
        if self.busy:
            return
        if not self.ftp_host.strip():
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("ftp_no_host"))
            return
        g = self._assets_g
        if g is None or not g.get("folder"):
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("ftp_no_folder"))
            return
        self.set_busy(True)
        if self._assets_msg is not None:
            self._assets_msg.configure(text=tr("ftp_sending"))
        threading.Thread(target=self._ftp_run, args=(g,), daemon=True).start()

    def ftp_deploy_covers(self):
        """Envia assets da pasta game_covers/<Nome>_<TID>/ para o console via FTP,
        criando a estrutura de pastas necessária."""
        if self.busy:
            return
        if not self.ftp_host.strip():
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("ftp_no_host"))
            return
        g = self._assets_g
        if g is None:
            return
        tid = g.get("tid", "").upper()
        name = self.game_title(g)
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", name)
        folder_name = f"{safe_name}_{tid}"
        local_dir = os.path.join(GAME_COVERS_DIR, folder_name)
        if not os.path.isdir(local_dir):
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("ftp_deploy_no_folder"))
            self.log(tr("ftp_deploy_no_folder"))
            return
        self.set_busy(True)
        if self._assets_msg is not None:
            self._assets_msg.configure(text=tr("ftp_deploying"))
        threading.Thread(target=self._ftp_deploy_run, args=(g, local_dir, folder_name), daemon=True).start()

    def _ftp_deploy_run(self, g, local_dir, folder_name):
        try:
            # Coleta todos os arquivos recursivamente
            files = []
            for root, dirs, fnames in os.walk(local_dir):
                for fname in fnames:
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, local_dir).replace("\\", "/")
                    files.append((full, rel))
        except OSError:
            files = []
        if not files:
            self.queue.put("__assets_msg__:0::")
            self.log(tr("logs_no_assets_to_export", g.get("tid", "").upper()))
            return
        ftp = None
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_host, int(self.ftp_port), timeout=30)
            ftp.login(self.ftp_user, self.ftp_pass)
            remote = self._ftp_ensure_dir(ftp, self.ftp_base)
            target = remote + "\\" + folder_name
            try:
                ftp.mkd(target)
            except ftplib.error_perm:
                pass
            ftp.cwd(target)
            n = 0
            for full, rel in files:
                # Cria subpastas se necessário
                rel_dir = os.path.dirname(rel)
                if rel_dir:
                    parts = rel_dir.split("/")
                    current = target
                    for part in parts:
                        current = current + "\\" + part
                        try:
                            ftp.mkd(current)
                        except ftplib.error_perm:
                            pass
                    ftp.cwd(target)
                    for part in parts:
                        try:
                            ftp.cwd(part)
                        except ftplib.error_perm:
                            pass
                with open(full, "rb") as f:
                    ftp.storbinary("STOR " + os.path.basename(rel), f)
                n += 1
            ftp.quit()
            self.queue.put("__assets_msg__:%d::%s" % (n, target))
            self.log(tr("ftp_deploy_ok", n, target))
        except Exception as exc:
            try:
                if ftp is not None:
                    ftp.close()
            except Exception:
                pass
            self.log(tr("logs_ftp_err", exc))
            self.queue.put("__assets_msg__:e:%s" % exc)
        finally:
            self.queue.put("__done__")

    def _ftp_run(self, g):
        try:
            files = [
                os.path.join(g["folder"], name)
                for name in sorted(os.listdir(g["folder"]))
                if os.path.isfile(os.path.join(g["folder"], name))
            ]
        except OSError:
            files = []
        if not files:
            self.queue.put("__assets_msg__:0::")
            return
        ftp = None
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_host, int(self.ftp_port), timeout=30)
            ftp.login(self.ftp_user, self.ftp_pass)
            remote = self._ftp_ensure_dir(ftp, self.ftp_base)
            target = remote + "\\" + g["folder_name"]
            try:
                ftp.mkd(target)
            except ftplib.error_perm:
                pass
            ftp.cwd(target)
            n = 0
            for full in files:
                with open(full, "rb") as f:
                    ftp.storbinary("STOR " + os.path.basename(full), f)
                n += 1
            ftp.quit()
            self.queue.put("__assets_msg__:%d::%s" % (n, target))
            self.log(tr("logs_ftp_sent", n, target))
        except Exception as exc:
            try:
                if ftp is not None:
                    ftp.close()
            except Exception:
                pass
            self.log(tr("logs_ftp_err", exc))
            self.queue.put("__assets_msg__:e:%s" % exc)
        finally:
            self.queue.put("__done__")

    def _ftp_ensure_dir(self, ftp, base):
        parts = [p.strip() for p in re.split(r"[\\/]+", base) if p.strip()]
        if not parts:
            parts = ["Hdd:", "Aurora", "Data", "GameData"]
        current = []
        for p in parts:
            current.append(p)
            path = "\\".join(current)
            try:
                ftp.mkd(path)
            except ftplib.error_perm:
                pass
            try:
                ftp.cwd(path)
            except ftplib.error_perm as exc:
                raise OSError(tr("ftp_inaccessible", path, exc))
        return "\\".join(current)

    def _assets_msg_show(self, payload):
        if self._assets_msg is None or not self._assets_dlg.winfo_exists():
            return
        if payload.startswith("e:"):
            self._assets_msg.configure(text=tr("ftp_err", payload[2:]))
        elif payload.endswith("::"):
            self._assets_msg.configure(text=tr("ftp_sent", 0, self.ftp_base))
        else:
            n, _, target = payload.partition("::")
            try:
                self._assets_msg.configure(text=tr("ftp_sent", int(n), target))
            except ValueError:
                self._assets_msg.configure(text=payload)

    def pick_selected_kind(self):
        kind = self._selected_kind()
        if kind is None:
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("assets_pick"))
            return
        self.pick_kind_file(self._assets_g, kind)

    def thread_download_kind(self, path, g, kind):
        if self.busy:
            return
        self.set_busy(True)
        self.log(tr("logs_downloading", kind, self.db.title_name(g["tid"]), g["tid"]))

        def _run():
            try:
                ok = self.download_kind(path, g, kind)
                self.log(tr("logs_kind_result", kind, "OK" if ok else tr("no_success")))
            except Exception as exc:
                self.log(tr("logs_kind_err", exc))
            finally:
                self.queue.put("__assets_refresh__")
                self.queue.put("__preview_refresh__")
                self.queue.put("__refresh_tree__")
                self.queue.put("__done__")

        threading.Thread(target=_run, daemon=True).start()

    def download_all_assets(self):
        if self.busy:
            return
        g = self._assets_g
        if g is None:
            if self._assets_msg is not None:
                self._assets_msg.configure(text=tr("assets_pick"))
            return
        if self._assets_msg is not None:
            self._assets_msg.configure(text=tr("dl_all_start"))
        self.thread_download_all(self._assets_path, g)

    def thread_download_all(self, path, g):
        if self.busy:
            return
        self.set_busy(True)
        self.log(tr("dl_all_log", self.db.title_name(g["tid"]), g["tid"]))
        kinds = [k for k, *_ in ASSET_KINDS]

        def _run():
            try:
                for kind in kinds:
                    if self.cancel_event.is_set():
                        break
                    if self.opt_force.get() or not self._kind_exists(g, path, kind):
                        try:
                            self.download_kind(path, g, kind)
                        except Exception as exc:
                            self.log(tr("logs_kind_err_with", kind, exc))
                    else:
                        self.log(tr("logs_kind_skip", kind))
            finally:
                self.queue.put("__assets_refresh__")
                self.queue.put("__preview_refresh__")
                self.queue.put("__refresh_tree__")
                self.queue.put("__done__")

        threading.Thread(target=_run, daemon=True).start()

    def pick_kind_file(self, g, kind):
        if self.busy:
            return
        filetypes = [("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp *.ico"), ("Todos", "*.*")]
        titles = {
            "boxart": tr("kind_boxart"),
            "background": tr("kind_background"),
            "icon": tr("kind_icon"),
            "banner": tr("kind_banner"),
            "screenshots": tr("kind_screenshots"),
        }
        file_name = filedialog.askopenfilename(
            title=tr("pick_kind", titles.get(kind, kind), self.db.title_name(g["tid"])),
            filetypes=filetypes,
        )
        if not file_name:
            return
        try:
            img = Image.open(file_name)
        except Exception as exc:
            messagebox.showerror(tr("error"), tr("img_open_fail", exc))
            return
        path = self.aurora_path.get().strip().strip('"')
        try:
            tid = g["tid"]
            if kind == "boxart":
                self.install_cover_img(path, g, box_render(img, self.cover_format))
            elif kind == "background":
                b = cover_fill(img, BG_W, BG_H)
                if g["folder"]:
                    self.write_asset(g["folder"], tid, "BK", b, ASSET_TYPE_BACKGROUND)
                self.write_import(path, tid, "background.png", b)
            elif kind == "icon":
                self.apply_gl_slot(path, g, ASSET_TYPE_ICON, cover_fill(img, ICON_W, ICON_H), "icon.png")
            elif kind == "banner":
                self.apply_gl_slot(path, g, ASSET_TYPE_BANNER, cover_fill(img, BANNER_W, BANNER_H), "banner.png")
            elif kind == "screenshots":
                s = cover_fill(img, SS_W, SS_H)
                if g["folder"]:
                    self.write_multi_asset(g["folder"], tid, "SS", [(ASSET_TYPE_SCREENSHOT, s)])
                self.write_import(path, tid, "screenshot1.png", s)
        except Exception as exc:
            messagebox.showerror(tr("error"), tr("img_write_fail", exc))
            return
        mark_installed(tid, kind)
        self.log(tr("asset_changed", kind, self.db.title_name(tid), tid))
        self.refresh_assets_dlg()
        self.update_tree_row(g)
        g2 = self.selected_game()
        if g2 is g:
            self.show_preview(g)

    def alt_covers(self, g):
        if self.busy:
            return
        tid = g["tid"]
        dlg = tk.Toplevel(self.root)
        dlg.title("%s (%s)" % (tr("alt_title"), self.db.title_name(tid)))
        dlg.transient(self.root)
        dlg.geometry("640x620")
        th = THEMES.get(self._applied_theme, THEMES["escuro"])
        dlg.configure(bg=th["bg"])
        ttk.Label(dlg, text=tr("alt_label")).pack(pady=(10, 4))
        lb = tk.Listbox(
            dlg, bg=th["field"], fg=th["fg"], selectbackground=th["sel"]
        )
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))
        lb.bind("<<ListboxSelect>>", self._alt_select)
        dest_row = ttk.Frame(dlg)
        dest_row.pack(fill=tk.X, padx=10, pady=(0, 4))
        ttk.Label(dest_row, text=tr("dest") + ":").pack(side=tk.LEFT)
        ttk.Entry(dest_row, textvariable=self.aurora_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(dest_row, text=tr("browse"), command=self.browse).pack(side=tk.LEFT)
        msg = tk.Label(dlg, text=tr("alt_searching"), bg=th["bg"], fg=th["muted"])
        msg.pack(pady=2, fill=tk.X)
        bf = ttk.Frame(dlg)
        bf.pack(pady=(0, 4))
        ttk.Button(bf, text=tr("alt_install"), command=self._alt_install_sel).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("close"), command=self._close_alt_dlg).pack(side=tk.LEFT, padx=4)
        preview_frame = tk.Frame(
            dlg, width=200, height=260, bd=1, relief=tk.SUNKEN, bg=th["field"]
        )
        preview_frame.pack_propagate(False)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        self._alt_preview = tk.Label(
            preview_frame, text=tr("alt_none"), bg=th["field"], fg=th["muted"], image=None,
        )
        self._alt_preview.pack(fill=tk.BOTH, expand=True)
        self._alt_dlg = dlg
        self._alt_lb = lb
        self._alt_msg = msg
        self._alt_g = g
        dlg.protocol("WM_DELETE_WINDOW", self._close_alt_dlg)
        threading.Thread(target=self._alt_fetch, args=(g,), daemon=True).start()

    def _close_alt_dlg(self):
        if self._alt_dlg is not None:
            try:
                self._alt_dlg.destroy()
            except tk.TclError:
                pass
        self._alt_dlg = None
        self._alt_lb = None
        self._alt_msg = None
        self._alt_preview = None
        self._alt_photo = None
        self._alt_g = None

    def _alt_fetch(self, g):
        tid = g["tid"]
        try:
            items = self.unity.covers(tid, force=True) or []
        except Exception:
            items = []
        # Homebrews: a Unity indexa a capa por um TitleID interno (pequeno) achado
        # pela busca por NOME (TitleList), não pelo TID sintético/SHA1 nem pelo TID do XEX.
        if not items and g:
            for q in homebrew_search_queries(g):
                real = self.unity.resolve_title_tid(q)
                if real and real.upper() != tid.upper():
                    items = self.unity.covers(real, force=True) or []
                    if items:
                        break
        if not items:
            items = [
                {
                    "name": tr("alt_official"),
                    "official": True,
                    "rating": "0",
                    "source": "x360db",
                }
            ]
        self._alt_items = items
        self.queue.put("__alt_populate__")

    def _alt_populate(self):
        if self._alt_dlg is None or not self._alt_dlg.winfo_exists():
            return
        self._alt_lb.delete(0, tk.END)
        if not self._alt_items:
            self._alt_msg.configure(text=tr("alt_none_found"))
            return
        for it in self._alt_items:
            self._alt_lb.insert(tk.END, self.unity.label(it))
        scored = [
            (0 if it.get("official") else 1, -unity_rating(it), i)
            for i, it in enumerate(self._alt_items)
        ]
        best = min(scored)[2]
        self._alt_lb.selection_set(best)
        self._alt_lb.activate(best)
        self._alt_lb.see(best)
        real = [it for it in self._alt_items if it.get("source") != "x360db"]
        if real:
            self._alt_msg.configure(text=tr("alt_count", len(self._alt_items)))
        else:
            self._alt_msg.configure(text=tr("alt_unity_empty"))
        self._alt_select()

    def _alt_select(self, _event=None):
        if self._alt_lb is None:
            return
        sel = self._alt_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self._alt_items[idx]
        if self._alt_msg is not None:
            self._alt_msg.configure(text=tr("alt_loading"))
        if self._alt_preview is not None:
            self._alt_preview.configure(image="", text=tr("alt_loading"))
        threading.Thread(target=self._alt_preview_fetch, args=(item, idx), daemon=True).start()

    def _alt_preview_fetch(self, item, idx):
        try:
            b = self.unity.cover_bytes(item, small=True)
        except Exception:
            b = None
        self._alt_preview_item = (idx, b)
        self.queue.put("__alt_preview__")

    def _alt_preview_show(self):
        d = self._alt_dlg
        if d is None or not d.winfo_exists() or self._alt_lb is None or self._alt_preview is None:
            return
        idx, b = self._alt_preview_item
        cur = self._alt_lb.curselection()
        if not cur or cur[0] != idx:
            return
        if not b:
            self._alt_preview.configure(image="", text=tr("alt_no_img"))
            if self._alt_msg is not None:
                self._alt_msg.configure(text=tr("alt_no_preview"))
            return
        try:
            img = Image.open(io.BytesIO(b)).convert("RGBA")
            img = cover_fit(img, 200, 260)
            ph = ImageTk.PhotoImage(img)
            self._alt_photo = ph
            self._alt_preview.configure(image=ph, text="")
            if self._alt_msg is not None:
                self._alt_msg.configure(text=tr("alt_loaded"))
        except Exception:
            self._alt_preview.configure(image="", text=tr("alt_no_preview"))

    def _alt_install_sel(self):
        if self.busy or self._alt_lb is None or self._alt_g is None:
            return
        sel = self._alt_lb.curselection()
        if not sel:
            if self._alt_msg is not None:
                self._alt_msg.configure(text=tr("alt_pick_first"))
            return
        item = self._alt_items[sel[0]]
        g = self._alt_g
        path = self.aurora_path.get().strip().strip('"')
        if self._alt_msg is not None:
            self._alt_msg.configure(text=tr("downloading"))
        self.set_busy(True)

        def _run():
            try:
                if item.get("source") == "x360db":
                    b = self.db.download_artwork(g["tid"], "boxart")
                else:
                    b = self.unity.cover_bytes(item)
                if not b:
                    self.log(tr("unity_fetch_fail"))
                    self.queue.put("__alt_installed__:f")
                    return
                if is_black_cover(b):
                    self.log(tr("unity_black_cover"))
                    self.queue.put("__alt_installed__:f")
                    return
                img = box_render(Image.open(io.BytesIO(b)), self.cover_format)
                self.install_cover_img(path, g, img)
                self.log(
                    tr("logs_alt_installed", self.db.title_name(g["tid"]), g["tid"])
                )
                self.queue.put("__alt_installed__:t")
            except Exception as exc:
                self.log(tr("logs_alt_err", exc))
                self.queue.put("__alt_installed__:f")

        threading.Thread(target=_run, daemon=True).start()


def main():
    if "--selftest" in sys.argv:
        selftest()
        return 0
    root = tk.Tk()
    set_window_icon(root)
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())