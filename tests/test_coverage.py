from pathlib import Path
import argparse
import sys
import json

from io import TextIOWrapper

import music21 as m21

from musicdiff import Visualization
from musicdiff.annotation import AnnScore
from musicdiff import Comparison
from musicdiff import DetailLevel

DEFAULT_DETAIL_LEVEL: int = DetailLevel.AllObjects | DetailLevel.Style | DetailLevel.Metadata

def compareListOfScorePairs(
    listFilePath: Path,
    detail: DetailLevel | int = DEFAULT_DETAIL_LEVEL
):
    outputPath = Path('/tmp/coverage_output.txt')
    with open(outputPath, 'w', encoding='utf-8') as outputf:
        pairList: list[str] = []
        with open(listFilePath, encoding='utf-8') as listf:
            s: str = listf.read()
            pairList = s.split('\n')

        for pair in pairList:
            if not pair or pair[0] == '#':
                # blank line or commented out
                print(pair)
                print(pair, file=outputf)
                outputf.flush()
                continue

            twoFiles = pair.split(' ')
            if len(twoFiles) != 2:
                raise ValueError(f'bad line in input: "{pair}"')
            path1 = Path(twoFiles[0])
            path2 = Path(twoFiles[1])
            print(str(path1.name) + ' vs ' + str(path2.name))
            print(str(path1.name) + ' vs ' + str(path2.name), file=outputf)
            outputf.flush()
            compareOnePair(path1, path2, outputf, detail)

        outputf.flush()

def compareOnePair(
    path1: Path,
    path2: Path,
    results: TextIOWrapper,
    detail: DetailLevel | int
):
    # figure out format from path's file extension
    c = m21.converter.Converter()
    fmt1 = c.getFormatFromFileExtension(path1)
    fmt2 = c.getFormatFromFileExtension(path2)
    results.flush()

    try:
        score1 = m21.converter.parse(
            path1,
            format=fmt1,
            forceSource=True
        )
        score2 = m21.converter.parse(
            path2,
            format=fmt2,
            forceSource=True
        )
        if score1 is None:
            print(': score1 creation failure')
            print(': score1 creation failure', file=results)
            results.flush()
            return
        if score2 is None:
            print(': score2 creation failure')
            print(': score2 creation failure', file=results)
            results.flush()
            return
    except KeyboardInterrupt:
        results.flush()
        sys.exit(0)

    if not isinstance(score1, m21.stream.Score):
        print(': score1 is not a Score')
        print(': score1 is not a Score', file=results)
        results.flush()
        return

    if not isinstance(score2, m21.stream.Score):
        print(': score2 is not a Score')
        print(': score2 is not a Score', file=results)
        results.flush()
        return

    if not score1.isWellFormedNotation():
        print(': score1 not well formed')
        print(': score1 not well formed', file=results)
        results.flush()
        return False

    if not score2.isWellFormedNotation():
        print(': score2 not well formed')
        print(': score2 not well formed', file=results)
        results.flush()
        return False

    try:
        # assume all score files contain only one score (reasonable, since I
        # created all the coverage score files).
        annotatedScore1 = AnnScore(score1, detail)
        annotatedScore2 = AnnScore(score2, detail)

        op_list, cost = Comparison.annotated_scores_diff(
            annotatedScore1, annotatedScore2
        )

        numDiffs = len(op_list)
        print(f'numDiffs = {numDiffs}')
        print(f'numDiffs = {numDiffs}', file=results)
        results.flush()

        # we do all of the following even if numDiffs == 0,
        # because we have constructed the coverage score files to
        # have particular differences. If they have 0 diffs, it's
        # a bug and I want to see why, so generate all the output.
        omrnedOut: dict = Visualization.get_omr_ned_output(
            cost, annotatedScore1, annotatedScore2
        )
        jsonStr: str = json.dumps(omrnedOut)
        print(jsonStr)
        print(jsonStr, file=results)

        textOut: str = Visualization.get_text_output(
            score1, score2, op_list
        )
        if textOut:
            print(textOut)
            print(textOut, file=results)
            results.flush()

        Visualization.mark_diffs(score1, score2, op_list)
        Visualization.show_diffs(score1, score2)

    except KeyboardInterrupt:
        results.flush()
        sys.exit(0)

# ------------------------------------------------------------------------------


'''
    main entry point (parse arguments and do conversion)
'''
parser = argparse.ArgumentParser()
parser.add_argument(
    'list_file',
    help='file containing a list of the file pairs to compare (full paths)'
)
args = parser.parse_args()

compareListOfScorePairs(
    Path(args.list_file)
)

print('done.')
