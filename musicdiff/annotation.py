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
from typing import Optional, List

import music21 as m21

from musicdiff import M21Utils
from musicdiff import DetailLevel

class AnnNote:
    def __init__(self, general_note: m21.note.GeneralNote, enhanced_beam_list, tuplet_list, detail: DetailLevel = DetailLevel.Default):
        """
        Extend music21 GeneralNote with some precomputed, easily compared information about it.

        Args:
            general_note (music21.note.GeneralNote): The music21 note/chord/rest to extend.
            enhanced_beam_list (list): A list of beaming information about this GeneralNote.
            tuplet_list (list): A list of tuplet info about this GeneralNote.
            detail (DetailLevel): What level of detail to use during the diff.  Can be
                GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
                currently equivalent to AllObjects).

        """
        self.general_note = general_note.id
        self.beamings = enhanced_beam_list
        self.tuplets = tuplet_list

        self.stylestr: str = ''
        self.styledict: dict = {}
        if M21Utils.has_style(general_note):
            self.styledict = M21Utils.obj_to_styledict(general_note, detail)
        self.noteshape: str = 'normal'
        self.noteheadFill: Optional[bool] = None
        self.noteheadParenthesis: bool = False
        self.stemDirection: str = 'unspecified'
        if detail >= DetailLevel.AllObjectsWithStyle and isinstance(general_note, m21.note.NotRest):
            self.noteshape = general_note.notehead
            self.noteheadFill = general_note.noteheadFill
            self.noteheadParenthesis = general_note.noteheadParenthesis
            self.stemDirection = general_note.stemDirection

        # compute the representation of NoteNode as in the paper
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
        # graceness
        if isinstance(general_note.duration, m21.duration.AppoggiaturaDuration):
            self.graceType = 'acc'
            self.graceSlash = general_note.duration.slash
        elif isinstance(general_note.duration, m21.duration.GraceDuration):
            self.graceType = 'nonacc'
            self.graceSlash = general_note.duration.slash
        else:
            self.graceType = ''
            self.graceSlash = False
        # articulations
        self.articulations = [a.name for a in general_note.articulations]
        if self.articulations:
            self.articulations.sort()
        # expressions
        self.expressions = [a.name for a in general_note.expressions]
        if self.expressions:
            self.expressions.sort()

        # lyrics
        self.lyrics: List[str] = []
        for lyric in general_note.lyrics:
            lyricStr: str = ""
            if lyric.number is not None:
                lyricStr += f"number={lyric.number}"
            if lyric._identifier is not None:
                lyricStr += f" identifier={lyric._identifier}"
            if lyric.syllabic is not None:
                lyricStr += f" syllabic={lyric.syllabic}"
            if lyric.text is not None:
                lyricStr += f" text={lyric.text}"
            lyricStr += f" rawText={lyric.rawText}"
            if M21Utils.has_style(lyric):
                lyricStr += f" style={M21Utils.obj_to_styledict(lyric, detail)}"
            self.lyrics.append(lyricStr)

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
        # add for the lyrics
        size += len(self.lyrics)
        return size

    def __repr__(self):
        # does consider the MEI id!
        return (f"{self.pitches},{self.note_head},{self.dots},{self.beamings}," +
                f"{self.tuplets},{self.general_note},{self.articulations},{self.expressions}," +
                f"{self.lyrics},{self.styledict}")

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
        if self.graceType:
            string += self.graceType
            if self.graceSlash:
                string += '/'
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
        if len(self.lyrics) > 0:  # add for lyrics
            for lyric in self.lyrics:
                string += lyric

        if self.noteshape != 'normal':
            string += f"noteshape={self.noteshape}"
        if self.noteheadFill is not None:
            string += f"noteheadFill={self.noteheadFill}"
        if self.noteheadParenthesis:
            string += f"noteheadParenthesis={self.noteheadParenthesis}"
        if self.stemDirection != 'unspecified':
            string += f"stemDirection={self.stemDirection}"

        # and then the style fields
        for i, (k, v) in enumerate(self.styledict.items()):
            if i > 0:
                string += ","
            string += f"{k}={v}"

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


