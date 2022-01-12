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

import re
import operator
import copy
import math
from pathlib import Path
import os
from typing import List, Tuple
from collections.abc import Iterable

import music21 as m21

from musicdiff import notation

class Visualization:
    def __init__(self, score1: notation.Score, score2: notation.Score, operations: List[Tuple]):
        # These can be set by the client to different colors
        self.INSERTED_COLOR = "red"
        self.DELETED_COLOR = "red"
        self.CHANGED_COLOR = "red"

        self.score1 = score1
        self.score2 = score2
        self.operations = operations

    def annotate_differences(score1, score2, operations):
        for op in operations:
            # bar
            if op[0] == "insbar":
                assert type(op[2]) == nlin.Bar
                # color all the notes in the inserted score2 measure using INS_COLOR
                measure2 = score2.recurse().getElementById(op[2].measure)
                textExp = m21.expressions.TextExpression("inserted measure")
                textExp.style.color = INS_COLOR
                measure2.insert(0, textExp)
                measure2.style.color = INS_COLOR  # this apparently does nothing
                for el in measure2.recurse().notesAndRests:
                    el.style.color = INS_COLOR

            elif op[0] == "delbar":
                assert type(op[1]) == nlin.Bar
                # color all the notes in the deleted score1 measure using DEL_COLOR
                measure1 = score1.recurse().getElementById(op[1].measure)
                textExp = m21.expressions.TextExpression("deleted measure")
                textExp.style.color = DEL_COLOR
                measure1.insert(0, textExp)
                measure1.style.color = DEL_COLOR  # this apparently does nothing
                for el in measure1.recurse().notesAndRests:
                    el.style.color = DEL_COLOR

            # voices
            elif op[0] == "voiceins":
                assert type(op[2]) == nlin.Voice
                # color all the notes in the inserted score2 voice using INS_COLOR
                voice2 = score2.recurse().getElementById(op[2].voice)
                textExp = m21.expressions.TextExpression("inserted voice")
                textExp.style.color = INS_COLOR
                voice2.insert(0, textExp)

                voice2.style.color = INS_COLOR  # this apparently does nothing
                for el in voice2.recurse().notesAndRests:
                    el.style.color = INS_COLOR

            elif op[0] == "voicedel":
                assert type(op[1]) == nlin.Voice
                # color all the notes in the deleted score1 voice using DEL_COLOR
                voice1 = score1.recurse().getElementById(op[1].voice)
                textExp = m21.expressions.TextExpression("deleted voice")
                textExp.style.color = DEL_COLOR
                voice1.insert(0, textExp)

                voice1.style.color = DEL_COLOR  # this apparently does nothing
                for el in voice1.recurse().notesAndRests:
                    el.style.color = DEL_COLOR

            # note
            elif op[0] == "noteins":
                assert type(op[2]) == nlin.AnnotatedNote
                # color the inserted score2 general note (note, chord, or rest) using INS_COLOR
                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = INS_COLOR
                if "Rest" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted rest")
                elif "Chord" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted chord")
                else:
                    textExp = m21.expressions.TextExpression("inserted note")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "notedel":
                assert type(op[1]) == nlin.AnnotatedNote
                # color the deleted score1 general note (note, chord, or rest) using DEL_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = DEL_COLOR
                if "Rest" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted rest")
                elif "Chord" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted chord")
                else:
                    textExp = m21.expressions.TextExpression("deleted note")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

            # pitch
            elif op[0] == "pitchnameedit":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the changed note (in both scores) using SUB_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = SUB_COLOR
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
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = SUB_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "inspitch":
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the inserted note in score2 using INS_COLOR
                chord2 = score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = INS_COLOR
                if "Rest" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted rest")
                else:
                    textExp = m21.expressions.TextExpression("inserted note")
                textExp.style.color = INS_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "delpitch":
                assert type(op[1]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the deleted note in score1 using DEL_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = DEL_COLOR
                if "Rest" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted rest")
                else:
                    textExp = m21.expressions.TextExpression("deleted note")
                textExp.style.color = DEL_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

            elif op[0] == "headedit":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the changed note/rest/chord (in both scores) using SUB_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # beam
            elif op[0] == "insbeam":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the modified note in both scores using INS_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = INS_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note1.beams:
                        beam.style.color = INS_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = INS_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = INS_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note2.beams:
                        beam.style.color = INS_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = INS_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delbeam":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the modified note in both scores using DEL_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = DEL_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note1.beams:
                        beam.style.color = DEL_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = DEL_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note2.beams:
                        beam.style.color = DEL_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = DEL_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editbeam":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the changed beam (in both scores) using SUB_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note1.beams:
                        beam.style.color = SUB_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note2.beams:
                        beam.style.color = SUB_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # accident
            elif op[0] == "accidentins":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using INS_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = INS_COLOR
                note1.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = INS_COLOR
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
                    note2.pitch.accidental.style.color = INS_COLOR
                note2.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = INS_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "accidentdel":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using DEL_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = DEL_COLOR
                note1.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = DEL_COLOR
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
                    note2.pitch.accidental.style.color = DEL_COLOR
                note2.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = DEL_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "accidentedit":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the changed accidental (in both scores) using SUB_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = SUB_COLOR
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = SUB_COLOR
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
                    note2.pitch.accidental.style.color = SUB_COLOR
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = SUB_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "dotins":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores, using SUB_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "dotdel":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores, using SUB_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # tuplets
            elif op[0] == "instuplet":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "deltuplet":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "edittuplet":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # ties
            elif op[0] == "tieins":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # Color the modified note here in both scores, using INS_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = INS_COLOR
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
                note2.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = INS_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "tiedel":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # Color the modified note in both scores, using DEL_COLOR
                chord1 = score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = DEL_COLOR
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
                note2.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = DEL_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            # expressions
            elif op[0] == "insexpression":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the note in both scores using INS_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = INS_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = INS_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delexpression":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the deleted expression in score1 using DEL_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = DEL_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = DEL_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editexpression":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the changed beam (in both scores) using SUB_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # articulations
            elif op[0] == "insarticulation":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the modified note in both scores using INS_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = INS_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = INS_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = INS_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delarticulation":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the modified note in both scores using DEL_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = DEL_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = DEL_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = DEL_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editarticulation":
                assert type(op[1]) == nlin.AnnotatedNote
                assert type(op[2]) == nlin.AnnotatedNote
                # color the modified note (in both scores) using SUB_COLOR
                note1 = score1.recurse().getElementById(op[1].general_note)
                note1.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = SUB_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = score2.recurse().getElementById(op[2].general_note)
                note2.style.color = SUB_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = SUB_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            else:
                print(
                    "Annotation type {} not yet supported for visualization".format(op[0])
                )


    def show_differences(score1: m21.stream.Score, score2: m21.stream.Score):
        # display the two (annotated) scores
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

        score1.show('musicxml.pdf', makeNotation=False)
        score2.show('musicxml.pdf', makeNotation=False)
