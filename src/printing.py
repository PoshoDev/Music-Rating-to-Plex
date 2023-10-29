from math import floor
from rich.panel import Panel
from rich.table import Table

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