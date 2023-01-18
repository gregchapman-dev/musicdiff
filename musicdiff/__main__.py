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
# Copyright:     (c) 2022 Francesco Foscarin, Greg Chapman
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
                description='Music score notation diff (MusicXML, MEI, Humdrum, etc)')
    parser.add_argument("file1",
                        help="first music score file to compare (any format music21 can parse)")
    parser.add_argument("file2",
                        help="second music score file to compare (any format music21 can parse)")
    parser.add_argument("-d", "--detail", default="Default",
                        choices=["GeneralNotesOnly", "AllObjects", "AllObjectsWithStyle", "Default"],
                        help="set detail level")
    args = parser.parse_args()

    detail: DetailLevel = DetailLevel.Default
    if args.detail == "GeneralNotesOnly":
        detail = DetailLevel.GeneralNotesOnly
    elif args.detail == "AllObjects":
        detail = DetailLevel.AllObjects
    elif args.detail == "AllObjectsWithStyle":
        detail = DetailLevel.AllObjectsWithStyle
    elif args.detail == "Default":
        detail = DetailLevel.Default

    # Note that diff() can take a music21 Score instead of a file, for either
    # or both arguments.
    # Note also that diff() can take str or pathlib.Path for files.
    numDiffs: int = diff(args.file1, args.file2, detail=detail)
    if numDiffs is not None and numDiffs == 0:
        print(f'Scores in {args.file1} and {args.file2} are identical.', file=sys.stderr)
