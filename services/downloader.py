# -*- coding: utf-8 -*-
"""
Integrated YouTube Music Downloader for FlowMusic 360.
Uses yt-dlp + FFmpeg (Gyan build) to download playlists/tracks in MP3 320kbps
directly into C:\\Users\\Administrator\\Downloads\\YouTube_Music\\<PlaylistName>
and notifies the Dynamic Island HUD.
"""

import os
import re
import shutil
import sys
import threading
import time

FFMPEG_DIR = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
BASE_DOWNLOAD_DIR = r"C:\Users\Administrator\Downloads\YouTube_Music"

# Active download state tracker
download_state = {
    "is_downloading": False,
    "playlist_name": "",
    "current_file": "",
    "percent": 0.0,
    "completed_count": 0,
    "total_count": 0,
    "error": None,
    "last_log": "",
}


def get_ffmpeg_path() -> str | None:
    if os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg.exe")):
        return FFMPEG_DIR
    which_ffmpeg = shutil.which("ffmpeg.exe")
    if which_ffmpeg:
        return os.path.dirname(which_ffmpeg)
    return None


def sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return cleaned or "Nova Playlist"


def is_valid_youtube_url(url: str) -> bool:
    patterns = [
        r"^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+",
        r"^https?://(?:music\.)?youtube\.com/playlist\?list=[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/watch\?.*list=[\w-]+",
        r"^https?://(?:music\.)?youtube\.com/watch\?.*list=[\w-]+",
        r"^https?://(?:www\.)?youtu\.be/[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^https?://(?:music\.)?youtube\.com/watch\?v=[\w-]+",
    ]
    return any(re.match(p, url.strip()) for p in patterns)


def extract_playlist_id_or_url(text: str) -> str:
    text = text.strip()
    if is_valid_youtube_url(text):
        return text
    # If user provided a raw playlist ID (e.g. PLe9tzpsXhBkc...)
    if re.match(r"^[A-Za-z0-9_-]{12,}$", text):
        return f"https://music.youtube.com/playlist?list={text}"
    return text


def start_download_async(
    url: str,
    folder_name: str | None = None,
    on_progress=None,
    on_finish=None,
    quality_kbps: int = 320,
):
    def worker():
        import yt_dlp

        download_state["is_downloading"] = True
        download_state["error"] = None
        download_state["completed_count"] = 0
        download_state["percent"] = 0.0

        target_url = extract_playlist_id_or_url(url)
        ffmpeg_bin = get_ffmpeg_path()

        # Probe playlist info to get playlist title if folder_name not specified
        ydl_probe_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
        }
        actual_folder = folder_name
        try:
            with yt_dlp.YoutubeDL(ydl_probe_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                if not actual_folder and info:
                    actual_folder = info.get("title") or "YouTube Music"
                if info and "entries" in info:
                    download_state["total_count"] = len(info["entries"])
        except Exception:
            pass

        final_folder_name = sanitize_folder_name(actual_folder or "Nova Playlist")
        download_state["playlist_name"] = final_folder_name
        dest_dir = os.path.join(BASE_DOWNLOAD_DIR, final_folder_name)
        os.makedirs(dest_dir, exist_ok=True)

        def ytdl_progress_hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                pct = (downloaded / total * 100.0) if total > 0 else 0.0
                download_state["percent"] = pct
                fn = os.path.basename(d.get("filename", ""))
                download_state["current_file"] = fn
                if on_progress:
                    try:
                        on_progress(final_folder_name, fn, pct)
                    except Exception:
                        pass
            elif d.get("status") == "finished":
                download_state["completed_count"] += 1
                fn = os.path.basename(d.get("filename", ""))
                download_state["last_log"] = f"Concluído: {fn}"

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(
                dest_dir, "%(playlist_index)02d - %(title)s.%(ext)s"
            ),
            "ignoreerrors": True,
            "no_warnings": False,
            "progress_hooks": [ytdl_progress_hook],
            "sleep_interval": 2,  # Helps prevent rate limits
            "sleep_interval_requests": 1,
            "retries": 3,
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": str(quality_kbps),
                },
                {"key": "FFmpegMetadata", "add_metadata": True},
                {"key": "EmbedThumbnail"},
            ],
        }

        if ffmpeg_bin:
            ydl_opts["ffmpeg_location"] = ffmpeg_bin

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([target_url])
        except Exception as e:
            download_state["error"] = str(e)
        finally:
            download_state["is_downloading"] = False
            if on_finish:
                try:
                    on_finish(
                        final_folder_name,
                        download_state["completed_count"],
                        download_state["error"],
                    )
                except Exception:
                    pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t

