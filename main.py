import os
from pathlib import Path

from dotenv import load_dotenv
from mutagen.flac import FLAC
from mutagen.id3 import ID3, POPM
from plexapi.server import PlexServer

load_dotenv()

BASE_URL = os.getenv("PLEX_URL")
if not BASE_URL:
    raise ValueError("PLEX_URL environment variable not set")
TOKEN = os.getenv("PLEX_TOKEN")
if not TOKEN:
    raise ValueError("PLEX_TOKEN environment variable not set")
LIBRARY_NAME = os.getenv("PLEX_LIBRARY")
if not LIBRARY_NAME:
    raise ValueError("PLEX_LIBRARY environment variable not set")
MUSIC_ROOT = os.getenv("PATH_LIBRARY")
if not MUSIC_ROOT:
    raise ValueError("PATH_LIBRARY environment variable not set")
MUSIC_ROOT = Path(MUSIC_ROOT)
DRY_RUN = True  # Set to False to actually write ratings.

# MusicBee POPM mapping: POPM value -> stars (0–5 in 0.5 steps)
# Collected from common POPM mappings used by MusicBee/MediaMonkey. :contentReference[oaicite:12]{index=12}
POPM_TO_STARS = {
    0: 0.0,
    13: 0.5,
    1: 1.0,
    54: 1.5,
    64: 2.0,
    118: 2.5,
    128: 3.0,
    186: 3.5,
    196: 4.0,
    242: 4.5,
    255: 5.0,
}


def popm_value_to_plex_rating(popm: int | None) -> int | None:
    """Map MusicBee POPM (0–255) to Plex rating 0–10 (0.5★ steps)."""
    if popm is None:
        return None
    nearest = min(POPM_TO_STARS.keys(), key=lambda v: abs(v - popm))
    stars = POPM_TO_STARS[nearest]  # 0–5 with 0.5 steps
    plex_rating = int(round(stars * 2))  # 0–10
    return plex_rating


def flac_rating_to_plex_rating(rating_str: str | None) -> int | None:
    """MusicBee FLAC RATING is typically 0,20,40,60,80,100 (0–5 stars). :contentReference[oaicite:13]{index=13}"""
    if rating_str is None:
        return None
    try:
        r = int(rating_str)
    except ValueError:
        return None
    # Convert 0–100 → 0–5 stars
    stars = max(0.0, min(5.0, r / 20.0))
    plex_rating = int(round(stars * 2))  # 0–10
    return plex_rating


def get_musicbee_rating_for_file(path: Path) -> int | None:
    """Return Plex-style rating 0–10 from a file's MusicBee tags, or None."""
    suf = path.suffix.lower()
    if suf == ".mp3":
        try:
            tags = ID3(path)
        except Exception:
            return None
        popms = tags.getall("POPM")
        if not popms:
            return None
        # Prefer the POPM frame written by MusicBee (email contains "MusicBee")
        frame = next(
            (f for f in popms if getattr(f, "email", "").lower().startswith("musicbee")),
            popms[0],
        )
        return popm_value_to_plex_rating(frame.rating)
    elif suf in (".flac", ".ogg"):
        try:
            f = FLAC(path)
        except Exception:
            return None
        if "RATING" not in f:
            return None
        return flac_rating_to_plex_rating(f["RATING"][0])
    else:
        return None


def build_plex_path_index(music_section):
    """Return dict: normalized file path -> Track object."""
    index: dict[str, object] = {}
    for track in music_section.all(libtype="track"):
        for loc in track.locations:  # list of file paths on disk :contentReference[oaicite:14]{index=14}
            norm = os.path.normpath(loc)
            index[norm] = track
    return index


def main():
    plex = PlexServer(BASE_URL, TOKEN)  # :contentReference[oaicite:15]{index=15}
    music = plex.library.section(LIBRARY_NAME)

    print("Building Plex path index...")
    plex_index = build_plex_path_index(music)
    print(f"Indexed {len(plex_index)} track paths from Plex")

    for file_path in MUSIC_ROOT.rglob("*"):
        if file_path.suffix.lower() not in (".mp3", ".flac", ".ogg"):
            continue

        rating = get_musicbee_rating_for_file(file_path)
        if rating is None:
            continue

        norm_path = os.path.normpath(str(file_path))
        track = plex_index.get(norm_path)
        if not track:
            # If your Plex paths differ (e.g. /mnt/music vs /media/music),
            # handle path mapping here.
            continue

        current = getattr(track, "userRating", None)
        if current == rating:
            continue

        print(f"{track.title} | {norm_path}")
        print(f"  Plex: {current}  ->  MB: {rating}")

        if not DRY_RUN:
            track.rate(float(rating))  # uses 0–10 scale :contentReference[oaicite:16]{index=16}

    
if __name__ == "__main__":
    main()
