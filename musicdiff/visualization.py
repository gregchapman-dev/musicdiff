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
import typing as t
from fractions import Fraction

import music21 as m21
from music21.common import OffsetQL, opFrac

from musicdiff.annotation import AnnScore, AnnPart, AnnMeasure, AnnVoice, AnnNote
from musicdiff.annotation import AnnExtra, AnnLyric, AnnStaffGroup, AnnMetadataItem
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

    @staticmethod
    def mark_diffs(
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        operations: list[tuple]
    ) -> None:
        """
        Mark up two music21 scores with the differences described by an operations
        list (e.g. a list returned from `musicdiff.Comparison.annotated_scores_diff`).

        Args:
            score1 (music21.stream.Score): The first score to mark up
            score2 (music21.stream.Score): The second score to mark up
            operations (list[tuple]): The operations list that describes the difference
                between the two scores
        """
        changedStr: str
        for op in operations:
            # bar
            if op[0] == "insbar":
                assert isinstance(op[2], AnnMeasure)
                # color all the notes in the inserted score2 measure
                # using Visualization.INSERTED_COLOR
                measure2 = score2.recurse().getElementById(op[2].measure)  # type: ignore
                if t.TYPE_CHECKING:
                    assert measure2 is not None
                textExp = m21.expressions.TextExpression("inserted measure")
                textExp.style.color = Visualization.INSERTED_COLOR
                measure2.insert(0, textExp)
                measure2.style.color = (
                    Visualization.INSERTED_COLOR
                )  # this apparently does nothing
                for el in measure2.recurse().notesAndRests:
                    el.style.color = Visualization.INSERTED_COLOR
                continue

            if op[0] == "delbar":
                assert isinstance(op[1], AnnMeasure)
                # color all the notes in the deleted score1 measure
                # using Visualization.DELETED_COLOR
                measure1 = score1.recurse().getElementById(op[1].measure)  # type: ignore
                if t.TYPE_CHECKING:
                    assert measure1 is not None
                textExp = m21.expressions.TextExpression("deleted measure")
                textExp.style.color = Visualization.DELETED_COLOR
                measure1.insert(0, textExp)
                measure1.style.color = (
                    Visualization.DELETED_COLOR
                )  # this apparently does nothing
                for el in measure1.recurse().notesAndRests:
                    el.style.color = Visualization.DELETED_COLOR
                continue

            # voices
            if op[0] == "voiceins":
                assert isinstance(op[2], AnnVoice)
                # color all the notes in the inserted score2 voice
                # using Visualization.INSERTED_COLOR
                voice2 = score2.recurse().getElementById(op[2].voice)  # type: ignore
                if t.TYPE_CHECKING:
                    assert voice2 is not None
                textExp = m21.expressions.TextExpression("inserted voice")
                textExp.style.color = Visualization.INSERTED_COLOR
                voice2.insert(0, textExp)

                voice2.style.color = (
                    Visualization.INSERTED_COLOR
                )  # this apparently does nothing
                for el in voice2.recurse().notesAndRests:
                    el.style.color = Visualization.INSERTED_COLOR
                continue

            if op[0] == "voicedel":
                assert isinstance(op[1], AnnVoice)
                # color all the notes in the deleted score1 voice
                # using Visualization.DELETED_COLOR
                voice1 = score1.recurse().getElementById(op[1].voice)  # type: ignore
                if t.TYPE_CHECKING:
                    assert voice1 is not None
                textExp = m21.expressions.TextExpression("deleted voice")
                textExp.style.color = Visualization.DELETED_COLOR
                voice1.insert(0, textExp)

                voice1.style.color = (
                    Visualization.DELETED_COLOR
                )  # this apparently does nothing
                for el in voice1.recurse().notesAndRests:
                    el.style.color = Visualization.DELETED_COLOR
                continue

            # extra
            if op[0] == "extrains":
                assert isinstance(op[2], AnnExtra)
                # color the extra using Visualization.INSERTED_COLOR,
                # and add a textExpression describing the insertion.
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra2 is not None
                textExp = m21.expressions.TextExpression(f"inserted {extra2.classes[0]}")
                textExp.style.color = Visualization.INSERTED_COLOR
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint = extra2.getFirst()
                    if isinstance(insertionPoint, m21.stream.Measure):
                        # insertionPoint is a measure, put the textExp at offset 0
                        # inside the measure
                        insertionPoint.insert(0, textExp)
                    else:
                        # insertionPoint is something else, put the textExp right next to it.
                        insertionPoint.activeSite.insert(insertionPoint.offset, textExp)
                else:
                    # extra2 is not a spanner, put the textExp right next to it
                    extra2.activeSite.insert(extra2.offset, textExp)
                continue

            if op[0] == "extradel":
                assert isinstance(op[1], AnnExtra)
                # color the extra using Visualization.DELETED_COLOR, and add a textExpression
                # describing the deletion.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                textExp = m21.expressions.TextExpression(f"deleted {extra1.classes[0]}")
                textExp.style.color = Visualization.DELETED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint = extra1.getFirst()
                    if isinstance(insertionPoint, m21.stream.Measure):
                        # insertionPoint is a measure, put the textExp at offset 0
                        # inside the measure
                        insertionPoint.insert(0, textExp)
                    else:
                        # insertionPoint is something else, put the textExp right next to it.
                        insertionPoint.activeSite.insert(insertionPoint.offset, textExp)
                else:
                    # extra1 is not a spanner, put the textExp right next to it
                    extra1.activeSite.insert(extra1.offset, textExp)
                continue

            if op[0] == "extrasub":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                # color the extra using Visualization.CHANGED_COLOR, and add a textExpression
                # describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                if extra1.classes[0] != extra2.classes[0]:
                    textExp1 = m21.expressions.TextExpression(
                        f"changed to {extra2.classes[0]}"
                    )
                    textExp2 = m21.expressions.TextExpression(
                        f"changed from {extra1.classes[0]}"
                    )
                else:
                    textExp1 = m21.expressions.TextExpression(f"changed {extra1.classes[0]}")
                    textExp2 = m21.expressions.TextExpression(f"changed {extra1.classes[0]}")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2
                if isinstance(insertionPoint1, m21.stream.Measure):
                    # insertionPoint1 is a measure, put the textExp at offset 0
                    # inside the measure
                    insertionPoint1.insert(0, textExp)
                else:
                    # insertionPoint1 is something else, put the textExp right next to it.
                    insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp)
                if isinstance(insertionPoint2, m21.stream.Measure):
                    # insertionPoint2 is a measure, put the textExp at offset 0
                    # inside the measure
                    insertionPoint2.insert(0, textExp)
                else:
                    # insertionPoint2 is something else, put the textExp right next to it.
                    insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp)
                continue

            if op[0] == "extracontentedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                # color the extra using Visualization.CHANGED_COLOR, and add a textExpression
                # describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                textExp1 = m21.expressions.TextExpression(f"changed {extra1.classes[0]} text")
                textExp2 = m21.expressions.TextExpression(f"changed {extra2.classes[0]} text")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2

                insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp1)
                insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp2)
                continue

            if op[0] == "extrasymboledit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                # color the extra using Visualization.CHANGED_COLOR, and add a textExpression
                # describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                textExp1 = m21.expressions.TextExpression(f"changed {extra1.classes[0]} symbol")
                textExp2 = m21.expressions.TextExpression(f"changed {extra2.classes[0]} symbol")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2

                insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp1)
                insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp2)
                continue

            if op[0] == "extrainfoedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                sd1 = op[1].infodict
                sd2 = op[2].infodict
                changedStr = "info: "
                for k1, v1 in sd1.items():
                    if k1 not in sd2 or sd2[k1] != v1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k1

                # one last thing: check for keys in sd2 that aren't in sd1
                for k2 in sd2:
                    if k2 not in sd1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k2

                # color the extra using Visualization.CHANGED_COLOR, and add a textExpression
                # describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                textExp1 = m21.expressions.TextExpression(
                    f"changed {extra1.classes[0]} {changedStr}")
                textExp2 = m21.expressions.TextExpression(
                    f"changed {extra2.classes[0]} {changedStr}")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2

                insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp1)
                insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp2)
                continue

            if op[0] == "extraoffsetedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                # color the extra using Visualization.CHANGED_COLOR, and add a textExpression
                # describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                textExp1 = m21.expressions.TextExpression(
                    f"changed {extra1.classes[0]} offset")
                textExp2 = m21.expressions.TextExpression(
                    f"changed {extra2.classes[0]} offset")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2
                insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp1)
                insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp2)
                continue

            if op[0] == "extradurationedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                # color the extra using Visualization.CHANGED_COLOR, and add a textExpression
                # describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                textExp1 = m21.expressions.TextExpression(
                    f"changed {extra1.classes[0]} duration")
                textExp2 = m21.expressions.TextExpression(
                    f"changed {extra1.classes[0]} duration")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra2, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2
                insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp1)
                insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp2)
                continue

            if op[0] == "extrastyleedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                sd1 = op[1].styledict
                sd2 = op[2].styledict
                changedStr = "style: "
                for k1, v1 in sd1.items():
                    if k1 not in sd2 or sd2[k1] != v1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k1

                # one last thing: check for keys in sd2 that aren't in sd1
                for k2 in sd2:
                    if k2 not in sd1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k2

                # color the extra using Visualization.CHANGED_COLOR,
                # and add a textExpression describing the change.
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None

                textExp1 = m21.expressions.TextExpression(
                    f"changed {extra1.classes[0]} {changedStr}")
                textExp2 = m21.expressions.TextExpression(
                    f"changed {extra1.classes[0]} {changedStr}")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint1 = extra1.getFirst()
                else:
                    insertionPoint1 = extra1
                if isinstance(extra1, m21.spanner.Spanner):
                    insertionPoint2 = extra2.getFirst()
                else:
                    insertionPoint2 = extra2
                insertionPoint1.activeSite.insert(insertionPoint1.offset, textExp1)
                insertionPoint2.activeSite.insert(insertionPoint2.offset, textExp2)
                continue

            # parts
            if op[0] == "inspart":
                assert isinstance(op[2], AnnPart)
                # add a textExpression describing the insertion.
                part2 = score2.recurse().getElementById(
                    op[2].part  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert part2 is not None
                textExp = m21.expressions.TextExpression("inserted Part")
                textExp.style.color = Visualization.INSERTED_COLOR
                # insert text at offset 0 in first measure of added part (part2)
                insertionSite = part2[m21.stream.Measure].first()
                insertionSite.insert(0, textExp)
                # color every note/rest in the inserted part
                for el in part2.recurse().notesAndRests:
                    el.style.color = Visualization.INSERTED_COLOR

                continue

            if op[0] == "delpart":
                assert isinstance(op[1], AnnPart)
                # add a textExpression describing the deletion.
                part1 = score1.recurse().getElementById(
                    op[1].part  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert part1 is not None
                textExp = m21.expressions.TextExpression("deleted Part")
                textExp.style.color = Visualization.DELETED_COLOR
                # insert text at offset 0 in first measure of deleted part (part1)
                insertionSite = part1[m21.stream.Measure].first()
                insertionSite.insert(0, textExp)
                # color every note/rest in the deleted part
                for el in part1.recurse().notesAndRests:
                    el.style.color = Visualization.INSERTED_COLOR
                continue

            # staff groups
            if op[0] == "staffgrpins":
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the insertion.
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup2 is not None
                textExp = m21.expressions.TextExpression("inserted StaffGroup")
                textExp.style.color = Visualization.INSERTED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp)
                continue

            if op[0] == "staffgrpdel":
                assert isinstance(op[1], AnnStaffGroup)
                # add a textExpression describing the deletion.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                textExp = m21.expressions.TextExpression("deleted StaffGroup")
                textExp.style.color = Visualization.DELETED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp)
                continue

            if op[0] == "staffgrpsub":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the change.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                textExp1 = m21.expressions.TextExpression("changed StaffGroup")
                textExp2 = m21.expressions.TextExpression("changed StaffGroup")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp1)
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp2)
                continue

            if op[0] == "staffgrpnameedit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the change.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                textExp1 = m21.expressions.TextExpression("changed StaffGroup name")
                textExp2 = m21.expressions.TextExpression("changed StaffGroup name")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp1)
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp2)
                continue

            if op[0] == "staffgrpabbreviationedit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the change.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                textExp1 = m21.expressions.TextExpression("changed StaffGroup abbreviation")
                textExp2 = m21.expressions.TextExpression("changed StaffGroup abbreviation")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp1)
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp2)
                continue

            if op[0] == "staffgrpsymboledit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the change.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                textExp1 = m21.expressions.TextExpression("changed StaffGroup symbol shape")
                textExp2 = m21.expressions.TextExpression("changed StaffGroup symbol shape")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp1)
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp2)
                continue

            if op[0] == "staffgrpbartogetheredit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the change.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                textExp1 = m21.expressions.TextExpression("changed StaffGroup barline type")
                textExp2 = m21.expressions.TextExpression("changed StaffGroup barline type")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp1)
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp2)
                continue

            if op[0] == "staffgrppartindicesedit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                # add a textExpression describing the change.
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                textExp1 = m21.expressions.TextExpression("changed StaffGroup parts")
                textExp2 = m21.expressions.TextExpression("changed StaffGroup parts")
                textExp1.style.color = Visualization.CHANGED_COLOR
                textExp2.style.color = Visualization.CHANGED_COLOR
                # insert text at offset 0 in first measure of first part in group
                insertionSite = staffGroup1.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp1)
                insertionSite = staffGroup2.getFirst()[m21.stream.Measure].first()
                insertionSite.insert(0, textExp2)
                continue

            # note
            if op[0] == "noteins":
                assert isinstance(op[2], AnnNote)
                # color the inserted score2 general note (note, chord, or rest)
                # using Visualization.INSERTED_COLOR
                # The note that was inserted may in fact be a note within a chord,
                # so be careful to use the chord and the note in that case for
                # the appropriate operations.
                noteOrChord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert noteOrChord2 is not None
                if len(op) >= 5 and op[4] is not None:
                    note2 = noteOrChord2.notes[op[4]]
                else:
                    note2 = noteOrChord2
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression(
                    f"inserted {note2.classes[0]}")
                textExp.style.color = Visualization.INSERTED_COLOR
                noteOrChord2.activeSite.insert(noteOrChord2.offset, textExp)
                continue

            if op[0] == "notedel":
                assert isinstance(op[1], AnnNote)
                # color the deleted score1 general note (note, chord, or rest)
                # using Visualization.DELETED_COLOR
                # The note that was deleted may in fact be a note within a chord,
                # so be careful to use the chord and the note in that case for
                # the appropriate operations.
                noteOrChord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert noteOrChord1 is not None
                if len(op) >= 5 and op[4] is not None:
                    note1 = noteOrChord1.notes[op[4]]
                else:
                    note1 = noteOrChord1
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression(f"deleted {note1.classes[0]}")
                textExp.style.color = Visualization.DELETED_COLOR
                noteOrChord1.activeSite.insert(noteOrChord1.offset, textExp)
                continue

            # pitch
            if op[0] == "pitchnameedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the changed note (in both scores) using Visualization.CHANGED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if not op[1].is_in_chord and "Chord" in chord1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if not op[2].is_in_chord and "Chord" in chord2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            if op[0] == "inspitch":
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the inserted note in score2 using Visualization.INSERTED_COLOR
                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if not op[2].is_in_chord and "Chord" in chord2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.INSERTED_COLOR
                if "Rest" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted rest")
                else:
                    textExp = m21.expressions.TextExpression("inserted note")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            if op[0] == "delpitch":
                assert isinstance(op[1], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the deleted note in score1 using Visualization.DELETED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.DELETED_COLOR
                if "Rest" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted rest")
                else:
                    textExp = m21.expressions.TextExpression("deleted note")
                textExp.style.color = Visualization.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)
                continue

            if op[0] == "headedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed note/rest/chord (in both scores)
                # using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "graceedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed note/rest/chord (in both scores)
                # using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed grace note")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed grace note")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "graceslashedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed note/rest/chord (in both scores)
                # using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed grace note slash")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed grace note slash")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            # beam
            if op[0] == "insbeam":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.INSERTED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.INSERTED_COLOR
                if hasattr(note1, "beams"):
                    for beam in note1.beams:
                        beam.style.color = (
                            Visualization.INSERTED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = Visualization.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.INSERTED_COLOR
                if hasattr(note2, "beams"):
                    for beam in note2.beams:
                        beam.style.color = (
                            Visualization.INSERTED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "delbeam":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.DELETED_COLOR
                if hasattr(note1, "beams"):
                    for beam in note1.beams:
                        beam.style.color = (
                            Visualization.DELETED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.DELETED_COLOR
                if hasattr(note2, "beams"):
                    for beam in note2.beams:
                        beam.style.color = (
                            Visualization.DELETED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = Visualization.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editbeam":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed beam (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                if hasattr(note1, "beams"):
                    for beam in note1.beams:
                        beam.style.color = (
                            Visualization.CHANGED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                if hasattr(note2, "beams"):
                    for beam in note2.beams:
                        beam.style.color = (
                            Visualization.CHANGED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editnoteshape":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note shape")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note shape")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editspace":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed space before")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed space before")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "insspace":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted space before")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted space before")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "delspace":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted space before")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted space before")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editnoteheadfill":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head fill")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head fill")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editnoteheadparenthesis":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head paren")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head paren")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editstemdirection":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed stem direction")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed stem direction")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editstyle":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                sd1 = op[1].styledict
                sd2 = op[2].styledict
                changedStr = ""
                for k1, v1 in sd1.items():
                    if k1 not in sd2 or sd2[k1] != v1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k1

                # one last thing: check for keys in sd2 that aren't in sd1
                for k2 in sd2:
                    if k2 not in sd1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k2

                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression(f"changed note {changedStr}")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression(f"changed note {changedStr}")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            # accident
            if op[0] == "accidentins":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using Visualization.INSERTED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                if hasattr(note1, 'pitch') and note1.pitch.accidental:
                    note1.pitch.accidental.style.color = Visualization.INSERTED_COLOR
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                if hasattr(note2, 'pitch') and note2.pitch.accidental:
                    note2.pitch.accidental.style.color = Visualization.INSERTED_COLOR
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            if op[0] == "accidentdel":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using Visualization.DELETED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                if hasattr(note1, 'pitch') and note1.pitch.accidental:
                    note1.pitch.accidental.style.color = Visualization.DELETED_COLOR
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = Visualization.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                if hasattr(note2, 'pitch') and note2.pitch.accidental:
                    note2.pitch.accidental.style.color = Visualization.DELETED_COLOR
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = Visualization.DELETED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            if op[0] == "accidentedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the changed accidental (in both scores)
                # using Visualization.CHANGED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                if hasattr(note1, 'pitch') and note1.pitch.accidental:
                    note1.pitch.accidental.style.color = Visualization.CHANGED_COLOR
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                if hasattr(note2, 'pitch') and note2.pitch.accidental:
                    note2.pitch.accidental.style.color = Visualization.CHANGED_COLOR
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            if op[0] == "dotins":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores,
                # using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "dotdel":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores,
                # using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            # tuplets
            if op[0] == "instuplet":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "deltuplet":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "edittuplet":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            # ties
            if op[0] == "tieins":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # Color the modified note here in both scores,
                # using Visualization.INSERTED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            if op[0] == "tiedel":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # Color the modified note in both scores, using Visualization.DELETED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = Visualization.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = Visualization.DELETED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)
                continue

            # expressions
            if op[0] == "insexpression":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the note in both scores using Visualization.INSERTED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = Visualization.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "delexpression":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the deleted expression in score1 using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = Visualization.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = Visualization.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editexpression":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed beam (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            # articulations
            if op[0] == "insarticulation":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.INSERTED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = Visualization.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "delarticulation":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = Visualization.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = Visualization.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "editarticulation":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            # lyrics
            if op[0] == "lyricins":
                assert isinstance(op[2], AnnLyric)
                # color the note with the lyric using Visualization.INSERTED_COLOR
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted lyric")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "lyricdel":
                assert isinstance(op[1], AnnLyric)
                # color the note with the lyric using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted lyric")
                textExp.style.color = Visualization.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)
                continue

            if op[0] in ("lyricsub", "lyricedit"):
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                # color the note with changed lyric (in both scores) using
                # Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "lyricnumedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                # color the modified note (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric verse num")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric verse num")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "lyricidedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                # color the modified note (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric verse id")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric verse id")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "lyricoffsetedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                # color the modified note (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric offset")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric offset")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            if op[0] == "lyricstyleedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                # color the modified note (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric style")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed lyric style")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)
                continue

            print(
                f"Annotation type {op[0]} not yet supported for visualization",
                file=sys.stderr
            )

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

    @staticmethod
    def get_text_output(
        score1: m21.stream.Score,
        score2: m21.stream.Score,
        operations: list[tuple],
        score1Name: str | Path | None = None,
        score2Name: str | Path | None = None
    ) -> str:
        """
        Generate text output from the differences described by an operations list
        (e.g. a list returned from `musicdiff.Comparison.annotated_scores_diff`).

        Args:
            score1 (music21.stream.Score): The first score that was compared
            score2 (music21.stream.Score): The second score that was compared
            operations (list[tuple]): The operations list that describes the difference
                between the two scores
            score1Name (str | Path | None): The name to use for the first score in the text output
            score2Name (str | Path | None): The name to use for the second score in the text output
        """
        output: str
        outputList: list[str] = []
        oneOutput: str  # one string, multiple lines (with \n at end of all but last line)

        for op in operations:
            # part
            if op[0] == "inspart":
                assert isinstance(op[2], AnnPart)
                part2 = score2.recurse().getElementById(op[2].part)  # type: ignore
                if t.TYPE_CHECKING:
                    assert part2 is not None
                newLine: str = f"@@ {Visualization._location_of(part2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+(part) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "delpart":
                assert isinstance(op[1], AnnPart)
                part1 = score1.recurse().getElementById(op[1].part)  # type: ignore
                if t.TYPE_CHECKING:
                    assert part1 is not None
                newLine = f"@@ {Visualization._location_of(part1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(part) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # bar
            if op[0] == "insbar":
                assert isinstance(op[2], AnnMeasure)
                measure2 = score2.recurse().getElementById(op[2].measure)  # type: ignore
                if t.TYPE_CHECKING:
                    assert measure2 is not None
                newLine = f"@@ {Visualization._location_of(measure2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+(measure) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "delbar":
                assert isinstance(op[1], AnnMeasure)
                measure1 = score1.recurse().getElementById(op[1].measure)  # type: ignore
                if t.TYPE_CHECKING:
                    assert measure1 is not None
                newLine = f"@@ {Visualization._location_of(measure1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(measure) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # voices
            if op[0] == "voiceins":
                assert isinstance(op[2], AnnVoice)
                voice2 = score2.recurse().getElementById(op[2].voice)  # type: ignore
                if t.TYPE_CHECKING:
                    assert voice2 is not None
                newLine = f"@@ {Visualization._location_of(voice2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+(voice) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "voicedel":
                assert isinstance(op[1], AnnVoice)
                voice1 = score1.recurse().getElementById(op[1].voice)  # type: ignore
                if t.TYPE_CHECKING:
                    assert voice1 is not None
                newLine = f"@@ {Visualization._location_of(voice1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(voice) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # extra
            if op[0] == "extrains":
                assert isinstance(op[2], AnnExtra)
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+({extra2.classes[0]}) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extradel":
                assert isinstance(op[1], AnnExtra)
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({extra1.classes[0]}) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extrasub":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({extra1.classes[0]}) {op[1].readable_str()}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+({extra2.classes[0]}) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extracontentedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({extra1.classes[0]}:content) {op[1].readable_str('content')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+({extra2.classes[0]}:content) {op[2].readable_str('content')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extrasymboledit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({extra1.classes[0]}:symbolic) {op[1].readable_str('symbolic')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+({extra2.classes[0]}:symbolic) {op[2].readable_str('symbolic')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extrainfoedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                sd1 = op[1].infodict
                sd2 = op[2].infodict
                changedStr = ""
                for k1, v1 in sd1.items():
                    if k1 not in sd2 or sd2[k1] != v1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k1

                # one last thing: check for keys in sd2 that aren't in sd1
                for k2 in sd2:
                    if k2 not in sd1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k2

                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                info1: str = op[1].readable_str('info', changedStr=changedStr)
                info2: str = op[2].readable_str('info', changedStr=changedStr)
                newLine = f"-({extra1.classes[0]}:{changedStr}) {info1}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+({extra2.classes[0]}:{changedStr}) {info2}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue


            if op[0] == "extraoffsetedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({extra1.classes[0]}:offset) {op[1].readable_str('offset')}"
                oneOutput += newLine
                outputList.append(oneOutput)

                newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+({extra2.classes[0]}:offset) {op[2].readable_str('offset')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extradurationedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({extra1.classes[0]}:dur) {op[1].readable_str('duration')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+({extra2.classes[0]}:dur) {op[2].readable_str('duration')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "extrastyleedit":
                assert isinstance(op[1], AnnExtra)
                assert isinstance(op[2], AnnExtra)
                sd1 = op[1].styledict
                sd2 = op[2].styledict
                changedStr = ""
                for k1, v1 in sd1.items():
                    if k1 not in sd2 or sd2[k1] != v1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k1

                # one last thing: check for keys in sd2 that aren't in sd1
                for k2 in sd2:
                    if k2 not in sd1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k2

                extra1 = score1.recurse().getElementById(op[1].extra)  # type: ignore
                extra2 = score2.recurse().getElementById(op[2].extra)  # type: ignore
                if t.TYPE_CHECKING:
                    assert extra1 is not None
                    assert extra2 is not None
                newLine = f"@@ {Visualization._location_of(extra1, score1)} @@\n"
                oneOutput = newLine
                style1: str = op[1].readable_str('style', changedStr=changedStr)
                style2: str = op[2].readable_str('style', changedStr=changedStr)
                newLine = f"-({extra1.classes[0]}:{changedStr}) {style1}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(extra2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+({extra2.classes[0]}:{changedStr}) {style2}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # staff groups
            if op[0] == "staffgrpins":
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+(StaffGroup) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrpdel":
                assert isinstance(op[1], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrpsub":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup) {op[1].readable_str()}\n"
                oneOutput += newLine
                newLine = f"+(StaffGroup) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrpnameedit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup:name) {op[1].readable_str('name')}\n"
                oneOutput += newLine
                newLine = f"+(StaffGroup:name) {op[2].readable_str('name')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrpabbreviationedit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup:abbr) {op[1].readable_str('abbr')}\n"
                oneOutput += newLine
                newLine = f"+(StaffGroup:abbr) {op[2].readable_str('abbr')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrpsymboledit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup:sym) {op[1].readable_str('sym')}\n"
                oneOutput += newLine
                newLine = f"+(StaffGroup:sym) {op[2].readable_str('sym')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrpbartogetheredit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup:barline) {op[1].readable_str('barline')}\n"
                oneOutput += newLine
                newLine = f"+(StaffGroup:barline) {op[2].readable_str('barline')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "staffgrppartindicesedit":
                assert isinstance(op[1], AnnStaffGroup)
                assert isinstance(op[2], AnnStaffGroup)
                staffGroup1 = score1.recurse().getElementById(
                    op[1].staff_group  # type: ignore
                )
                staffGroup2 = score2.recurse().getElementById(
                    op[2].staff_group  # type: ignore
                )
                if t.TYPE_CHECKING:
                    assert staffGroup1 is not None
                    assert staffGroup2 is not None
                newLine = f"@@ {Visualization._location_of(staffGroup1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(StaffGroup:parts) {op[1].readable_str('parts')}\n"
                oneOutput += newLine
                newLine = f"+(StaffGroup:parts) {op[2].readable_str('parts')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # note
            if op[0] == "noteins":
                assert isinstance(op[2], AnnNote)
                # The note that was inserted may in fact be a note within a chord,
                # so be careful to use the chord and the note in that case for
                # the appropriate operations.
                noteOrChord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert noteOrChord2 is not None
                if len(op) >= 5 and op[4] is not None:
                    note2 = noteOrChord2.notes[op[4]]
                else:
                    note2 = noteOrChord2
                newLine = f"@@ {Visualization._location_of(noteOrChord2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+({note2.classes[0]}) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "notedel":
                assert isinstance(op[1], AnnNote)
                # The note that was deleted may in fact be a note within a chord,
                # so be careful to use the chord and the note in that case for
                # the appropriate operations.
                noteOrChord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert noteOrChord1 is not None
                if len(op) >= 5 and op[4] is not None:
                    note1 = noteOrChord1.notes[op[4]]
                else:
                    note1 = noteOrChord1
                newLine = f"@@ {Visualization._location_of(noteOrChord1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # pitch
            if op[0] == "pitchnameedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if not op[1].is_in_chord and "Chord" in chord1.classes:
                    # report just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if not op[2].is_in_chord and "Chord" in chord2.classes:
                    # report just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                else:
                    idx = 0
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(chord1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:pitch) {op[1].readable_str('pitch', idx=idx)}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:pitch) {op[2].readable_str('pitch', idx=idx)}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "inspitch":
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if not op[2].is_in_chord and "Chord" in chord2.classes:
                    # report just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                else:
                    idx = 0
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(chord2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+({note2.classes[0]}:pitch) {op[2].readable_str('pitch', idx=idx)}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "delpitch":
                assert isinstance(op[1], AnnNote)
                assert len(op) == 5  # the indices must be there
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # report just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                else:
                    idx = 0
                if t.TYPE_CHECKING:
                    assert note1 is not None
                newLine = f"@@ {Visualization._location_of(chord1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:pitch) {op[1].readable_str('pitch', idx=idx)}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "headedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:head) {op[1].readable_str('head')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:head) {op[2].readable_str('head')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "graceedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:grace) {op[1].readable_str('grace')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:grace) {op[2].readable_str('grace')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "graceslashedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:graceslash) {op[1].readable_str('graceslash')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:graceslash) {op[2].readable_str('graceslash')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # beam
            if op[0] in ("insbeam", "delbeam", "editbeam"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:flagsbeams) {op[1].readable_str('flagsbeams')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:flagsbeams) {op[2].readable_str('flagsbeams')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "editnoteshape":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:noteshape) {op[1].readable_str('noteshape')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:noteshape) {op[2].readable_str('noteshape')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] in ("editspace", "insspace", "delspace"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:spacebefore) {op[1].readable_str('spacebefore')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:spacebefore) {op[2].readable_str('spacebefore')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "editnoteheadfill":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:notefill) {op[1].readable_str('notefill')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:notefill) {op[2].readable_str('notefill')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "editnoteheadparenthesis":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:noteparen) {op[1].readable_str('noteparen')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:noteparen) {op[2].readable_str('noteparen')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "editstemdirection":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:stemdir) {op[1].readable_str('stemdir')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:stemdir) {op[2].readable_str('stemdir')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "editstyle":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                sd1 = op[1].styledict
                sd2 = op[2].styledict
                changedStr = ""
                for k1, v1 in sd1.items():
                    if k1 not in sd2 or sd2[k1] != v1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k1

                # one last thing: check for keys in sd2 that aren't in sd1
                for k2 in sd2:
                    if k2 not in sd1:
                        if changedStr:
                            changedStr += ","
                        changedStr += k2

                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                style1 = op[1].readable_str('style', changedStr=changedStr)
                style2 = op[2].readable_str('style', changedStr=changedStr)
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:{changedStr}) {style1}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:{changedStr}) {style2}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # accident
            if op[0] in ("accidentins", "accidentdel", "accidentedit"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # report only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # report only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                else:
                    idx = 0
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(chord1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:accid) {op[1].readable_str('accid', idx=idx)}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:accid) {op[2].readable_str('accid', idx=idx)}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] in ("dotins", "dotdel"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:dots) {op[1].readable_str('dots')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:dots) {op[2].readable_str('dots')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # tuplets
            if op[0] in ("instuplet", "deltuplet", "edittuplet"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:tuplet) {op[1].readable_str('tuplet')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:tuplet) {op[2].readable_str('tuplet')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # ties
            if op[0] in ("tieins", "tiedel"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # Color the modified note here in both scores,
                # using Visualization.INSERTED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord1 is not None
                note1 = chord1
                if "Chord" in chord1.classes:
                    # report just the indexed note in the chord
                    idx = op[4][0]
                    note1 = chord1.notes[idx]
                if t.TYPE_CHECKING:
                    assert note1 is not None
                chord2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert chord2 is not None
                note2 = chord2
                if "Chord" in chord2.classes:
                    # report just the indexed note in the chord
                    idx = op[4][1]
                    note2 = chord2.notes[idx]
                else:
                    idx = 0
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(chord1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:tie) {op[1].readable_str('tie', idx=idx)}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:tie) {op[2].readable_str('tie', idx=idx)}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # expressions
            if op[0] in ("insexpression", "delexpression", "editexpression"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:expression) {op[1].readable_str('expression')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:expression) {op[2].readable_str('expression')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # articulations
            if op[0] in ("insarticulation", "delarticulation", "editarticulation"):
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].general_note)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-({note1.classes[0]}:artic) {op[1].readable_str('artic')}\n"
                oneOutput += newLine
                newLine = f"+({note2.classes[0]}:artic) {op[2].readable_str('artic')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # lyrics
            if op[0] == "lyricins":
                assert isinstance(op[2], AnnLyric)
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+(Lyric) {op[2].readable_str('')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricdel":
                assert isinstance(op[1], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric) {op[1].readable_str('')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricsub":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric) {op[1].readable_str('')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+(Lyric) {op[2].readable_str('')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric:rawtext) {op[1].readable_str('rawtext')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+(Lyric:rawtext) {op[2].readable_str('rawtext')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricnumedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric:number) {op[1].readable_str('number')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+(Lyric:number) {op[2].readable_str('number')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricidedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric:id) {op[1].readable_str('id')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+(Lyric:id) {op[2].readable_str('id')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricoffsetedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric:offset) {op[1].readable_str('offset')}\n"
                oneOutput += newLine
                newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                oneOutput += newLine
                newLine = f"+(Lyric:offset) {op[2].readable_str('offset')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "lyricstyleedit":
                assert isinstance(op[1], AnnLyric)
                assert isinstance(op[2], AnnLyric)
                note1 = score1.recurse().getElementById(op[1].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note1 is not None
                note2 = score2.recurse().getElementById(op[2].lyric_holder)  # type: ignore
                if t.TYPE_CHECKING:
                    assert note2 is not None
                newLine = f"@@ {Visualization._location_of(note1, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(Lyric:style) {op[1].readable_str('style')}"
                oneOutput += newLine
                if op[1].offset != op[2].offset:
                    outputList.append(oneOutput)
                    newLine = f"@@ {Visualization._location_of(note2, score2)} @@\n"
                    oneOutput = newLine
                else:
                    oneOutput += "\n"
                newLine = f"+(Lyric:style) {op[2].readable_str('style')}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            # metadata
            if op[0] == "mditemins":
                assert isinstance(op[2], AnnMetadataItem)
                newLine = f"@@ {Visualization._location_of(score2.metadata, score2)} @@\n"
                oneOutput = newLine
                newLine = f"+(metadata) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "mditemdel":
                assert isinstance(op[1], AnnMetadataItem)
                newLine = f"@@ {Visualization._location_of(score1.metadata, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(metadata) {op[1].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "mditemsub":
                assert isinstance(op[1], AnnMetadataItem)
                assert isinstance(op[2], AnnMetadataItem)
                newLine = f"@@ {Visualization._location_of(score1.metadata, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(metadata) {op[1].readable_str()}\n"
                oneOutput += newLine
                newLine = f"+(metadata) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "mditemkeyedit":
                assert isinstance(op[1], AnnMetadataItem)
                assert isinstance(op[2], AnnMetadataItem)
                newLine = f"@@ {Visualization._location_of(score1.metadata, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(metadata:key) {op[1].readable_str()}\n"
                oneOutput += newLine
                newLine = f"+(metadata:key) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            if op[0] == "mditemvalueedit":
                assert isinstance(op[1], AnnMetadataItem)
                assert isinstance(op[2], AnnMetadataItem)
                newLine = f"@@ {Visualization._location_of(score1.metadata, score1)} @@\n"
                oneOutput = newLine
                newLine = f"-(metadata:value) {op[1].readable_str()}\n"
                oneOutput += newLine
                newLine = f"+(metadata:value) {op[2].readable_str()}"
                oneOutput += newLine
                outputList.append(oneOutput)
                continue

            print(
                f"Annotation type {op[0]} not yet supported for visualization",
                file=sys.stderr
            )

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

        if operations:
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
    def get_secr_output(
        cost: int,
        annotated_predicted_score: AnnScore,
        annotated_ground_truth_score: AnnScore,
    ) -> dict[str, str]:
        num_syms_in_ground_truth: int = annotated_ground_truth_score.notation_size()
        num_syms_in_predicted: int = annotated_predicted_score.notation_size()
        secr: float = Visualization.get_secr(
            cost, num_syms_in_predicted, num_syms_in_ground_truth
        )
        num_syms_in_both: int = num_syms_in_ground_truth + num_syms_in_predicted
        output: dict[str, str] = {
            'symbolEditCost': f'{cost}',
            'numSymbolsInPredicted': f'{num_syms_in_predicted}',
            'numSymbolsInGroundTruth': f'{num_syms_in_ground_truth}',
            'numSymbolsInBoth': f'{num_syms_in_both}',
            'SECR': f'{secr}',
        }
        return output

    @staticmethod
    def get_secr(
        cost: int,
        num_syms_in_predicted: int,
        num_syms_in_ground_truth: int,
    ) -> float:
        num_syms_in_both: int = num_syms_in_ground_truth + num_syms_in_predicted

        # Instead of divide by zero, return secr == 0.0 (because both scores being
        # empty means they are exactly the same)
        secr: float = 0.0
        if num_syms_in_both != 0:
            secr = float(cost) / float(num_syms_in_both)
        return secr

    @staticmethod
    def get_edit_costs_dict(
        op_list: list[tuple],
        num_syntax_errors_fixed: int,
        detail: DetailLevel | int
    ) -> dict[str, int]:
        Visualization.create_header_names_once(detail)

        edit_costs_dict: dict[str, int] = {}
        for op in op_list:
            name: str = Visualization._HEADER_NAME_OF_EDIT_NAME[op[0]]
            if op[0].startswith('extra'):
                extra: AnnExtra | None = op[1] or op[2]
                if extra is not None and extra.kind:
                    name = re.sub('extra', extra.kind, op[0])
                    name = Visualization._HEADER_NAME_OF_EDIT_NAME[name]
            cost: int = op[3]
            if name not in edit_costs_dict:
                edit_costs_dict[name] = cost
            else:
                edit_costs_dict[name] = edit_costs_dict[name] + cost

        edit_costs_dict['bad kern syntax SEC'] = num_syntax_errors_fixed

        return edit_costs_dict

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
            ordered_names.append(re.sub('SEC', '% contribution to SECR', hn))

        Visualization._ORDERED_HEADER_NAMES = ordered_names


    _ORDERED_HEADER_NAMES: list[str] = []

    _HEADER_NAME_OF_EDIT_NAME: dict[str, str] = {
        'syntax_errors_fixed': 'bad kern syntax SEC',
        'noteins': 'wrong note SEC',
        'notedel': 'wrong note SEC',
        'headedit': 'wrong note head SEC',
        'insbeam': 'wrong flag/beam SEC',
        'delbeam': 'wrong flag/beam SEC',
        'editbeam': 'wrong flag/beam SEC',
        'dotdel': 'wrong dot SEC',
        'dotins': 'wrong dot SEC',
        'instuplet': 'wrong tuplet SEC',
        'deltuplet': 'wrong tuplet SEC',
        'edittuplet': 'wrong tuplet SEC',
        'accidentins': 'wrong accidental SEC',
        'accidentdel': 'wrong accidental SEC',
        'accidentedit': 'wrong accidental SEC',
        'editstemdirection': 'wrong note stem SEC',
        'graceedit': 'wrong graceness SEC',
        'graceslashedit': 'wrong graceness SEC',
        'editnoteshape': 'wrong note head SEC',
        'editnoteheadfill': 'wrong note head SEC',
        'editnoteheadparenthesis': 'wrong note head SEC',
        'editstyle': 'wrong note SEC',
        'tiedel': 'wrong tie SEC',
        'tieins': 'wrong tie SEC',
        'insarticulation': 'wrong articulation SEC',
        'delarticulation': 'wrong articulation SEC',
        'editarticulation': 'wrong articulation SEC',
        'insexpression': 'wrong ornament SEC',
        'delexpression': 'wrong ornament SEC',
        'editexpression': 'wrong ornament SEC',

        'insspace': 'wrong note SEC',
        'delspace': 'wrong note SEC',
        'editspace': 'wrong note SEC',

        'lyricins': 'wrong lyric SEC',
        'lyricdel': 'wrong lyric SEC',
        'lyricedit': 'wrong lyric SEC',
        'lyricnumedit': 'wrong lyric SEC',
        'lyricidedit': 'wrong lyric SEC',
        'lyricoffsetedit': 'wrong lyric SEC',
        'lyricstyleedit': 'wrong lyric SEC',

        'clefins': 'wrong clef SEC',
        'clefdel': 'wrong clef SEC',
        'clefcontentedit': 'wrong clef SEC',  # shouldn't happen, clefs have a symbol
        'clefsymboledit': 'wrong clef SEC',
        'clefinfoedit': 'wrong clef SEC',  # shouldn't happen, clefs have a symbol
        'clefoffsetedit': 'wrong clef SEC',  # shouldn't happen; we pair by offset
        'clefdurationedit': 'wrong clef SEC',  # shouldn't happen; clefs have no dur
        'clefstyleedit': 'wrong clef SEC',

        'timesigins': 'wrong timesig SEC',
        'timesigdel': 'wrong timesig SEC',
        'timesigcontentedit': 'wrong timesig SEC',  # shouldn't happen, timesigs have info
        'timesigsymboledit': 'wrong timesig SEC',  # shouldn't happen, ditto
        'timesiginfoedit': 'wrong timesig SEC',
        'timesigoffsetedit': 'wrong timesig SEC',  # shouldn't happen; we pair by offset
        'timesigdurationedit': 'wrong timesig SEC',  # shouldn't happen; timesigs have no dur
        'timesigstyleedit': 'wrong timesig SEC',

        'keysigins': 'wrong keysig SEC',
        'keysigdel': 'wrong keysig SEC',
        'keysigcontentedit': 'wrong keysig SEC',  # shouldn't happen; keysigs have info
        'keysigsymboledit': 'wrong keysig SEC',  # shouldn't happen; keysigs have info
        'keysiginfoedit': 'wrong keysig SEC',
        'keysigoffsetedit': 'wrong keysig SEC',  # shouldn't happen; we pair by offset
        'keysigdurationedit': 'wrong keysig SEC',  # shouldn't happen; keysigs have no dur
        'keysigstyleedit': 'wrong keysig SEC',

        'tempoins': 'wrong tempo SEC',
        'tempodel': 'wrong tempo SEC',
        'tempocontentedit': 'wrong tempo SEC',
        'temposymboledit': 'wrong tempo SEC',
        'tempoinfoedit': 'wrong tempo SEC',  # shouldn't happen; tempos have no info
        'tempooffsetedit': 'wrong tempo SEC',  # shouldn't happen; we pair by offset
        'tempodurationedit': 'wrong tempo SEC',  # shouldn't happen; tempos have no dur
        'tempostyleedit': 'wrong tempo SEC',

        'barlineins': 'wrong barline SEC',
        'barlinedel': 'wrong barline SEC',
        'barlinecontentedit': 'wrong barline SEC',  # shouldn't happen; barlines have no content
        'barlinesymboledit': 'wrong barline SEC',
        'barlineinfoedit': 'wrong barline SEC',
        'barlineoffsetedit': 'wrong barline SEC',  # shouldn't happen; we pair by offset
        'barlinedurationedit': 'wrong barline SEC',  # shouldn't happen; barlines have no dur
        'barlinestyleedit': 'wrong barline SEC',

        # we combine barlines and repeats because repeats are just different types
        # of barline
        'repeatins': 'wrong barline SEC',
        'repeatdel': 'wrong barline SEC',
        'repeatcontentedit': 'wrong barline SEC',  # shouldn't happen; repeats have no content
        'repeatsymboledit': 'wrong barline SEC',
        'repeatinfoedit': 'wrong barline SEC',
        'repeatoffsetedit': 'wrong barline SEC',  # shouldn't happen; we pair by offset
        'repeatdurationedit': 'wrong barline SEC',  # shouldn't happen; repeats have no dur
        'repeatstyleedit': 'wrong barline SEC',

        'directionins': 'wrong direction SEC',
        'directiondel': 'wrong direction SEC',
        'directioncontentedit': 'wrong direction SEC',
        'directionsymboledit': 'wrong direction SEC',  # shouldn't happen; directions have content
        'directioninfoedit': 'wrong direction SEC',  # shouldn't happen; directions have content
        'directionoffsetedit': 'wrong direction SEC',  # shouldn't happen; we pair by offset
        'directiondurationedit': 'wrong direction SEC',  # shouldn't happen; directions have no dur
        'directionstyleedit': 'wrong direction SEC',

        'dynamicins': 'wrong dynamic SEC',
        'dynamicdel': 'wrong dynamic SEC',
        'dynamiccontentedit': 'wrong dynamic SEC',  # shouldn't happen; directions are symbolic
        'dynamicsymboledit': 'wrong dynamic SEC',
        'dynamicinfoedit': 'wrong dynamic SEC',  # shouldn't happen; directions are symbolic
        'dynamicoffsetedit': 'wrong dynamic SEC',  # shouldn't happen; we pair by offset
        'dynamicdurationedit': 'wrong dynamic SEC',
        'dynamicstyleedit': 'wrong dynamic SEC',

        'slurins': 'wrong slur SEC',
        'slurdel': 'wrong slur SEC',
        'slurcontentedit': 'wrong slur SEC',  # shouldn't happen
        'slursymboledit': 'wrong slur SEC',  # shouldn't happen
        'slurinfoedit': 'wrong slur SEC',  # shouldn't happen
        'sluroffsetedit': 'wrong slur SEC',  # shouldn't happen; we pair by offset
        'slurdurationedit': 'wrong slur SEC',
        'slurstyleedit': 'wrong slur SEC',

        'ottavains': 'wrong ottava SEC',
        'ottavadel': 'wrong ottava SEC',
        'ottavacontentedit': 'wrong ottava SEC',  # shouldn't happen; ottava is symbolic
        'ottavasymboledit': 'wrong ottava SEC',
        'ottavainfoedit': 'wrong ottava SEC',  # shouldn't happen; ottava is symbolic
        'ottavaoffsetedit': 'wrong ottava SEC',  # shouldn't happen; we pair by offset
        'ottavadurationedit': 'wrong ottava SEC',
        'ottavastyleedit': 'wrong ottava SEC',

        'arpeggioins': 'wrong multi-staff arpeggio SEC',
        'arpeggiodel': 'wrong multi-staff arpeggio SEC',
        'arpeggiocontentedit': 'wrong multi-staff arpeggio SEC',  # shouldn't happen
        'arpeggiosymboledit': 'wrong multi-staff arpeggio SEC',
        'arpeggioinfoedit': 'wrong multi-staff arpeggio SEC',
        'arpeggiooffsetedit': 'wrong multi-staff arpeggio SEC',  # shouldn't happen
        'arpeggiodurationedit': 'wrong multi-staff arpeggio SEC',  # shouldn't happen
        'arpeggiostyleedit': 'wrong multi-staff arpeggio SEC',  # shouldn't happen

        'tremoloins': 'wrong fingered tremolo SEC',
        'tremolodel': 'wrong fingered tremolo SEC',
        'tremolocontentedit': 'wrong fingered tremolo SEC',  # shouldn't happen
        'tremolosymboledit': 'wrong fingered tremolo SEC',
        'tremoloinfoedit': 'wrong fingered tremolo SEC',  # shouldn't happen
        'tremolooffsetedit': 'wrong fingered tremolo SEC',  # shouldn't happen; we pair by offset
        'tremolodurationedit': 'wrong fingered tremolo SEC',
        'tremolostyleedit': 'wrong fingered tremolo SEC',  # shouldn't happen

        'chordsymins': 'wrong chord symbol SEC',
        'chordsymdel': 'wrong chord symbol SEC',
        'chordsymcontentedit': 'wrong chord symbol SEC',  # shouldn't happen
        'chordsymsymboledit': 'wrong chord symbol SEC',
        'chordsyminfoedit': 'wrong chord symbol SEC',  # shouldn't happen
        'chordsymoffsetedit': 'wrong chord symbol SEC',  # shouldn't happen; we pair by offset
        'chordsymdurationedit': 'wrong chord symbol SEC',  # shouldn't happen
        'chordsymstyleedit': 'wrong chord symbol SEC',

        'endingins': 'wrong ending SEC',
        'endingdel': 'wrong ending SEC',
        'endingcontentedit': 'wrong ending SEC',
        'endingsymboledit': 'wrong ending SEC',
        'endinginfoedit': 'wrong ending SEC',
        'endingoffsetedit': 'wrong ending SEC',  # shouldn't happen; we pair by offset
        'endingdurationedit': 'wrong ending SEC',
        'endingstyleedit': 'wrong ending SEC',  # shouldn't happen

        'staffinfoins': 'wrong staff info SEC',
        'staffinfodel': 'wrong staff info SEC',
        'staffinfocontentedit': 'wrong staff info SEC',  # shouldn't happen
        'staffinfosymboledit': 'wrong staff info SEC',  # shouldn't happen
        'staffinfoinfoedit': 'wrong staff info SEC',
        'staffinfooffsetedit': 'wrong staff info SEC',  # shouldn't happen; we pair by offset
        'staffinfodurationedit': 'wrong staff info SEC',  # shouldn't happen
        'staffinfostyleedit': 'wrong staff info SEC',  # shouldn't happen

        'systembreakins': 'wrong system break SEC',
        'systembreakdel': 'wrong system break SEC',
        'systembreakcontentedit': 'wrong system break SEC',  # shouldn't happen
        'systembreaksymboledit': 'wrong system break SEC',
        'systembreakinfoedit': 'wrong system break SEC',  # shouldn't happen
        'systembreakoffsetedit': 'wrong system break SEC',  # shouldn't happen; we pair by offset
        'systembreakdurationedit': 'wrong system break SEC',  # shouldn't happen
        'systembreakstyleedit': 'wrong system break SEC',  # shouldn't happen

        'pagebreakins': 'wrong page break SEC',
        'pagebreakdel': 'wrong page break SEC',
        'pagebreakcontentedit': 'wrong page break SEC',  # shouldn't happen
        'pagebreaksymboledit': 'wrong page break SEC',
        'pagebreakinfoedit': 'wrong page break SEC',  # shouldn't happen
        'pagebreakoffsetedit': 'wrong page break SEC',  # shouldn't happen; we pair by offset
        'pagebreakdurationedit': 'wrong page break SEC',  # shouldn't happen
        'pagebreakstyleedit': 'wrong page break SEC',  # shouldn't happen

        # These 'extra*' are still here in case there is an AnnExtra (in future) we didn't
        # cover above
        'extrains': 'wrong other object SEC',
        'extradel': 'wrong other object SEC',
        'extracontentedit': 'wrong other object SEC',
        'extrasymboledit': 'wrong other object SEC',
        'extrainfoedit': 'wrong other object SEC',
        'extraoffsetedit': 'wrong other object SEC',  # shouldn't happen; we pair by offset
        'extradurationedit': 'wrong other object SEC',
        'extrastyleedit': 'wrong other object SEC',

        'insbar': 'entire measure insert/delete SEC',
        'delbar': 'entire measure insert/delete SEC',

        'inspart': 'entire staff insert/delete SEC',
        'delpart': 'entire staff insert/delete SEC',

        'mditemins': 'wrong metadata SEC',
        'mditemdel': 'wrong metadata SEC',
        'mditemkeyedit': 'wrong metadata SEC',  # shouldn't happen because we pair by key
        'mditemvalueedit': 'wrong metadata SEC',

        'staffgrpins': 'wrong staff group SEC',
        'staffgrpdel': 'wrong staff group SEC',
        'staffgrpnameedit': 'wrong staff group name/abbrev SEC',
        'staffgrpabbreviationedit': 'wrong staff group name/abbrev SEC',
        'staffgrpsymboledit': 'wrong staff group brace SEC',
        'staffgrpbartogetheredit': 'wrong staff group barline SEC',
        'staffgrppartindicesedit': 'wrong staff group SEC',
    }

    _VOICING_HEADER_NAME_OF_EDIT_NAME_EXTRAS: dict[str, str] = {
        # The following will only happen if Voicing is selected,
        # because when Voicing is not selected, (1) chords are ignored,
        # so we will never see chords with inserted or deleted pitches,
        # (2) notes are paired by pitch, so instead of pitch edits we
        # get note insertions and deletions, and (3) we ignore voices
        # completely, so we certainly don't insert or delete them.
        'inspitch': 'pitch insert/delete SEC',
        'delpitch': 'pitch insert/delete SEC',
        'pitchnameedit': 'wrong pitch SEC',
        'pitchtypeedit': 'wrong pitch SEC',
        'voiceins': 'voice insert/delete SEC',
        'voicedel': 'voice insert/delete SEC',
    }

    _PRE_EDITS_HEADER_NAMES: list[str] = [
        'gtpath',
        'predpath',
    ]
    _POST_EDITS_HEADER_NAMES: list[str] = [
        'gt numsyms',
        'pred numsyms',
        'total numsyms (in both scores)',
        'SEC (symbolic edit cost)',
        'SECR (SEC / total numsyms)',
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
        total_sym_edit_cost: int = 0
        total_edit_costs_dict: dict[str, int] = {}

        for metrics in metrics_list:
            total_gt_numsyms += metrics.gt_numsyms
            total_pred_numsyms += metrics.pred_numsyms
            total_sym_edit_cost += metrics.sym_edit_cost
            for name in metrics.edit_costs_dict:
                if name not in total_edit_costs_dict:
                    total_edit_costs_dict[name] = metrics.edit_costs_dict[name]
                else:
                    total_edit_costs_dict[name] += metrics.edit_costs_dict[name]

        total_numsyms: int = total_gt_numsyms + total_pred_numsyms

        overall_SECR: float = Visualization.get_secr(
            total_sym_edit_cost, total_pred_numsyms, total_gt_numsyms
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
            elif name == 'SEC (symbolic edit cost)':
                totals_line += f'{total_sym_edit_cost}'
            elif name == 'SECR (SEC / total numsyms)':
                totals_line += f'{overall_SECR}'

        # then the edit fields
        previousColumnCost: int = 0
        for name in Visualization._ORDERED_HEADER_NAMES:
            totals_line += ', '
            if name.endswith('SEC'):
                if name in total_edit_costs_dict:
                    previousColumnCost = total_edit_costs_dict[name]
                    totals_line += f'{total_edit_costs_dict[name]}'
                else:
                    previousColumnCost = 0
                    totals_line += '0'
            elif name.endswith('% contribution to SECR'):
                if previousColumnCost:
                    totals_line += (
                        f'{float(previousColumnCost * 100) / float(total_sym_edit_cost)}'
                    )
                else:
                    totals_line += '0.'
                previousColumnCost = 0
            else:
                # how did we get here?
                previousColumnCost = 0


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
            elif name == 'SEC (symbolic edit cost)':
                totals_line += f'{total_sym_edit_cost}'
            elif name == 'SECR (SEC / total numsyms)':
                totals_line += f'{overall_SECR}'

        repeated_header_line: str = Visualization.get_output_csv_header(detail)

        trailer_line: str = totals_line + '\n' + repeated_header_line
        return trailer_line

    @staticmethod
    def get_output_csv_line(
        metrics: EvaluationMetrics,
        detail: DetailLevel | int
    ) -> str:
        Visualization.create_header_names_once(detail)

        # 888 could validate metrics.sym_edit_cost here (make sure it is the sum of
        # 888 everything in metrics.edit_costs_dict)
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
            elif name == 'SEC (symbolic edit cost)':
                line += f'{metrics.sym_edit_cost}'
            elif name == 'SECR (SEC / total numsyms)':
                line += f'{metrics.sym_edit_cost_ratio}'

        # then the edit fields
        previousColumnCost: int = 0
        for name in Visualization._ORDERED_HEADER_NAMES:
            line += ', '
            if name.endswith('SEC'):
                if name in metrics.edit_costs_dict:
                    previousColumnCost = metrics.edit_costs_dict[name]
                    line += f'{metrics.edit_costs_dict[name]}'
                else:
                    line += '0'
            elif name.endswith('% contribution to SECR'):
                if previousColumnCost:
                    line += (
                        f'{float(previousColumnCost * 100) / float(metrics.sym_edit_cost)}'
                    )
                else:
                    line += '0.'
                previousColumnCost = 0
            else:
                # how did we get here?
                previousColumnCost = 0

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
            elif name == 'SEC (symbolic edit cost)':
                line += f'{metrics.sym_edit_cost}'
            elif name == 'SECR (SEC / total numsyms)':
                line += f'{metrics.sym_edit_cost_ratio}'

        return line
