import os
from math import floor
import mutagen
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from rich.progress import Progress
from .logging import log_write, log_error
from .printing import get_panel
from .info import get_track_info


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
                    track_info = get_track_info(file_path)
                    if track_info["stars"] == None:
                        log_error(f"GOT NONE: {file_path}")
                    elif track_info["stars"] == 0:
                        continue
                    try:
                        if not attempt_sync(library, track_info):
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

def attempt_sync(library, track_info):
    results = search_match(library, track_info)
    if not results:
        return False
    results[0].rate(track_info["stars"] * 2)
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
