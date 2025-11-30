import os
import time
import json
import signal
from pathlib import Path

from rich import print
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from dotenv import load_dotenv
from mutagen.flac import FLAC
from mutagen.id3 import ID3, POPM
from mutagen.mp4 import MP4
from plexapi.server import PlexServer

console = Console()
load_dotenv()

BASE_URL = os.getenv("PLEX_URL")
TOKEN = os.getenv("PLEX_TOKEN")
LIBRARY_NAME = os.getenv("PLEX_LIBRARY")
MUSIC_ROOT = Path(os.getenv("PATH_LIBRARY"))
INDEX_CACHE_FILE = Path(__file__).with_name("plex_path_index.json")
DRY_RUN = True
VERBOSE = True
STOP_REQUESTED = False
error_rows_global = []

POPM_TO_STARS = {
    0: 0.0, 13: 0.5, 1: 1.0, 54: 1.5, 64: 2.0,
    118: 2.5, 128: 3.0, 186: 3.5, 196: 4.0,
    242: 4.5, 255: 5.0,
}
# Limit to formats we actually parse to avoid false positives/errors
FILETYPES = (".mp3", ".flac", ".ogg", ".m4a", ".wav")

def shorten(path: str, parts: int = 3) -> str:
    p = Path(path)
    return str(Path(*p.parts[-parts:]))

def popm_value_to_plex_rating(popm):
    if popm is None:
        return None
    nearest = min(POPM_TO_STARS.keys(), key=lambda v: abs(v - popm))
    stars = POPM_TO_STARS[nearest]
    return int(round(stars * 2))  # 0–10

def generic_rating_to_plex(r):
    """Convert a variety of rating scales to Plex 0–10."""
    if r is None:
        return None
    try:
        val = float(r)
    except Exception:
        return None
    if 0.0 <= val <= 1.0:
        return int(round(val * 10))  # fmps style 0-1
    if 0.0 <= val <= 5.0:
        return int(round(val * 2))  # 0–5 stars
    if 0.0 <= val <= 100.0:
        stars = max(0.0, min(5.0, val / 20.0))
        return int(round(stars * 2))
    return None

def get_txxx_rating(tags):
    """Look for text rating frames like FMPS_Rating or RATING."""
    for txxx in tags.getall("TXXX"):
        desc = (txxx.desc or "").lower()
        if "rating" not in desc:
            continue
        if not getattr(txxx, "text", None):
            continue
        rating = generic_rating_to_plex(txxx.text[0])
        if rating is not None:
            return rating
    return None

def extract_mp4_rating(tags: MP4):
    """Pull rating from common MP4 atoms used by MusicBee/iTunes."""
    rating_keys = [
        "----:com.apple.iTunes:RATING",
        "----:com.apple.iTunes:Rating",
        "----:com.apple.iTunes:POPM",
    ]
    for key in rating_keys:
        if key not in tags:
            continue
        val = tags[key]
        if isinstance(val, list) and val:
            val = val[0]
        if isinstance(val, bytes):
            try:
                val = val.decode("utf-8", errors="ignore")
            except Exception:
                continue
        rating = generic_rating_to_plex(val)
        if rating is not None:
            return rating
    return None

def flac_rating_to_plex_rating(r):
    if r is None:
        return None
    try:
        val = int(r)
    except:
        return None
    stars = max(0.0, min(5.0, val / 20.0))
    return int(round(stars * 2))

def get_musicbee_rating_for_file(path: Path):
    suf = path.suffix.lower()
    artist = album = title = ""
    error_msg = None

    if suf in (".mp3", ".wav"):
        try:
            tags = ID3(path)
        except Exception as exc:
            return None, artist, album, title, f"ID3 read error: {exc}"
        def get_text(frame_id):
            frame = tags.get(frame_id)
            if frame and getattr(frame, "text", None):
                return frame.text[0]
            return ""
        artist = get_text("TPE1")
        album = get_text("TALB")
        title = get_text("TIT2")
        popms = tags.getall("POPM")
        if not popms:
            txxx_rating = get_txxx_rating(tags)
            if txxx_rating is not None:
                return txxx_rating, artist, album, title, None
            return None, artist, album, title, None
        frame = next((f for f in popms if "musicbee" in f.email.lower()), popms[0])
        return popm_value_to_plex_rating(frame.rating), artist, album, title, None

    elif suf in (".flac", ".ogg"):
        try:
            f = FLAC(path)
        except Exception as exc:
            return None, artist, album, title, f"FLAC/OGG read error: {exc}"
        artist = (f.get("artist") or f.get("ARTIST") or [""])[0]
        album = (f.get("album") or f.get("ALBUM") or [""])[0]
        title = (f.get("title") or f.get("TITLE") or [""])[0]
        if "RATING" not in f:
            return None, artist, album, title, None
        return flac_rating_to_plex_rating(f["RATING"][0]), artist, album, title, None

    elif suf == ".m4a":
        try:
            mp4 = MP4(path)
        except Exception as exc:
            return None, artist, album, title, f"MP4 read error: {exc}"
        artist = (mp4.get("\xa9ART") or [""])[0]
        album = (mp4.get("\xa9alb") or [""])[0]
        title = (mp4.get("\xa9nam") or [""])[0]
        rating = extract_mp4_rating(mp4)
        if rating is None:
            return None, artist, album, title, None
        return rating, artist, album, title, None

    return None, artist, album, title, "Unsupported file type"

