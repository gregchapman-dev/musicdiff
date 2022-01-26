# ------------------------------------------------------------------------------
# Purpose:       visualization is a diff visualization package for use by musicdiff.
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

from typing import List, Tuple

import music21 as m21

from musicdiff.annotation import AnnMeasure, AnnVoice, AnnNote


class Visualization:
    # These can be set by the client to different colors
    INSERTED_COLOR = "red"
    DELETED_COLOR = "red"
    CHANGED_COLOR = "red"

    @staticmethod
    def mark_diffs(
        score1: m21.stream.Score, score2: m21.stream.Score, operations: List[Tuple]
    ):
        for op in operations:
            # bar
            if op[0] == "insbar":
                assert isinstance(op[2], AnnMeasure)
                # color all the notes in the inserted score2 measure using Visualization.INSERTED_COLOR
                measure2 = score2.recurse().getElementById(op[2].measure)
                textExp = m21.expressions.TextExpression("inserted measure")
                textExp.style.color = Visualization.INSERTED_COLOR
                measure2.insert(0, textExp)
                measure2.style.color = (
                    Visualization.INSERTED_COLOR
                )  # this apparently does nothing
                for el in measure2.recurse().notesAndRests:
                    el.style.color = Visualization.INSERTED_COLOR

            elif op[0] == "delbar":
                assert isinstance(op[1], AnnMeasure)
                # color all the notes in the deleted score1 measure using Visualization.DELETED_COLOR
                measure1 = score1.recurse().getElementById(op[1].measure)
                textExp = m21.expressions.TextExpression("deleted measure")
                textExp.style.color = Visualization.DELETED_COLOR
                measure1.insert(0, textExp)
                measure1.style.color = (
                    Visualization.DELETED_COLOR
                )  # this apparently does nothing
                for el in measure1.recurse().notesAndRests:
                    el.style.color = Visualization.DELETED_COLOR

            # voices
            elif op[0] == "voiceins":
                assert isinstance(op[2], AnnVoice)
                # color all the notes in the inserted score2 voice using Visualization.INSERTED_COLOR
                voice2 = score2.recurse().getElementById(op[2].voice)
                textExp = m21.expressions.TextExpression("inserted voice")
                textExp.style.color = Visualization.INSERTED_COLOR
                voice2.insert(0, textExp)

                voice2.style.color = (
                    Visualization.INSERTED_COLOR
                )  # this apparently does nothing
                for el in voice2.recurse().notesAndRests:
                    el.style.color = Visualization.INSERTED_COLOR

            elif op[0] == "voicedel":
                assert isinstance(op[1], AnnVoice)
                # color all the notes in the deleted score1 voice using Visualization.DELETED_COLOR
                voice1 = score1.recurse().getElementById(op[1].voice)
                textExp = m21.expressions.TextExpression("deleted voice")
                textExp.style.color = Visualization.DELETED_COLOR
                voice1.insert(0, textExp)

                voice1.style.color = (
                    Visualization.DELETED_COLOR
                )  # this apparently does nothing
                for el in voice1.recurse().notesAndRests:
                    el.style.color = Visualization.DELETED_COLOR

            # note
            elif op[0] == "noteins":
                assert isinstance(op[2], AnnNote)
                # color the inserted score2 general note (note, chord, or rest) using Visualization.INSERTED_COLOR
                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.INSERTED_COLOR
                if "Rest" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted rest")
                elif "Chord" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted chord")
                else:
                    textExp = m21.expressions.TextExpression("inserted note")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "notedel":
                assert isinstance(op[1], AnnNote)
                # color the deleted score1 general note (note, chord, or rest) using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.DELETED_COLOR
                if "Rest" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted rest")
                elif "Chord" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted chord")
                else:
                    textExp = m21.expressions.TextExpression("deleted note")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

            # pitch
            elif op[0] == "pitchnameedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the changed note (in both scores) using Visualization.CHANGED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "inspitch":
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the inserted note in score2 using Visualization.INSERTED_COLOR
                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
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

            elif op[0] == "delpitch":
                assert isinstance(op[1], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the deleted note in score1 using Visualization.DELETED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
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

            elif op[0] == "headedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed note/rest/chord (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # beam
            elif op[0] == "insbeam":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.INSERTED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.INSERTED_COLOR
                if hasattr(note1, "beams"):
                    for beam in note1.beams:
                        beam.style.color = (
                            Visualization.INSERTED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = Visualization.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.INSERTED_COLOR
                if hasattr(note2, "beams"):
                    for beam in note2.beams:
                        beam.style.color = (
                            Visualization.INSERTED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delbeam":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.DELETED_COLOR
                if hasattr(note1, "beams"):
                    for beam in note1.beams:
                        beam.style.color = (
                            Visualization.DELETED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.DELETED_COLOR
                if hasattr(note2, "beams"):
                    for beam in note2.beams:
                        beam.style.color = (
                            Visualization.DELETED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = Visualization.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editbeam":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed beam (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                if hasattr(note1, "beams"):
                    for beam in note1.beams:
                        beam.style.color = (
                            Visualization.CHANGED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                if hasattr(note2, "beams"):
                    for beam in note2.beams:
                        beam.style.color = (
                            Visualization.CHANGED_COLOR
                        )  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # accident
            elif op[0] == "accidentins":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using Visualization.INSERTED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = Visualization.INSERTED_COLOR
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                if note2.pitch.accidental:
                    note2.pitch.accidental.style.color = Visualization.INSERTED_COLOR
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "accidentdel":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using Visualization.DELETED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = Visualization.DELETED_COLOR
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = Visualization.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                if note2.pitch.accidental:
                    note2.pitch.accidental.style.color = Visualization.DELETED_COLOR
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = Visualization.DELETED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "accidentedit":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # color the changed accidental (in both scores) using Visualization.CHANGED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = Visualization.CHANGED_COLOR
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                if note2.pitch.accidental:
                    note2.pitch.accidental.style.color = Visualization.CHANGED_COLOR
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = Visualization.CHANGED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "dotins":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores, using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "dotdel":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores, using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # tuplets
            elif op[0] == "instuplet":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "deltuplet":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "edittuplet":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # ties
            elif op[0] == "tieins":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # Color the modified note here in both scores, using Visualization.INSERTED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = Visualization.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "tiedel":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                assert len(op) == 5  # the indices must be there
                # Color the modified note in both scores, using Visualization.DELETED_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = Visualization.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = Visualization.DELETED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            # expressions
            elif op[0] == "insexpression":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the note in both scores using Visualization.INSERTED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = Visualization.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delexpression":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the deleted expression in score1 using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = Visualization.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = Visualization.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editexpression":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the changed beam (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # articulations
            elif op[0] == "insarticulation":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.INSERTED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = Visualization.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = Visualization.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delarticulation":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note in both scores using Visualization.DELETED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = Visualization.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = Visualization.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editarticulation":
                assert isinstance(op[1], AnnNote)
                assert isinstance(op[2], AnnNote)
                # color the modified note (in both scores) using Visualization.CHANGED_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = Visualization.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = Visualization.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = Visualization.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            else:
                print(f"Annotation type {op[0]} not yet supported for visualization")

    @staticmethod
    def show_diffs(score1: m21.stream.Score, score2: m21.stream.Score, out_path1: str = None, out_path2 : str = None):
        # display the two (presumably annotated) scores
        originalComposer1: str = None
        originalComposer2: str = None

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

        #save files if requested
        if (out_path1 is not None) and (out_path2 is not None):
            score1.write("musicxml.pdf", makeNotation=False, fp=out_path1)
            score2.write("musicxml.pdf", makeNotation=False, fp=out_path2)
            print(f"Annotated scores saved in {out_path1} and {out_path2}.")
        else: # just display the scores
            score1.show("musicxml.pdf", makeNotation=False)
            score2.show("musicxml.pdf", makeNotation=False)

