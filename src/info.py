import mutagen
from mutagen.easyid3 import EasyID3

def get_track_info(file_path):
    # Method 1
    info = get_tags(mutagen.File(file_path))
    if info["title"]:
        return info
    # Method 2
    info = get_tags(EasyID3(file_path))
    return info

def get_tags(track_obj):
    return {
        "title": get_tag(track_obj, "title"),
        "album": get_tag(track_obj, "album"),
        "artist": get_tag(track_obj, "artist")
    }

def get_tag(track_obj, tag):
    tag = track_obj.get(tag)
    if isinstance(tag, list):
        tag = tag[0]
    return tag