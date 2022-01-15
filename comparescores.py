# ------------------------------------------------------------------------------
# Purpose:       comparescores.py is a music file comparison tool built on musicdiff.
#                musicdiff is a package for comparing music scores using music21.
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

import music21 as m21

import musicdiff

# To use the new Humdrum importer from converter21 in place of the one in music21:
# git clone https://github.com/gregchapman-dev/converter21.git
# pip install converter21   # or pip install -e converter21 if you want it "editable"
# Then uncomment all lines in this file marked "# c21"

# from converter21 import HumdrumConverter # c21

# ------------------------------------------------------------------------------

'''
    main entry point (parse arguments and do conversion)
'''
# to use the new Humdrum importer from converter21 in place of the one in music21...
# m21.converter.unregisterSubconverter(m21.converter.subConverters.ConverterHumdrum) # c21
# m21.converter.registerSubconverter(HumdrumConverter)                               # c21
# print('registered converter21 humdrum importer')                                   # c21

parser = argparse.ArgumentParser()
parser.add_argument("file1",
                    help="first music file to compare")
parser.add_argument("file2",
                    help="second music file to compare")
args = parser.parse_args()

numDiffs: int = musicdiff.diff(args.file1, args.file2)
if numDiffs is not None and numDiffs == 0:
    print('Scores in {args.file1} and {args.files} are identical.', file=sys.stderr)
