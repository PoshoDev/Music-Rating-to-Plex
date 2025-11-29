from rich import print
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from mutagen.flac import FLAC
from mutagen.id3 import ID3, POPM
from plexapi.server import PlexServer

console = Console()
load_dotenv()

BASE_URL = os.getenv("PLEX_URL")
TOKEN = os.getenv("PLEX_TOKEN")
LIBRARY_NAME = os.getenv("PLEX_LIBRARY")
MUSIC_ROOT = Path(os.getenv("PATH_LIBRARY"))
DRY_RUN = True

POPM_TO_STARS = {
    0: 0.0, 13: 0.5, 1: 1.0, 54: 1.5, 64: 2.0,
    118: 2.5, 128: 3.0, 186: 3.5, 196: 4.0,
    242: 4.5, 255: 5.0,
}

def shorten(path: str, parts: int = 3) -> str:
    p = Path(path)
    return str(Path(*p.parts[-parts:]))

def popm_value_to_plex_rating(popm):
    if popm is None:
        return None
    nearest = min(POPM_TO_STARS.keys(), key=lambda v: abs(v - popm))
    stars = POPM_TO_STARS[nearest]
    return int(round(stars * 2))  # 0–10

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

    if suf == ".mp3":
        try:
            tags = ID3(path)
        except:
            return None
        popms = tags.getall("POPM")
        if not popms:
            return None
        frame = next((f for f in popms if "musicbee" in f.email.lower()), popms[0])
        return popm_value_to_plex_rating(frame.rating)

    elif suf in (".flac", ".ogg"):
        try:
            f = FLAC(path)
        except:
            return None
        if "RATING" not in f:
            return None
        return flac_rating_to_plex_rating(f["RATING"][0])

    return None

def build_plex_path_index(music_section):
    index = {}
    for track in music_section.all(libtype="track"):
        for loc in track.locations:
            index[os.path.normpath(loc)] = track
    return index

def main():
    console.print(f"[bold cyan]Connecting to Plex at[/] {BASE_URL}")
    plex = PlexServer(BASE_URL, TOKEN)
    music = plex.library.section(LIBRARY_NAME)

    console.print("[yellow]Building Plex index...[/]")
    plex_index = build_plex_path_index(music)
    console.print(f"[green]Indexed {len(plex_index)} track paths[/]")

    total_audio = sum(1 for _ in MUSIC_ROOT.rglob("*") if _.suffix.lower() in (".mp3", ".flac", ".ogg"))

    updated = 0
    matched = 0
    with_rating = 0

    with Progress(console=console) as progress:
        task = progress.add_task("[blue]Processing files...", total=total_audio)

        # store the live status object
        with console.status("[dim]Starting...[/]", spinner="dots") as status:

            for file_path in MUSIC_ROOT.rglob("*"):

                # live-updating "Checking ..." line
                status.update(
                    f"[dim]Checking[/] [cyan]{shorten(str(file_path))}[/]"
                )

                if file_path.suffix.lower() not in (".mp3", ".flac", ".ogg"):
                    continue

                progress.advance(task)

                rating = get_musicbee_rating_for_file(file_path)
                if rating is None:
                    continue
                with_rating += 1

                norm = os.path.normpath(str(file_path))
                track = plex_index.get(norm)
                if not track:
                    continue
                matched += 1

                current = getattr(track, "userRating", None)
                if current == rating:
                    continue

                updated += 1
                console.print(
                    f"[white]{track.title}[/] "
                    f"[dim]{shorten(norm)}[/] "
                    f"[yellow]{current} → {rating}[/]"
                )

                if not DRY_RUN:
                    track.rate(float(rating))



    table = Table(title="Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Files with MB rating", str(with_rating))
    table.add_row("Matched in Plex", str(matched))
    table.add_row("Updated ratings", str(updated))

    console.print(table)

if __name__ == "__main__":
    main()