def build_plex_path_index(music_section):
    index = {}
    for track in music_section.all(libtype="track"):
        if STOP_REQUESTED:
            break
        for loc in track.locations:
            index[os.path.normpath(loc)] = track.ratingKey
    return index

def build_suffix_index(plex_index: dict, min_parts: int = 2, max_parts: int = 6):
    """
    Build a map of trailing path segments to rating keys when the tail is unique.
    This helps match when Plex path roots differ from the local library root.
    """
    tails = {}
    collisions = set()
    for full_path, key in plex_index.items():
        parts = Path(full_path).parts
        for n in range(min_parts, min(max_parts, len(parts)) + 1):
            tail = os.path.normpath(os.path.join(*parts[-n:])).lower()
            prev = tails.get(tail)
            if prev is None:
                tails[tail] = key
            elif prev != key:
                collisions.add(tail)
    for tail in collisions:
        tails.pop(tail, None)
    return tails

def load_cached_index(cache_file: Path):
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text())
        # normalize paths on load to avoid OS differences
        return {os.path.normpath(k): v for k, v in data.items()}
    except Exception as exc:
        console.print(f"[red]Failed to load cached Plex index:[/] {exc}")
        return None

def save_cached_index(cache_file: Path, index: dict):
    try:
        cache_file.write_text(json.dumps(index))
        console.print(f"[green]Saved Plex index cache[/] → {cache_file}")
    except Exception as exc:
        console.print(f"[red]Failed to save Plex index:[/] {exc}")

