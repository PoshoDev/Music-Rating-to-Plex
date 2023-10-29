import os
from math import floor
import mutagen
from rich.progress import Progress
from .logging import log_write
from .printing import get_panel


MUSIC_FORMATS = ('.mp3', '.ogg', '.flac', '.m4a', '.wav')

def sync_ratings(console, library, root_directory):
    # Get total number of files to process
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