class AnnExtra:
    def __init__(self, extra: m21.base.Music21Object, measure: m21.stream.Measure, score: m21.stream.Score, detail: DetailLevel = DetailLevel.Default):
        """
        Extend music21 non-GeneralNote and non-Stream objects with some precomputed, easily compared information about it.
        Examples: TextExpression, Dynamic, Clef, Key, TimeSignature, MetronomeMark, etc.

        Args:
            extra (music21.base.Music21Object): The music21 non-GeneralNote/non-Stream object to extend.
            measure (music21.stream.Measure): The music21 Measure the extra was found in.  If the extra
                was found in a Voice, this is the Measure that the Voice was found in.
            detail (DetailLevel): What level of detail to use during the diff.  Can be
                GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
                currently equivalent to AllObjects).
        """
        self.extra = extra.id
        self.offset: float
        self.duration: float
        self.numNotes: int = 1
        if isinstance(extra, m21.spanner.Spanner):
            self.numNotes = len(extra)
            firstNote: m21.note.GeneralNote = extra.getFirst()
            lastNote: m21.note.GeneralNote = extra.getLast()
            self.offset = float(firstNote.getOffsetInHierarchy(measure))
            # to compute duration we need to use offset-in-score, since the end note might be in another Measure
            startOffsetInScore: float = float(firstNote.getOffsetInHierarchy(score))
            endOffsetInScore: float = float(lastNote.getOffsetInHierarchy(score) + lastNote.duration.quarterLength)
            self.duration = endOffsetInScore - startOffsetInScore
        else:
            self.offset = float(extra.getOffsetInHierarchy(measure))
            self.duration = float(extra.duration.quarterLength)
        self.content: str = M21Utils.extra_to_string(extra)
        self.styledict: str = {}
        if M21Utils.has_style(extra):
            self.styledict = M21Utils.obj_to_styledict(extra, detail) # includes extra.placement if present
        self._notation_size: int = 1 # so far, always 1, but maybe some extra will be bigger someday

        # precomputed representations for faster comparison
        self.precomputed_str = self.__str__()

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnExtra`.

        Returns:
            int: The notation size of the annotated extra
        """
        return self._notation_size

    def __repr__(self):
        return str(self)

    def __str__(self):
        """
        Returns:
            str: the compared representation of the AnnExtra. Does not consider music21 id.
        """
        string = f'{self.content},off={self.offset},dur={self.duration}'
        if self.numNotes != 1:
            string += f',numNotes={self.numNotes}'
        # and then any style fields
        for k, v in self.styledict.items():
            string += f",{k}={v}"
        return string

    def __eq__(self, other):
        # equality does not consider the MEI id!
        return self.precomputed_str == other.precomputed_str


class AnnVoice:
    def __init__(self, voice: m21.stream.Voice, detail: DetailLevel = DetailLevel.Default):
        """
        Extend music21 Voice with some precomputed, easily compared information about it.

        Args:
            voice (music21.stream.Voice): The music21 voice to extend.
            detail (DetailLevel): What level of detail to use during the diff.  Can be
                GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
                currently equivalent to AllObjects).
        """
        self.voice = voice.id
        note_list = M21Utils.get_notes_and_gracenotes(voice)
        if not note_list:
            self.en_beam_list = []
            self.tuplet_list = []
            self.tuple_info = []
            self.annot_notes = []
        else:
            self.en_beam_list = M21Utils.get_enhance_beamings(
                note_list
            )  # beams and type (type for note shorter than quarter notes)
            self.tuplet_list = M21Utils.get_tuplets_type(
                note_list
            )  # corrected tuplets (with "start" and "continue")
            self.tuple_info = M21Utils.get_tuplets_info(note_list)
            # create a list of notes with beaming and tuplets information attached
            self.annot_notes = []
            for i, n in enumerate(note_list):
                self.annot_notes.append(
                    AnnNote(n, self.en_beam_list[i], self.tuplet_list[i], detail)
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
    def __init__(self, measure: m21.stream.Measure,
                       score: m21.stream.Score,
                       spannerBundle: m21.spanner.SpannerBundle,
                       detail: DetailLevel = DetailLevel.Default):
        """
        Extend music21 Measure with some precomputed, easily compared information about it.

        Args:
            measure (music21.stream.Measure): The music21 measure to extend.
            score (music21.stream.Score): the enclosing music21 Score.
            spannerBundle (music21.spanner.SpannerBundle): a bundle of all the spanners in the score.
            detail (DetailLevel): What level of detail to use during the diff.  Can be
                GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
                currently equivalent to AllObjects).
        """
        self.measure = measure.id
        self.voices_list = []
        if (
            len(measure.voices) == 0
        ):  # there is a single AnnVoice ( == for the library there are no voices)
            ann_voice = AnnVoice(measure, detail)
            if ann_voice.n_of_notes > 0:
                self.voices_list.append(ann_voice)
        else:  # there are multiple voices (or an array with just one voice)
            for voice in measure.voices:
                ann_voice = AnnVoice(voice, detail)
                if ann_voice.n_of_notes > 0:
                    self.voices_list.append(ann_voice)
        self.n_of_voices = len(self.voices_list)

        self.extras_list = []
        if detail >= DetailLevel.AllObjects:
            for extra in M21Utils.get_extras(measure, spannerBundle):
                self.extras_list.append(AnnExtra(extra, measure, score, detail))

            # For correct comparison, sort the extras_list, so that any list slices
            # that all have the same offset are sorted alphabetically.
            self.extras_list.sort(key=lambda e: ( e.offset, str(e) ))

        # precomputed values to speed up the computation. As they start to be long, they are hashed
        self.precomputed_str = hash(self.__str__())
        self.precomputed_repr = hash(self.__repr__())

    def __str__(self):
        return str([str(v) for v in self.voices_list]) + ' Extras:' + str([str(e) for e in self.extras_list])

    def __repr__(self):
        return self.voices_list.__repr__() + ' Extras:' + self.extras_list.__repr__()

    def __eq__(self, other):
        # equality does not consider MEI id!
        if not isinstance(other, AnnMeasure):
            return False

        if len(self.voices_list) != len(other.voices_list):
            return False

        if len(self.extras_list) != len(other.extras_list):
            return False

        return self.precomputed_str == other.precomputed_str
        # return all([v[0] == v[1] for v in zip(self.voices_list, other.voices_list)])

    def notation_size(self):
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnMeasure`.

        Returns:
            int: The notation size of the annotated measure
        """
        return sum([v.notation_size() for v in self.voices_list]) + sum([e.notation_size() for e in self.extras_list])

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
    def __init__(self, part: m21.stream.Part,
                       score: m21.stream.Score,
                       spannerBundle: m21.spanner.SpannerBundle,
                       detail: DetailLevel = DetailLevel.Default):
        """
        Extend music21 Part/PartStaff with some precomputed, easily compared information about it.

        Args:
            part (music21.stream.Part, music21.stream.PartStaff): The music21 Part/PartStaff to extend.
            score (music21.stream.Score): the enclosing music21 Score.
            spannerBundle (music21.spanner.SpannerBundle): a bundle of all the spanners in the score.
            detail (DetailLevel): What level of detail to use during the diff.  Can be
                GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
                currently equivalent to AllObjects).
        """
        self.part = part.id
        self.bar_list = []
        for measure in part.getElementsByClass("Measure"):
            ann_bar = AnnMeasure(measure, score, spannerBundle, detail)  # create the bar objects
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
    def __init__(self, score: m21.stream.Score, detail: DetailLevel = DetailLevel.Default):
        """
        Take a music21 score and store it as a sequence of Full Trees.
        The hierarchy is "score -> parts -> measures -> voices -> notes"
        Args:
            score (music21.stream.Score): The music21 score
            detail (DetailLevel): What level of detail to use during the diff.  Can be
                GeneralNotesOnly, AllObjects, AllObjectsWithStyle or Default (Default is
                currently equivalent to AllObjects).
        """
        self.score = score.id
        self.part_list = []
        spannerBundle: m21.spanner.SpannerBundle = score.spannerBundle
        for part in score.parts.stream():
            # create and add the AnnPart object to part_list
            ann_part = AnnPart(part, score, spannerBundle, detail)
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
