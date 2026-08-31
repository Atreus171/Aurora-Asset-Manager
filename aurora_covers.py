import io
import json
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
    "show_debug_button": False,
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
        "scan_first": "Digitalize os jogos primeiro.",
        "pick_art": "Marque pelo menos um tipo de arte (capa, background, ícone, banner ou screenshots).",
        "pick_aurora": "Escolha a pasta raiz do Aurora primeiro.",
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
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Pesquisar título...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Buscar títulos automaticamente (XboxUnity)",
        "show_debug_button": "Mostrar botão Debug DB",
        "m_search": "Pesquisar título...",
        "m_rename": "Renomear jogo",
        "rename_prompt": "Novo nome para %s (%s):",
        "renamed": "Jogo %s renomeado para: %s",
        "ok": "OK",
        "add_game": "Adicionar jogo...",
        "add_game_tid": "Title ID (8 dígitos hex):",
        "add_game_name": "Nome (opcional):",
        "add_game_mkdir": "Criar pasta GameData no HD",
        "add_game_bad_tid": "Title ID inválido (use 8 dígitos hex, ex.: 5841120F).",
        "add_game_exists": "Este jogo já está na lista.",
        "add_game_need_name": "Informe um nome para criar a pasta.",
        "add_game_added": "Jogo adicionado: %s (%s)",
        "rename_ftp_start": "Renomeando a pasta no console via FTP...",
        "rename_ftp_ok": "Pasta renomeada no console: %s",
        "rename_ftp_err": "Não foi possível renomear no console: %s",
        "m_open_folder": "Abrir pasta do jogo",
        "set_ftp": "Enviar por FTP (console):",
        "ftp_host_lbl": "IP do console:",
        "ftp_port_lbl": "Porta:",
        "ftp_user_lbl": "Usuário:",
        "ftp_pass_lbl": "Senha:",
        "ftp_base_lbl": "Pasta remota (GameData):",
        "ftp_send": "Enviar por FTP",
        "ftp_sending": "Enviando para o console via FTP...",
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
    },
    "en": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
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
        "scan_first": "Scan the games first.",
        "pick_art": "Check at least one art type (cover, background, icon, banner or screenshots).",
        "pick_aurora": "Choose the Aurora root folder first.",
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
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Search title...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Auto-search titles (XboxUnity)",
        "show_debug_button": "Show Debug DB button",
        "m_search": "Search title...",
        "m_rename": "Rename game",
        "rename_prompt": "New name for %s (%s):",
        "renamed": "Game %s renamed to: %s",
        "ok": "OK",
        "add_game": "Add game...",
        "add_game_tid": "Title ID (8 hex digits):",
        "add_game_name": "Name (optional):",
        "add_game_mkdir": "Create GameData folder on HD",
        "add_game_bad_tid": "Invalid Title ID (use 8 hex digits, e.g. 5841120F).",
        "add_game_exists": "This game is already in the list.",
        "add_game_need_name": "Enter a name to create the folder.",
        "add_game_added": "Game added: %s (%s)",
        "rename_ftp_start": "Renaming folder on the console via FTP...",
        "rename_ftp_ok": "Folder renamed on the console: %s",
        "rename_ftp_err": "Could not rename on the console: %s",
        "m_open_folder": "Open game folder",
        "set_ftp": "Send via FTP (console):",
        "ftp_host_lbl": "Console IP:",
        "ftp_port_lbl": "Port:",
        "ftp_user_lbl": "User:",
        "ftp_pass_lbl": "Password:",
        "ftp_base_lbl": "Remote folder (GameData):",
        "ftp_send": "Send via FTP",
        "ftp_sending": "Sending to the console via FTP...",
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
    },
    "es": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
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
        "scan_first": "Escanee los juegos primero.",
        "pick_art": "Marque al menos un tipo de arte (portada, fondo, icono, banner o screenshots).",
        "pick_aurora": "Elija la carpeta raíz de Aurora primero.",
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
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Buscar título...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Buscar títulos automaticamente (XboxUnity)",
        "show_debug_button": "Mostrar botón Debug DB",
        "m_search": "Buscar título...",
        "m_rename": "Renombrar juego",
        "rename_prompt": "Nuevo nombre para %s (%s):",
        "renamed": "Juego %s renombrado a: %s",
        "ok": "Aceptar",
        "add_game": "Agregar juego...",
        "add_game_tid": "Title ID (8 dígitos hex):",
        "add_game_name": "Nombre (opcional):",
        "add_game_mkdir": "Crear carpeta GameData en el disco",
        "add_game_bad_tid": "Title ID no válido (usa 8 dígitos hex, ej.: 5841120F).",
        "add_game_exists": "Este juego ya está en la lista.",
        "add_game_need_name": "Introduce un nombre para crear la carpeta.",
        "add_game_added": "Juego agregado: %s (%s)",
        "rename_ftp_start": "Renombrando carpeta en la consola por FTP...",
        "rename_ftp_ok": "Carpeta renombrada en la consola: %s",
        "rename_ftp_err": "No se pudo renombrar en la consola: %s",
        "m_open_folder": "Abrir carpeta del juego",
        "set_ftp": "Enviar por FTP (consola):",
        "ftp_host_lbl": "IP de la consola:",
        "ftp_port_lbl": "Puerto:",
        "ftp_user_lbl": "Usuario:",
        "ftp_pass_lbl": "Contraseña:",
        "ftp_base_lbl": "Carpeta remota (GameData):",
        "ftp_send": "Enviar por FTP",
        "ftp_sending": "Enviando a la consola por FTP...",
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
    },
    "fr": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
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
        "scan_first": "Scannez les jeux d'abord.",
        "pick_art": "Cochez au moins un type d'art (jaquette, fond, icône, bannière ou captures).",
        "pick_aurora": "Choisissez le dossier racine d'Aurora d'abord.",
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
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "Rechercher titre...",
        "debug_db": "Debug DB",
        "auto_search_titles": "Recherche auto des titres (XboxUnity)",
        "show_debug_button": "Afficher bouton Debug DB",
        "m_search": "Rechercher titre...",
        "m_rename": "Renommer le jeu",
        "rename_prompt": "Nouveau nom pour %s (%s):",
        "renamed": "Jeu %s renommé en: %s",
        "ok": "OK",
        "add_game": "Ajouter un jeu...",
        "add_game_tid": "Title ID (8 chiffres hex) :",
        "add_game_name": "Nom (optionnel) :",
        "add_game_mkdir": "Créer le dossier GameData sur le disque",
        "add_game_bad_tid": "Title ID invalide (utilisez 8 chiffres hex, ex. : 5841120F).",
        "add_game_exists": "Ce jeu est déjà dans la liste.",
        "add_game_need_name": "Entrez un nom pour créer le dossier.",
        "add_game_added": "Jeu ajouté : %s (%s)",
        "rename_ftp_start": "Renommage du dossier sur la console via FTP...",
        "rename_ftp_ok": "Dossier renommé sur la console : %s",
        "rename_ftp_err": "Impossible de renommer sur la console : %s",
        "m_open_folder": "Ouvrir le dossier du jeu",
        "set_ftp": "Envoyer par FTP (console):",
        "ftp_host_lbl": "IP de la console:",
        "ftp_port_lbl": "Port:",
        "ftp_user_lbl": "Utilisateur:",
        "ftp_pass_lbl": "Mot de passe:",
        "ftp_base_lbl": "Dossier distant (GameData):",
        "ftp_send": "Envoyer par FTP",
        "ftp_sending": "Envoi vers la console par FTP...",
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
    },
    "ja": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
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
        "scan_first": "まずゲームをスキャンしてください。",
        "pick_art": "アートタイプを少なくとも1つ選択してください (カバー, 背景, アイコン, バナー, スクリーンショット)。",
        "pick_aurora": "まずAuroraのルートフォルダを選択してください。",
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
        "sort_asc": "A-Z",
        "sort_desc": "Z-A",
        "search_title": "タイトルを検索...",
        "debug_db": "DB デバッグ",
        "auto_search_titles": "タイトル自動検索 (XboxUnity)",
        "show_debug_button": "Debug DB ボタンを表示",
        "m_search": "タイトルを検索...",
        "m_rename": "ゲーム名を変更",
        "rename_prompt": "%s (%s) の新しい名前:",
        "renamed": "ゲーム %s を %s にリネームしました。",
        "ok": "OK",
        "add_game": "ゲームを追加...",
        "add_game_tid": "Title ID（8桁の16進数）:",
        "add_game_name": "名前（任意）:",
        "add_game_mkdir": "HDにGameDataフォルダを作成",
        "add_game_bad_tid": "Title IDが無効です（8桁の16進数、例: 5841120F）。",
        "add_game_exists": "このゲームはすでにリストにあります。",
        "add_game_need_name": "フォルダを作成するには名前を入力してください。",
        "add_game_added": "ゲームを追加しました: %s (%s)",
        "rename_ftp_start": "FTPで本体のフォルダ名を変更しています...",
        "rename_ftp_ok": "本体のフォルダ名を変更しました: %s",
        "rename_ftp_err": "本体でフォルダ名を変更できませんでした: %s",
        "m_open_folder": "ゲームフォルダを開く",
        "set_ftp": "FTPで送信 (コンソール):",
        "ftp_host_lbl": "コンソールIP:",
        "ftp_port_lbl": "ポート:",
        "ftp_user_lbl": "ユーザー:",
        "ftp_pass_lbl": "パスワード:",
        "ftp_base_lbl": "リモートフォルダ (GameData):",
        "ftp_send": "FTPで送信",
        "ftp_sending": "コンソールにFTPで送信中...",
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
    },
    "ru": {
        "title": "Aurora Asset Manager",
        "unity_status": "XboxUnity:",
        "x360db_status": "x360db:",
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
        "scan_first": "Сначала отсканируйте игры.",
        "pick_art": "Выберите хотя бы один тип арта (обложка, фон, иконка, баннер или скриншоты).",
        "pick_aurora": "Сначала выберите корневую папку Aurora.",
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
        "sort_asc": "А-Я",
        "sort_desc": "Я-А",
        "search_title": "Поиск названия...",
        "debug_db": "Отладка БД",
        "auto_search_titles": "Автопоиск названий (XboxUnity)",
        "show_debug_button": "Показать кнопку Debug DB",
        "m_search": "Поиск названия...",
        "m_rename": "Переименовать игру",
        "rename_prompt": "Новое имя для %s (%s):",
        "renamed": "Игра %s переименована в: %s",
        "ok": "OK",
        "add_game": "Добавить игру...",
        "add_game_tid": "Title ID (8 шестнадцатеричных цифр):",
        "add_game_name": "Название (необязательно):",
        "add_game_mkdir": "Создать папку GameData на диске",
        "add_game_bad_tid": "Неверный Title ID (используйте 8 шестнадцатеричных цифр, напр. 5841120F).",
        "add_game_exists": "Эта игра уже есть в списке.",
        "add_game_need_name": "Введите название, чтобы создать папку.",
        "add_game_added": "Игра добавлена: %s (%s)",
        "rename_ftp_start": "Переименование папки на консоли по FTP...",
        "rename_ftp_ok": "Папка на консоли переименована в: %s",
        "rename_ftp_err": "Не удалось переименовать на консоли: %s",
        "m_open_folder": "Открыть папку игры",
        "set_ftp": "Отправить по FTP (консоль):",
        "ftp_host_lbl": "IP консоли:",
        "ftp_port_lbl": "Порт:",
        "ftp_user_lbl": "Пользователь:",
        "ftp_pass_lbl": "Пароль:",
        "ftp_base_lbl": "Удаленная папка (GameData):",
        "ftp_send": "Отправить по FTP",
        "ftp_sending": "Отправка на консоль по FTP...",
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


def fetch_bytes(url, timeout=40, attempts=2):
    for _ in range(attempts):
        try:
            req = urllib.request.Request(url, headers=USER_AGENT)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if resp.status == 200 and len(data) > 0:
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
        return self.alt_ids.get(tid.upper(), tid.upper())

    def title_name(self, tid):
        info = self.titles.get(tid.upper())
        if info:
            return info["title"]
        return tid.upper()

    def artwork_url(self, tid, kind):
        return X360DB_RAW + "titles/" + self.canonical(tid) + "/artwork/" + kind + ".jpg"

    def info(self, tid):
        tid = self.canonical(tid)
        if tid in self.info_cache:
            return self.info_cache[tid]
        info = download_json(X360DB_RAW + "titles/" + tid + "/info.json")
        self.info_cache[tid] = info or {}
        return self.info_cache[tid]

    def download_artwork(self, tid, kind):
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
                if isinstance(data2, dict) and isinstance(data2.get("covers"), list):
                    items = [it for it in data2["covers"] if isinstance(it, dict)]
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


def cover_fill(image, target_w, target_h):
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGBA")
    scale = max(target_w / image.width, target_h / image.height)
    nw = max(target_w, round(image.width * scale))
    nh = max(target_h, round(image.height * scale))
    image = image.resize((nw, nh), Image.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return image.crop((left, top, left + target_w, top + target_h))


def cover_fit(image, target_w, target_h):
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGBA")
    image.thumbnail((target_w, target_h), Image.LANCZOS)
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
    """Lê o content.db do Aurora para obter nomes reais dos jogos."""
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
    
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        
        # Tenta descobrir a tabela e colunas corretas
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        _log(f"  [DB] Tabelas encontradas: {tables}")
        
        # Tenta várias tabelas possíveis (ordem de prioridade baseada no debug)
        content_table = None
        for t in ["ContentItems", "Content", "Games", "GameList", "Titles", "ContentList"]:
            if t in tables:
                content_table = t
                _log(f"  [DB] Usando tabela: {content_table}")
                break
        
        if not content_table:
            _log(f"  [DB] Nenhuma tabela conhecida encontrada")
            conn.close()
            return games
        
        # Descobre colunas disponíveis
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({content_table})")]
        _log(f"  [DB] Colunas em {content_table}: {cols}")
        
        # Para ContentItems, usa colunas específicas conhecidas
        if content_table == "ContentItems":
            query = """
                SELECT TitleId, TitleName, Directory, MediaId, ContentType, FileType
                FROM ContentItems
                WHERE TitleId IS NOT NULL AND TitleId != 0
                ORDER BY TitleName
            """
        else:
            # Mapeia colunas esperadas
            col_tid = next((c for c in cols if c.lower() in ("titleid", "tid", "title_id")), "TitleID")
            col_title = next((c for c in cols if c.lower() in ("title", "name", "gamename", "displayname", "titlename")), "Title")
            col_dbid = next((c for c in cols if c.lower() in ("databaseid", "dbid", "db_id")), "DatabaseID")
            col_mediaid = next((c for c in cols if c.lower() in ("mediaid", "media_id")), "MediaID")
            col_path = next((c for c in cols if c.lower() in ("path", "gamepath", "location", "directory", "dir")), "Path")
            col_type = next((c for c in cols if c.lower() in ("titletype", "type", "gametype", "title_type", "contenttype", "filetype")), "TitleType")
            
            _log(f"  [DB] Mapeamento: tid={col_tid}, title={col_title}, type={col_type}")
            
            # Tenta query sem filtro de tipo primeiro (mais robusto)
            query = f"""
                SELECT {col_tid}, {col_title}, {col_dbid}, {col_mediaid}, {col_path}, {col_type}
                FROM {content_table}
                ORDER BY {col_title}
            """
        
        _log(f"  [DB] Query: {query}")
        cur = conn.execute(query)
        count = 0
        for row in cur:
            count += 1
            # Para ContentItems, TitleId é integer
            if content_table == "ContentItems":
                tid_int = row["TitleId"]
                if tid_int is None or tid_int == 0:
                    continue
                tid = f"{tid_int:08X}"
                title = (row["TitleName"] or "").strip()
                path = row["Directory"]
            else:
                tid = (row[col_tid] or "").upper()
                if not tid or tid == "00000000":
                    continue
                title = (row[col_title] or "").strip()
                path = row[col_path]
            
            if not title:
                continue
            dname = title
            folder = None
            rel = re.sub(r"^(?:[A-Za-z]+:)?[\\/]*", "", (path or "").strip())
            for _base in (root, os.path.join(root, "Aurora")):
                _cand = os.path.join(_base, rel) if rel else ""
                if _cand and os.path.isdir(_cand):
                    folder = _cand
                    break
            has_cover = False
            if folder:
                for fn in os.listdir(folder):
                    if fn.upper().startswith("GC") and has_cover_image(os.path.join(folder, fn)):
                        has_cover = True
                        break
            games.append({
                "folder": folder,
                "tid": tid,
                "folder_name": os.path.basename(folder) if folder else tid,
                "dname": dname,
                "has_cover": has_cover,
            })
        conn.close()
        _log(f"  [DB] Total jogos carregados: {len(games)} (de {count} linhas)")
    except Exception as e:
        _log(f"  [DB] Erro ao ler banco: {e}")
    return games


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
        pattern = re.compile(r"^([0-9A-Fa-f]{8})_(.+)")
        for name in sorted(os.listdir(gamedata)):
            m = pattern.match(name)
            if not m:
                continue
            tid = m.group(1).upper()
            if tid == "00000000":
                continue
            dname = m.group(2).strip()
            # Aplica nome customizado se existir
            if tid in custom_names:
                dname = custom_names[tid]
            folder = os.path.join(gamedata, name)
            if not os.path.isdir(folder):
                continue
            has_cover = False
            for file_name in os.listdir(folder):
                full = os.path.join(folder, file_name)
                if not os.path.isfile(full):
                    continue
                if file_name.upper().startswith("GC") and has_cover_image(full):
                    has_cover = True
                    break
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
    import_dir = os.path.join(root, "User", "Import")
    if os.path.isdir(import_dir):
        for tid_dir in os.listdir(import_dir):
            if not re.match(r"^[0-9A-Fa-f]{8}$", tid_dir):
                continue
            tid = tid_dir.upper()
            if tid == "00000000":
                continue
            # Verifica se já temos esse jogo
            if any(g["tid"] == tid for g in games):
                continue
            # Tenta pegar nome customizado
            dname = custom_names.get(tid, tid)
            import_path = os.path.join(import_dir, tid_dir)
            has_cover = False
            if os.path.isdir(import_path):
                for fn in os.listdir(import_path):
                    upper = fn.upper()
                    if upper == "COVER.PNG" or (upper.startswith("GC") and fn.lower().endswith((".png", ".asset"))):
                        if has_cover_image(os.path.join(import_path, fn)):
                            has_cover = True
                            break
            games.append({
                "folder": None,
                "tid": tid,
                "folder_name": tid,
                "dname": dname,
                "has_cover": has_cover,
            })

    # Aplica nomes customizados aos jogos do DB que não têm dname
    for g in games:
        if g["tid"] in custom_names and not g.get("dname"):
            g["dname"] = custom_names[g["tid"]]

    # Deduplicação
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
    log(f"  [SCAN] Total de jogos encontrados: {len(deduped)}")
    return deduped


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


def find_cover_file(folder):
    if not folder or not os.path.isdir(folder):
        return None
    for name in sorted(os.listdir(folder)):
        if name.upper().startswith("GC") and name.lower().endswith(".asset"):
            return os.path.join(folder, name)
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
        "show_debug_button": False,
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
        self._applied_theme = ""
        self.aurora_path = tk.StringVar()
        self.opt_boxart = tk.BooleanVar(value=True)
        self.opt_background = tk.BooleanVar(value=True)
        self.opt_force = tk.BooleanVar(value=False)
        self.opt_backup = tk.BooleanVar(value=True)
        self.opt_icon = tk.BooleanVar(value=True)
        self.opt_banner = tk.BooleanVar(value=True)
        self.opt_screenshots = tk.BooleanVar(value=True)
        self.games = []
        self.worker = None
        self.busy = False
        self.item_to_game = {}
        self._photo = None
        self.preview_cache = {}
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

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        self.btn_scan = ttk.Button(btn_row, text=tr("scan"), command=self.start_scan)
        self.btn_scan.pack(side=tk.LEFT)
        self.btn_add = ttk.Button(btn_row, text=tr("add_game"), command=self.add_game)
        self.btn_add.pack(side=tk.LEFT, padx=(8, 0))
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
        self.btn_sort = ttk.Button(
            btn_row, text=tr("sort_asc"), command=self.toggle_sort
        )
        self.btn_sort.pack(side=tk.LEFT, padx=(8, 0))
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
            self.queue.put("__config_loaded__")
        threading.Thread(target=_run, daemon=True).start()

    def _on_config_loaded(self):
        self.apply_theme()
        self.apply_show_status()
        self.apply_show_log()
        self._paint_status()
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
            self.log("Nomes atualizados via XboxUnity.")

    def _paint_status(self):
        th = THEMES.get(detect_system_theme() if self.theme == "sistema" else self.theme, THEMES["escuro"])
        for status, dot, lbl in (
            (self.unity_status, self.unity_dot, self.unity_lbl),
            (self.x360db_status, self.x360db_dot, self.x360db_lbl),
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
            time.sleep(PING_INTERVAL)

    def theme_loop(self):
        while True:
            time.sleep(15)
            if self.theme == "sistema":
                eff = detect_system_theme()
                if eff != self._applied_theme:
                    self.queue.put("__theme_check__")

    def browse(self):
        # Permite selecionar unidade (drive) ou pasta
        path = filedialog.askdirectory(title=tr("aurora_folder"))
        if not path:
            return
        # Se for uma unidade (ex: X:\), tenta detectar estrutura Aurora automaticamente
        if os.path.splitdrive(path)[1] in ("\\", "/"):
            # É uma raiz de unidade, tenta encontrar estrutura Aurora
            aurora_paths = [
                os.path.join(path, "Aurora"),
                os.path.join(path, "Aurora", "Data", "GameData"),
                os.path.join(path, "Data", "GameData"),
            ]
            for p in aurora_paths:
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
        self.log(tr("canceled"))

    def start_scan(self):
        if self.busy:
            return
        path = self.aurora_path.get().strip().strip('"')
        if not path or not os.path.isdir(path):
            messagebox.showerror(tr("warn"), tr("pick_aurora"))
            return
        self.cancel_event.clear()
        self.set_busy(True)
        threading.Thread(target=self.scan_worker, args=(path,), daemon=True).start()

    def scan_worker(self, path):
        try:
            self.log("Escaneando: %s" % path)
            if not self.db.ready.wait(timeout=30):
                self.log("Aviso: índice do x360db não carregou; sem filtro de DLC/updates.")
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
                    self.log("Ignorados %d TitleIDs de DLC/update (não constam no índice de jogos)." % len(dlc_ids))
                if game_ids:
                    self.log(
                        "Jogos GOD/XDLC no HD sem pasta GameData: %d (serão tratados via Import)"
                        % len(game_ids)
                    )
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
            self.log("Total de jogos: %d" % len(self.games))
            # Busca nomes faltando no XboxUnity em background (se habilitado)
            if self.cfg.get("auto_search_titles", True):
                missing = [g for g in self.games if self.game_title(g) == g["tid"]]
                if missing:
                    self.log("Buscando %d nomes no XboxUnity..." % len(missing))
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
        order = sorted(
            self.games,
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

    def search_title(self):
        g = self.selected_game()
        if not g:
            return
        tid = g["tid"]
        # Busca no x360db
        name = self.db.title_name(tid)
        if name != tid:
            g["dname"] = name
            self.log("Título encontrado no x360db: %s" % name)
            self.refresh_tree()
            return
        # Busca no XboxUnity
        unity_name = self.unity.get_best_title(tid)
        if unity_name:
            g["dname"] = unity_name
            self.log("Título encontrado no XboxUnity: %s" % unity_name)
            self.refresh_tree()
            return
        # Fallback: dname
        if g.get("dname"):
            self.log("Usando nome da pasta: %s" % g["dname"])
            self.refresh_tree()
            return
        self.log("Título não encontrado para %s" % tid)

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
            messagebox.showerror(tr("debug_db"), "content.db não encontrado")
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
            messagebox.showerror(tr("debug_db"), f"Erro: {e}")

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
        # Se tem pasta GameData, renomeia a pasta
        folder = g.get("folder")
        if not folder:
            folder = self.find_gamedata_folder(g["tid"])
        if folder:
            parent = os.path.dirname(folder)
            new_folder = os.path.join(parent, "%s_%s" % (g["tid"], clean))
            try:
                os.rename(folder, new_folder)
            except OSError as exc:
                messagebox.showerror(tr("error"), str(exc))
                return
            g["folder"] = new_folder
            g["folder_name"] = os.path.basename(new_folder)
            self.log("Renamed folder: %s -> %s" % (g["folder_name"], os.path.basename(new_folder)))
        else:
            self.log("  pasta GameData não encontrada para %s; renomeação salva apenas na lista." % g["tid"])
        g["dname"] = clean
        # Salva nome customizado permanentemente
        custom_names = load_custom_names()
        custom_names[g["tid"]] = clean
        save_custom_names(custom_names)
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
        if not g.get("folder"):
            return
        try:
            os.startfile(g["folder"])
        except Exception as e:
            self.log("Erro ao abrir pasta: %s" % e)

    def gamedata_dir(self):
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
        return None

    def add_game(self):
        dlg = tk.Toplevel(self.root)
        dlg.title(tr("add_game"))
        dlg.transient(self.root)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text=tr("add_game_tid")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        v_tid = tk.StringVar()
        e_tid = ttk.Entry(frm, textvariable=v_tid, width=16)
        e_tid.grid(row=0, column=1, sticky="w", pady=(0, 6))
        ttk.Label(frm, text=tr("add_game_name")).grid(row=1, column=0, sticky="w", pady=(0, 6))
        v_name = tk.StringVar()
        e_name = ttk.Entry(frm, textvariable=v_name, width=24)
        e_name.grid(row=1, column=1, sticky="w", pady=(0, 6))
        v_mkdir = tk.BooleanVar(value=self.gamedata_dir() is not None)
        ttk.Checkbutton(frm, text=tr("add_game_mkdir"), variable=v_mkdir).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e")
        res = {"ok": False, "tid": None, "name": None, "mkdir": False}

        def _ok(_event=None):
            res["tid"] = v_tid.get().strip().upper()
            res["name"] = v_name.get().strip()
            res["mkdir"] = v_mkdir.get()
            res["ok"] = True
            dlg.destroy()

        ttk.Button(btns, text=tr("ok"), command=_ok).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text=tr("cancel"), command=dlg.destroy).pack(side=tk.LEFT)
        e_tid.focus_set()
        dlg.bind("<Return>", _ok)
        dlg.grab_set()
        self.root.wait_window(dlg)
        if not res["ok"]:
            return
        tid = res["tid"]
        if not re.match(r"^[0-9A-F]{8}$", tid):
            messagebox.showerror(tr("warn"), tr("add_game_bad_tid"))
            return
        if any(g["tid"] == tid for g in self.games):
            messagebox.showwarning(tr("warn"), tr("add_game_exists"))
            return
        name = res["name"]
        g = {"folder": None, "tid": tid, "folder_name": tid, "dname": name, "has_cover": False}
        if res["mkdir"]:
            if not name:
                messagebox.showwarning(tr("warn"), tr("add_game_need_name"))
                return
            gamedata = self.gamedata_dir()
            if not gamedata:
                gamedata = os.path.join(self.aurora_path.get().strip().strip('"'), "Data", "GameData")
            try:
                fld = os.path.join(gamedata, "%s_%s" % (tid, name))
                os.makedirs(fld, exist_ok=True)
                g["folder"] = fld
                g["folder_name"] = os.path.basename(fld)
                self.log("Pasta GameData criada: %s" % g["folder_name"])
            except OSError as exc:
                messagebox.showerror(tr("error"), str(exc))
                return
        if name:
            custom_names = load_custom_names()
            custom_names[tid] = name
            save_custom_names(custom_names)
        extra = load_extra_games()
        if tid not in extra:
            extra.append(tid)
            save_extra_games(extra)
        self.games.append(g)
        self.log(tr("add_game_added", name or tid, tid))
        self.refresh_tree()

    def selected_game(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.item_to_game.get(sel[0])

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
        if key in self.preview_cache:
            return self.preview_cache[key]
        img = None
        cover_file = find_cover_file(g["folder"])
        if cover_file:
            img = open_cover_image(cover_file)
        if img is None:
            png = os.path.join(
                self.aurora_path.get().strip().strip('"'), "User", "Import", g["tid"], "cover.png"
            )
            if os.path.isfile(png):
                try:
                    img = Image.open(png).convert("RGBA")
                except Exception:
                    img = None
        self.preview_cache[key] = img
        return img

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

    def _format_info(self, info):
        genres = ", ".join(info.get("genre") or [])[:60]
        dev = info.get("developer") or ""
        desc = (info.get("description") or {}).get("short") or ""
        if len(desc) > 180:
            desc = desc[:177] + "..."
        parts = []
        if info.get("release_date"):
            rd = info["release_date"]
            if CURRENT_LANG in ("pt", "es"):
                # Formato dia/mês/ano para PT e ES
                try:
                    # Tenta parsear vários formatos comuns
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(str(rd), fmt)
                            rd = dt.strftime("%d/%m/%Y")
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            parts.append(tr("release_date") + ": " + str(rd))
        if dev:
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
            if game is g:
                self.tree.item(
                    item,
                    values=(g["tid"], self.game_title(g), status),
                )
                return

    def start_download(self):
        if self.busy:
            return
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
        self.cancel_event.clear()
        self.set_busy(True)
        threading.Thread(target=self.download_worker, daemon=True).start()

    def download_worker(self):
        try:
            path = self.aurora_path.get().strip().strip('"')
            targets = [g for g in self.games if self.needs_download(g, path)]
            total = len(targets)
            if total == 0:
                self.log(tr("no_games_notice"))
            done = 0
            for g in targets:
                if self.cancel_event.is_set():
                    self.log(tr("canceled"))
                    break
                done += 1
                self.queue.put("__progress__:%d:%d" % (done, total))
                self.log(
                    "[%d/%d] %s (%s)" % (done, total, self.db.title_name(g["tid"]), g["tid"])
                )
                try:
                    self.download_one(path, g)
                except Exception as exc:
                    self.log("  erro neste jogo: %s" % exc)
                time.sleep(0.4)
            self.log(tr("done_notice"))
            self.queue.put("__refresh_tree__")
        except Exception as exc:
            self.queue.put("Erro: %s" % exc)
        finally:
            self.queue.put("__done__")

    def needs_download(self, g, path):
        if self.opt_force.get():
            return True
        folder = g["folder"]
        base = folder if folder else os.path.join(path, "User", "Import", g["tid"])
        checks = []
        if self.opt_boxart.get():
            checks.append(
                os.path.join(base, "GC%s.asset" % g["tid"])
                if folder
                else os.path.join(base, "cover.png")
            )
        if self.opt_background.get():
            checks.append(
                os.path.join(base, "BK%s.asset" % g["tid"])
                if folder
                else os.path.join(base, "background.png")
            )
        if self.opt_icon.get() or self.opt_banner.get():
            checks.append(
                os.path.join(base, "GL%s.asset" % g["tid"])
                if folder
                else os.path.join(base, "icon.png")
            )
        if self.opt_screenshots.get():
            checks.append(
                os.path.join(base, "SS%s.asset" % g["tid"])
                if folder
                else os.path.join(base, "screenshot1.png")
            )
        return any(not os.path.exists(ck) for ck in checks)

    def download_one(self, path, g):
        tid = g["tid"]
        got = False
        if self.opt_boxart.get():
            got = self.download_kind(path, g, "boxart") or got
        if self.opt_background.get():
            self.download_kind(path, g, "background")
        if self.opt_icon.get():
            self.download_kind(path, g, "icon")
        if self.opt_banner.get():
            self.download_kind(path, g, "banner")
        if self.opt_screenshots.get():
            self.download_kind(path, g, "screenshots")
        if got:
            g["has_cover"] = True

    def get_cover_blob(self, tid):
        try:
            if self.repo == "xboxunity":
                b = self._unity_cover(tid)
                if b:
                    return b
                b = self.db.download_artwork(tid, "boxart")
                if b:
                    return b
                self.log(tr("cover_missing_both"))
                return None
            b = self.db.download_artwork(tid, "boxart")
            if b:
                return b
            b = self._unity_cover(tid)
            if b:
                return b
            self.log(tr("cover_missing_both"))
            return None
        except Exception as exc:
            self.log("  erro ao buscar capa: %s" % exc)
            return None

    def _unity_cover(self, tid):
        items = self.unity.covers(tid)
        if not items:
            if self.unity._down_until > time.time():
                self.log(tr("unity_offline") + " (%s)" % tid)
            else:
                self.log(tr("unity_no_cover", tid))
            return None
        ordered = sorted(
            items,
            key=lambda i: (0 if i.get("official") else 1, -unity_rating(i)),
        )
        for item in ordered[:6]:
            b = self.unity.cover_bytes(item)
            if b:
                return b
        self.log(tr("unity_fallback") + " (%s)" % tid)
        return None

    def download_kind(self, path, g, kind):
        tid = g["tid"]
        try:
            if kind == "boxart":
                blob = self.get_cover_blob(tid)
                if blob:
                    img = box_render(Image.open(io.BytesIO(blob)), self.cover_format)
                    if g["folder"]:
                        self.write_asset(g["folder"], tid, "GC", img, ASSET_TYPE_BOXART)
                    self.write_import(path, tid, "cover.png", img)
                    mark_installed(tid, "boxart")
                    return True
                self.log("  capa não encontrada no repositório.")
                return False
            if kind == "background":
                blob = self.db.download_artwork(tid, "background")
                if blob:
                    img = cover_fill(Image.open(io.BytesIO(blob)), BG_W, BG_H)
                    if g["folder"]:
                        self.write_asset(g["folder"], tid, "BK", img, ASSET_TYPE_BACKGROUND)
                    self.write_import(path, tid, "background.png", img)
                    mark_installed(tid, "background")
                    return True
                self.log("  background não encontrado no x360db.")
                return False
            if kind in ("icon", "banner"):
                slot = ASSET_TYPE_ICON if kind == "icon" else ASSET_TYPE_BANNER
                size = (ICON_W, ICON_H) if kind == "icon" else (BANNER_W, BANNER_H)
                name = "icon" if kind == "icon" else "banner"
                blob = self.db.download_artwork(tid, kind)
                if not blob:
                    self.log("  %s não encontrado no x360db." % name)
                    return False
                new_img = cover_fill(Image.open(io.BytesIO(blob)), *size)
                ok = self.apply_gl_slot(path, g, slot, new_img, name + ".png")
                if ok:
                    mark_installed(tid, kind)
                return ok
            if kind == "screenshots":
                grabs = []
                for url in self.db.gallery_urls(tid)[: self.ss_max]:
                    data = fetch_bytes(url)
                    if not data:
                        continue
                    try:
                        grabs.append(cover_fill(Image.open(io.BytesIO(data)), SS_W, SS_H))
                    except Exception:
                        continue
                if not grabs:
                    self.log("  sem screenshots disponíveis no x360db.")
                    return False
                textures = [(ASSET_TYPE_SCREENSHOT + i, s) for i, s in enumerate(grabs[: self.ss_max])]
                if g["folder"]:
                    self.write_multi_asset(g["folder"], tid, "SS", textures)
                for i, s in enumerate(textures):
                    self.write_import(path, tid, "screenshot%d.png" % (i + 1), s[1])
                mark_installed(tid, "screenshots")
                self.log("  %d screenshots instaladas." % len(textures))
                return True
        except Exception as exc:
            self.log("  erro ao baixar %s: %s" % (kind, exc))
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
        self.log("  gravado %s" % display_path(target))

    def write_import(self, root, tid, name, img):
        import_dir = os.path.join(root, "User", "Import", tid)
        try:
            os.makedirs(import_dir, exist_ok=True)
        except OSError:
            return
        target = os.path.join(import_dir, name)
        try:
            img.save(target, "PNG")
        except OSError:
            return
        self.log("  import alternativo em %s" % display_path(target))

    def install_custom(self, g=None):
        if self.busy:
            return
        if g is None:
            g = self.selected_game()
        if g is None:
            messagebox.showwarning(tr("warn"), tr("pick_game"))
            return
        filetypes = [("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp"), ("Todos", "*.*")]
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
        self.log("Capa personalizada instalada para %s (%s)" % (self.db.title_name(g["tid"]), g["tid"]))
        self.show_preview(g)
        self.update_tree_row(g)

    def install_cover_img(self, path, g, img):
        if g["folder"]:
            self.write_asset(g["folder"], g["tid"], "GC", img, ASSET_TYPE_BOXART)
        self.write_import(path, g["tid"], "cover.png", img)
        mark_installed(g["tid"], "boxart")
        g["has_cover"] = True
        self.preview_cache.pop(g["tid"] + "|" + (g["folder"] or "import"), None)

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
        menu.add_separator()
        menu.add_command(label=tr("m_rename"), command=lambda: self.rename_game(g))
        if g.get("folder"):
            menu.add_command(label=tr("m_open_folder"), command=lambda: self.open_game_folder(g))
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
        dlg.title("Configurações")
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

        show_debug_var = tk.BooleanVar(value=self.cfg.get("show_debug_button", False))
        add_row(tr("show_debug_button"), ttk.Checkbutton(outer, text=tr("show_debug_button"), variable=show_debug_var))

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
                self.cfg.update(
                    theme=self.theme,
                    repo=self.repo,
                    cover_format=self.cover_format,
                    screenshots=self.ss_max,
                    lang=new_lang,
                    show_status=self.show_status,
                    show_log=self.show_log,
                    auto_search_titles=bool(auto_search_var.get()),
                    show_debug_button=bool(show_debug_var.get()),
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
        ttk.Button(bf, text=tr("change_pc"), command=self.pick_selected_kind).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("ftp_send"), command=self.ftp_send_assets).pack(side=tk.LEFT, padx=4)
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

    def load_kind_images(self, g, kind, path):
        imgs = []
        tid = g["tid"]
        folder = g["folder"]
        import_path = os.path.join(path, "User", "Import", tid)
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
                im = _open_image(os.path.join(import_path, "screenshot%d.png" % i))
                if im is None:
                    break
                imgs.append(im)
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
        import_path = os.path.join(path, "User", "Import", tid)
        if kind == "boxart":
            if folder:
                asset = os.path.join(folder, "GC%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, ASSET_TYPE_BOXART)
                        if im:
                            return im
            return _open_image(os.path.join(import_path, "cover.png"))
        if kind == "background":
            if folder:
                asset = os.path.join(folder, "BK%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, ASSET_TYPE_BACKGROUND)
                        if im:
                            return im
            return _open_image(os.path.join(import_path, "background.png"))
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
            return _open_image(os.path.join(import_path, name))
        if kind == "screenshots":
            if folder:
                asset = os.path.join(folder, "SS%s.asset" % tid)
                if os.path.isfile(asset):
                    raw = _read_file(asset)
                    if raw:
                        im = _decode_asset_safe(raw, ASSET_TYPE_SCREENSHOT)
                        if im:
                            return im
            return _open_image(os.path.join(import_path, "screenshot1.png"))
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
            self.log("FTP: %d arquivo(s) enviado(s) para %s." % (n, target))
        except Exception as exc:
            try:
                if ftp is not None:
                    ftp.close()
            except Exception:
                pass
            self.log("  erro FTP: %s" % exc)
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
                raise OSError("FTP: impossível acessar %s (%s)" % (path, exc))
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
        self.log("Baixando %s para %s (%s)..." % (kind, self.db.title_name(g["tid"]), g["tid"]))

        def _run():
            try:
                ok = self.download_kind(path, g, kind)
                self.log("  %s: %s" % (kind, "OK" if ok else "sem sucesso"))
            except Exception as exc:
                self.log("  erro: %s" % exc)
            finally:
                self.queue.put("__assets_refresh__")
                self.queue.put("__preview_refresh__")
                self.queue.put("__refresh_tree__")
                self.queue.put("__done__")

        threading.Thread(target=_run, daemon=True).start()

    def pick_kind_file(self, g, kind):
        if self.busy:
            return
        filetypes = [("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp"), ("Todos", "*.*")]
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
        threading.Thread(target=self._alt_fetch, args=(tid,), daemon=True).start()

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

    def _alt_fetch(self, tid):
        try:
            items = self.unity.covers(tid, force=True) or []
        except Exception:
            items = []
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
            self._alt_preview.configure(image="", text="Sem preview")

    def _alt_install_sel(self):
        if self.busy or self._alt_lb is None or self._alt_g is None:
            return
        sel = self._alt_lb.curselection()
        if not sel:
            if self._alt_msg is not None:
                self._alt_msg.configure(text="Selecione uma capa primeiro.")
            return
        item = self._alt_items[sel[0]]
        g = self._alt_g
        path = self.aurora_path.get().strip().strip('"')
        if self._alt_msg is not None:
            self._alt_msg.configure(text="Baixando...")
        self.set_busy(True)

        def _run():
            try:
                if item.get("source") == "x360db":
                    b = self.db.download_artwork(g["tid"], "boxart")
                else:
                    b = self.unity.cover_bytes(item)
                if not b:
                    self.log("  falha ao baixar a capa do XboxUnity.")
                    self.queue.put("__alt_installed__:f")
                    return
                img = box_render(Image.open(io.BytesIO(b)), self.cover_format)
                self.install_cover_img(path, g, img)
                self.log(
                    "Capa alternativa instalada para %s (%s)."
                    % (self.db.title_name(g["tid"]), g["tid"])
                )
                self.queue.put("__alt_installed__:t")
            except Exception as exc:
                self.log("  erro: %s" % exc)
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