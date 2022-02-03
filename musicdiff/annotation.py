# ------------------------------------------------------------------------------
# Purpose:       notation is a set of annotated music21 notation wrappers for use
#                by musicdiff.
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

__docformat__ = "google"

from fractions import Fraction

import music21 as m21

from musicdiff import M21Utils


class AnnNote:
    def __init__(self, general_note, enhanced_beam_list, tuplet_list):
        """
        Extend music21 GeneralNote with some precomputed, easily compared information about it.

        Args:
            general_note (music21.note.GeneralNote): The music21 note/chord/rest to extend.
            enhanced_beam_list (list): A list of beaming information about this GeneralNote.
            tuplet_list (list): A list of tuplet info about this GeneralNote.
        """
        self.general_note = general_note.id
        self.beamings = enhanced_beam_list
        self.tuplets = tuplet_list
        ##compute the representaiton of NoteNode as in the paper
        # pitches is a list  of elements, each one is (pitchposition, accidental, tie)
        if general_note.isRest:
            self.pitches = [
                ("R", "None", False)
            ]  # accidental and tie are automaticaly set for rests
        elif general_note.isChord or "ChordBase" in general_note.classSet:
            # ChordBase/PercussionChord is new in v7, so I am being careful to use
            # it only as a string so v6 will still work.
            noteList: [m21.note.GeneralNote] = general_note.notes
            if hasattr(general_note, "sortDiatonicAscending"): # PercussionChords don't have this
                noteList = general_note.sortDiatonicAscending().notes
            self.pitches = [
                M21Utils.note2tuple(p) for p in noteList
            ]
        elif general_note.isNote or isinstance(general_note, m21.note.Unpitched):
            self.pitches = [M21Utils.note2tuple(general_note)]
        else:
            raise TypeError("The generalNote must be a Chord, a Rest or a Note")
        # note head
        type_number = Fraction(
            M21Utils.get_type_num(general_note.duration)
        )
        if type_number >= 4:
            self.note_head = 4
        else:
            self.note_head = type_number
        # dots
        self.dots = general_note.duration.dots
        # articulations
        self.articulations = [a.name for a in general_note.articulations]
        if self.articulations:
            self.articulations.sort()
        # expressions
        self.expressions = [a.name for a in general_note.expressions]
        if self.expressions:
            self.expressions.sort()

        # precomputed representations for faster comparison
        self.precomputed_str = self.__str__()

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnNote`.

        Returns:
            int: The notation size of the annotated note
        """
        size = 0
        # add for the pitches
        for pitch in self.pitches:
            size += M21Utils.pitch_size(pitch)
        # add for the dots
        size += self.dots * len(self.pitches)  # one dot for each note if it's a chord
        # add for the beamings
        size += len(self.beamings)
        # add for the tuplets
        size += len(self.tuplets)
        # add for the articulations
        size += len(self.articulations)
        # add for the expressions
        size += len(self.expressions)
        return size

    def __repr__(self):
        # does consider the MEI id!
        return (f"{self.pitches},{self.note_head},{self.dots},{self.beamings}," +
                f"{self.tuplets},{self.general_note},{self.articulations},{self.expressions}")

    def __str__(self):
        """
        Returns:
            str: the representation of the Annotated note. Does not consider MEI id
        """
        string = "["
        for p in self.pitches:  # add for pitches
            string += p[0]
            if p[1] != "None":
                string += p[1]
            if p[2]:
                string += "T"
            string += ","
        string = string[:-1]  # delete the last comma
        string += "]"
        string += str(self.note_head)  # add for notehead
        for _ in range(self.dots):  # add for dots
            string += "*"
        if len(self.beamings) > 0:  # add for beaming
            string += "B"
            for b in self.beamings:
                if b == "start":
                    string += "sr"
                elif b == "continue":
                    string += "co"
                elif b == "stop":
                    string += "sp"
                elif b == "partial":
                    string += "pa"
                else:
                    raise Exception(f"Incorrect beaming type: {b}")
        if len(self.tuplets) > 0:  # add for tuplets
            string += "T"
            for t in self.tuplets:
                if t == "start":
                    string += "sr"
                elif t == "continue":
                    string += "co"
                elif t == "stop":
                    string += "sp"
                else:
                    raise Exception(f"Incorrect tuplets type: {t}")
        if len(self.articulations) > 0:  # add for articulations
            for a in self.articulations:
                string += a
        if len(self.expressions) > 0:  # add for articulations
            for e in self.expressions:
                string += e
        return string

    def get_note_ids(self):
        """
        Computes a list of the GeneralNote ids for this `AnnNote`.  Since there
        is only one GeneralNote here, this will always be a single-element list.

        Returns:
            [int]: A list containing the single GeneralNote id for this note.
        """
        return [self.general_note]

    def __eq__(self, other):
        # equality does not consider the MEI id!
        return self.precomputed_str == other.precomputed_str

        # if not isinstance(other, AnnNote):
        #     return False
        # elif self.pitches != other.pitches:
        #     return False
        # elif self.note_head != other.note_head:
        #     return False
        # elif self.dots != other.dots:
        #     return False
        # elif self.beamings != other.beamings:
        #     return False
        # elif self.tuplets != other.tuplets:
        #     return False
        # elif self.articulations != other.articulations:
        #     return False
        # elif self.expressions != other.expressions:
        #     return False
        # else:
        #     return True


class AnnVoice:
    def __init__(self, voice):
        """
        Extend music21 Voice with some precomputed, easily compared information about it.

        Args:
            voice (music21.stream.Voice): The music21 voice to extend.
        """
        self.voice = voice.id
        self.note_list = M21Utils.get_notes(voice)
        if not self.note_list:
            self.en_beam_list = []
            self.tuplet_list = []
            self.tuple_info = []
            self.annot_notes = []
        else:
            self.en_beam_list = M21Utils.get_enhance_beamings(
                self.note_list
            )  # beams and type (type for note shorter than quarter notes)
            self.tuplet_list = M21Utils.get_tuplets_type(
                self.note_list
            )  # corrected tuplets (with "start" and "continue")
            self.tuple_info = M21Utils.get_tuplets_info(self.note_list)
            # create a list of notes with beaming and tuplets information attached
            self.annot_notes = []
            for i, n in enumerate(self.note_list):
                self.annot_notes.append(
                    AnnNote(n, self.en_beam_list[i], self.tuplet_list[i])
                )

        self.n_of_notes = len(self.annot_notes)
        self.precomputed_str = self.__str__()

    def __eq__(self, other):
        # equality does not consider MEI id!
        if not isinstance(other, AnnVoice):
            return False

        if len(self.annot_notes) != len(other.annot_notes):
            return False

        return self.precomputed_str == other.precomputed_str
        # return all(
        #     [an[0] == an[1] for an in zip(self.annot_notes, other.annot_notes)]
        # )

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnVoice`.

        Returns:
            int: The notation size of the annotated voice
        """
        return sum([an.notation_size() for an in self.annot_notes])

    def __repr__(self):
        return self.annot_notes.__repr__()

    def __str__(self):
        string = "["
        for an in self.annot_notes:
            string += str(an)
            string += ","

        if string[-1] == ",":
            string = string[:-1] # delete the last comma

        string += "]"
        return string

    def get_note_ids(self):
        """
        Computes a list of the GeneralNote ids for this `AnnVoice`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this voice
        """
        return [an.general_note for an in self.annot_notes]


class AnnMeasure:
    def __init__(self, measure):
        """
        Extend music21 Measure with some precomputed, easily compared information about it.

        Args:
            measure (music21.stream.Measure): The music21 measure to extend.
        """
        self.measure = measure.id
        self.voices_list = []
        if (
            len(measure.voices) == 0
        ):  # there is a single AnnVoice ( == for the library there are no voices)
            ann_voice = AnnVoice(measure)
            if ann_voice.n_of_notes > 0:
                self.voices_list.append(ann_voice)
        else:  # there are multiple voices (or an array with just one voice)
            for voice in measure.voices:
                ann_voice = AnnVoice(voice)
                if ann_voice.n_of_notes > 0:
                    self.voices_list.append(AnnVoice(voice))
        self.n_of_voices = len(self.voices_list)

        # precomputed values to speed up the computation. As they start to be long, they are hashed
        self.precomputed_str = hash(self.__str__())
        self.precomputed_repr = hash(self.__repr__())

    def __str__(self):
        return str([str(v) for v in self.voices_list])

    def __eq__(self, other):
        # equality does not consider MEI id!
        if not isinstance(other, AnnMeasure):
            return False

        if len(self.voices_list) != len(other.voices_list):
            return False

        return self.precomputed_str == other.precomputed_str
        # return all([v[0] == v[1] for v in zip(self.voices_list, other.voices_list)])

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnMeasure`.

        Returns:
            int: The notation size of the annotated measure
        """
        return sum([v.notation_size() for v in self.voices_list])

    def __repr__(self):
        return self.voices_list.__repr__()

    def get_note_ids(self):
        """
        Computes a list of the GeneralNote ids for this `AnnMeasure`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this measure
        """
        notes_id = []
        for v in self.voices_list:
            notes_id.extend(v.get_note_ids())
        return notes_id


