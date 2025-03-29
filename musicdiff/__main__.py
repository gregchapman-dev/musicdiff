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
# Copyright:     (c) 2022-2025 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------
import sys
import argparse

from musicdiff import DetailLevel
from musicdiff import diff, diff_ml_training

# ------------------------------------------------------------------------------

'''
    main entry point (parse arguments and do conversion)
'''
if __name__ == "__main__":
    usage: str = """python3 -m musicdiff [-h]
                            [-i [{decoratednotesandrests,otherobjects,allobjects,style,metadata,voicing,notesandrests,beams,tremolos,ornaments,articulations,ties,slurs,signatures,directions,barlines,staffdetails,chordsymbols,ottavas,arpeggios,lyrics} ...]]
                            [-x [{decoratednotesandrests,otherobjects,allobjects,style,metadata,voicing,notesandrests,beams,tremolos,ornaments,articulations,ties,slurs,signatures,directions,barlines,staffdetails,chordsymbols,ottavas,arpeggios,lyrics} ...]]
                            [-o [{visual,v,text,t,omrned,o} ...]]
                            [--fix_first_file_syntax]
                            file1 file2

Alternate usage (for ML training runs):
usage: python3 -m musicdiff [-h]
                            --ml_training_evaluation
                            --ground_truth_folder gtfolderpath
                            --predicted_folder predfolderpath
                            --output_folder outputfolderpath
                            [-i [{decoratednotesandrests,otherobjects,allobjects,style,metadata,voicing,notesandrests,beams,tremolos,ornaments,articulations,ties,slurs,signatures,directions,barlines,staffdetails,chordsymbols,ottavas,arpeggios,lyrics} ...]]
                            [-x [{decoratednotesandrests,otherobjects,allobjects,style,metadata,voicing,notesandrests,beams,tremolos,ornaments,articulations,ties,slurs,signatures,directions,barlines,staffdetails,chordsymbols,ottavas,arpeggios,lyrics} ...]]

"""
    epilog: str = """\
If --ml_training_evaluation is specified, the following options are
required:
  --ground_truth_folder gtfolderpath
                        Must be set if (and only if) --ml_training_evaluation
                        is set. A folder full of ground truth scores. The
                        filenames in this folder must be identical to those
                        in the predicted folder.
  --predicted_folder predfolderpath
                        Must be set if (and only if) --ml_training_evaluation
                        is set. A folder full of scores predicted by the model.
                        The filenames in this folder must be identical to those
                        in the predicted folder.
  --output_folder outputfolderpath
                        Must be set if (and only if) --ml_training_evaluation
                        is set. A folder where the musicdiff results (OMR-NED
                        metrics for each predicted score, as well as an overall
                        OMR-NED metric for the run) will be written into an
                        output.csv file. This folder must already exist.
"""
    parser = argparse.ArgumentParser(
        prog='python3 -m musicdiff',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=usage,
        epilog=epilog,
        description='Music score notation diff (MusicXML, MEI, Humdrum, etc)'
    )

    # arg parsing is quite different for training vs non-training
    training_mode: bool = '--ml_training_evaluation' in sys.argv

    if not training_mode:
        parser.add_argument(
            "file1",
            help=(
                "first music score file to compare"
                + " (cannot be specified with --ml_training_evaluation)"
            )
        )
        parser.add_argument(
            "file2",
            help=(
                "second music score file to compare"
                + " (cannot be specified with --ml_training_evaluation)"
            )
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

    if not training_mode:
        parser.add_argument(
            "-o",
            "--output",
            default=["visual"],
            nargs="*",
            choices=["visual", "v", "text", "t", "omrned", "o"],
            help="'visual'/'v' is marked up scores, rendered to PDFs;"
            + " 'text'/'t' is diff-like, written to stdout;"
            + " 'omrned'/'o' is the OMR Normalized Edit Distance"
            + " (OMR edit distance/total symbols),"
            + " written to stdout."
            + " Any, all, or none of these can be requested."
            + " Cannot be specified with --ml_training_evaluation."
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
            + " Cannot be specified with --ml_training_evaluation."
        )

    parser.add_argument(
        "--ml_training_evaluation",
        action='store_true',
        help="If set, ML training evaluation mode (evaluation of folders of"
        + " scores) is triggered. Ground truth, predicted, and output folders"
        + " must be specified, and the ground truth folder and predicted folders"
        + " must contain files with the same names. Every score in the predicted"
        + " folder will be compared with the score of the same name in the"
        + " ground truth folder. Syntax errors in predicted scores will be fixed"
        + " if possible, and OMR-NED metrics for each predicted score (as well as"
        + " an overall metric for the run) will be produced in output.csv"
        + " in the output folder. No files can be specified on the command line,"
        + " nor can -o/--output or --fix_first_file_syntax be specified."
        + " -i/--include and -x/--exclude, of course, are valid options to"
        + " specify."
    )

    if training_mode:
        parser.add_argument(
            "--ground_truth_folder",
            help="Must be set if (and only if) --ml_training_eval is set."
            + " A folder full of ground truth scores.  The filenames in this"
            + " folder must be identical to those in the predicted folder."
        )

        parser.add_argument(
            "--predicted_folder",
            help="Must be set if (and only if) --ml_training_eval is set."
            + " A folder full of scores predicted by the model.  The filenames"
            + " in this folder must be identical to those in the ground truth"
            + " folder."
        )

        parser.add_argument(
            "--output_folder",
            help="Must be set if (and only if) --ml_training_eval is set."
            + " A folder where the musicdiff results will be written in an"
            + " output.csv file."
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

    bad_args: bool = False

    ml_training_evaluation: bool = args.ml_training_evaluation
    if ml_training_evaluation:
        if not args.ground_truth_folder or not args.predicted_folder or not args.output_folder:
            print(
                "If --ml_training_evaluation is set, --ground_truth_folder, --predicted_folder,"
                + " and --output_folder must also be set."
            )
            bad_args = True

    if bad_args:
        sys.exit(-1)

    # The big mode switch: folders or files?
    if ml_training_evaluation:
        # folders
        out_file_path: str
        overall_score: float
        overall_score, out_file_path = diff_ml_training(
            detail=detail,
            predicted_folder=args.predicted_folder,
            ground_truth_folder=args.ground_truth_folder,
            output_folder=args.output_folder
        )
        print(
            f'ML training overall score is: {overall_score}, output file is: {out_file_path}',
            file=sys.stderr
        )
        sys.exit(0)

    # files
    visualize_diffs: bool = "visual" in args.output or "v" in args.output
    print_text_output: bool = "text" in args.output or "t" in args.output
    print_omr_ned_output: bool = "omrned" in args.output or "o" in args.output
    fix_first_file_syntax: bool = args.fix_first_file_syntax is True

    cost: int | None = diff(
        args.file1,
        args.file2,
        detail=detail,
        visualize_diffs=visualize_diffs,
        print_text_output=print_text_output,
        print_omr_ned_output=print_omr_ned_output,
        fix_first_file_syntax=fix_first_file_syntax,
    )

    if cost is None:
        print('musicdiff failed.', file=sys.stderr)
    elif cost == 0:
        print(f'Scores in {args.file1} and {args.file2} are identical.', file=sys.stderr)
