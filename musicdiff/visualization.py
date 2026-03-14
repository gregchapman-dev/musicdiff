# ------------------------------------------------------------------------------
# Purpose:       visualization is a diff visualization package for use by musicdiff.
#                musicdiff is a package for comparing music scores using music21.
#
# Authors:       Greg Chapman <gregc@mac.com>
#                musicdiff is derived from:
#                   https://github.com/fosfrancesco/music-score-diff.git
#                   by Francesco Foscarin <foscarin.francesco@gmail.com>
#
# Copyright:     (c) 2022-2025 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------

__docformat__ = "google"

from pathlib import Path
import sys
import re
# import typing as t
import collections
from fractions import Fraction

import music21 as m21
from music21.common import OffsetQL, opFrac

from musicdiff.annotation import AnnScore, AnnExtra, AnnNote, AnnObject
from musicdiff.comparison import DiffOperation
from musicdiff import M21Utils
from musicdiff import DetailLevel
from musicdiff import EvaluationMetrics

class Visualization:
    # These can be set by the client to different colors
    INSERTED_COLOR = "red"
    """
    `INSERTED_COLOR` can be set to customize the rendered score markup that `mark_diffs` does.
    """
    DELETED_COLOR = "red"
    """
    `DELETED_COLOR` can be set to customize the rendered score markup that `mark_diffs` does.
    """
    CHANGED_COLOR = "red"
    """
    `CHANGED_COLOR` can be set to customize the rendered score markup that `mark_diffs` does.
    """

    COLOR_FOR_OPNAME: dict[str, str] = {
        "inserted": INSERTED_COLOR,
        "deleted": DELETED_COLOR,
        "changed": CHANGED_COLOR
    }


    VisFunctionType = collections.abc.Callable[
        [
            DiffOperation,
            m21.stream.Score,
            m21.stream.Score,
            str,
            str,
            bool,
            str,
            str,
        ],
        list[str]
    ]

    @staticmethod
    def mark_diffs(
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        op_list: list[DiffOperation]
    ) -> None:
        """
        Mark up two music21 scores with the differences described by an operations
        list (e.g. a list returned from `musicdiff.Comparison.annotated_scores_diff`).

        Args:
            score1 (music21.stream.Score): The first score to mark up
            score2 (music21.stream.Score): The second score to mark up
            op_list (list[DiffOperation]): The operations list that describes the difference
                between the two scores
        """
        Visualization._visualize_op_list(
            op_list,
            score1,
            score2,
            "draw"
        )

    @staticmethod
    def _draw_diffs(
        op: DiffOperation,
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        # the next set of params are only for drawing in the score (used here)
        opname: str = "",  # must be "inserted", "deleted", "changed"
        custom_text: str = "",  # replaces opname + name + sub_name
        # (e.g. "changed grace note" instead of "changed" + "note" + "grace")
        color_accidental_too: bool = False,
        # the next set of params are for both types of visualization
        name: str = "",  # name of object
        sub_name: str = "",  # e.g. "content" or "sym"
    ) -> list[str]:
        m21_obj1: m21.base.Music21Object | None
        m21_obj2: m21.base.Music21Object | None
        m21_obj1, m21_obj2 = op.get_m21_objs(score1, score2)

        note_idx1: int | None = None
        note_idx2: int | None = None
        if op.indexes is not None:
            if isinstance(op.indexes, int):
                if op.obj1 is not None and op.obj2 is None:
                    note_idx1 = op.indexes
                elif op.obj1 is None and op.obj2 is not None:
                    note_idx2 = op.indexes
                else:
                    raise ValueError(
                        "invalid call to _draw_diffs: one note_idx, but two (or zero) chords"
                    )
            else:
                assert isinstance(op.indexes, tuple)
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                note_idx1 = op.indexes[0]
                note_idx2 = op.indexes[1]


        # 88888 need to notice sub_name = style and replace sub_name below with changeStr

        if m21_obj1 is not None:
            obj1_text: str = custom_text
            if not obj1_text:
                # opname + name + sub_name
                obj1_text = name
                if not obj1_text:
                    obj1_text = m21_obj1.classes[0]
                if sub_name:
                    obj1_text += " " + sub_name
                obj1_text = opname + " " + obj1_text
            Visualization._draw_diff(
                m21_obj1,
                text=obj1_text,
                color=Visualization.COLOR_FOR_OPNAME[opname],
                note_idx=note_idx1,
                color_accidental_too=color_accidental_too
            )

        if m21_obj2 is not None:
            obj2_text: str = custom_text
            if not obj2_text:
                # opname + name + sub_name
                obj2_text = name
                if not obj2_text:
                    obj2_text = m21_obj2.classes[0]
                if sub_name:
                    obj2_text += " " + sub_name
                obj2_text = opname + " " + obj2_text
            Visualization._draw_diff(
                m21_obj2,
                text=obj2_text,
                color=Visualization.COLOR_FOR_OPNAME[opname],
                note_idx=note_idx2,
                color_accidental_too=color_accidental_too
            )

        return []  # ignored by callers

    @staticmethod
    def _draw_diff(
        m21_obj: m21.base.Music21Object,
        text: str,
        color: str,
        note_idx: int | None = None,
        color_accidental_too: bool = False
    ):
        # Create (and color) text expression, and insert it as requested
        textExp = m21.expressions.TextExpression(text)
        textExp.style.color = color

        insert_in_stream: m21.stream.Stream | None = None
        insert_at_offset: OffsetQL | None = None
        if isinstance(m21_obj, m21.stream.Stream):
            if isinstance(m21_obj, m21.stream.Part):
                # insert at beginning of the first Measure of Part
                insert_in_stream = m21_obj[m21.stream.Measure].first()
                insert_at_offset = 0.
            else:
                # insert at beginning of the stream
                insert_in_stream = m21_obj
                insert_at_offset = 0.
        elif isinstance(m21_obj, m21.spanner.Spanner):
            spannerFirst: m21.base.Music21Object = m21_obj.getFirst()
            if isinstance(spannerFirst, m21.stream.Part):
                # spannerFirst is a Part, put the textExp at beginning
                # of the first Measure in the Part
                insert_in_stream = spannerFirst[m21.stream.Measure].first()
                insert_at_offset = 0.
            elif isinstance(spannerFirst, m21.stream.Stream):
                # spannerFirst is a Stream, put the textExp at beginning
                # of the Stream
                insert_in_stream = spannerFirst
                insert_at_offset = 0.
            else:
                # spannerFirst is not a Stream, put the textExp right next to it.
                insert_in_stream = spannerFirst.activeSite
                insert_at_offset = spannerFirst.offset
        else:
            # neither Stream nor Spanner, put the textExp right next to it.
            insert_in_stream = m21_obj.activeSite
            insert_at_offset = m21_obj.offset

        if insert_in_stream is not None and insert_at_offset is not None:
            insert_in_stream.insert(insert_at_offset, textExp)
        else:
            # should never happen, but might if the code above is modified.
            raise ValueError("stream or offset of descriptive text is unknown.")

        # Now color the m21_obj with the requested color
        if isinstance(m21_obj, m21.stream.Stream):
            # m21_obj is a Score or Part or Measure or Voice...
            # Color every note and rest in that stream, recursively.
            # Don't bother with accidentals (we don't bother with
            # extras either, for that matter).
            for el in m21_obj.recurse().notesAndRests:
                el.style.color = color
        elif note_idx is not None:
            if isinstance(m21_obj, m21.chord.ChordBase):
                specified_note: m21.note.GeneralNote = m21_obj.notes[note_idx]
                specified_note.style.color = color
                if color_accidental_too and hasattr(specified_note, 'pitch'):
                    if specified_note.pitch.accidental:
                        specified_note.pitch.accidental.style.color = color
            else:
                # Can happen if imported xml has repeated xml:id values,
                # so getElementById returns an unexpected non-Chord.
                # Don't crash by looking for notes, just color whatever the
                # non-Chord object is.
                m21_obj.style.color = color
                if color_accidental_too and hasattr(m21_obj, 'pitch'):
                    if m21_obj.pitch.accidental:
                        m21_obj.pitch.accidental.style.color = color
        else:
            m21_obj.style.color = color
            if color_accidental_too and hasattr(m21_obj, 'pitch'):
                if m21_obj.pitch.accidental:
                    m21_obj.pitch.accidental.style.color = color

    @staticmethod
    def _dict_change_str(dict1: dict[str, str], dict2: dict[str, str]) -> str:
        # returns a comma-delimited list of differing keys (either missing in
        # one of the dictionaries, or existing in both but with different values).
        change_str: str = ""
        for k1, v1 in dict1.items():
            if k1 not in dict2 or dict2[k1] != v1:
                if change_str:
                    change_str += ","
                change_str += k1
        # one last thing: check for keys in dict2 that aren't in dict1
        for k2 in dict2:
            if k2 not in dict1:
                if change_str:
                    change_str += ","
                change_str += k2
        return change_str

    @staticmethod
    def show_diffs(
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        out_path1: str | Path | None = None,
        out_path2: str | Path | None = None
    ) -> None:
        """
        Render two (presumably marked-up) music21 scores.  If both out_path1 and
        out_path2 are not None, save the rendered PDFs at those two locations,
        otherwise just display them using the default PDF viewer on the system.

        Args:
            score1 (music21.stream.Score): The first score to render
            score2 (music21.stream.Score): The second score to render
            out_path1 (str, Path): Where to save the first marked-up rendered score PDF.
                If out_path1 is None, both PDFs will be displayed in the default PDF viewer.
                (default is None)
            out_path2 (str, Path): Where to save the second marked-up rendered score PDF.
                If out_path2 is None, both PDFs will be displayed in the default PDF viewer.
                (default is None)
        """
        # display the two (presumably annotated) scores

        # avoid some crashes during write()/show() operations
        from converter21 import M21Utilities
        M21Utilities.fixupComplexHiddenRests(score1, inPlace=True)
        M21Utilities.fixupComplexHiddenRests(score2, inPlace=True)

        originalComposer1: str | None = None
        originalComposer2: str | None = None

        if score1.metadata is None:
            score1.metadata = m21.metadata.Metadata()
        if score2.metadata is None:
            score2.metadata = m21.metadata.Metadata()

        originalComposer1 = score1.metadata.composer
        if originalComposer1 is None:
            score1.metadata.composer = "score1"
        else:
            score1.metadata.composer = "score1          " + originalComposer1

        originalComposer2 = score2.metadata.composer
        if originalComposer2 is None:
            score2.metadata.composer = "score2"
        else:
            score2.metadata.composer = "score2          " + originalComposer2

        # save files if requested
        if (out_path1 is not None) and (out_path2 is not None):
            score1.write("musicxml.pdf", makeNotation=False, fp=out_path1)
            score2.write("musicxml.pdf", makeNotation=False, fp=out_path2)
            print(f"Annotated scores saved in {out_path1} and {out_path2}.", file=sys.stderr)
        else:
            # just display the scores
            score1.show("musicxml.pdf", makeNotation=False)
            score2.show("musicxml.pdf", makeNotation=False)

    @staticmethod
    def _location_of(m21obj: m21.base.Music21Object, score: m21.stream.Score) -> str:
        output: str
        meas: m21.stream.Stream | None
        part: m21.stream.Stream | None
        staffNum: int
        fractionalBeats: OffsetQL

        if isinstance(m21obj, (m21.metadata.Metadata, m21.layout.StaffGroup)):
            # These are not in the timeline.  Put them first (there may be a
            # a measure 0/staff 0, but the first beat of that measure is beat 1).
            output = "measure 0, staff 0, beat 0.0"
            return output

        if isinstance(m21obj, m21.spanner.RepeatBracket):
            # spans measures, location is start of first measure in RepeatBracket
            meas = m21obj.getFirst()
            if not isinstance(meas, m21.stream.Measure):
                return ""
            part = score.containerInHierarchy(meas)
            if not isinstance(part, m21.stream.Part):
                return ""
            staffNum = M21Utils.get_part_index(part, score)
            staffNum += 1  # staff number is 1-based
            output = f"measure {M21Utils.get_measure_number_with_suffix(meas, part)}, "
            output += f"staff {staffNum}, "
            fractionalBeats = 1.
            output += f"beat {M21Utils.ql_to_string(fractionalBeats)}"
            return output

        # part
        if isinstance(m21obj, m21.stream.Part):
            staffNum = M21Utils.get_part_index(m21obj, score)
            staffNum += 1  # staffNum is 1-based
            output = "measure 0, "
            output += f"staff {staffNum}, "
            fractionalBeats = 1.
            output += f"beat {M21Utils.ql_to_string(fractionalBeats)}"
            return output

        # measure
        if isinstance(m21obj, m21.stream.Measure):
            part = score.containerInHierarchy(m21obj)
            if not isinstance(part, m21.stream.Part):
                return ""
            staffNum = M21Utils.get_part_index(part, score)
            staffNum += 1  # staffNum is 1-based
            output = f"measure {M21Utils.get_measure_number_with_suffix(m21obj, part)}, "
            output += f"staff {staffNum}, "
            fractionalBeats = 1.
            output += f"beat {M21Utils.ql_to_string(fractionalBeats)}"
            return output

        # voice
        if isinstance(m21obj, m21.stream.Voice):
            meas = score.containerInHierarchy(m21obj)
            if not isinstance(meas, m21.stream.Measure):
                return ""
            part = score.containerInHierarchy(meas)
            if not isinstance(part, m21.stream.Part):
                return ""
            staffNum = M21Utils.get_part_index(part, score)
            staffNum += 1  # staffNum is 1-based
            voiceStartOffset: OffsetQL = m21obj.getOffsetInHierarchy(meas)
            output = f"measure {M21Utils.get_measure_number_with_suffix(meas, part)}, "
            output += f"staff {staffNum}, "
            ts: m21.meter.TimeSignature | None = m21obj.getContextByClass(m21.meter.TimeSignature)
            if ts is None:
                ts = m21.meter.TimeSignature()  # 4/4
            fractionalBeats = M21Utils.get_beats(voiceStartOffset, ts)
            output += f"beat {M21Utils.ql_to_string(fractionalBeats)}"
            return output

        # spanner
        if isinstance(m21obj, m21.spanner.Spanner):
            first: m21.base.Music21Object | None = m21obj.getFirst()
            if first is None:
                return ""
            m21obj = first
            # fall through to handle normal non-stream/non-spanner m21obj

        # normal object (not stream, not spanner)
        container: m21.stream.Stream | None = score.containerInHierarchy(m21obj)
        if isinstance(container, m21.stream.Measure):
            meas = container
        elif isinstance(container, m21.stream.Voice):
            meas = score.containerInHierarchy(container)
            if not isinstance(meas, m21.stream.Measure):
                return ""
        else:
            return ""

        part = score.containerInHierarchy(meas)
        if not isinstance(part, m21.stream.Part):
            return ""
        staffNum = M21Utils.get_part_index(part, score)
        staffNum += 1  # staffNum is 1-based
        startOffset: OffsetQL = m21obj.getOffsetInHierarchy(meas)
        output = f"measure {M21Utils.get_measure_number_with_suffix(meas, part)}, "
        output += f"staff {staffNum}, "
        ts = m21obj.getContextByClass(m21.meter.TimeSignature)
        if ts is None:
            ts = m21.meter.TimeSignature()  # 4/4
        fractionalBeats = M21Utils.get_beats(startOffset, ts)
        output += f"beat {M21Utils.ql_to_string(fractionalBeats)}"
        return output

    READABLE_STR_NAMES: dict[str, str] = {
        "dur": "duration"
    }

    @staticmethod
    def _text_diff(
        op: DiffOperation,
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        # the next set of params are only for drawing in the score (used here)
        opname: str = "",  # must be "inserted", "deleted", "changed"
        custom_text: str = "",
        color_accidental_too: bool = False,
        # the next set of params are only for diff-like text output (unused here)
        name: str = "",  # name of object
        sub_name: str = "",  # e.g. "content" or "sym"
    ) -> list[str]:
        outputList: list[str] = []
        oneOutput: str  # one string, multiple lines (with \n at end of all but last line)

        m21_obj1: m21.base.Music21Object | None
        m21_obj2: m21.base.Music21Object | None
        m21_obj1, m21_obj2 = op.get_m21_objs(score1, score2)

        name1: str = ""
        name2: str = ""
        if name:
            name1 = name
            name2 = name
        else:
            if m21_obj1 is not None:
                name1 = m21_obj1.classes[0]
                if isinstance(op.obj1, AnnNote):
                    if op.obj1.is_in_chord:
                        assert isinstance(m21_obj1, m21.chord.ChordBase)
                        name1 = m21_obj1.notes[0].classes[0]
            if m21_obj2 is not None:
                name2 = m21_obj2.classes[0]
                if isinstance(op.obj2, AnnNote):
                    if op.obj2.is_in_chord:
                        assert isinstance(m21_obj2, m21.chord.ChordBase)
                        name2 = m21_obj2.notes[0].classes[0]

        readable_str_subname: str = ""
        changedStr: str = ""
        if sub_name:
            readable_str_subname = Visualization.READABLE_STR_NAMES.get(sub_name, sub_name)
            if sub_name == "info":
                # only AnnExtra has infodict
                assert isinstance(op.obj1, AnnExtra)
                assert isinstance(op.obj2, AnnExtra)
                changedStr = Visualization._dict_change_str(op.obj1.infodict, op.obj2.infodict)
                name1 += f":{changedStr}"
                name2 += f":{changedStr}"
            elif sub_name == "style":
                # every AnnObject has styledict
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                changedStr = Visualization._dict_change_str(op.obj1.styledict, op.obj2.styledict)
                name2 += f":{changedStr}"
            else:
                # other sub_names just go in the output
                name1 += f":{sub_name}"
                name2 += f":{sub_name}"

        if m21_obj1 is not None:
            assert op.obj1 is not None
            note_idx: int = 0
            if op.indexes is not None:
                if isinstance(m21_obj1, m21.chord.ChordBase):
                    if isinstance(op.indexes, int):
                        note_idx = op.indexes
                    else:
                        note_idx = op.indexes[0]
                else:
                    # Can happen if imported xml has repeated xml:id values,
                    # so getElementById returns an unexpected non-Chord.
                    # Don't crash by looking for notes, just use whatever the
                    # non-Chord object is.
                    pass

            newLine: str = f"@@ {Visualization._location_of(m21_obj1, score1)} @@\n"
            oneOutput = newLine
            readable: str = op.obj1.readable_str(
                readable_str_subname, idx=note_idx, changedStr=changedStr
            )
            newLine = f"-({name1}) {readable}"
            oneOutput += newLine

        if m21_obj2 is not None:
            assert op.obj2 is not None
            # do we need a location_of(2)?  Yes if no obj1, and yes if obj1 offset is different.
            if op.obj1 is None:
                # This is the first line of the output
                newLine = f"@@ {Visualization._location_of(m21_obj2, score2)} @@\n"
                oneOutput = newLine
            elif op.obj1.offset != op.obj2.offset:
                # not first line, and we need location_of(2)
                outputList.append(oneOutput)
                newLine = f"@@ {Visualization._location_of(m21_obj2, score2)} @@\n"
                oneOutput = newLine
            else:
                # not first line, but no location_of(2) needed; just an EOL
                oneOutput += "\n"

            note_idx = 0
            if op.indexes is not None:
                if isinstance(m21_obj1, m21.chord.ChordBase):
                    if isinstance(op.indexes, int):
                        note_idx = op.indexes
                    else:
                        note_idx = op.indexes[1]
                else:
                    # Can happen if imported xml has repeated xml:id values,
                    # so getElementById returns an unexpected non-Chord.
                    # Don't crash by looking for notes, just use whatever the
                    # non-Chord object is.
                    pass

            readable = op.obj2.readable_str(
                readable_str_subname, idx=note_idx, changedStr=changedStr
            )
            newLine = f"+({name2}) {readable}"
            oneOutput += newLine

        outputList.append(oneOutput)
        return outputList

    @staticmethod
    def get_text_output(
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        op_list: list[DiffOperation],
        score1Name: str | Path | None = None,
        score2Name: str | Path | None = None
    ) -> str:
        """
        Generate text output from the differences described by an operations list
        (e.g. a list returned from `musicdiff.Comparison.annotated_scores_diff`).

        Args:
            score1 (music21.stream.Score): The first score that was compared
            score2 (music21.stream.Score): The second score that was compared
            op_list (list[DiffOperation]): The operations list that describes the difference
                between the two scores
            score1Name (str | Path | None): The name to use for the first score in the text output
            score2Name (str | Path | None): The name to use for the second score in the text output
        """
        output: str | None = Visualization._visualize_op_list(
            op_list,
            score1,
            score2,
            "text",
            score1Name,
            score2Name
        )

        assert isinstance(output, str)
        return output

    @staticmethod
    def _visualize_op_list(
        op_list: list[DiffOperation],
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        vis_type: str,
        score1Name: str | Path | None = None,
        score2Name: str | Path | None = None,
    ) -> str | None:
        """
        Generate text output from the differences described by an operations list
        (e.g. a list returned from `musicdiff.Comparison.annotated_scores_diff`).

        Args:
            score1 (music21.stream.Score): The first score that was compared
            score2 (music21.stream.Score): The second score that was compared
            op_list (list[DiffOperation]): The operations list that describes the difference
                between the two scores
            score1Name (str | Path | None): The name to use for the first score in the text output
            score2Name (str | Path | None): The name to use for the second score in the text output
        """
        vis_func: Visualization.VisFunctionType

        output: str
        outputList: list[str] = []

        if vis_type == "text":
            vis_func = Visualization._text_diff
        elif vis_type == "draw":
            vis_func = Visualization._draw_diffs
        else:
            raise ValueError(f"invalid vis_type: {vis_type}. Must be 'text' or 'draw'.")

        for op in op_list:
            text_diff: list[str] | None
            # part
            if op.name == "inspart":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="inserted", name="part")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delpart":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2, opname="deleted", name="part")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # bar
            if op.name == "insbar":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="inserted", name="measure")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delbar":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2, opname="deleted", name="measure")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # voices
            if op.name == "voiceins":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="inserted", name="voice")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "voicedel":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2, opname="deleted", name="voice")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # extra
            if op.name == "extrains":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="inserted")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extradel":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2, opname="deleted")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extracontentedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="content")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extrasymboledit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="symbolic")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extrainfoedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="info")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extraoffsetedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="offset")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extradurationedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="dur")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "extrastyleedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="style")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # staff groups
            if op.name == "staffgrpins":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="inserted", name="StaffGroup")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "staffgrpdel":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2, opname="deleted", name="StaffGroup")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "staffgrpnameedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="StaffGroup", sub_name="name")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "staffgrpabbreviationedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="StaffGroup", sub_name="abbr")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "staffgrpsymboledit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="StaffGroup", sub_name="sym")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "staffgrpbartogetheredit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="StaffGroup", sub_name="barline")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "staffgrppartindicesedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="StaffGroup", sub_name="parts")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # note
            if op.name == "noteins":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                assert op.indexes is None or isinstance(op.indexes, int)
                text_diff = vis_func(op, score1, score2, opname="inserted")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "notedel":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                assert op.indexes is None or isinstance(op.indexes, int)
                text_diff = vis_func(op, score1, score2, opname="deleted")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # pitch
            if op.name == "pitchnameedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, tuple)  # both indices must be there
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="pitch")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "inspitch":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, int)  # the index must be there
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="pitch", custom_text="inserted note in chord")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delpitch":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, int)  # the index must be there
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="pitch", custom_text="deleted note from chord")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "headedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="head")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "graceedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="grace", custom_text="changed grace note")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "graceslashedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="graceslash", custom_text="changed grace note slash")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # beam
            if op.name == "insbeam":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="flagsbeams", custom_text="increased flags")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delbeam":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="flagsbeams", custom_text="decreased flags")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editbeam":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="flagsbeams", custom_text="changed flags")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editnoteshape":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="noteshape", custom_text="changed note shape")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "insspace":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="spacebefore", custom_text="inserted space before")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delspace":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="spacebefore", custom_text="deleted space before")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editspace":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="spacebefore", custom_text="changed space before")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editnoteheadfill":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="notefill", custom_text="changed note head fill")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editnoteheadparenthesis":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="noteparen", custom_text="changed note head paren")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editstemdirection":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="stemdir", custom_text="changed stem direction")
                text_diff = vis_func(op, score1, score2, sub_name="stemdir")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editstyle":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, opname="changed", sub_name="style")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # accident
            if op.name == "accidentins":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, tuple)  # both indices must be there
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="accid", custom_text="inserted accidental")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "accidentdel":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, tuple)  # both indices must be there
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="accid", custom_text="deleted accidental")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "accidentedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, tuple)  # both indices must be there
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="accid", custom_text="changed accidental")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "dotins":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="dots", custom_text="inserted dot")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "dotdel":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="dots", custom_text="deleted dot")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # tuplets
            if op.name == "instuplet":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="tuplet", custom_text="inserted tuplet")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "deltuplet":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="tuplet", custom_text="deleted tuplet")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "edittuplet":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="tuplet", custom_text="changed tuplet")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # ties
            if op.name == "tieins":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, tuple)  # both indices must be there
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="tie", custom_text="inserted tie")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "tiedel":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                assert isinstance(op.indexes, tuple)  # both indices must be there
                assert len(op.indexes) == 2
                assert isinstance(op.indexes[0], int)
                assert isinstance(op.indexes[1], int)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="tie", custom_text="deleted tie")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # expressions
            if op.name == "insexpression":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="expression", custom_text="inserted expression")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delexpression":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="expression", custom_text="deleted expression")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editexpression":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="expression", custom_text="changed expression")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # articulations
            if op.name == "insarticulation":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", sub_name="artic", custom_text="inserted articulation")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "delarticulation":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", sub_name="artic", custom_text="deleted articulation")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "editarticulation":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", sub_name="artic", custom_text="changed articulation")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # lyrics
            if op.name == "lyricins":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="inserted", name="Lyric")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "lyricdel":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2,
                    opname="deleted", name="Lyric")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "lyricedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="Lyric", sub_name="rawtext",
                    custom_text="changed lyric")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "lyricnumedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="Lyric", sub_name="number",
                    custom_text="changed lyric verse num")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "lyricidedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="Lyric", sub_name="id",
                    custom_text="changed lyric verse id")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "lyricoffsetedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="Lyric", sub_name="offset")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "lyricstyleedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    opname="changed", name="Lyric", sub_name="style")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            # metadata
            if op.name == "mditemins":
                assert op.obj1 is None
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2, name="metadata", opname="inserted")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "mditemdel":
                assert isinstance(op.obj1, AnnObject)
                assert op.obj2 is None
                text_diff = vis_func(op, score1, score2, name="metadata", opname="deleted")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            if op.name == "mditemvalueedit":
                assert isinstance(op.obj1, AnnObject)
                assert isinstance(op.obj2, AnnObject)
                text_diff = vis_func(op, score1, score2,
                    name="metadata", opname="changed", sub_name="value")
                if text_diff is not None:
                    outputList.extend(text_diff)
                continue

            print(
                f"Annotation type {op.name} not yet supported for visualization",
                file=sys.stderr
            )

        if vis_type == "draw":
            return None

        # The rest of this is all about vis_type == "text" and the outputList.

        # Sort by measure number (int), then measure number suffix (str), then part
        # number, and then beat (as parsed from "@@ measure 3b, staff 2, beat 1.5 @@")
        # The goal is for all measure 0's to be printed first (with measure 0's staff 0
        # first), with the contents of each staff of each measure coming out in beat order.
        LOC_PATTERN: str = (
            r"\@\@ measure (\d+)(\w*), staff (\d+), beat (\d+|\d+[./]\d+|\d+ \d+/\d+) \@\@"
        )
        def measNum(s: str) -> int:
            m = re.match(LOC_PATTERN, s)
            if not m:
                return -1
            measNumStr: str = m.group(1)
            measNum: int = -1
            try:
                measNum = int(measNumStr)
            except Exception:
                pass
            return measNum

        def measSuf(s: str) -> str:
            m = re.match(LOC_PATTERN, s)
            if not m:
                return ''
            measSuf: str = m.group(2)
            return measSuf

        def staffNum(s: str) -> int:
            m = re.match(LOC_PATTERN, s)
            if not m:
                return -1
            staffNumStr: str = m.group(3)
            staffNum: int = -1
            try:
                staffNum = int(staffNumStr)
            except Exception:
                pass
            return staffNum

        def beat(s: str) -> OffsetQL:
            # can be of the form "j n/m" (mixed), "n/m" (Fraction), or "n.m" (float)
            m = re.match(LOC_PATTERN, s)
            if not m:
                return 0.
            beatStr: str = m.group(4)
            beats: OffsetQL = 0.
            beatsFrac: Fraction = Fraction(0, 1)
            beatsFloat: float = 0.
            try:
                if " " in beatStr and "/" in beatStr:
                    # mixed fraction "j n/m"
                    nums: list[str] = beatStr.split(' ')
                    wholeNum: int = int(nums[0])
                    frac: Fraction = Fraction(nums[1])
                    beats = opFrac(wholeNum + frac)
                elif "/" in beatStr:
                    # fraction
                    beatsFrac = Fraction(beatStr)
                    beats = opFrac(beatsFrac)
                else:
                    beatsFloat = float(beatStr)
                    beats = opFrac(beatsFloat)
            except Exception:
                pass
            return beats

        outputList.sort(key=lambda s: (measNum(s), measSuf(s), staffNum(s), beat(s)))

        if op_list:
            # filenames only show up at the start of text output if there are any diffs
            if score1Name:
                outputList.insert(0, f"--- {score1Name}")
                outputList.insert(1, f"+++ {score2Name}")
            else:
                outputList.insert(0, "--- score1")
                outputList.insert(1, "+++ score2")

        output = '\n'.join(outputList)
        return output

    @staticmethod
    def get_omr_ned_output(
        omr_ed: int,
        annotated_predicted_score: AnnScore,
        annotated_ground_truth_score: AnnScore,
    ) -> dict[str, str]:
        num_syms_in_ground_truth: int = annotated_ground_truth_score.notation_size()
        num_syms_in_predicted: int = annotated_predicted_score.notation_size()
        omr_ned: float = Visualization.get_omr_ned(
            omr_ed, num_syms_in_predicted, num_syms_in_ground_truth
        )
        num_syms_in_both: int = num_syms_in_ground_truth + num_syms_in_predicted
        output: dict[str, str] = {
            'OMR-ED': f'{omr_ed}',
            'numSymbolsInPredicted': f'{num_syms_in_predicted}',
            'numSymbolsInGroundTruth': f'{num_syms_in_ground_truth}',
            'numSymbolsInBoth': f'{num_syms_in_both}',
            'OMR-NED': f'{omr_ned}',
        }
        return output

    @staticmethod
    def get_omr_ned(
        omr_ed: int,
        num_syms_in_predicted: int,
        num_syms_in_ground_truth: int,
    ) -> float:
        num_syms_in_both: int = num_syms_in_ground_truth + num_syms_in_predicted

        # Instead of divide by zero, return omr_ned == 0.0 (because both scores being
        # empty means they are exactly the same)
        omr_ned: float = 0.0
        if num_syms_in_both != 0:
            omr_ned = float(omr_ed) / float(num_syms_in_both)
        return omr_ned

    @staticmethod
    def get_edit_distances_dict(
        op_list: list[DiffOperation],
        num_syntax_errors_fixed: int,
        detail: DetailLevel | int
    ) -> dict[str, int]:
        Visualization.create_header_names_once(detail)

        edit_distances_dict: dict[str, int] = {}
        for op in op_list:
            edit_name: str = op.name
            if edit_name.startswith('extra'):
                extra: AnnObject | None = op.obj1 or op.obj2
                if extra is not None:
                    assert isinstance(extra, AnnExtra)
                    if extra.kind:
                        edit_name = re.sub('extra', extra.kind, edit_name)

            if edit_name not in Visualization._HEADER_NAME_OF_EDIT_NAME:
                edit_name = 'directionins'  # default to direction
            name: str = Visualization._HEADER_NAME_OF_EDIT_NAME[edit_name]

            omr_ed: int = op.edit_distance
            if name not in edit_distances_dict:
                edit_distances_dict[name] = omr_ed
            else:
                edit_distances_dict[name] = edit_distances_dict[name] + omr_ed

        edit_distances_dict['bad kern syntax OMR-ED'] = num_syntax_errors_fixed

        return edit_distances_dict

    @staticmethod
    def create_header_names_once(detail: DetailLevel | int):
        if Visualization._ORDERED_HEADER_NAMES:
            return

        if DetailLevel.includesVoicing(detail):
            Visualization._HEADER_NAME_OF_EDIT_NAME.update(
                Visualization._VOICING_HEADER_NAME_OF_EDIT_NAME_EXTRAS
            )

        ordered_names: list[str] = []
        for en in Visualization._HEADER_NAME_OF_EDIT_NAME:
            hn: str = Visualization._HEADER_NAME_OF_EDIT_NAME[en]
            if hn in ordered_names:
                continue
            ordered_names.append(hn)
            ordered_names.append(re.sub('OMR-ED', '% contribution to OMR-NED', hn))

        Visualization._ORDERED_HEADER_NAMES = ordered_names


    _ORDERED_HEADER_NAMES: list[str] = []

    _HEADER_NAME_OF_EDIT_NAME: dict[str, str] = {
        'syntax_errors_fixed': 'bad kern syntax OMR-ED',
        'noteins': 'wrong note OMR-ED',
        'notedel': 'wrong note OMR-ED',
        'headedit': 'wrong note head OMR-ED',
        'insbeam': 'wrong flag/beam OMR-ED',
        'delbeam': 'wrong flag/beam OMR-ED',
        'editbeam': 'wrong flag/beam OMR-ED',
        'dotdel': 'wrong dot OMR-ED',
        'dotins': 'wrong dot OMR-ED',
        'instuplet': 'wrong tuplet OMR-ED',
        'deltuplet': 'wrong tuplet OMR-ED',
        'edittuplet': 'wrong tuplet OMR-ED',
        'accidentins': 'wrong accidental OMR-ED',
        'accidentdel': 'wrong accidental OMR-ED',
        'accidentedit': 'wrong accidental OMR-ED',
        'editstemdirection': 'wrong note stem OMR-ED',
        'graceedit': 'wrong graceness OMR-ED',
        'graceslashedit': 'wrong graceness OMR-ED',
        'editnoteshape': 'wrong note head OMR-ED',
        'editnoteheadfill': 'wrong note head OMR-ED',
        'editnoteheadparenthesis': 'wrong note head OMR-ED',
        'editstyle': 'wrong note OMR-ED',
        'tiedel': 'wrong tie OMR-ED',
        'tieins': 'wrong tie OMR-ED',
        'insarticulation': 'wrong articulation OMR-ED',
        'delarticulation': 'wrong articulation OMR-ED',
        'editarticulation': 'wrong articulation OMR-ED',
        'insexpression': 'wrong ornament OMR-ED',
        'delexpression': 'wrong ornament OMR-ED',
        'editexpression': 'wrong ornament OMR-ED',

        'insspace': 'wrong note OMR-ED',
        'delspace': 'wrong note OMR-ED',
        'editspace': 'wrong note OMR-ED',

        'lyricins': 'wrong lyric OMR-ED',
        'lyricdel': 'wrong lyric OMR-ED',
        'lyricedit': 'wrong lyric OMR-ED',
        'lyricnumedit': 'wrong lyric OMR-ED',
        'lyricidedit': 'wrong lyric OMR-ED',
        'lyricoffsetedit': 'wrong lyric OMR-ED',
        'lyricstyleedit': 'wrong lyric OMR-ED',

        'clefins': 'wrong clef OMR-ED',
        'clefdel': 'wrong clef OMR-ED',
        'clefcontentedit': 'wrong clef OMR-ED',  # shouldn't happen, clefs have a symbol
        'clefsymboledit': 'wrong clef OMR-ED',
        'clefinfoedit': 'wrong clef OMR-ED',  # shouldn't happen, clefs have a symbol
        'clefoffsetedit': 'wrong clef OMR-ED',  # shouldn't happen; we pair by offset
        'clefdurationedit': 'wrong clef OMR-ED',  # shouldn't happen; clefs have no dur
        'clefstyleedit': 'wrong clef OMR-ED',

        'timesigins': 'wrong timesig OMR-ED',
        'timesigdel': 'wrong timesig OMR-ED',
        'timesigcontentedit': 'wrong timesig OMR-ED',  # shouldn't happen, timesigs have info
        'timesigsymboledit': 'wrong timesig OMR-ED',  # shouldn't happen, ditto
        'timesiginfoedit': 'wrong timesig OMR-ED',
        'timesigoffsetedit': 'wrong timesig OMR-ED',  # shouldn't happen; we pair by offset
        'timesigdurationedit': 'wrong timesig OMR-ED',  # shouldn't happen; timesigs have no dur
        'timesigstyleedit': 'wrong timesig OMR-ED',

        'keysigins': 'wrong keysig OMR-ED',
        'keysigdel': 'wrong keysig OMR-ED',
        'keysigcontentedit': 'wrong keysig OMR-ED',  # shouldn't happen; keysigs have info
        'keysigsymboledit': 'wrong keysig OMR-ED',  # shouldn't happen; keysigs have info
        'keysiginfoedit': 'wrong keysig OMR-ED',
        'keysigoffsetedit': 'wrong keysig OMR-ED',  # shouldn't happen; we pair by offset
        'keysigdurationedit': 'wrong keysig OMR-ED',  # shouldn't happen; keysigs have no dur
        'keysigstyleedit': 'wrong keysig OMR-ED',

        'tempoins': 'wrong tempo OMR-ED',
        'tempodel': 'wrong tempo OMR-ED',
        'tempocontentedit': 'wrong tempo OMR-ED',
        'temposymboledit': 'wrong tempo OMR-ED',
        'tempoinfoedit': 'wrong tempo OMR-ED',  # shouldn't happen; tempos have no info
        'tempooffsetedit': 'wrong tempo OMR-ED',  # shouldn't happen; we pair by offset
        'tempodurationedit': 'wrong tempo OMR-ED',  # shouldn't happen; tempos have no dur
        'tempostyleedit': 'wrong tempo OMR-ED',

        'barlineins': 'wrong barline OMR-ED',
        'barlinedel': 'wrong barline OMR-ED',
        'barlinecontentedit': 'wrong barline OMR-ED',  # shouldn't happen; barlines have no content
        'barlinesymboledit': 'wrong barline OMR-ED',
        'barlineinfoedit': 'wrong barline OMR-ED',
        'barlineoffsetedit': 'wrong barline OMR-ED',  # shouldn't happen; we pair by offset
        'barlinedurationedit': 'wrong barline OMR-ED',  # shouldn't happen; barlines have no dur
        'barlinestyleedit': 'wrong barline OMR-ED',

        # we combine barlines and repeats because repeats are just different types
        # of barline
        'repeatins': 'wrong barline OMR-ED',
        'repeatdel': 'wrong barline OMR-ED',
        'repeatcontentedit': 'wrong barline OMR-ED',  # shouldn't happen; repeats have no content
        'repeatsymboledit': 'wrong barline OMR-ED',
        'repeatinfoedit': 'wrong barline OMR-ED',
        'repeatoffsetedit': 'wrong barline OMR-ED',  # shouldn't happen; we pair by offset
        'repeatdurationedit': 'wrong barline OMR-ED',  # shouldn't happen; repeats have no dur
        'repeatstyleedit': 'wrong barline OMR-ED',

        'directionins': 'wrong direction OMR-ED',
        'directiondel': 'wrong direction OMR-ED',
        'directioncontentedit': 'wrong direction OMR-ED',
        'directionsymboledit': 'wrong direction OMR-ED',  # shouldn't happen; dirs have content
        'directioninfoedit': 'wrong direction OMR-ED',  # shouldn't happen; dirs have content
        'directionoffsetedit': 'wrong direction OMR-ED',  # shouldn't happen; we pair by offset
        'directiondurationedit': 'wrong direction OMR-ED',  # shouldn't happen; no dur
        'directionstyleedit': 'wrong direction OMR-ED',

        'dynamicins': 'wrong dynamic OMR-ED',
        'dynamicdel': 'wrong dynamic OMR-ED',
        'dynamiccontentedit': 'wrong dynamic OMR-ED',  # shouldn't happen; dynamics are symbolic
        'dynamicsymboledit': 'wrong dynamic OMR-ED',
        'dynamicinfoedit': 'wrong dynamic OMR-ED',  # shouldn't happen; dynamics are symbolic
        'dynamicoffsetedit': 'wrong dynamic OMR-ED',  # shouldn't happen; we pair by offset
        'dynamicdurationedit': 'wrong dynamic OMR-ED',
        'dynamicstyleedit': 'wrong dynamic OMR-ED',

        'crescendoins': 'wrong crescendo OMR-ED',
        'crescendodel': 'wrong crescendo OMR-ED',
        'crescendocontentedit': 'wrong crescendo OMR-ED',  # shouldn't happen; crescs are symbolic
        'crescendosymboledit': 'wrong crescendo OMR-ED',
        'crescendoinfoedit': 'wrong crescendo OMR-ED',  # shouldn't happen; crescs are symbolic
        'crescendooffsetedit': 'wrong crescendo OMR-ED',  # shouldn't happen; we pair by offset
        'crescendodurationedit': 'wrong crescendo OMR-ED',
        'crescendostyleedit': 'wrong crescendo OMR-ED',

        'diminuendoins': 'wrong diminuendo OMR-ED',
        'diminuendodel': 'wrong diminuendo OMR-ED',
        'diminuendocontentedit': 'wrong diminuendo OMR-ED',  # shouldn't happen; dims are symbolic
        'diminuendosymboledit': 'wrong diminuendo OMR-ED',
        'diminuendoinfoedit': 'wrong diminuendo OMR-ED',  # shouldn't happen; dims are symbolic
        'diminuendooffsetedit': 'wrong diminuendo OMR-ED',  # shouldn't happen; we pair by offset
        'diminuendodurationedit': 'wrong diminuendo OMR-ED',
        'diminuendostyleedit': 'wrong diminuendo OMR-ED',

        'slurins': 'wrong slur OMR-ED',
        'slurdel': 'wrong slur OMR-ED',
        'slurcontentedit': 'wrong slur OMR-ED',  # shouldn't happen
        'slursymboledit': 'wrong slur OMR-ED',  # shouldn't happen
        'slurinfoedit': 'wrong slur OMR-ED',  # shouldn't happen
        'sluroffsetedit': 'wrong slur OMR-ED',  # shouldn't happen; we pair by offset
        'slurdurationedit': 'wrong slur OMR-ED',
        'slurstyleedit': 'wrong slur OMR-ED',

        'ottavains': 'wrong ottava OMR-ED',
        'ottavadel': 'wrong ottava OMR-ED',
        'ottavacontentedit': 'wrong ottava OMR-ED',  # shouldn't happen; ottava is symbolic
        'ottavasymboledit': 'wrong ottava OMR-ED',
        'ottavainfoedit': 'wrong ottava OMR-ED',  # shouldn't happen; ottava is symbolic
        'ottavaoffsetedit': 'wrong ottava OMR-ED',  # shouldn't happen; we pair by offset
        'ottavadurationedit': 'wrong ottava OMR-ED',
        'ottavastyleedit': 'wrong ottava OMR-ED',

        'arpeggioins': 'wrong multi-staff arpeggio OMR-ED',
        'arpeggiodel': 'wrong multi-staff arpeggio OMR-ED',
        'arpeggiocontentedit': 'wrong multi-staff arpeggio OMR-ED',  # shouldn't happen
        'arpeggiosymboledit': 'wrong multi-staff arpeggio OMR-ED',
        'arpeggioinfoedit': 'wrong multi-staff arpeggio OMR-ED',
        'arpeggiooffsetedit': 'wrong multi-staff arpeggio OMR-ED',  # shouldn't happen
        'arpeggiodurationedit': 'wrong multi-staff arpeggio OMR-ED',  # shouldn't happen
        'arpeggiostyleedit': 'wrong multi-staff arpeggio OMR-ED',  # shouldn't happen

        'tremoloins': 'wrong fingered tremolo OMR-ED',
        'tremolodel': 'wrong fingered tremolo OMR-ED',
        'tremolocontentedit': 'wrong fingered tremolo OMR-ED',  # shouldn't happen
        'tremolosymboledit': 'wrong fingered tremolo OMR-ED',
        'tremoloinfoedit': 'wrong fingered tremolo OMR-ED',  # shouldn't happen
        'tremolooffsetedit': 'wrong fingered tremolo OMR-ED',  # shouldn't happen; we pair by offset
        'tremolodurationedit': 'wrong fingered tremolo OMR-ED',
        'tremolostyleedit': 'wrong fingered tremolo OMR-ED',  # shouldn't happen

        'chordsymins': 'wrong chord symbol OMR-ED',
        'chordsymdel': 'wrong chord symbol OMR-ED',
        'chordsymcontentedit': 'wrong chord symbol OMR-ED',  # shouldn't happen
        'chordsymsymboledit': 'wrong chord symbol OMR-ED',
        'chordsyminfoedit': 'wrong chord symbol OMR-ED',  # shouldn't happen
        'chordsymoffsetedit': 'wrong chord symbol OMR-ED',  # shouldn't happen; we pair by offset
        'chordsymdurationedit': 'wrong chord symbol OMR-ED',  # shouldn't happen
        'chordsymstyleedit': 'wrong chord symbol OMR-ED',

        'endingins': 'wrong ending OMR-ED',
        'endingdel': 'wrong ending OMR-ED',
        'endingcontentedit': 'wrong ending OMR-ED',
        'endingsymboledit': 'wrong ending OMR-ED',
        'endinginfoedit': 'wrong ending OMR-ED',
        'endingoffsetedit': 'wrong ending OMR-ED',  # shouldn't happen; we pair by offset
        'endingdurationedit': 'wrong ending OMR-ED',
        'endingstyleedit': 'wrong ending OMR-ED',  # shouldn't happen

        'staffinfoins': 'wrong staff info OMR-ED',
        'staffinfodel': 'wrong staff info OMR-ED',
        'staffinfocontentedit': 'wrong staff info OMR-ED',  # shouldn't happen
        'staffinfosymboledit': 'wrong staff info OMR-ED',  # shouldn't happen
        'staffinfoinfoedit': 'wrong staff info OMR-ED',
        'staffinfooffsetedit': 'wrong staff info OMR-ED',  # shouldn't happen; we pair by offset
        'staffinfodurationedit': 'wrong staff info OMR-ED',  # shouldn't happen
        'staffinfostyleedit': 'wrong staff info OMR-ED',  # shouldn't happen

        'systembreakins': 'wrong system break OMR-ED',
        'systembreakdel': 'wrong system break OMR-ED',
        'systembreakcontentedit': 'wrong system break OMR-ED',  # shouldn't happen
        'systembreaksymboledit': 'wrong system break OMR-ED',
        'systembreakinfoedit': 'wrong system break OMR-ED',  # shouldn't happen
        'systembreakoffsetedit': 'wrong system break OMR-ED',  # shouldn't happen; we pair by offset
        'systembreakdurationedit': 'wrong system break OMR-ED',  # shouldn't happen
        'systembreakstyleedit': 'wrong system break OMR-ED',  # shouldn't happen

        'pagebreakins': 'wrong page break OMR-ED',
        'pagebreakdel': 'wrong page break OMR-ED',
        'pagebreakcontentedit': 'wrong page break OMR-ED',  # shouldn't happen
        'pagebreaksymboledit': 'wrong page break OMR-ED',
        'pagebreakinfoedit': 'wrong page break OMR-ED',  # shouldn't happen
        'pagebreakoffsetedit': 'wrong page break OMR-ED',  # shouldn't happen; we pair by offset
        'pagebreakdurationedit': 'wrong page break OMR-ED',  # shouldn't happen
        'pagebreakstyleedit': 'wrong page break OMR-ED',  # shouldn't happen

        # These 'extra*' are still here in case there is an AnnExtra (in future) we didn't
        # cover above
        'extrains': 'wrong other object OMR-ED',
        'extradel': 'wrong other object OMR-ED',
        'extracontentedit': 'wrong other object OMR-ED',
        'extrasymboledit': 'wrong other object OMR-ED',
        'extrainfoedit': 'wrong other object OMR-ED',
        'extraoffsetedit': 'wrong other object OMR-ED',  # shouldn't happen; we pair by offset
        'extradurationedit': 'wrong other object OMR-ED',
        'extrastyleedit': 'wrong other object OMR-ED',

        'insbar': 'entire measure insert/delete OMR-ED',
        'delbar': 'entire measure insert/delete OMR-ED',

        'inspart': 'entire staff insert/delete OMR-ED',
        'delpart': 'entire staff insert/delete OMR-ED',

        'mditemins': 'wrong metadata OMR-ED',
        'mditemdel': 'wrong metadata OMR-ED',
        'mditemvalueedit': 'wrong metadata OMR-ED',

        'staffgrpins': 'wrong staff group OMR-ED',
        'staffgrpdel': 'wrong staff group OMR-ED',
        'staffgrpnameedit': 'wrong staff group name/abbrev OMR-ED',
        'staffgrpabbreviationedit': 'wrong staff group name/abbrev OMR-ED',
        'staffgrpsymboledit': 'wrong staff group brace OMR-ED',
        'staffgrpbartogetheredit': 'wrong staff group barline OMR-ED',
        'staffgrppartindicesedit': 'wrong staff group OMR-ED',
    }

    _VOICING_HEADER_NAME_OF_EDIT_NAME_EXTRAS: dict[str, str] = {
        # The following will only happen if Voicing is selected,
        # because when Voicing is not selected, (1) chords are ignored,
        # so we will never see chords with inserted or deleted pitches,
        # (2) notes are paired by pitch, so instead of pitch edits we
        # get note insertions and deletions, and (3) we ignore voices
        # completely, so we certainly don't insert or delete them.
        'inspitch': 'pitch insert/delete OMR-ED',
        'delpitch': 'pitch insert/delete OMR-ED',
        'pitchnameedit': 'wrong pitch OMR-ED',
        'pitchtypeedit': 'wrong pitch OMR-ED',
        'voiceins': 'voice insert/delete OMR-ED',
        'voicedel': 'voice insert/delete OMR-ED',
    }

    _PRE_EDITS_HEADER_NAMES: list[str] = [
        'gtpath',
        'predpath',
    ]
    _POST_EDITS_HEADER_NAMES: list[str] = [
        'gt numsyms',
        'pred numsyms',
        'total numsyms (in both scores)',
        'OMR-ED (OMR Edit Distance)',
        'OMR-NED (OMR-ED / total numsyms)',
    ]

    @staticmethod
    def get_output_csv_header(detail: DetailLevel | int) -> str:
        Visualization.create_header_names_once(detail)

        header: str = ''
        for name in Visualization._PRE_EDITS_HEADER_NAMES:
            header += ', '  # even at start of header (empty column, for "Totals:" at the bottom)
            header += name
        for name in Visualization._ORDERED_HEADER_NAMES:
            header += ', '
            header += name
        for name in Visualization._POST_EDITS_HEADER_NAMES:
            header += ', '
            header += name

        return header

    @staticmethod
    def get_output_csv_trailer(
        metrics_list: list[EvaluationMetrics],
        detail: DetailLevel | int
    ) -> str:
        Visualization.create_header_names_once(detail)

        # Compute all the totals
        total_gt_numsyms: int = 0
        total_pred_numsyms: int = 0
        total_omr_edit_distance: int = 0
        total_edit_distances_dict: dict[str, int] = {}

        for metrics in metrics_list:
            total_gt_numsyms += metrics.gt_numsyms
            total_pred_numsyms += metrics.pred_numsyms
            total_omr_edit_distance += metrics.omr_edit_distance
            for name in metrics.edit_distances_dict:
                if name not in total_edit_distances_dict:
                    total_edit_distances_dict[name] = metrics.edit_distances_dict[name]
                else:
                    total_edit_distances_dict[name] += metrics.edit_distances_dict[name]

        total_numsyms: int = total_gt_numsyms + total_pred_numsyms

        overall_omr_ned: float = Visualization.get_omr_ned(
            total_omr_edit_distance, total_pred_numsyms, total_gt_numsyms
        )

        totals_line: str = 'Total:'  # the only thing in first column

        # first the pre-edits fields
        for name in Visualization._PRE_EDITS_HEADER_NAMES:
            totals_line += ', '
            if name in ('gtpath', 'predpath'):
                pass  # leave empty
            elif name == 'gt numsyms':
                totals_line += f'{total_gt_numsyms}'
            elif name == 'pred numsyms':
                totals_line += f'{total_pred_numsyms}'
            elif name == 'total numsyms (in both scores)':
                totals_line += f'{total_numsyms}'
            elif name == 'OMR-ED (OMR Edit Distance)':
                totals_line += f'{total_omr_edit_distance}'
            elif name == 'OMR-NED (OMR-ED / total numsyms)':
                totals_line += f'{overall_omr_ned}'

        # then the edit fields
        previous_column_edit_distance: int = 0
        for name in Visualization._ORDERED_HEADER_NAMES:
            totals_line += ', '
            if name.endswith('OMR-ED'):
                if name in total_edit_distances_dict:
                    previous_column_edit_distance = total_edit_distances_dict[name]
                    totals_line += f'{total_edit_distances_dict[name]}'
                else:
                    previous_column_edit_distance = 0
                    totals_line += '0'
            elif name.endswith('% contribution to OMR-NED'):
                if previous_column_edit_distance:
                    contrib: float = (
                        float(previous_column_edit_distance * 100)
                        / float(total_omr_edit_distance)
                    )
                    totals_line += f'{contrib}'
                else:
                    totals_line += '0.'
                previous_column_edit_distance = 0
            else:
                # how did we get here?
                previous_column_edit_distance = 0


        # then the post-edits fields
        for name in Visualization._POST_EDITS_HEADER_NAMES:
            totals_line += ', '
            if name in ('gtpath', 'predpath'):
                pass  # leave empty
            elif name == 'gt numsyms':
                totals_line += f'{total_gt_numsyms}'
            elif name == 'pred numsyms':
                totals_line += f'{total_pred_numsyms}'
            elif name == 'total numsyms (in both scores)':
                totals_line += f'{total_numsyms}'
            elif name == 'OMR-ED (OMR Edit Distance)':
                totals_line += f'{total_omr_edit_distance}'
            elif name == 'OMR-NED (OMR-ED / total numsyms)':
                totals_line += f'{overall_omr_ned}'

        repeated_header_line: str = Visualization.get_output_csv_header(detail)

        trailer_line: str = totals_line + '\n' + repeated_header_line
        return trailer_line

    @staticmethod
    def get_output_csv_line(
        metrics: EvaluationMetrics,
        detail: DetailLevel | int
    ) -> str:
        Visualization.create_header_names_once(detail)

        # 888 could validate metrics.omr_edit_distance here (make sure it is the sum of
        # 888 everything in metrics.edit_distances_dict)
        total_numsyms: int = metrics.pred_numsyms + metrics.gt_numsyms

        line: str = ''

        # first the pre-edits fields
        for name in Visualization._PRE_EDITS_HEADER_NAMES:
            line += ', '  # even at start of line (empty column, for "Totals:" at the bottom)
            if name == 'gtpath':
                line += str(metrics.gt_path)
            elif name == 'predpath':
                line += str(metrics.pred_path)
            elif name == 'gt numsyms':
                line += f'{metrics.gt_numsyms}'
            elif name == 'pred numsyms':
                line += f'{metrics.pred_numsyms}'
            elif name == 'total numsyms (in both scores)':
                line += f'{total_numsyms}'
            elif name == 'OMR-ED (OMR Edit Distance)':
                line += f'{metrics.omr_edit_distance}'
            elif name == 'OMR-NED (OMR-ED / total numsyms)':
                line += f'{metrics.omr_ned}'

        # then the edit fields
        previous_column_edit_distance: int = 0
        for name in Visualization._ORDERED_HEADER_NAMES:
            line += ', '
            if name.endswith('OMR-ED'):
                if name in metrics.edit_distances_dict:
                    previous_column_edit_distance = metrics.edit_distances_dict[name]
                    line += f'{metrics.edit_distances_dict[name]}'
                else:
                    line += '0'
            elif name.endswith('% contribution to OMR-NED'):
                if previous_column_edit_distance:
                    contrib: float = (
                        float(previous_column_edit_distance * 100)
                        / float(metrics.omr_edit_distance)
                    )
                    line += (
                        f'{contrib}'
                    )
                else:
                    line += '0.'
                previous_column_edit_distance = 0
            else:
                # how did we get here?
                previous_column_edit_distance = 0

        # then the post-edits fields
        for name in Visualization._POST_EDITS_HEADER_NAMES:
            line += ', '
            if name == 'gtpath':
                line += str(metrics.gt_path)
            elif name == 'predpath':
                line += str(metrics.pred_path)
            elif name == 'gt numsyms':
                line += f'{metrics.gt_numsyms}'
            elif name == 'pred numsyms':
                line += f'{metrics.pred_numsyms}'
            elif name == 'total numsyms (in both scores)':
                line += f'{total_numsyms}'
            elif name == 'OMR-ED (OMR Edit Distance)':
                line += f'{metrics.omr_edit_distance}'
            elif name == 'OMR-NED (OMR-ED / total numsyms)':
                line += f'{metrics.omr_ned}'

        return line
