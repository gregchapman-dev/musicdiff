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

# To use the new Humdrum importer from converter21 in place of the one in music21:
# git clone https://github.com/gregchapman-dev/converter21.git
# pip install converter21   # or pip install -e converter21 if you want it "editable"
# Then uncomment all lines in this file marked "# c21"

# from converter21 import HumdrumConverter # c21

# ------------------------------------------------------------------------------

'''
    main entry point (parse arguments and do conversion)
'''
if __name__ == "__main__":

    # to use the new Humdrum importer from converter21 in place of the one in music21...
    # m21.converter.unregisterSubconverter(m21.converter.subConverters.ConverterHumdrum) # c21
    # m21.converter.registerSubconverter(HumdrumConverter)                               # c21
    # print('registered converter21 humdrum importer', file=sys.stderr)                  # c21

    parser = argparse.ArgumentParser(
                prog='python3 -m musicdiff',
                description='Music score notation diff (MusicXML, MEI, Humdrum, etc)')
    parser.add_argument("file1",
                        help="first music score file to compare (any format music21 can parse)")
    parser.add_argument("file2",
                        help="second music score file to compare (any format music21 can parse)")
    args = parser.parse_args()

    # Note that diff() can take a music21 Score instead of a file, for either
    # or both arguments.
    # Note also that diff() can take str or pathlib.Path for files.
    numDiffs: int = diff(args.file1, args.file2)
    if numDiffs is not None and numDiffs == 0:
        print(f'Scores in {args.file1} and {args.file2} are identical.', file=sys.stderr)
