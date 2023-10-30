import os
import sys
from rich import print
from mutagen.easyid3 import EasyID3
import eyed3
from src.sync import get_track_info
from tinytag import TinyTag

#dir_file = "05 - Sacrificial.mp3"
#dir_file = "04 - Unknown Depths Below.mp3"
dir_file = "06 - Conflicted.mp3"
if not os.path.exists(dir_file):
    print(f"File '{dir_file}' does not exist!")
    sys.exit()
track = EasyID3(dir_file)
print(get_track_info(track))

from mutagen.id3 import ID3, POPM

audio = ID3(dir_file)
rating = audio.getall("POPM")[0].rating
stars = round((rating / 255) * 5)

print("Stars:", stars)