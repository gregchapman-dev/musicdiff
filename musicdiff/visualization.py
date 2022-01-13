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

from musicdiff import notation

class Visualization:
    def __init__(self, score1: m21.stream.Score, score2: m21.stream.Score, operations: List[Tuple]):
        # These can be set by the client to different colors
        self.INSERTED_COLOR = "red"
        self.DELETED_COLOR = "red"
        self.CHANGED_COLOR = "red"

        # these are not notation.Score, they are music21 Scores to annotate with the diffs
        self.score1 = score1
        self.score2 = score2
        self.operations = operations

    def annotate_differences(self):
        for op in self.operations:
            # bar
            if op[0] == "insbar":
                assert type(op[2]) == notation.Bar
                # color all the notes in the inserted score2 measure using self.INSERTED_COLOR
                measure2 = self.score2.recurse().getElementById(op[2].measure)
                textExp = m21.expressions.TextExpression("inserted measure")
                textExp.style.color = self.INSERTED_COLOR
                measure2.insert(0, textExp)
                measure2.style.color = self.INSERTED_COLOR  # this apparently does nothing
                for el in measure2.recurse().notesAndRests:
                    el.style.color = self.INSERTED_COLOR

            elif op[0] == "delbar":
                assert type(op[1]) == notation.Bar
                # color all the notes in the deleted score1 measure using self.DELETED_COLOR
                measure1 = self.score1.recurse().getElementById(op[1].measure)
                textExp = m21.expressions.TextExpression("deleted measure")
                textExp.style.color = self.DELETED_COLOR
                measure1.insert(0, textExp)
                measure1.style.color = self.DELETED_COLOR  # this apparently does nothing
                for el in measure1.recurse().notesAndRests:
                    el.style.color = self.DELETED_COLOR

            # voices
            elif op[0] == "voiceins":
                assert type(op[2]) == notation.Voice
                # color all the notes in the inserted score2 voice using self.INSERTED_COLOR
                voice2 = self.score2.recurse().getElementById(op[2].voice)
                textExp = m21.expressions.TextExpression("inserted voice")
                textExp.style.color = self.INSERTED_COLOR
                voice2.insert(0, textExp)

                voice2.style.color = self.INSERTED_COLOR  # this apparently does nothing
                for el in voice2.recurse().notesAndRests:
                    el.style.color = self.INSERTED_COLOR

            elif op[0] == "voicedel":
                assert type(op[1]) == notation.Voice
                # color all the notes in the deleted score1 voice using self.DELETED_COLOR
                voice1 = self.score1.recurse().getElementById(op[1].voice)
                textExp = m21.expressions.TextExpression("deleted voice")
                textExp.style.color = self.DELETED_COLOR
                voice1.insert(0, textExp)

                voice1.style.color = self.DELETED_COLOR  # this apparently does nothing
                for el in voice1.recurse().notesAndRests:
                    el.style.color = self.DELETED_COLOR

            # note
            elif op[0] == "noteins":
                assert type(op[2]) == notation.AnnotatedNote
                # color the inserted score2 general note (note, chord, or rest) using self.INSERTED_COLOR
                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.INSERTED_COLOR
                if "Rest" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted rest")
                elif "Chord" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted chord")
                else:
                    textExp = m21.expressions.TextExpression("inserted note")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "notedel":
                assert type(op[1]) == notation.AnnotatedNote
                # color the deleted score1 general note (note, chord, or rest) using self.DELETED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.DELETED_COLOR
                if "Rest" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted rest")
                elif "Chord" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted chord")
                else:
                    textExp = m21.expressions.TextExpression("deleted note")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

            # pitch
            elif op[0] == "pitchnameedit":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the changed note (in both scores) using self.CHANGED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = self.CHANGED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed pitch")
                textExp.style.color = self.CHANGED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "inspitch":
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the inserted note in score2 using self.INSERTED_COLOR
                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = self.INSERTED_COLOR
                if "Rest" in note2.classes:
                    textExp = m21.expressions.TextExpression("inserted rest")
                else:
                    textExp = m21.expressions.TextExpression("inserted note")
                textExp.style.color = self.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "delpitch":
                assert type(op[1]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the deleted note in score1 using self.DELETED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = self.DELETED_COLOR
                if "Rest" in note1.classes:
                    textExp = m21.expressions.TextExpression("deleted rest")
                else:
                    textExp = m21.expressions.TextExpression("deleted note")
                textExp.style.color = self.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

            elif op[0] == "headedit":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the changed note/rest/chord (in both scores) using self.CHANGED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed note head")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # beam
            elif op[0] == "insbeam":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the modified note in both scores using self.INSERTED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.INSERTED_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note1.beams:
                        beam.style.color = self.INSERTED_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = self.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.INSERTED_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note2.beams:
                        beam.style.color = self.INSERTED_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("increased flags")
                textExp.style.color = self.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delbeam":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the modified note in both scores using self.DELETED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.DELETED_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note1.beams:
                        beam.style.color = self.DELETED_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.DELETED_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note2.beams:
                        beam.style.color = self.DELETED_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("decreased flags")
                textExp.style.color = self.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editbeam":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the changed beam (in both scores) using self.CHANGED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note1.beams:
                        beam.style.color = self.CHANGED_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                if hasattr(note1, 'beams'):
                    for beam in note2.beams:
                        beam.style.color = self.CHANGED_COLOR  # this apparently does nothing
                textExp = m21.expressions.TextExpression("changed flags")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # accident
            elif op[0] == "accidentins":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using self.INSERTED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = self.INSERTED_COLOR
                note1.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = self.INSERTED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                if note2.pitch.accidental:
                    note2.pitch.accidental.style.color = self.INSERTED_COLOR
                note2.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted accidental")
                textExp.style.color = self.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "accidentdel":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the modified note in both scores using self.DELETED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = self.DELETED_COLOR
                note1.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = self.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color only the indexed note's accidental in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                if note2.pitch.accidental:
                    note2.pitch.accidental.style.color = self.DELETED_COLOR
                note2.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted accidental")
                textExp.style.color = self.DELETED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "accidentedit":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # color the changed accidental (in both scores) using self.CHANGED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                if note1.pitch.accidental:
                    note1.pitch.accidental.style.color = self.CHANGED_COLOR
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = self.CHANGED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                if note2.pitch.accidental:
                    note2.pitch.accidental.style.color = self.CHANGED_COLOR
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed accidental")
                textExp.style.color = self.CHANGED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "dotins":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores, using self.CHANGED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted dot")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "dotdel":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # In music21, the dots are not separately colorable from the note,
                # so we will just color the modified note here in both scores, using self.CHANGED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted dot")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # tuplets
            elif op[0] == "instuplet":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("inserted tuplet")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "deltuplet":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("deleted tuplet")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "edittuplet":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed tuplet")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # ties
            elif op[0] == "tieins":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # Color the modified note here in both scores, using self.INSERTED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = self.INSERTED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted tie")
                textExp.style.color = self.INSERTED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            elif op[0] == "tiedel":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                assert len(op) == 5  # the indices must be there
                # Color the modified note in both scores, using self.DELETED_COLOR
                chord1 = self.score1.recurse().getElementById(op[1].general_note)
                note1 = chord1
                if "Chord" in note1.classes:
                    # color just the indexed note in the chord
                    idx = op[4][0]
                    note1 = note1.notes[idx]
                note1.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = self.DELETED_COLOR
                if note1.activeSite is not None:
                    note1.activeSite.insert(note1.offset, textExp)
                else:
                    chord1.activeSite.insert(chord1.offset, textExp)

                chord2 = self.score2.recurse().getElementById(op[2].general_note)
                note2 = chord2
                if "Chord" in note2.classes:
                    # color just the indexed note in the chord
                    idx = op[4][1]
                    note2 = note2.notes[idx]
                note2.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted tie")
                textExp.style.color = self.DELETED_COLOR
                if note2.activeSite is not None:
                    note2.activeSite.insert(note2.offset, textExp)
                else:
                    chord2.activeSite.insert(chord2.offset, textExp)

            # expressions
            elif op[0] == "insexpression":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the note in both scores using self.INSERTED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = self.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted expression")
                textExp.style.color = self.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delexpression":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the deleted expression in self.score1 using self.DELETED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = self.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted expression")
                textExp.style.color = self.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editexpression":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the changed beam (in both scores) using self.CHANGED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed expression")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            # articulations
            elif op[0] == "insarticulation":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the modified note in both scores using self.INSERTED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = self.INSERTED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.INSERTED_COLOR
                textExp = m21.expressions.TextExpression("inserted articulation")
                textExp.style.color = self.INSERTED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "delarticulation":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the modified note in both scores using self.DELETED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = self.DELETED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.DELETED_COLOR
                textExp = m21.expressions.TextExpression("deleted articulation")
                textExp.style.color = self.DELETED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            elif op[0] == "editarticulation":
                assert type(op[1]) == notation.AnnotatedNote
                assert type(op[2]) == notation.AnnotatedNote
                # color the modified note (in both scores) using self.CHANGED_COLOR
                note1 = self.score1.recurse().getElementById(op[1].general_note)
                note1.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = self.CHANGED_COLOR
                note1.activeSite.insert(note1.offset, textExp)

                note2 = self.score2.recurse().getElementById(op[2].general_note)
                note2.style.color = self.CHANGED_COLOR
                textExp = m21.expressions.TextExpression("changed articulation")
                textExp.style.color = self.CHANGED_COLOR
                note2.activeSite.insert(note2.offset, textExp)

            else:
                print(f"Annotation type {op[0]} not yet supported for visualization")


    def show_differences(self):
        # display the two (presumably annotated) scores
        originalComposer1: str = None
        originalComposer2: str = None

        if self.score1.metadata is None:
            self.score1.metadata = m21.metadata.Metadata()
        if self.score2.metadata is None:
            self.score2.metadata = m21.metadata.Metadata()

        originalComposer1 = self.score1.metadata.composer
        if originalComposer1 is None:
            self.score1.metadata.composer = "score1"
        else:
            self.score1.metadata.composer = "score1          " + originalComposer1

        originalComposer2 = self.score2.metadata.composer
        if originalComposer2 is None:
            self.score2.metadata.composer = "score2"
        else:
            self.score2.metadata.composer = "score2          " + originalComposer2

        self.score1.show('musicxml.pdf', makeNotation=False)
        self.score2.show('musicxml.pdf', makeNotation=False)
