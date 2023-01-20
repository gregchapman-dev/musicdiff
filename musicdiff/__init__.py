# ------------------------------------------------------------------------------
# Purpose:       musicdiff is a package for comparing music scores using music21.
#
# Authors:       Greg Chapman <gregc@mac.com>
#                musicdiff is derived from:
#                   https://github.com/fosfrancesco/music-score-diff.git
#                   by Francesco Foscarin <foscarin.francesco@gmail.com>
#
# Copyright:     (c) 2022 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------

__docformat__ = "google"

import sys
import os
from typing import Union, List, Tuple
from pathlib import Path

import music21 as m21
import converter21

from musicdiff.m21utils import M21Utils
from musicdiff.m21utils import DetailLevel
from musicdiff.annotation import AnnScore
from musicdiff.comparison import Comparison
from musicdiff.visualization import Visualization

def _getInputExtensionsList() -> [str]:
    c = m21.converter.Converter()
    inList = c.subconvertersList('input')
    result = []
    for subc in inList:
        for inputExt in subc.registerInputExtensions:
            result.append('.' + inputExt)
    return result

def _printSupportedInputFormats():
    c = m21.converter.Converter()
    inList = c.subconvertersList('input')
    print("Supported input formats are:", file=sys.stderr)
    for subc in inList:
        if subc.registerInputExtensions:
            print('\tformats   : ' + ', '.join(subc.registerFormats)
                    + '\textensions: ' + ', '.join(subc.registerInputExtensions), file=sys.stderr)

def diff(score1: Union[str, Path, m21.stream.Score],
         score2: Union[str, Path, m21.stream.Score],
         out_path1:  Union[str, Path] = None,
         out_path2:  Union[str, Path] = None,
         force_parse: bool = True,
         visualize_diffs: bool = True,
         detail: DetailLevel = DetailLevel.Default
        ) -> int:
    '''
    Compare two musical scores and optionally save/display the differences as two marked-up
    rendered PDFs.

    Args:
        score1 (str, Path, music21.stream.Score): The first music score to compare. The score
            can be a file of any format readable by music21 (e.g. MusicXML, MEI, Humdrum, MIDI,
            etc), or a music21 Score object.
        score2 (str, Path, music21.stream.Score): The second musical score to compare. The score
            can be a file of any format readable by music21 (e.g. MusicXML, MEI, Humdrum, MIDI,
            etc), or a music21 Score object.
        out_path1 (str, Path): Where to save the first marked-up rendered score PDF.
            If out_path1 is None, both PDFs will be displayed in the default PDF viewer.
            (default is None)
        out_path2 (str, Path): Where to save the second marked-up rendered score PDF.
            If out_path2 is None, both PDFs will be displayed in the default PDF viewer.
            (default is None)
        force_parse (bool): Whether or not to force music21 to re-parse a file it has parsed
            previously.
            (default is True)
        visualize_diffs (bool): Whether or not to render diffs as marked up PDFs. If False,
            the only result of the call will be the return value (the number of differences).
            (default is True)
        detail (DetailLevel): What level of detail to use during the diff.  Can be
            GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
            currently equivalent to AllObjects).

    Returns:
        int: The number of differences found (0 means the scores were identical, None means the diff failed)
    '''
    # Use the new Humdrum/MEI importers from converter21 in place of the ones in music21...
    # Comment out this line to go back to music21's built-in Humdrum/MEI importers.
    converter21.register()

    badArg1: bool = False
    badArg2: bool = False

    # Convert input strings to Paths
    if isinstance(score1, str):
        try:
            score1 = Path(score1)
        except:
            print(f'score1 ({score1}) is not a valid path.', file=sys.stderr)
            badArg1 = True

    if isinstance(score2, str):
        try:
            score2 = Path(score2)
        except:
            print(f'score2 ({score2}) is not a valid path.', file=sys.stderr)
            badArg2 = True

    if badArg1 or badArg2:
        return None

    if isinstance(score1, Path):
        fileName1 = score1.name
        fileExt1 = score1.suffix

        if fileExt1 not in _getInputExtensionsList():
            print(f'score1 file extension ({fileExt1}) not supported by music21.', file=sys.stderr)
            badArg1 = True

        if not badArg1:
            # pylint: disable=broad-except
            try:
                score1 = m21.converter.parse(score1, forceSource = force_parse)
            except Exception as e:
                print(f'score1 ({fileName1}) could not be parsed by music21', file=sys.stderr)
                print(e, file=sys.stderr)
                badArg1 = True
            # pylint: enable=broad-except

    if isinstance(score2, Path):
        fileName2: str = score2.name
        fileExt2: str = score2.suffix

        if fileExt2 not in _getInputExtensionsList():
            print(f'score2 file extension ({fileExt2}) not supported by music21.', file=sys.stderr)
            badArg2 = True

        if not badArg2:
            # pylint: disable=broad-except
            try:
                score2 = m21.converter.parse(score2, forceSource = force_parse)
            except Exception as e:
                print(f'score2 ({fileName2}) could not be parsed by music21', file=sys.stderr)
                print(e, file=sys.stderr)
                badArg2 = True
            # pylint: enable=broad-except

    if badArg1 or badArg2:
        return None

    # scan each score, producing an annotated wrapper
    annotated_score1: AnnScore = AnnScore(score1, detail)
    annotated_score2: AnnScore = AnnScore(score2, detail)

    diff_list: List = None
    _cost: int = None
    diff_list, _cost = Comparison.annotated_scores_diff(annotated_score1, annotated_score2)

    numDiffs: int = len(diff_list)
    if visualize_diffs and numDiffs != 0:
        # you can change these three colors as you like...
        #Visualization.INSERTED_COLOR = 'red'
        #Visualization.DELETED_COLOR = 'red'
        #Visualization.CHANGED_COLOR = 'red'

        # color changed/deleted/inserted notes, add descriptive text for each change, etc
        Visualization.mark_diffs(score1, score2, diff_list)

        # ask music21 to display the scores as PDFs.  Composer's name will be prepended with
        # 'score1 ' and 'score2 ', respectively, so you can see which is which.
        Visualization.show_diffs(score1, score2, out_path1, out_path2)

    return numDiffs
