import os
import json
import mutagen
from rich import print

MUSIC_FORMATS = ['.mp3', '.flac', '.aac']

def get_tracks_above_rating(root_directory):
    tracks_above_rating = []

    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if os.path.splitext(filename)[1] in MUSIC_FORMATS:
                file_path = os.path.join(dirpath, filename)
                try:
                    track = mutagen.File(file_path)
                    rating = track.get("rating")
                    if rating is not None and int(rating[0]) > 0:
                        track_info = {}
                        if track.get("title") is not None:
                            track_info["title"] = track.get("title")[0]
                        if track.get("album") is not None:
                            track_info["album"] = track.get("album")[0]
                        if track.get("artist") is not None:
                            track_info["artist"] = track.get("artist")[0]
                        if track.get("rating") is not None:
                            track_info["rating"] = int(track.get("rating")[0])
                        tracks_above_rating.append(track_info)
                        print(track_info)
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

    return tracks_above_rating

if __name__ == "__main__":
    # Load the cache JSON file.
    if os.path.exists("cache.json"):
        with open("cache.json", "r") as cache_file:
            cache = json.load(cache_file)
    else:
        cache = {}
    
    changes = False

    # Get the directory from the cache, or ask the user for it.
    if "directory" not in cache:
        cache["directory"] = input("Enter the directory to search: ")
        changes = True

    # Get the Plex token from the cache, or ask the user for it.
    if "token" not in cache:
        cache["token"] = input("Enter your Plex token: ")
        changes = True

    # Save the cache.
    if changes:
        with open("cache.json", "w") as cache_file:
            json.dump(cache, cache_file)
    

    tracks_above_rating = get_tracks_above_rating(cache["directory"])
    for track in tracks_above_rating:
        print(track)