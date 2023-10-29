import os
import json

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