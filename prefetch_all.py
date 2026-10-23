# -*- coding: utf-8 -*-
"""
Fast concurrent cover prefetcher for all library songs.
"""

from concurrent.futures import ThreadPoolExecutor
import sys
import time

import os
APPMUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
if APPMUSIC_DIR not in sys.path:
    sys.path.insert(0, APPMUSIC_DIR)

from covers import _fetch_and_create_cover, get_track_cache_key
from library import scan_library


def prefetch_all():
    tracks = scan_library()
    print(f"Prefetching covers for {len(tracks)} tracks...")

    def fetch_one(t):
        key = get_track_cache_key(t["path"])
        _fetch_and_create_cover(t, key)

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(fetch_one, tracks))

    print("Prefetch completed!")


if __name__ == "__main__":
    t0 = time.time()
    prefetch_all()
    print(f"Elapsed: {time.time() - t0:.2f}s")

