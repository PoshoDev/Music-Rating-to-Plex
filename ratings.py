import os
import json
from math import floor
import mutagen
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich import print
from plexapi.server import PlexServer


MUSIC_FORMATS = ['.mp3', '.flac', '.aac']

console = Console()

def get_tracks_above_rating(root_directory):
    tracks_above_rating = []
    # Get total number of files to process
    total_files = sum(len(files) for _, _, files in os.walk(root_directory))
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
                            track_info = {
                                "title": track.get("title")[0] if track.get("title") is not None else "",
                                "album": track.get("album")[0] if track.get("album") is not None else "",
                                "artist": track.get("artist")[0] if track.get("artist") is not None else "",
                                "rating": int(rating[0])
                            }
                            tracks_above_rating.append(track_info)
                            console.clear()
                            console.print(get_panel(track_info))
                        progress.advance(task)
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")
                        progress.advance(task)
    return tracks_above_rating

def update_plex_ratings(tracks, plex_url, plex_token, library_id, plex_user):
    plex = PlexServer(plex_url, plex_token)
    errors = []
    with Progress(console=console) as progress:
        task = progress.add_task("[green]Updating Plex...", total=len(tracks))
        library = plex.library.section(library_id)
        for track in tracks:
            search = library.search(filters={
                "track.title": track["title"],
                "album.title": track["album"],
                "artist.title": track["artist"]
            })
            if not search:
                console.print(f"Could not find track {track['title']} by {track['artist']}")
                continue
            plex_track = search[0]
            console.print(f"Found track {track['title']} by {track['artist']}")
            rating = floor(track["rating"] / 10)
            console.print(f"Current rating: {plex_track.userRating}")
            plex_track.rate(rating)
            console.print(f"New rating: {plex_track.userRating}")
            console.print(f"Rated track {track['title']} by {track['artist']} as {rating}")
            progress.advance(task)

def get_panel(track_info):
    stars = "⭐" * floor(track_info["rating"] / 20)
    content = f"🎵 {track_info['title']}\n" + \
              f"📀 {track_info['album']}\n" + \
              f"👤 {track_info['artist']}\n" + \
              f"{stars}"
    panel = Panel(content)
    return panel

if __name__ == "__main__":
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

    # Get the Plex user ID from the cache, or ask the user for it.
    if "user_id" not in cache:
        cache["user_id"] = input("Enter your Plex user ID: ")
        changes = True

    # Save the cache.
    if changes:
        with open("cache.json", "w") as cache_file:
            json.dump(cache, cache_file)
    

    tracks_above_rating = get_tracks_above_rating(cache["directory"])
    """for track in tracks_above_rating:
        print(get_panel(track))"""
    update_plex_ratings(tracks_above_rating, cache["url"], cache["token"], cache["library"], cache["user_id"])
    
