import os
import sys
from rich import print
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
import eyed3
from src.info import get_track_info
from tinytag import TinyTag
from src.logging import log_remove

files = [
    "05 - Sacrificial.mp3",
    "04 - Unknown Depths Below.mp3",
    "06 - Conflicted.mp3",
    "1-01 - Steven Universe Future (feat. Zach Callison, Deedee Magno Hall, Estelle, Michaela Dietz, Shelby Rabara, Rebecca Sugar & aivi & sur.flac",
    "1-02 - Happy Welcome Back Day (feat. aivi & surasshu) (Title Card).flac",
    "1-61 - I'd Rather Be Me (With You) (feat. Zach Callison & Rebecca Sugar).flac"
]

log_remove()

for file in files:
    if not os.path.exists(file):
        print(f"File '{file}' does not exist!")
        sys.exit()
    
    print(get_track_info(file))