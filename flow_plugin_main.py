# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Flow Launcher Plugin Entry Point.
Features:
- Real Album Cover Art icons for every track
- Instant search across library & playlists
- Favorites command ('m fav') & context menu actions
- Priority queue ('Tocar a Seguir')
- YouTube Music Downloader integration ('m dl')
- Dynamic Island HUD controls ('m hud')
"""

import ctypes
import json
import os
import subprocess
import sys

plugin_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(plugin_dir, "client.py")):
    APPMUSIC_DIR = plugin_dir
elif os.environ.get("FLOWMUSIC_DIR"):
    APPMUSIC_DIR = os.environ.get("FLOWMUSIC_DIR")
else:
    APPMUSIC_DIR = os.path.join(os.path.expanduser("~"), "Documents", "AppMusic")

if APPMUSIC_DIR not in sys.path:
    sys.path.insert(0, APPMUSIC_DIR)

from client import execute_action, get_fast_status
from covers import get_cover_icon_path
from downloader import extract_playlist_id_or_url, is_valid_youtube_url
from library import get_playlists, is_favorite, normalize_text, scan_library, search_tracks

ACTION_KEYWORD = "m"


def get_clipboard_text() -> str:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13

    if not user32.OpenClipboard(None):
        return ""
    try:
        h_glb = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_glb:
            return ""
        p_data = kernel32.GlobalLock(h_glb)
        if not p_data:
            return ""
        try:
            return ctypes.c_wchar_p(p_data).value or ""
        finally:
            kernel32.GlobalUnlock(h_glb)
    except Exception:
        return ""
    finally:
        user32.CloseClipboard()


def make_result(
    title: str,
    subtitle: str,
    icon: str,
    method: str = "",
    params: list | None = None,
    hide: bool = True,
    score: int = 50,
    context_data: dict | None = None,
) -> dict:
    if os.path.isabs(icon):
        ico_path = icon
    elif icon.startswith("assets/"):
        ico_path = icon
    else:
        ico_path = f"assets/{icon}"

    item = {
        "Title": title,
        "SubTitle": subtitle,
        "IcoPath": ico_path,
        "score": score,
    }
    if context_data is not None:
        item["ContextData"] = context_data
    if method:
        item["JsonRPCAction"] = {
            "method": method,
            "parameters": params or [],
            "dontHideAfterAction": not hide,
        }
    return item


class FlowMusicPlugin:
    def query(self, param: str = "") -> list:
        q = param.strip()
        q_norm = normalize_text(q)
        status = get_fast_status()
        tracks = scan_library()

        # 1. Downloader command: "m dl"
        if q_norm == "dl" or q_norm.startswith("dl ") or q_norm.startswith("download"):
            sub_param = ""
            if " " in q:
                sub_param = q.split(" ", 1)[1].strip()
            return self._render_downloader(sub_param, status)

        # 2. Favorites command: "m fav"
        if q_norm in ("fav", "favs", "favoritos", "favoritas") or q_norm.startswith("fav "):
            sub_filter = ""
            if " " in q_norm:
                sub_filter = q_norm.split(" ", 1)[1].strip()
            return self._render_favorites(tracks, status, sub_filter)

        # 3. Playlists browser: "m pl"
        if q_norm == "pl" or q_norm.startswith("pl ") or q_norm.startswith("playlist"):
            sub_filter = ""
            if " " in q_norm:
                sub_filter = q_norm.split(" ", 1)[1].strip()
            return self._render_playlists(tracks, status, sub_filter)

        # 4. Volume command: "m vol"
        if q_norm == "vol" or q_norm.startswith("vol ") or q_norm.startswith("v "):
            parts = q_norm.split()
            if len(parts) >= 2 and parts[1].isdigit():
                val = max(0, min(100, int(parts[1])))
                return [
                    make_result(
                        title=f"🔊 Definir Volume para {val}%",
                        subtitle=f"Volume atual: {status.get('volume', 80)}%  •  Aperte Enter para aplicar",
                        icon="volume.png",
                        method="act_volume",
                        params=[val],
                        hide=True,
                        score=100,
                    )
                ]
            return self._render_volume_presets(status)

        # 5. HUD command: "m hud"
        if q_norm == "hud" or q_norm.startswith("hud "):
            return [
                make_result(
                    title="✨ Mostrar Dynamic Island HUD na Tela",
                    subtitle="Exibe a pílula acrílica com capa do álbum (Atalho: Ctrl+Alt+M)",
                    icon="app.png",
                    method="act_hud",
                    params=[],
                    hide=True,
                    score=100,
                ),
                make_result(
                    title="📐 Alternar Posição da Pílula HUD",
                    subtitle=f"Posição atual: {status.get('hud_position', 'top_center')} (Topo Central / Superior Direito / Inferior Direito)",
                    icon="shuffle.png",
                    method="act_hud_pos",
                    params=[],
                    hide=True,
                    score=95,
                ),
                make_result(
                    title="🎨 Alternar Tema da Ilha (Claro / Escuro)",
                    subtitle=f"Tema atual: {'Opal Glass (Claro)' if load_config().get('theme', 'opal') == 'opal' else 'Obsidian (Escuro)'} - Alterna entre Claro e Escuro",
                    icon="app.png",
                    method="act_toggle_theme",
                    params=[],
                    hide=True,
                    score=92,
                ),
            ]

        # 5b. Theme command: "m theme", "m tema", "m modo", "m dark", "m light"
        if q_norm in ("theme", "tema", "modo", "dark", "light", "claro", "escuro"):
            cur_th = load_config().get("theme", "opal")
            th_lbl = "Opal Glass (Claro)" if cur_th == "opal" else "Obsidian Glass (Escuro)"
            return [
                make_result(
                    title=f"🎨 Alternar Tema da Ilha: {th_lbl}",
                    subtitle="Aperte Enter para alternar instantaneamente entre Tema Claro (Opal) e Tema Escuro (Obsidian)",
                    icon="app.png",
                    method="act_toggle_theme",
                    params=[],
                    hide=False,
                    score=100,
                )
            ]

        # 5c. Music Folders command: "m pasta", "m folder", "m dir", "m add"
        if q_norm.startswith(("pasta", "folder", "dir", "add")):
            parts = query_str.strip().split(maxsplit=1)
            target_path = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
            cfg = load_config()
            curr_dirs = cfg.get("music_dirs", [])

            if target_path:
                if os.path.isdir(target_path):
                    return [
                        make_result(
                            title=f"📁 Adicionar Pasta: {target_path}",
                            subtitle="Aperte Enter para incluir esta pasta na biblioteca e escanear novas faixas",
                            icon="app.png",
                            method="act_add_folder",
                            params=[target_path],
                            hide=False,
                            score=100,
                        )
                    ]
                else:
                    return [
                        make_result(
                            title=f"⚠️ Pasta não encontrada: {target_path}",
                            subtitle="Verifique se o caminho digitado existe no seu computador",
                            icon="app.png",
                            method="",
                            params=[],
                            hide=False,
                            score=100,
                        )
                    ]
            else:
                res = [
                    make_result(
                        title="📁 Gerenciar Pastas de Músicas",
                        subtitle="Digite 'm pasta C:\\Caminho' para adicionar uma nova pasta à biblioteca",
                        icon="app.png",
                        method="",
                        params=[],
                        hide=False,
                        score=100,
                    )
                ]
                for p in curr_dirs:
                    res.append(
                        make_result(
                            title=f"📂 {os.path.basename(p) or p}",
                            subtitle=f"Caminho: {p} (Aperte Enter para abrir no Explorer)",
                            icon="track.png",
                            method="act_open_folder",
                            params=[p],
                            hide=True,
                            score=90,
                        )
                    )
                return res

        # 6. Autostart command: "m startup" or "m autostart"
        if q_norm in ("startup", "autostart", "inicio", "boot"):
            from services.autostart import is_autostart_enabled
            enabled = is_autostart_enabled()
            st = "ATIVADO (Inicia silenciosamente com o PC)" if enabled else "DESATIVADO"
            return [
                make_result(
                    title=f"🪟 Iniciar com o Windows: {st}",
                    subtitle="Aperte Enter para alternar inicialização automática em segundo plano (sem telas pretas)",
                    icon="app.png",
                    method="act_autostart",
                    params=[],
                    hide=False,
                    score=100,
                )
            ]

        # 7. Reload / Rescan command: "m reload" or "m rescan"
        if q_norm in ("reload", "rescan", "refresh", "atualizar"):
            return [
                make_result(
                    title="🔄 Recarregar Biblioteca e Capas",
                    subtitle="Reescaneia as pastas e sincroniza as músicas imediatamente (Enter para aplicar)",
                    icon="app.png",
                    method="act_rescan",
                    params=[],
                    hide=True,
                    score=100,
                )
            ]

        # 8. Direct quick command aliases
        if q_norm in ("n", "next", ">", "prox", "proxima"):
            nxt = status.get("next_track")
            nxt_lbl = f": {nxt['display_title']}" if nxt else ""
            nxt_icon = get_cover_icon_path(nxt) if nxt else "next.png"
            return [
                make_result(
                    title=f"⏭️ Pular para a Próxima Música{nxt_lbl}",
                    subtitle="Atalho Global em Jogo: Ctrl + Alt + Seta Direita",
                    icon=nxt_icon,
                    method="act_next",
                    params=[],
                    hide=True,
                    score=100,
                )
            ]

        if q_norm in ("p", "prev", "<", "ant", "anterior"):
            return [
                make_result(
                    title="⏮️ Voltar para a Música Anterior",
                    subtitle="Atalho Global em Jogo: Ctrl + Alt + Seta Esquerda",
                    icon="prev.png",
                    method="act_prev",
                    params=[],
                    hide=True,
                    score=100,
                )
            ]

        if q_norm in ("pp", "pause", "play", "tocar", "pausar"):
            return [
                make_result(
                    title="⏯️ Alternar Play / Pause",
                    subtitle="Atalho Global em Jogo: Ctrl + Alt + Espaço",
                    icon="play.png",
                    method="act_toggle",
                    params=[],
                    hide=True,
                    score=100,
                )
            ]

        if q_norm in ("sh", "shuffle", "aleatorio"):
            sh_state = "ATIVADO" if status.get("shuffle") else "DESATIVADO"
            return [
                make_result(
                    title=f"🔀 Alternar Modo Aleatório (Atual: {sh_state})",
                    subtitle="Atalho Global em Jogo: Ctrl + Alt + S",
                    icon="shuffle.png",
                    method="act_shuffle",
                    params=[],
                    hide=True,
                    score=100,
                )
            ]

        if q_norm in ("stop", "quit", "sair", "fechar"):
            return [
                make_result(
                    title="⏹️ Parar Reprodutor em Segundo Plano",
                    subtitle="Encerra a reprodução e fecha o motor invisível",
                    icon="pause.png",
                    method="act_stop_daemon",
                    params=[],
                    hide=True,
                    score=100,
                )
            ]

        # 7. Empty query -> Dashboard
        if not q_norm:
            return self._render_dashboard(status, tracks)

        # 8. Search tracks & playlists by query
        return self._render_search(q, tracks, status)

    def _render_dashboard(self, status: dict, tracks: list) -> list:
        results = []
        state = status.get("state", "stopped")
        curr = status.get("current_track")
        nxt = status.get("next_track")
        vol = status.get("volume", 80)
        sh_on = status.get("shuffle", False)
        dl_state = status.get("download_state", {})

        # Active download banner if running
        if dl_state and dl_state.get("is_downloading"):
            pct = dl_state.get("percent", 0.0)
            pl = dl_state.get("playlist_name", "Playlist")
            fn = dl_state.get("current_file", "arquivo...")
            results.append(
                make_result(
                    title=f"📥 Baixando Playlist: {pl} ({pct:.0f}%)",
                    subtitle=f"Faixa atual: {fn}  •  Aperte Enter para ver detalhes",
                    icon="download.png",
                    method="act_change_query",
                    params=[f"{ACTION_KEYWORD} dl", True],
                    hide=False,
                    score=110,
                )
            )

        # 1. Now Playing / Resume Card with real album cover
        if curr:
            is_playing = state == "playing"
            prefix_icon = "🎵 Tocando" if is_playing else "⏸️ Pausado"
            action_hint = "Enter = Pausar" if is_playing else "Enter = Continuar"
            pos_str = status.get("position_str", "00:00")
            dur_str = status.get("duration_str", "00:00")
            sh_str = "ON" if sh_on else "OFF"
            fav_mark = " ❤️" if curr.get("is_favorite") else ""
            cover_icon = get_cover_icon_path(curr)
            results.append(
                make_result(
                    title=f"{prefix_icon}: {curr.get('display_title', curr.get('title'))}{fav_mark}",
                    subtitle=f"⏱️ {pos_str} / {dur_str}  •  📂 {curr.get('playlist')}  •  🔊 {vol}%  •  🔀 {sh_str}  [{action_hint}]",
                    icon=cover_icon,
                    method="act_toggle",
                    params=[],
                    hide=True,
                    score=100,
                    context_data=curr,
                )
            )
        else:
            results.append(
                make_result(
                    title=f"▶️ Tocar Biblioteca ({len(tracks)} músicas prontas)",
                    subtitle="Aperte Enter para tocar ou digite o nome de uma música/playlist",
                    icon="play.png",
                    method="act_toggle",
                    params=[],
                    hide=True,
                    score=100,
                )
            )

        # 2. Next Track (with its album cover)
        nxt_title = f"  →  {nxt['display_title']}" if nxt else ""
        nxt_icon = get_cover_icon_path(nxt) if nxt else "next.png"
        results.append(
            make_result(
                title=f"⏭️ Próxima Faixa{nxt_title}",
                subtitle="Pular música  •  Atalho Global: Ctrl + Alt + ➡️  (ou digite 'm n')",
                icon=nxt_icon,
                method="act_next",
                params=[],
                hide=True,
                score=95,
            )
        )

        # 3. Previous Track
        results.append(
            make_result(
                title="⏮️ Faixa Anterior",
                subtitle="Voltar música  •  Atalho Global: Ctrl + Alt + ⬅️  (ou digite 'm p')",
                icon="prev.png",
                method="act_prev",
                params=[],
                hide=True,
                score=90,
            )
        )

        # 4. Playlists menu (including Favorites)
        playlists = get_playlists(tracks)
        fav_count = len(playlists.get("❤️ Favoritas", []))
        fav_hint = f"  •  ❤️ {fav_count} Favoritas" if fav_count > 0 else ""
        results.append(
            make_result(
                title=f"📂 Playlists ({len(playlists)} pastas  •  Ativa: {status.get('active_playlist', 'Todas')}){fav_hint}",
                subtitle="Aperte Enter para escolher uma playlist inteira  •  Digite 'm pl'",
                icon="playlist.png",
                method="act_change_query",
                params=[f"{ACTION_KEYWORD} pl ", True],
                hide=False,
                score=85,
            )
        )

        # 5. Shuffle & Favorites
        sh_badge = "ATIVADO (ON)" if sh_on else "DESATIVADO (OFF)"
        results.append(
            make_result(
                title=f"🔀 Modo Aleatório: {sh_badge}  •  ❤️ Favoritar: Ctrl+Alt+F",
                subtitle="Enter = Alternar Shuffle  •  Atalho em Jogo: Ctrl + Alt + S",
                icon="shuffle.png",
                method="act_shuffle",
                params=[],
                hide=True,
                score=80,
            )
        )

        # 6. YouTube Downloader entry
        results.append(
            make_result(
                title="📥 Baixar Playlists do YouTube Music ('m dl')",
                subtitle="Baixa álbuns completos em 320kbps MP3 em segundo plano direto para suas pastas",
                icon="download.png",
                method="act_change_query",
                params=[f"{ACTION_KEYWORD} dl", True],
                hide=False,
                score=75,
            )
        )

        # 7. Quick preview of songs with real album art covers!
        for idx, t in enumerate(tracks[:12]):
            cover_icon = get_cover_icon_path(t)
            art_desc = f"{t['artist']} — " if t.get("artist") else ""
            fav_mark = " ❤️" if t.get("is_favorite") else ""
            results.append(
                make_result(
                    title=f"{t['display_title']}{fav_mark}",
                    subtitle=f"{art_desc}📂 {t['playlist']}  •  Enter = Tocar  •  Shift+Enter = Opções",
                    icon=cover_icon,
                    method="act_play_track",
                    params=[t["path"], t["playlist"]],
                    hide=True,
                    score=60 - idx,
                    context_data=t,
                )
            )

        return results

    def _render_downloader(self, sub_param: str, status: dict) -> list:
        results = []
        clip = get_clipboard_text().strip()
        has_url_in_clip = is_valid_youtube_url(clip)

        dl_state = status.get("download_state", {})
        if dl_state and dl_state.get("is_downloading"):
            pct = dl_state.get("percent", 0.0)
            pl = dl_state.get("playlist_name", "Playlist")
            fn = dl_state.get("current_file", "arquivo...")
            results.append(
                make_result(
                    title=f"⏳ Baixando Agora: {pl} ({pct:.0f}%)",
                    subtitle=f"Arquivo atual: {fn}  •  O download continua em segundo plano",
                    icon="download.png",
                    score=100,
                )
            )

        if sub_param:
            parts = sub_param.split()
            url_part = None
            name_part = None

            for p in parts:
                if is_valid_youtube_url(p):
                    url_part = p
                    break

            if url_part:
                remaining = [p for p in parts if p != url_part]
                name_part = " ".join(remaining).strip() if remaining else None
                folder_lbl = name_part or "Nome Automático da Playlist"
                results.append(
                    make_result(
                        title=f"📥 Baixar Playlist: {folder_lbl}",
                        subtitle=f"URL: {url_part[:60]}...  •  Enter para iniciar em 320kbps MP3",
                        icon="download.png",
                        method="act_download",
                        params=[url_part, name_part],
                        hide=True,
                        score=100,
                    )
                )
            elif has_url_in_clip:
                results.append(
                    make_result(
                        title=f"📥 Baixar para a Pasta: '{sub_param}'",
                        subtitle=f"Usando link do Clipboard: {clip[:60]}...  •  [Enter = Começar]",
                        icon="download.png",
                        method="act_download",
                        params=[clip, sub_param],
                        hide=True,
                        score=100,
                    )
                )
            else:
                results.append(
                    make_result(
                        title=f"Cole a URL do YouTube Music após '{sub_param}'",
                        subtitle=f"Exemplo: m dl {sub_param} https://music.youtube.com/playlist?list=...",
                        icon="download.png",
                        score=90,
                    )
                )

        if has_url_in_clip and not (sub_param and is_valid_youtube_url(sub_param)):
            results.append(
                make_result(
                    title="📥 Baixar Playlist Detectada na Área de Transferência",
                    subtitle=f"{clip[:75]}...  •  [Enter = Baixar com nome automático]",
                    icon="download.png",
                    method="act_download",
                    params=[clip, None],
                    hide=True,
                    score=95,
                )
            )

        results.append(
            make_result(
                title="💡 Como usar o Downloader no Flow Launcher",
                subtitle="Copie o link do YouTube Music e digite 'm dl <Nome da Pasta>'",
                icon="app.png",
                score=60,
            )
        )
        return results

    def _render_favorites(self, tracks: list, status: dict, sub_filter: str = "") -> list:
        fav_tracks = [t for t in tracks if t.get("is_favorite")]
        results = []

        if not fav_tracks:
            results.append(
                make_result(
                    title="Nenhuma música marcada como Favorita ainda",
                    subtitle="Enquanto estiver ouvindo, use Ctrl + Alt + F ou Shift + Enter numa música para favoritar!",
                    icon="heart.png",
                    score=100,
                )
            )
            return results

        results.append(
            make_result(
                title=f"▶️ Tocar Playlist ❤️ Favoritas ({len(fav_tracks)} músicas)",
                subtitle="Aperte Enter para tocar todas as suas músicas favoritas",
                icon="heart.png",
                method="act_play_playlist",
                params=["❤️ Favoritas"],
                hide=True,
                score=100,
            )
        )

        curr_path = os.path.normcase(status["current_track"].get("path", "")) if status.get("current_track") else ""
        for idx, t in enumerate(fav_tracks):
            if sub_filter and sub_filter not in normalize_text(t["search_blob"]):
                continue
            is_curr = os.path.normcase(t["path"]) == curr_path
            badge = "  🟢 [TOCANDO]" if is_curr else ""
            cover_icon = get_cover_icon_path(t)
            results.append(
                make_result(
                    title=f"❤️ {t['display_title']}{badge}",
                    subtitle=f"📂 {t['playlist']}  •  Enter = Tocar agora",
                    icon=cover_icon,
                    method="act_play_track",
                    params=[t["path"], "❤️ Favoritas"],
                    hide=True,
                    score=95 - idx,
                    context_data=t,
                )
            )

        return results

    def _render_playlists(self, tracks: list, status: dict, sub_filter: str = "") -> list:
        playlists = get_playlists(tracks)
        results = []

        if not sub_filter or "todas" in sub_filter:
            results.append(
                make_result(
                    title=f"📂 Todas as Músicas ({len(tracks)} faixas)",
                    subtitle="Tocar todas as músicas de todas as pastas",
                    icon="playlist.png",
                    method="act_play_playlist",
                    params=["Todas as Músicas"],
                    hide=True,
                    score=100,
                )
            )

        for idx, (pl_name, pl_tracks) in enumerate(playlists.items()):
            if sub_filter and sub_filter not in normalize_text(pl_name):
                continue
            sample = ", ".join(t["title"] for t in pl_tracks[:3])
            is_active = "  ★ ATIVA" if status.get("active_playlist") == pl_name else ""
            icon_file = "heart.png" if "Favoritas" in pl_name else "playlist.png"
            results.append(
                make_result(
                    title=f"{pl_name} ({len(pl_tracks)} músicas){is_active}",
                    subtitle=f"Inclui: {sample}...  •  [Enter = Tocar Playlist]",
                    icon=icon_file,
                    method="act_play_playlist",
                    params=[pl_name],
                    hide=True,
                    score=95 - idx,
                )
            )
        return results

    def _render_volume_presets(self, status: dict) -> list:
        curr_vol = status.get("volume", 80)
        presets = [
            (100, "Volume Máximo (100%)"),
            (80, "Volume Alto / Padrão (80%)"),
            (60, "Volume Médio / Jogo (60%)"),
            (40, "Volume Baixo / Fundo (40%)"),
            (20, "Volume Sussurro / Estudo (20%)"),
        ]
        results = []
        for idx, (val, desc) in enumerate(presets):
            mark = "  ★ ATUAL" if curr_vol == val else ""
            results.append(
                make_result(
                    title=f"🔊 {val}% — {desc}{mark}",
                    subtitle="Ou digite 'm vol <0-100>' para um valor exato  •  Atalho: Ctrl+Alt+⬆️/⬇️",
                    icon="volume.png",
                    method="act_volume",
                    params=[val],
                    hide=True,
                    score=100 - idx,
                )
            )
        return results

    def _render_search(self, query: str, tracks: list, status: dict) -> list:
        results = []
        q_norm = normalize_text(query)

        # Check playlist match
        playlists = get_playlists(tracks)
        for pl_name, pl_tracks in playlists.items():
            if q_norm in normalize_text(pl_name):
                results.append(
                    make_result(
                        title=f"📂 Tocar Playlist: {pl_name} ({len(pl_tracks)} músicas)",
                        subtitle="Aperte Enter para iniciar esta playlist completa",
                        icon="heart.png" if "Favoritas" in pl_name else "playlist.png",
                        method="act_play_playlist",
                        params=[pl_name],
                        hide=True,
                        score=98,
                    )
                )

        matched = search_tracks(query, tracks, limit=30)
        curr_path = os.path.normcase(status["current_track"].get("path", "")) if status.get("current_track") else ""

        for idx, t in enumerate(matched):
            is_curr = os.path.normcase(t["path"]) == curr_path
            badge = "  🟢 [TOCANDO]" if is_curr else ""
            fav_mark = " ❤️" if t.get("is_favorite") else ""
            cover_icon = get_cover_icon_path(t)
            art_desc = f"{t['artist']} — " if t.get("artist") else ""
            results.append(
                make_result(
                    title=f"{t['display_title']}{fav_mark}{badge}",
                    subtitle=f"{art_desc}📂 {t['playlist']}  •  Enter = Tocar  •  Shift+Enter = Opções",
                    icon=cover_icon,
                    method="act_play_track",
                    params=[t["path"], t["playlist"]],
                    hide=True,
                    score=90 - idx,
                    context_data=t,
                )
            )

        if not results:
            results.append(
                make_result(
                    title=f"Nenhuma música encontrada para '{query}'",
                    subtitle="Aperte Enter para buscar como playlist ou atualizar a biblioteca",
                    icon="app.png",
                    method="act_rescan",
                    params=[],
                    hide=True,
                    score=50,
                )
            )
        return results

    def context_menu(self, data) -> list:
        if not isinstance(data, dict) or "path" not in data:
            return []
        path = data["path"]
        pl = data.get("playlist", "Todas as Músicas")
        title = data.get("display_title", data.get("title", "Música"))
        is_fav = is_favorite(path)
        fav_action_title = "💔 Remover das Favoritas" if is_fav else "❤️ Adicionar às Favoritas"
        cover_icon = get_cover_icon_path(data)

        return [
            make_result(
                title=f"▶️ Tocar '{title}' agora",
                subtitle=f"Inicia a reprodução na playlist '{pl}'",
                icon=cover_icon,
                method="act_play_track",
                params=[path, pl],
                hide=True,
            ),
            make_result(
                title="⏭️ Tocar a Seguir (Fila Prioritária)",
                subtitle="Esta música será a próxima a tocar após a atual terminar",
                icon="next.png",
                method="act_enqueue_next",
                params=[path],
                hide=True,
            ),
            make_result(
                title=fav_action_title,
                subtitle="Alternar status de favorita  •  Atalho Global em reprodução: Ctrl + Alt + F",
                icon="heart.png",
                method="act_toggle_fav_path",
                params=[path],
                hide=True,
            ),
            make_result(
                title=f"📂 Tocar toda a playlist '{pl}' do início",
                subtitle="Reproduz todas as faixas desta pasta",
                icon="playlist.png",
                method="act_play_playlist",
                params=[pl],
                hide=True,
            ),
            make_result(
                title="📁 Mostrar arquivo no Windows Explorer",
                subtitle=path,
                icon="app.png",
                method="act_open_folder",
                params=[path],
                hide=True,
            ),
        ]

    # --- Action handlers called by Flow Launcher JSON-RPC ---
    def act_play_track(self, path: str, playlist: str = ""):
        execute_action({"cmd": "play_track", "path": path, "playlist": playlist})

    def act_enqueue_next(self, path: str):
        execute_action({"cmd": "enqueue_next", "path": path})

    def act_toggle_fav_path(self, path: str):
        from library import toggle_favorite
        toggle_favorite(path)
        execute_action({"cmd": "rescan"})

    def act_play_playlist(self, playlist: str):
        execute_action({"cmd": "play_playlist", "playlist": playlist})

    def act_download(self, url: str, folder_name: str | None = None):
        execute_action({"cmd": "download_playlist", "url": url, "name": folder_name})

    def act_toggle(self):
        execute_action({"cmd": "toggle"})

    def act_next(self):
        execute_action({"cmd": "next"})

    def act_prev(self):
        execute_action({"cmd": "prev"})

    def act_shuffle(self):
        execute_action({"cmd": "shuffle"})

    def act_repeat(self):
        execute_action({"cmd": "repeat"})

    def act_volume(self, value: int):
        execute_action({"cmd": "volume", "value": int(value)})

    def act_hud(self):
        execute_action({"cmd": "hud"})

    def act_hud_pos(self):
        execute_action({"cmd": "hud_pos"})

    def act_toggle_theme(self):
        execute_action({"cmd": "toggle_theme"})

    def act_add_folder(self, folder_path: str):
        if os.path.isdir(folder_path):
            cfg = load_config()
            dirs = cfg.get("music_dirs", [])
            norm_target = os.path.normpath(folder_path)
            if not any(os.path.normpath(d) == norm_target for d in dirs):
                dirs.append(folder_path)
                cfg["music_dirs"] = dirs
                save_config(cfg)
                execute_action({"cmd": "rescan"})

    def act_autostart(self):
        execute_action({"cmd": "autostart", "action": "toggle"})

    def act_rescan(self):
        execute_action({"cmd": "rescan"})

    def act_stop_daemon(self):
        execute_action({"cmd": "stop_daemon"})

    def act_open_folder(self, filepath: str):
        if os.path.exists(filepath):
            subprocess.Popen(["explorer.exe", f"/select,{os.path.normpath(filepath)}"])

    def act_change_query(self, new_query: str, requery: bool = True):
        print(
            json.dumps(
                {
                    "method": "Flow.Launcher.ChangeQuery",
                    "parameters": [new_query, requery],
                }
            )
        )


def main():
    plugin = FlowMusicPlugin()
    rpc_request = {"method": "query", "parameters": [""]}
    if len(sys.argv) > 1:
        try:
            rpc_request = json.loads(sys.argv[1])
        except Exception:
            pass

    method_name = rpc_request.get("method", "query")
    params = rpc_request.get("parameters", [])

    fn = getattr(plugin, method_name, None)
    if fn is not None:
        res = fn(*params)
        if method_name in ("query", "context_menu"):
            sys.stdout.buffer.write(
                json.dumps({"result": res or []}, ensure_ascii=False).encode("utf-8")
            )
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