def handle_stop_signal(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True
    console.print("\n[yellow]Ctrl+C detected, stopping...[/]")
    raise KeyboardInterrupt()

def log_verbose(message: str):
    if VERBOSE:
        console.print(f"[dim]{message}[/]")

def update_verbose_progress(progress: Progress, task_id: int, with_rating: int, matched: int, updated: int):
    if not VERBOSE:
        return
    progress.update(
        task_id,
        description=(
            f"[blue]Processing files...[/] "
            f"rated:{with_rating} matched:{matched} updated:{updated} errors:{len(error_rows_global)}"
        ),
    )

def find_rating_key_for_path(file_path: Path, plex_index: dict, suffix_index: dict):
    """Try to find a Plex rating key for a local path using exact and suffix matches."""
    norm = os.path.normpath(str(file_path))
    # 1) exact path match
    if norm in plex_index:
        return plex_index[norm], "exact"
    # 2) case-insensitive match
    lower_norm = norm.lower()
    for k, v in plex_index.items():
        if k.lower() == lower_norm:
            return v, "case-insensitive"
    # 3) tail-based match
    tail = os.path.normpath(str(file_path)).lower()
    if tail in suffix_index:
        return suffix_index[tail], "tail-full"
    parts = file_path.parts
    for n in range(2, min(len(parts), 6) + 1):
        tail = os.path.normpath(os.path.join(*parts[-n:])).lower()
        if tail in suffix_index:
            return suffix_index[tail], f"tail-{n}"
    return None, None

def main():
    signal.signal(signal.SIGINT, handle_stop_signal)
    signal.signal(signal.SIGTERM, handle_stop_signal)

    console.print(f"[bold cyan]Connecting to Plex at[/] {BASE_URL}")
    plex = PlexServer(BASE_URL, TOKEN)
    music = plex.library.section(LIBRARY_NAME)

    plex_index = load_cached_index(INDEX_CACHE_FILE)
    if plex_index is not None:
        console.print(f"[green]Loaded cached Plex index[/] ({len(plex_index)} paths)")
    else:
        console.print("[yellow]Building Plex index...[/]")
        plex_index = build_plex_path_index(music)
        console.print(f"[green]Indexed {len(plex_index)} track paths[/]")
        save_cached_index(INDEX_CACHE_FILE, plex_index)
    suffix_index = build_suffix_index(plex_index)

    total_audio = sum(1 for _ in MUSIC_ROOT.rglob("*") if _.suffix.lower() in FILETYPES)

    updated = 0
    matched = 0
    with_rating = 0
    track_cache = {}
    interrupted = False
    matched_rows = []
    error_rows = []
    success_paths = []
    # keep a reference for verbose progress updates
    global error_rows_global
    error_rows_global = error_rows

    try:
        with Progress(console=console) as progress:
            task = progress.add_task("[blue]Processing files...", total=total_audio)
            update_verbose_progress(progress, task, with_rating, matched, updated)

            # store the live status object
            with console.status("[dim]Starting...[/]", spinner="dots") as status:

                for file_path in MUSIC_ROOT.rglob("*"):
                    if STOP_REQUESTED:
                        interrupted = True
                        break

                    # live-updating "Checking ..." line
                    status.update(
                        f"[dim]Checking[/] [cyan]{shorten(str(file_path))}[/]"
                    )

                    if file_path.suffix.lower() not in FILETYPES:
                        continue

                    progress.advance(task)

                    rating, artist_mb, album_mb, title_mb, rating_error = get_musicbee_rating_for_file(file_path)
                    if rating_error:
                        error_rows.append(
                            (
                                artist_mb,
                                album_mb,
                                title_mb or file_path.stem,
                                "",
                                str(file_path),
                                rating_error,
                            )
                        )
                        update_verbose_progress(progress, task, with_rating, matched, updated)
                        continue
                    if rating is None:
                        update_verbose_progress(progress, task, with_rating, matched, updated)
                        continue
                    with_rating += 1

                    norm = os.path.normpath(str(file_path))
                    rating_key, match_kind = find_rating_key_for_path(file_path, plex_index, suffix_index)
                    if not rating_key:
                        log_verbose(f"No Plex match for rated file: {shorten(norm)}")
                        error_rows.append(
                            (
                                artist_mb,
                                album_mb,
                                title_mb or file_path.stem,
                                rating,
                                str(file_path),
                                "No Plex match",
                            )
                        )
                        update_verbose_progress(progress, task, with_rating, matched, updated)
                        continue
                    matched += 1
                    log_verbose(f"Matched Plex track ({match_kind}): {shorten(norm)}")

                    track = track_cache.get(rating_key)
                    if track is None:
                        try:
                            track = plex.fetchItem(rating_key)
                            track_cache[rating_key] = track
                        except Exception as exc:
                            console.print(
                                f"[red]Failed to fetch track[/] [dim]{shorten(norm)}[/]: {exc}"
                            )
                            error_rows.append(
                                (
                                    artist_mb,
                                    album_mb,
                                    title_mb or file_path.stem,
                                    rating,
                                    str(file_path),
                                    f"Plex fetch error: {exc}",
                                )
                            )
                            update_verbose_progress(progress, task, with_rating, matched, updated)
                            continue
                    log_verbose(f"Matched Plex track: {track.title} ({shorten(norm)})")

                    artist = getattr(track, "grandparentTitle", "") or ""
                    album = getattr(track, "parentTitle", "") or ""
                    current = getattr(track, "userRating", None)
                    if current == rating:
                        log_verbose(f"Already up to date: {track.title} ({shorten(norm)})")
                        matched_rows.append((track.title, artist, album, rating, current, False))
                        success_paths.append(str(file_path))
                        update_verbose_progress(progress, task, with_rating, matched, updated)
                        continue

                    updated += 1
                    console.print(
                        f"[white]{track.title}[/] "
                        f"[dim]{shorten(norm)}[/] "
                        f"[yellow]{current} → {rating}[/]"
                    )
                    matched_rows.append((track.title, artist, album, rating, current, True))
                    success_paths.append(str(file_path))

                    if not DRY_RUN:
                        track.rate(float(rating))

                    update_verbose_progress(progress, task, with_rating, matched, updated)
    except KeyboardInterrupt:
        interrupted = True
        console.print("\n[yellow]Interrupted by user. Partial results:[/]")

    if matched_rows:
        updated_table = Table(title="Matched Tracks", show_header=True, header_style="bold green")
        updated_table.add_column("👤 Artist")
        updated_table.add_column("📀 Album")
        updated_table.add_column("🎵 Track")
        updated_table.add_column("🐝 MB Rating")
        updated_table.add_column("⭐ Plex Rating")
        updated_table.add_column("📝 Updating?")
        for title, artist, album, mb_rating, plex_rating, updating in matched_rows:
            row_style = "dim" if not updating else None
            updated_table.add_row(
                str(artist),
                str(album),
                str(title),
                str(mb_rating),
                str(plex_rating),
                "YES" if updating else "NO",
                style=row_style,
            )
        console.print(updated_table)
    else:
        console.print("[yellow]No tracks matched[/]")

    if error_rows:
        error_table = Table(
            title="Errors",
            show_header=True,
            style="red",
        )
        error_table.add_column("👤 Artist")
        error_table.add_column("📀 Album")
        error_table.add_column("🎵 Track")
        error_table.add_column("⭐ Rating")
        error_table.add_column("📄 Full Path")
        error_table.add_column("❌️ Error Message")
        for artist, album, title, rating, full_path, msg in error_rows:
            error_table.add_row(
                str(artist),
                str(album),
                str(title),
                str(rating),
                full_path,
                msg,
            )
        console.print(error_table)
    else:
        console.print("[green]No errors encountered[/]")

    # Write successful tracks to m3u
    if success_paths:
        m3u_path = Path(__file__).with_name("successful.m3u")
        try:
            with m3u_path.open("a") as m3u_file:
                for p in success_paths:
                    m3u_file.write(f"{p}\n")
            console.print(f"[green]Appended {len(success_paths)} successful tracks to[/] {m3u_path}")
        except Exception as exc:
            console.print(f"[red]Failed to write successful.m3u:[/] {exc}")

    table = Table(title="Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Files with MB rating", str(with_rating))
    table.add_row("Matched in Plex", str(matched))
    table.add_row("Updated ratings", str(updated))

    console.print(table)

if __name__ == "__main__":
    main()
