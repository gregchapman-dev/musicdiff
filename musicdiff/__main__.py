# ------------------------------------------------------------------------------
# Purpose:       __main__.py is a music file comparison tool built on musicdiff.
#                musicdiff is a package for comparing music scores using music21.
#                Usage:
#                   python3 -m musicdiff filePath1 filePath2
#
# Authors:       Greg Chapman <gregc@mac.com>
#                musicdiff is derived from:
#                   https://github.com/fosfrancesco/music-score-diff.git
#                   by Francesco Foscarin <foscarin.francesco@gmail.com>
#
# Copyright:     (c) 2022, 2023 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------
import sys
import argparse

from musicdiff import diff
from musicdiff import DetailLevel

# ------------------------------------------------------------------------------

'''
    main entry point (parse arguments and do conversion)
'''
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='python3 -m musicdiff',
        description='Music score notation diff (MusicXML, MEI, Humdrum, etc)'
    )
    parser.add_argument(
        "file1",
        help="first music score file to compare (any format music21 can parse)"
    )
    parser.add_argument(
        "file2",
        help="second music score file to compare (any format music21 can parse)"
    )
    parser.add_argument(
        "-d",
        "--detail",
        default=[],
        nargs='*',
        choices=[
            "GeneralNotes",
            "Extras",
            "Lyrics",
            "Style",
            "Voicing",
            "Metadata",
            "AllObjects",
            "AllObjectsAndMetadata",
            "AllObjectsWithStyle",
            "AllObjectsWithStyleAndMetadata"],
        help="set detail level (can set multiple details)"
    )
    args = parser.parse_args()

    detail: int = DetailLevel.Default
    if args.detail:
        detail = 0
        for det in args.detail:
            if det == "GeneralNotes":
                detail |= DetailLevel.GeneralNotes
            elif det == "Extras":
                detail |= DetailLevel.Extras
            elif det == "Lyrics":
                detail |= DetailLevel.Lyrics
            elif det == "Style":
                detail |= DetailLevel.Style
            elif det == "Voicing":
                detail |= DetailLevel.Voicing
            elif det == "Metadata":
                detail |= DetailLevel.Metadata
            elif det == "AllObjects":
                detail |= DetailLevel.AllObjects
            elif det == "AllObjectsAndMetadata":
                detail |= DetailLevel.AllObjectsAndMetadata
            elif det == "AllObjectsWithStyle":
                detail |= DetailLevel.AllObjectsWithStyle
            elif det == "AllObjectsWithStyleAndMetadata":
                detail |= DetailLevel.AllObjectsWithStyleAndMetadata

    # Note that diff() can take a music21 Score instead of a file, for either
    # or both arguments.
    # Note also that diff() can take str or pathlib.Path for files.
    detailLevel: DetailLevel = detail  # type: ignore
    numDiffs: int | None = diff(args.file1, args.file2, detail=detailLevel)
    if numDiffs is None:
        print('musicdiff failed.', file=sys.stderr)
    elif numDiffs == 0:
        print(f'Scores in {args.file1} and {args.file2} are identical.', file=sys.stderr)
