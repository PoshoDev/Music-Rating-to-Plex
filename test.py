import json
from rich import print
from plexapi.server import PlexServer

with open("cache.json", "r", encoding="utf-8") as cache_file:
    cache = json.load(cache_file)

plex = PlexServer(cache["url"], cache["token"])
print(plex)

# Specify the search parameters for the song
artist_name = "C418"
album_name = "0x10c"
track_name = "0x10c"
library_name = "Sountracks 🎵"

# Get the library
library = plex.library.section(library_name)
print(library)

# Search for the song using the specified parameters
"""results = plex.search(
    query=track_name,
    artist=artist_name,
    album=album_name,
    track=track_name
)"""
"""results = library.search(filters={
    "track.title": track_name,
    "album.title": album_name,
    "artist.title": artist_name
})"""
results = library.searchTracks(filters={
    "track.title": track_name,
    "album.title": album_name,
    "artist.title": artist_name
    },
    maxresults=1)
print(results)

# Get the first search result (assuming it's the correct song)
song = results[0]
print(song)

# Rate the song
song.rate(8)
