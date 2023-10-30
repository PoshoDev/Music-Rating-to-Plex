import os
from math import floor
import mutagen
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from rich.progress import Progress
from .logging import log_write, log_error
from .printing import get_panel


MUSIC_FORMATS = ('.mp3', '.ogg', '.flac', '.m4a', '.wav')

def sync_ratings(console, library, root_directory):
    # Get total number of files to process.
    total_files = sum(len(files) for _, _, files in os.walk(root_directory))
    # Start task.
    failed_tracks = []
    with Progress(console=console) as progress:
        task = progress.add_task("[green]Processing...", total=total_files)
        for dirpath, _, filenames in os.walk(root_directory):
            log_write(dirpath)
            for filename in filenames:
                log_write(f"- {filename}")
                if os.path.splitext(filename)[1] in MUSIC_FORMATS:
                    file_path = os.path.join(dirpath, filename)
                    stars = get_stars(file_path)
                    if stars == None:
                        continue
                    track_info = get_track_info(file_path, stars)
                    try:
                        if stars:
                            if not attempt_sync(library, track_info, stars):
                                console.clear()
                                console.print(get_panel(track_info, "Track not found!"))
                            else:
                                console.clear()
                                console.print(get_panel(track_info))
                        progress.advance(task)
                    except Exception as e:
                        track_info["error"] = str(e)
                        failed_tracks.append(track_info)
                        progress.advance(task)
    return failed_tracks

def attempt_sync(library, track_info, stars):
    results = search_match(library, track_info)
    if not results:
        return False
    results[0].rate(stars * 2)
    return True


def search_match(library, track_info):
    return library.searchTracks(
        filters={
            "track.title": track_info["title"],
            "album.title": track_info["album"],
            "artist.title": track_info["artist"]
        },
        maxresults=1
    )

def get_track_info(file_path, rating):
    track = mutagen.File(file_path)
    return {
        "title": track.get("title"),
        "album": track.get("album"),
        "artist": track.get("artist"),
        "rating": rating
    }

def get_stars(file_path):
    # Get the track stuff.
    try:
        audio = ID3(file_path)
    except Exception as e:
        log_error(str(e))
        return None
    # Get the rating as stars.
    try:
        rating = audio.getall("POPM")[0].rating
        return round((rating / 255) * 5)
    except IndexError:
        return 0