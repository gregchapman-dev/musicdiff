# ------------------------------------------------------------------------------
# Purpose:       musicdiff is a package for comparing music scores using music21.
#
# Authors:       Greg Chapman <gregc@mac.com>
#                musicdiff is derived from:
#                   https://github.com/fosfrancesco/music-score-diff.git
#                   by Francesco Foscarin <foscarin.francesco@gmail.com>
#
# Copyright:     (c) 2022-2024 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------

__docformat__ = "google"

import sys
import os
import json
import typing as t
from pathlib import Path

import music21 as m21
import converter21

from musicdiff.detaillevel import DetailLevel
from musicdiff.m21utils import M21Utils
from musicdiff.annotation import AnnScore
from musicdiff.comparison import Comparison
from musicdiff.visualization import Visualization

def _getInputExtensionsList() -> list[str]:
    c = m21.converter.Converter()
    inList = c.subConvertersList('input')
    result = []
    for subc in inList:
        for inputExt in subc.registerInputExtensions:
            result.append('.' + inputExt)
    return result

def _printSupportedInputFormats() -> None:
    c = m21.converter.Converter()
    inList = c.subConvertersList('input')
    print("Supported input formats are:", file=sys.stderr)
    for subc in inList:
        if subc.registerInputExtensions:
            print('\tformats   : ' + ', '.join(subc.registerFormats)
                    + '\textensions: ' + ', '.join(subc.registerInputExtensions), file=sys.stderr)

def diff(
    score1: str | Path | m21.stream.Score,
    score2: str | Path | m21.stream.Score,
    out_path1: str | Path | None = None,
    out_path2: str | Path | None = None,
    force_parse: bool = True,
    visualize_diffs: bool = True,
    print_text_output: bool = False,
    print_ser_output: bool = False,
    fix_first_file_syntax: bool = False,
    detail: DetailLevel | int = DetailLevel.Default
) -> int | None:
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
        print_text_output (bool): Whether or not to print diffs in diff-like text to stdout.
            (default is False)
        print_ser_output (bool): Whether or not to print the symbolic error rate (SER),
            which is computed as number of symbolic errors divided by the max number of
            symbols in the two scores.
            (default is False)
        fix_first_file_syntax (bool): Whether to attempt to fix syntax errors in the first
            file (and add the number of such fixes to the returned number of edits/cost in
            symbol errors).
            (default is False)
        detail (DetailLevel | int): What level of detail to use during the diff.
            Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
            AllObjects), or any combination (with | or &~) of those or NotesAndRests,
            Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
            Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
            Style, Metadata, or Voicing.

    Returns:
        int | None: The total cost of the edits, i.e. the number of individual symbols
            that must be added or deleted. (0 means that the scores were identical, and
            None means that one or more of the input files failed to parse.)
    '''
    # Use the Humdrum/MEI importers from converter21 in place of the ones in music21...
    # Comment out this line to go back to music21's built-in Humdrum/MEI importers.
    converter21.register()

    badArg1: bool = False
    badArg2: bool = False
    score1Name: str | Path | None = None
    score2Name: str | Path | None = None

    # Convert input strings to Paths
    if isinstance(score1, str):
        score1Name = score1
        try:
            score1 = Path(score1)
        except Exception:  # pylint: disable=broad-exception-caught
            print(f'score1 ({score1}) is not a valid path.', file=sys.stderr)
            badArg1 = True

    if isinstance(score2, str):
        score2Name = score2
        try:
            score2 = Path(score2)
        except Exception:  # pylint: disable=broad-exception-caught
            print(f'score2 ({score2}) is not a valid path.', file=sys.stderr)
            badArg2 = True

    if badArg1 or badArg2:
        return None

    if isinstance(score1, Path):
        if not score1Name:
            score1Name = score1
        fileName1 = score1.name
        fileExt1 = score1.suffix

        if fileExt1 not in _getInputExtensionsList():
            print(f'score1 file extension ({fileExt1}) not supported by music21.', file=sys.stderr)
            badArg1 = True

        if not badArg1:
            # pylint: disable=broad-except
            try:
                sc = m21.converter.parse(
                    score1,
                    forceSource=force_parse,
                    acceptSyntaxErrors=fix_first_file_syntax
                )
                if t.TYPE_CHECKING:
                    assert isinstance(sc, m21.stream.Score)
                score1 = sc

            except Exception as e:
                print(f'score1 ({fileName1}) could not be parsed by music21', file=sys.stderr)
                print(e, file=sys.stderr)
                badArg1 = True
            # pylint: enable=broad-except

    if isinstance(score2, Path):
        if not score2Name:
            score2Name = score2
        fileName2: str = score2.name
        fileExt2: str = score2.suffix

        if fileExt2 not in _getInputExtensionsList():
            print(f'score2 file extension ({fileExt2}) not supported by music21.', file=sys.stderr)
            badArg2 = True

        if not badArg2:
            # pylint: disable=broad-except
            try:
                sc = m21.converter.parse(score2, forceSource=force_parse)
                if t.TYPE_CHECKING:
                    assert isinstance(sc, m21.stream.Score)
                score2 = sc
            except Exception as e:
                print(f'score2 ({fileName2}) could not be parsed by music21', file=sys.stderr)
                print(e, file=sys.stderr)
                badArg2 = True
            # pylint: enable=broad-except

    if badArg1 or badArg2:
        return None

    if t.TYPE_CHECKING:
        assert isinstance(score1, m21.stream.Score)
        assert isinstance(score2, m21.stream.Score)

    # scan each score, producing an annotated wrapper
    annotated_score1: AnnScore = AnnScore(score1, detail)
    annotated_score2: AnnScore = AnnScore(score2, detail)

    diff_list: list
    cost: int
    diff_list, cost = Comparison.annotated_scores_diff(annotated_score1, annotated_score2)

    if cost != 0:
        if visualize_diffs:
            # you can change these three colors as you like...
            # Visualization.INSERTED_COLOR = 'red'
            # Visualization.DELETED_COLOR = 'red'
            # Visualization.CHANGED_COLOR = 'red'

            # color changed/deleted/inserted notes, add descriptive text for each change, etc
            Visualization.mark_diffs(score1, score2, diff_list)

            # ask music21 to display the scores as PDFs.  Composer's name will be prepended with
            # 'score1 ' and 'score2 ', respectively, so you can see which is which.
            Visualization.show_diffs(score1, score2, out_path1, out_path2)

    if print_ser_output:
        ser_output: dict = Visualization.get_ser_output(
            cost, annotated_score2
        )
        jsonStr: str = json.dumps(ser_output, indent=4)
        print(jsonStr)

    if print_text_output:
        text_output: str = Visualization.get_text_output(
            score1, score2, diff_list, score1Name=score1Name, score2Name=score2Name
        )
        if text_output:
            if print_ser_output and print_text_output:
                # put a blank line between them
                print('')
            print(text_output)

    return cost
