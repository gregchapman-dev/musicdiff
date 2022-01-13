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
import os
import argparse

import music21 as m21

from musicdiff import Visualization
from musicdiff import notation # for notation.Score, etc
from musicdiff import Comparison

# To use the new Humdrum importer from converter21 in place of the one in music21:
# git clone https://github.com/gregchapman-dev/converter21.git
# pip install converter21 # or pip install -e converter21 if you want it "editable"
# Then uncomment all lines in this file marked "# c21"

# from converter21 import HumdrumConverter # c21

def getInputExtensionsList() -> [str]:
    c = m21.converter.Converter()
    inList = c.subconvertersList('input')
    result = []
    for subc in inList:
        for inputExt in subc.registerInputExtensions:
            result.append('.' + inputExt)
    return result

def printSupportedInputFormats():
    c = m21.converter.Converter()
    inList = c.subconvertersList('input')
    print("Supported input formats are:")
    for subc in inList:
        if subc.registerInputExtensions:
            print('\tformats   : ' + ', '.join(subc.registerFormats)
                    + '\textensions: ' + ', '.join(subc.registerInputExtensions))

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

print('music21 version:', m21.base.VERSION_STR)
args = parser.parse_args()

# check file1 and file2 extensions for support within music21
badExt: bool = False
_, fileExt1 = os.path.splitext(args.file1)
_, fileExt2 = os.path.splitext(args.file2)

if fileExt1 not in getInputExtensionsList():
    print(f"file1 extension '{fileExt1}' not supported.")
    badExt = True
if fileExt2 not in getInputExtensionsList():
    print(f"file2 extension '{fileExt2}' not supported.")
    badExt = True
if badExt:
    printSupportedInputFormats()
    sys.exit(1)

score1 = m21.converter.parse(args.file1, forceSource=True)
score2 = m21.converter.parse(args.file2, forceSource=True)

# build ScoreTrees
score_lin1 = notation.Score(score1)
score_lin2 = notation.Score(score2)

# compute the complete score diff
comp: Comparison = Comparison(score_lin1, score_lin2)
comp.complete_scorelin_diff()

numDiffs = len(comp.op_list)
print(f'number of differences = {numDiffs}')

if numDiffs > 0:
    # display the two annotated scores
    viz: Visualization = Visualization(score1, score2, comp.op_list)
    viz.annotate_differences()
    viz.show_differences()
