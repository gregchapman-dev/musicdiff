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
import json
import sys
import os
import resource
import argparse
from pathlib import Path
from timeit import default_timer as timer

import music21 as m21
from musicdiff import visualization as sv
from musicdiff import notation as nlin
from musicdiff import comparison as scl

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
    print("file1 extension '{}' not supported.".format(fileExt1))
    badExt = True
if fileExt2 not in getInputExtensionsList():
    print("file2 extension '{}' not supported.".format(fileExt2))
    badExt = True
if badExt:
    printSupportedInputFormats()
    sys.exit(1)

totalTime = 0
start = timer()
score1 = m21.converter.parse(args.file1, forceSource=True)
end = timer()
print('imported first file into music21 score: {:.3f} seconds'.format(end - start))
totalTime += end - start

start = timer()
score2 = m21.converter.parse(args.file2, forceSource=True)
end = timer()
print('imported second file into music21 score: {:.3f} seconds'.format(end - start))
totalTime += end - start

# build ScoreTrees
start = timer()
score_lin1 = nlin.Score(score1)
end = timer()
print('built ScoreTree from score1: {:.3f} seconds'.format(end - start))
totalTime += end - start

start = timer()
score_lin2 = nlin.Score(score2)
end = timer()
print('built ScoreTree from score2: {:.3f} seconds'.format(end - start))
totalTime += end - start

# compute the complete score diff
start = timer()
op_list, cost = scl.complete_scorelin_diff(score_lin1, score_lin2)
end = timer()
print('diffed two ScoreTrees: {:.3f} seconds'.format(end - start))
totalTime += end - start

numDiffs = len(op_list)
print(f'number of differences = {numDiffs}')

if numDiffs > 0:
    # annotate the scores to show differences
    start = timer()
    sv.annotate_differences(score1, score2, op_list)
    end = timer()
    print('annotated the two music21 scores: {:.3f} seconds'.format(end - start))
    totalTime += end - start

    # display the two annotated scores
    start = timer()
    sv.show_differences(score1, score2)
    end = timer()
    print('rendered the two annotated scores: {:.3f} seconds'.format(end - start))
    totalTime += end - start

print('total time:: {:.3f} seconds'.format(totalTime))