class AnnPart:
    def __init__(self, part):
        """
        Extend music21 Part/PartStaff with some precomputed, easily compared information about it.

        Args:
            part (music21.stream.Part, music21.stream.PartStaff): The music21 Part/PartStaff to extend.
        """
        self.part = part.id
        self.bar_list = []
        for measure in part.getElementsByClass("Measure"):
            ann_bar = AnnMeasure(measure)  # create the bar objects
            if ann_bar.n_of_voices > 0:
                self.bar_list.append(ann_bar)
        self.n_of_bars = len(self.bar_list)
        # precomputed str to speed up the computation. String itself start to be long, so it is hashed
        self.precomputed_str = hash(self.__str__())

    def __str__(self):
        return str([str(b) for b in self.bar_list])

    def __eq__(self, other):
        # equality does not consider MEI id!
        if not isinstance(other, AnnPart):
            return False

        if len(self.bar_list) != len(other.bar_list):
            return False

        return all(b[0] == b[1] for b in zip(self.bar_list, other.bar_list))

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnPart`.

        Returns:
            int: The notation size of the annotated part
        """
        return sum([b.notation_size() for b in self.bar_list])

    def __repr__(self):
        return self.bar_list.__repr__()

    def get_note_ids(self):
        """
        Computes a list of the GeneralNote ids for this `AnnPart`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this part
        """
        notes_id = []
        for b in self.bar_list:
            notes_id.extend(b.get_note_ids())
        return notes_id


class AnnScore:
    def __init__(self, score):
        """
        Take a music21 score and store it as a sequence of Full Trees.
        The hierarchy is "score -> parts -> measures -> voices -> notes"
        Args:
            score (music21.stream.Score): The music21 score
        """
        self.score = score.id
        self.part_list = []
        for part in score.parts.stream():
            # create and add the AnnPart object to part_list
            ann_part = AnnPart(part)
            if ann_part.n_of_bars > 0:
                self.part_list.append(ann_part)
        self.n_of_parts = len(self.part_list)

    def __eq__(self, other):
        # equality does not consider MEI id!
        if not isinstance(other, AnnScore):
            return False

        if len(self.part_list) != len(other.part_list):
            return False

        return all(p[0] == p[1] for p in zip(self.part_list, other.part_list))

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnScore`.

        Returns:
            int: The notation size of the annotated score
        """
        return sum([p.notation_size() for p in self.part_list])

    def __repr__(self):
        return self.part_list.__repr__()

    def get_note_ids(self):
        """
        Computes a list of the GeneralNote ids for this `AnnScore`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this score
        """
        notes_id = []
        for p in self.part_list:
            notes_id.extend(p.get_note_ids())
        return notes_id

    # return the sequences of measures for a specified part
    def _measures_from_part(self, part_number):
        # only used by tests/test_scl.py
        if part_number not in range(0, len(self.part_list)):
            raise Exception(
                f"parameter 'part_number' should be between 0 and {len(self.part_list) - 1}"
            )
        return self.part_list[part_number].bar_list
