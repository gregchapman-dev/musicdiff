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
# Copyright:     (c) 2022-2024 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------
import sys
import argparse

from musicdiff import DetailLevel
from musicdiff import diff

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
        "-i",
        "--include",
        default=["allobjects"],
        nargs="*",
        choices=[
            "decoratednotesandrests",
            "otherobjects",
            "allobjects",

            "style",
            "metadata",
            "voicing",

            "notesandrests",
            "beams",
            "tremolos",
            "ornaments",
            "articulations",
            "ties",
            "slurs",

            "signatures",
            "directions",
            "barlines",
            "staffdetails",
            "chordsymbols",
            "ottavas",
            "arpeggios",
            "lyrics"],
        help="included details (can include multiple details)"
    )
    parser.add_argument(
        "-x",
        "--exclude",
        default=[],
        nargs="*",
        choices=[
            "decoratednotesandrests",
            "otherobjects",
            "allobjects",

            "style",
            "metadata",
            "voicing",

            "notesandrests",
            "beams",
            "tremolos",
            "ornaments",
            "articulations",
            "ties",
            "slurs",

            "signatures",
            "directions",
            "barlines",
            "staffdetails",
            "chordsymbols",
            "ottavas",
            "arpeggios",
            "lyrics"],
        help="excluded details (can exclude multiple details)"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=["visual"],
        nargs="*",
        choices=["visual", "v", "text", "t", "ser", "s"],
        help="'visual'/'v' is marked up scores, rendered to PDFs;"
        + " 'text'/'t' is diff-like, written to stdout;"
        + " 'ser'/'s is the symbolic error rate (symbol errors/total symbols),"
        + " written to stdout."
        + " Any, all, or none of these can be requested."
    )

    parser.add_argument(
        "--fix_first_file_syntax",
        action='store_true',
        help="If set, syntax errors in the first input file will be fixed"
        + " (if possible) so the diff can continue. Any fixes will be"
        + " added to the returned cost in symbol errors). Note that errors"
        + " in the second file (assumed to be the ground truth) are never"
        + " corrected.  Note also that this currently only works for Humdrum"
        + " **kern files."
    )

    args = parser.parse_args()

    detail: int = DetailLevel.Default
    if args.include:
        detail = 0
        for det in args.include:
            # combos
            if det == "decoratednotesandrests":
                detail |= DetailLevel.DecoratedNotesAndRests
            elif det == "otherobjects":
                detail |= DetailLevel.OtherObjects
            elif det == "allobjects":
                detail |= DetailLevel.AllObjects

            # bits not in any combo
            elif det == "style":
                detail |= DetailLevel.Style
            elif det == "voicing":
                detail |= DetailLevel.Voicing
            elif det == "metadata":
                detail |= DetailLevel.Metadata

            # bits in the DecoratedNotesAndRests combo
            elif det == "notesandrests":
                detail |= DetailLevel.NotesAndRests
            elif det == "beams":
                detail |= DetailLevel.Beams
            elif det == "tremolos":
                detail |= DetailLevel.Tremolos
            elif det == "ornaments":
                detail |= DetailLevel.Ornaments
            elif det == "articulations":
                detail |= DetailLevel.Articulations
            elif det == "ties":
                detail |= DetailLevel.Ties
            elif det == "slurs":
                detail |= DetailLevel.Slurs

            # bits in the OtherObjects combo
            elif det == "signatures":
                detail |= DetailLevel.Signatures
            elif det == "directions":
                detail |= DetailLevel.Directions
            elif det == "barlines":
                detail |= DetailLevel.Barlines
            elif det == "staffdetails":
                detail |= DetailLevel.StaffDetails
            elif det == "chordsymbols":
                detail |= DetailLevel.ChordSymbols
            elif det == "ottavas":
                detail |= DetailLevel.Ottavas
            elif det == "arpeggios":
                detail |= DetailLevel.Arpeggios
            elif det == "lyrics":
                detail |= DetailLevel.Lyrics

    if detail != 0 and args.exclude:
        for det in args.exclude:
            # combos
            if det == "decoratednotesandrests":
                detail &= ~DetailLevel.DecoratedNotesAndRests
            elif det == "otherobjects":
                detail &= ~DetailLevel.OtherObjects
            elif det == "allobjects":
                detail &= ~DetailLevel.AllObjects

            # bits not in any combo
            elif det == "style":
                detail &= ~DetailLevel.Style
            elif det == "voicing":
                detail &= ~DetailLevel.Voicing
            elif det == "metadata":
                detail &= ~DetailLevel.Metadata

            # bits in the DecoratedNotesAndRests combo
            elif det == "notesandrests":
                detail &= ~DetailLevel.NotesAndRests
            elif det == "beams":
                detail &= ~DetailLevel.Beams
            elif det == "tremolos":
                detail &= ~DetailLevel.Tremolos
            elif det == "ornaments":
                detail &= ~DetailLevel.Ornaments
            elif det == "articulations":
                detail &= ~DetailLevel.Articulations
            elif det == "ties":
                detail &= ~DetailLevel.Ties
            elif det == "slurs":
                detail &= ~DetailLevel.Slurs

            # bits in the OtherObjects combo
            elif det == "signatures":
                detail &= ~DetailLevel.Signatures
            elif det == "directions":
                detail &= ~DetailLevel.Directions
            elif det == "barlines":
                detail &= ~DetailLevel.Barlines
            elif det == "staffdetails":
                detail &= ~DetailLevel.StaffDetails
            elif det == "chordsymbols":
                detail &= ~DetailLevel.ChordSymbols
            elif det == "ottavas":
                detail &= ~DetailLevel.Ottavas
            elif det == "arpeggios":
                detail &= ~DetailLevel.Arpeggios
            elif det == "lyrics":
                detail &= ~DetailLevel.Lyrics

    visualize_diffs: bool = "visual" in args.output or "v" in args.output
    print_text_output: bool = "text" in args.output or "t" in args.output
    print_ser_output: bool = "ser" in args.output or "s" in args.output
    fix_first_file_syntax: bool = args.fix_first_file_syntax is True

    cost: int | None = diff(
        args.file1,
        args.file2,
        detail=detail,
        visualize_diffs=visualize_diffs,
        print_text_output=print_text_output,
        print_ser_output=print_ser_output,
        fix_first_file_syntax=fix_first_file_syntax,
    )

    if cost is None:
        print('musicdiff failed.', file=sys.stderr)
    elif cost == 0:
        print(f'Scores in {args.file1} and {args.file2} are identical.', file=sys.stderr)
