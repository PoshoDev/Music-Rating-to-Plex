import os
import json
from math import floor
import mutagen
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich import print
from plexapi.server import PlexServer

MUSIC_FORMATS = ('.mp3', '.ogg', '.flac', '.m4a', '.wav')

def sync_ratings(console, library, root_directory):
    # Get total number of files to process
    total_files = sum(len(files) for _, _, files in os.walk(root_directory))
    # Start task.
    failed_tracks = []
    with Progress(console=console) as progress:
        task = progress.add_task("[green]Processing...", total=total_files)
        for dirpath, _, filenames in os.walk(root_directory):
            for filename in filenames:
                if os.path.splitext(filename)[1] in MUSIC_FORMATS:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        track = mutagen.File(file_path)
                        rating = track.get("rating")
                        if rating is not None and int(rating[0]) > 0:
                            # Fetch the track info.
                            track_info = {
                                "title": track.get("title")[0] if track.get("title") is not None else "",
                                "album": track.get("album")[0] if track.get("album") is not None else "",
                                "artist": track.get("artist")[0] if track.get("artist") is not None else "",
                                "rating": int(rating[0])
                            }
                            # Find the track in Plex.
                            results = library.searchTracks(
                                filters={
                                    "track.title": track_info["title"],
                                    "album.title": track_info["album"],
                                    "artist.title": track_info["artist"]
                                },
                                maxresults=1
                            )
                            if results:
                                song = results[0]
                                # Rate the track.
                                rating = floor(track_info["rating"] / 10)
                                song.rate(rating)
                                console.clear()
                                console.print(get_panel(track_info))
                            else:
                                track_info["error"] = "Track not found!"
                                failed_tracks.append(track_info)
                                console.clear()
                                console.print(get_panel(track_info, "Track not found!"))
                        progress.advance(task)
                    except Exception as e:
                        track_info["error"] = str(e)
                        failed_tracks.append(track_info)
                        progress.advance(task)
    return failed_tracks

def get_panel(track_info, error=""):
    content = f"🎵 {track_info['title']}\n" + \
              f"📀 {track_info['album']}\n" + \
              f"👤 {track_info['artist']}\n" + \
              f"{get_stars(track_info['rating'])}"
    panel = Panel(
        content,
        style="gold1" if not error else "red",
        title="Rating Synced!" if not error else error,
        title_align="left"
    )
    return panel

def load_cache():
    # Load the cache JSON file.
    if os.path.exists("cache.json"):
        with open("cache.json", "r", encoding="utf-8") as cache_file:
            cache = json.load(cache_file)
    else:
        cache = {}
    changes = False
    # Get the directory from the cache, or ask the user for it.
    if "directory" not in cache:
        cache["directory"] = input("Enter the directory to search: ")
        changes = True
    # Get the Plex URL from the cache, or ask the user for it.
    if "url" not in cache:
        cache["url"] = input("Enter your Plex URL: ")
        changes = True
    # Get the Plex token from the cache, or ask the user for it.
    if "token" not in cache:
        cache["token"] = input("Enter your Plex token: ")
        changes = True
    # Get the Plex library from the cache, or ask the user for it.
    if "library" not in cache:
        cache["library"] = input("Enter your Plex library: ")
        changes = True
    # Save the cache.
    if changes:
        with open("cache.json", "w") as cache_file:
            json.dump(cache, cache_file)
    return cache

def get_stars(rating):
    stars = "⭐" * floor(rating / 20)
    return stars

def failed_table(console, failed_tracks):
    console.clear()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("👤 Artist")
    table.add_column("📀 Album")
    table.add_column("🎵 Title")
    table.add_column("⭐ Rating")
    table.add_column("❌ Error")
    for track in failed_tracks:
        table.add_row(
            track["artist"],
            track["album"],
            track["title"],
            get_stars(track["rating"]),
            track["error"]
        )
    console.print("[blink]The following tracks could not be found in Plex:")
    console.print(table)
    console.print(f"[blink]Total: {len(failed_tracks)} track(s)")

if __name__ == "__main__":
    cache = load_cache()
    # Plex stuff.
    plex = PlexServer(cache["url"], cache["token"])
    library = plex.library.section(cache["library"])
    console = Console()
    if failed_tracks := sync_ratings(console, library, cache["directory"]):
        failed_table(console, failed_tracks)
    else:
        console.print("[blink]All track ratings synced successfully!")
