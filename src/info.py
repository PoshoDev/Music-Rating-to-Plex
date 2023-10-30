import mutagen
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from .logging import log_error

def get_track_info(file_path):
    info = get_track_info_tags(file_path)
    if not info.get("stars", None):
        info["stars"] = get_stars(file_path)
    return info

## TAGS

def get_track_info_tags(file_path):
    # Method 1
    info = get_tags(mutagen.File(file_path))
    if info["title"]:
        return info
    # Method 2
    info = get_tags(EasyID3(file_path))
    return info

def get_tags(track_obj):
    tags = {
        "title": get_tag(track_obj, "title"),
        "album": get_tag(track_obj, "album"),
        "artist": get_tag(track_obj, "artist")
    }
    if rating := get_tag(track_obj, "rating"):
        tags["stars"] = int(int(rating) / 20)
    return tags

def get_tag(track_obj, tag):
    tag = track_obj.get(tag)
    if isinstance(tag, list):
        tag = tag[0]
    return tag


## STARS

def get_stars(file_path):
    # Get the track stuff.
    try:
        audio = ID3(file_path)
        # Get the rating as stars.
        try:
            rating = audio.getall("POPM")[0].rating
            return round((rating / 255) * 5)
        except IndexError:
            return 0
    # File doesn't start with ID3.
    except Exception as e:
        log_error(str(e))
        return None
