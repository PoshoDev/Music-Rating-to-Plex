from rich.console import Console
from plexapi.server import PlexServer
from src.cache import load_cache
from src.logging import log_remove
from src.sync import sync_ratings
from src.printing import failed_table

if __name__ == "__main__":
    # Clear logs.
    log_remove()
    # Load the cache.
    cache = load_cache()
    # Plex stuff.
    plex = PlexServer(cache["url"], cache["token"])
    library = plex.library.section(cache["library"])
    # Setup print destination.
    console = Console()
    # Main operations.
    if failed_tracks := sync_ratings(console, library, cache["directory"]):
        failed_table(console, failed_tracks)
    else:
        console.print("[blink]All track ratings synced successfully!")