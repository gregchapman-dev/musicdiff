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
# Copyright:     (c) 2022, 2023 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------

__docformat__ = "google"

from fractions import Fraction

import typing as t

import music21 as m21

from musicdiff import M21Utils
from musicdiff import DetailLevel

class AnnNote:
    def __init__(
        self,
        general_note: m21.note.GeneralNote,
        enhanced_beam_list: list[str],
        tuplet_list: list[str],
        tuplet_info: list[str],
        detail: DetailLevel = DetailLevel.Default
    ) -> None:
        """
        Extend music21 GeneralNote with some precomputed, easily compared information about it.

        Args:
            general_note (music21.note.GeneralNote): The music21 note/chord/rest to extend.
            enhanced_beam_list (list): A list of beaming information about this GeneralNote.
            tuplet_list (list): A list of tuplet info about this GeneralNote.
            detail (DetailLevel): What level of detail to use during the diff.
                Can be GeneralNotesOnly, AllObjects, AllObjectsWithStyle, MetadataOnly,
                GeneralNotesAndMetadata, AllObjectsAndMetadata, AllObjectsWithStyleAndMetadata,
                or Default (Default is currently equivalent to AllObjects).

        """
        self.general_note: int | str = general_note.id
        self.beamings: list[str] = enhanced_beam_list
        self.tuplets: list[str] = tuplet_list
        self.tuplet_info: list[str] = tuplet_info

        self.stylestr: str = ''
        self.styledict: dict = {}
        if M21Utils.has_style(general_note):
            self.styledict = M21Utils.obj_to_styledict(general_note, detail)
        self.noteshape: str = 'normal'
        self.noteheadFill: bool | None = None
        self.noteheadParenthesis: bool = False
        self.stemDirection: str = 'unspecified'
        if DetailLevel.includesStyle(detail) and isinstance(general_note, m21.note.NotRest):
            self.noteshape = general_note.notehead
            self.noteheadFill = general_note.noteheadFill
            self.noteheadParenthesis = general_note.noteheadParenthesis
            self.stemDirection = general_note.stemDirection

        # compute the representation of NoteNode as in the paper
        # pitches is a list  of elements, each one is (pitchposition, accidental, tied)
        self.pitches: list[tuple[str, str, bool]]
        if isinstance(general_note, m21.chord.ChordBase):
            notes: tuple[m21.note.NotRest, ...] = general_note.notes
            if hasattr(general_note, "sortDiatonicAscending"):
                # PercussionChords don't have this
                notes = general_note.sortDiatonicAscending().notes
            self.pitches = []
            for p in notes:
                if not isinstance(p, (m21.note.Note, m21.note.Unpitched)):
                    raise TypeError("The chord must contain only Note or Unpitched")
                self.pitches.append(M21Utils.note2tuple(p, detail))

        elif isinstance(general_note, (m21.note.Note, m21.note.Unpitched, m21.note.Rest)):
            self.pitches = [M21Utils.note2tuple(general_note, detail)]
        else:
            raise TypeError("The generalNote must be a Chord, a Rest, a Note, or an Unpitched")

        # note head
        type_number = Fraction(
            M21Utils.get_type_num(general_note.duration)
        )
        self.note_head: int | Fraction
        if type_number >= 4:
            self.note_head = 4
        else:
            self.note_head = type_number
        # dots
        self.dots: int = general_note.duration.dots
        # graceness
        if isinstance(general_note.duration, m21.duration.AppoggiaturaDuration):
            self.graceType: str = 'acc'
            self.graceSlash: bool | None = general_note.duration.slash
        elif isinstance(general_note.duration, m21.duration.GraceDuration):
            self.graceType = 'nonacc'
            self.graceSlash = general_note.duration.slash
        else:
            self.graceType = ''
            self.graceSlash = False
        # articulations
        self.articulations: list[str] = [
            M21Utils.articulation_to_string(a, detail) for a in general_note.articulations
        ]
        if self.articulations:
            self.articulations.sort()
        # expressions
        self.expressions: list[str] = [
            M21Utils.expression_to_string(a, detail) for a in general_note.expressions
        ]
        if self.expressions:
            self.expressions.sort()

        # lyrics
        self.lyrics: list[str] = []
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
        self.precomputed_str: str = self.__str__()

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnNote`.

        Returns:
            int: The notation size of the annotated note
        """
        size: int = 0
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

    def __repr__(self) -> str:
        # does consider the MEI id!
        return (
            f"{self.pitches},{self.note_head},{self.dots},B:{self.beamings},"
            + f"T:{self.tuplets},TI:{self.tuplet_info},{self.general_note},"
            + f"{self.articulations},{self.expressions},{self.lyrics},{self.styledict}"
        )

    def __str__(self) -> str:
        """
        Returns:
            str: the representation of the Annotated note. Does not consider MEI id
        """
        string: str = "["
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
                    raise ValueError(f"Incorrect beaming type: {b}")

        if len(self.tuplets) > 0:  # add for tuplets
            string += "T"
            for tup, ti in zip(self.tuplets, self.tuplet_info):
                if ti != "":
                    ti = "(" + ti + ")"
                if tup == "start":
                    string += "sr" + ti
                elif tup == "continue":
                    string += "co" + ti
                elif tup == "stop":
                    string += "sp" + ti
                else:
                    raise ValueError(f"Incorrect tuplet type: {tup}")

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

    def get_note_ids(self) -> list[str | int]:
        """
        Computes a list of the GeneralNote ids for this `AnnNote`.  Since there
        is only one GeneralNote here, this will always be a single-element list.

        Returns:
            [int]: A list containing the single GeneralNote id for this note.
        """
        return [self.general_note]

    def __eq__(self, other) -> bool:
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
    def __init__(
        self,
        extra: m21.base.Music21Object,
        measure: m21.stream.Measure,
        score: m21.stream.Score,
        detail: DetailLevel = DetailLevel.Default
    ) -> None:
        """
        Extend music21 non-GeneralNote and non-Stream objects with some precomputed,
        easily compared information about it.

        Examples: TextExpression, Dynamic, Clef, Key, TimeSignature, MetronomeMark, etc.

        Args:
            extra (music21.base.Music21Object): The music21 non-GeneralNote/non-Stream
                object to extend.
            measure (music21.stream.Measure): The music21 Measure the extra was found in.
                If the extra was found in a Voice, this is the Measure that the Voice was
                found in.
            detail (DetailLevel): What level of detail to use during the diff.
                Can be GeneralNotesOnly, AllObjects, AllObjectsWithStyle, MetadataOnly,
                GeneralNotesAndMetadata, AllObjectsAndMetadata, AllObjectsWithStyleAndMetadata,
                or Default (Default is currently equivalent to AllObjects).
        """
        self.extra = extra.id
        self.offset: float
        self.duration: float
        self.numNotes: int = 1

        if isinstance(extra, m21.spanner.Spanner):
            self.numNotes = len(extra)
            firstNote: m21.note.GeneralNote | m21.spanner.SpannerAnchor = (
                M21Utils.getPrimarySpannerElement(extra)
            )
            lastNote: m21.note.GeneralNote | m21.spanner.SpannerAnchor = (
                extra.getLast()
            )
            self.offset = float(firstNote.getOffsetInHierarchy(measure))
            # to compute duration we need to use offset-in-score, since the end note might
            # be in another Measure.  Except for ArpeggioMarkSpanners, where the duration
            # doesn't matter, so we just set it to 0, rather than figuring out the longest
            # duration in all the notes/chords in the arpeggio.
            if isinstance(extra, m21.expressions.ArpeggioMarkSpanner):
                self.duration = 0.
            else:
                startOffsetInScore: float = float(firstNote.getOffsetInHierarchy(score))
                try:
                    endOffsetInScore: float = float(
                        lastNote.getOffsetInHierarchy(score) + lastNote.duration.quarterLength
                    )
                except m21.sites.SitesException:
                    endOffsetInScore = startOffsetInScore
                self.duration = endOffsetInScore - startOffsetInScore
        else:
            self.offset = float(extra.getOffsetInHierarchy(measure))
            self.duration = float(extra.duration.quarterLength)

        self.content: str = M21Utils.extra_to_string(extra, detail)
        self.styledict: dict = {}

        if M21Utils.has_style(extra):
            # includes extra.placement if present
            self.styledict = M21Utils.obj_to_styledict(extra, detail)

        # so far, always 1, but maybe some extra will be bigger someday
        self._notation_size: int = 1

        # precomputed representations for faster comparison
        self.precomputed_str: str = self.__str__()

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnExtra`.

        Returns:
            int: The notation size of the annotated extra
        """
        return self._notation_size

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
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

    def __eq__(self, other) -> bool:
        # equality does not consider the MEI id!
        return self.precomputed_str == other.precomputed_str


class AnnVoice:
    def __init__(
        self,
        voice: m21.stream.Voice | m21.stream.Measure,
        detail: DetailLevel = DetailLevel.Default
    ) -> None:
        """
        Extend music21 Voice with some precomputed, easily compared information about it.

        Args:
            voice (music21.stream.Voice or Measure): The music21 voice to extend. This
                can be a Measure, but only if it contains no Voices.
            detail (DetailLevel): What level of detail to use during the diff.
                Can be GeneralNotesOnly, AllObjects, AllObjectsWithStyle, MetadataOnly,
                GeneralNotesAndMetadata, AllObjectsAndMetadata, AllObjectsWithStyleAndMetadata,
                or Default (Default is currently equivalent to AllObjects).
        """
        self.voice: int | str = voice.id
        note_list: list[m21.note.GeneralNote] = []

        if DetailLevel.includesGeneralNotes(detail):
            note_list = M21Utils.get_notes_and_gracenotes(voice)

        if not note_list:
            self.en_beam_list: list[list[str]] = []
            self.tuplet_list: list[list[str]] = []
            self.tuplet_info: list[list[str]] = []
            self.annot_notes: list[AnnNote] = []
        else:
            self.en_beam_list = M21Utils.get_enhance_beamings(
                note_list
            )  # beams and type (type for note shorter than quarter notes)
            self.tuplet_list = M21Utils.get_tuplets_type(
                note_list
            )  # corrected tuplets (with "start" and "continue")
            self.tuplet_info = M21Utils.get_tuplets_info(note_list)
            # create a list of notes with beaming and tuplets information attached
            self.annot_notes = []
            for i, n in enumerate(note_list):
                self.annot_notes.append(
                    AnnNote(
                        n,
                        self.en_beam_list[i],
                        self.tuplet_list[i],
                        self.tuplet_info[i],
                        detail
                    )
                )

        self.n_of_notes: int = len(self.annot_notes)
        self.precomputed_str: str = self.__str__()

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id!
        if not isinstance(other, AnnVoice):
            return False

        if len(self.annot_notes) != len(other.annot_notes):
            return False

        return self.precomputed_str == other.precomputed_str
        # return all(
        #     [an[0] == an[1] for an in zip(self.annot_notes, other.annot_notes)]
        # )

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnVoice`.

        Returns:
            int: The notation size of the annotated voice
        """
        return sum([an.notation_size() for an in self.annot_notes])

    def __repr__(self) -> str:
        return self.annot_notes.__repr__()

    def __str__(self) -> str:
        string = "["
        for an in self.annot_notes:
            string += str(an)
            string += ","

        if string[-1] == ",":
            # delete the last comma
            string = string[:-1]

        string += "]"
        return string

    def get_note_ids(self) -> list[str | int]:
        """
        Computes a list of the GeneralNote ids for this `AnnVoice`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this voice
        """
        return [an.general_note for an in self.annot_notes]


class AnnMeasure:
    def __init__(
        self,
        measure: m21.stream.Measure,
        part: m21.stream.Part,
        score: m21.stream.Score,
        spannerBundle: m21.spanner.SpannerBundle,
        detail: DetailLevel = DetailLevel.Default
    ) -> None:
        """
        Extend music21 Measure with some precomputed, easily compared information about it.

        Args:
            measure (music21.stream.Measure): The music21 Measure to extend.
            part (music21.stream.Part): the enclosing music21 Part
            score (music21.stream.Score): the enclosing music21 Score.
            spannerBundle (music21.spanner.SpannerBundle): a bundle of all the spanners
                in the score.
            detail (DetailLevel): What level of detail to use during the diff.
                Can be GeneralNotesOnly, AllObjects, AllObjectsWithStyle, MetadataOnly,
                GeneralNotesAndMetadata, AllObjectsAndMetadata, AllObjectsWithStyleAndMetadata,
                or Default (Default is currently equivalent to AllObjects).
        """
        self.measure: int | str = measure.id
        self.voices_list: list[AnnVoice] = []

        if len(measure.voices) == 0:
            # there is a single AnnVoice (i.e. in the music21 Measure there are no voices)
            ann_voice = AnnVoice(measure, detail)
            if ann_voice.n_of_notes > 0:
                self.voices_list.append(ann_voice)
        else:  # there are multiple voices (or an array with just one voice)
            for voice in measure.voices:
                ann_voice = AnnVoice(voice, detail)
                if ann_voice.n_of_notes > 0:
                    self.voices_list.append(ann_voice)
        self.n_of_voices: int = len(self.voices_list)

        self.extras_list: list[AnnExtra] = []
        if DetailLevel.includesOtherMusicObjects(detail):
            for extra in M21Utils.get_extras(measure, part, spannerBundle, detail):
                self.extras_list.append(AnnExtra(extra, measure, score, detail))

            # For correct comparison, sort the extras_list, so that any list slices
            # that all have the same offset are sorted alphabetically.
            self.extras_list.sort(key=lambda e: (e.offset, str(e)))

        # precomputed values to speed up the computation. As they start to be long, they are hashed
        self.precomputed_str: int = hash(self.__str__())
        self.precomputed_repr: int = hash(self.__repr__())

    def __str__(self) -> str:
        return (
            str([str(v) for v in self.voices_list])
            + ' Extras:'
            + str([str(e) for e in self.extras_list])
        )

    def __repr__(self) -> str:
        return self.voices_list.__repr__() + ' Extras:' + self.extras_list.__repr__()

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id!
        if not isinstance(other, AnnMeasure):
            return False

        if len(self.voices_list) != len(other.voices_list):
            return False

        if len(self.extras_list) != len(other.extras_list):
            return False

        return self.precomputed_str == other.precomputed_str
        # return all([v[0] == v[1] for v in zip(self.voices_list, other.voices_list)])

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnMeasure`.

        Returns:
            int: The notation size of the annotated measure
        """
        return (
            sum([v.notation_size() for v in self.voices_list])
            + sum([e.notation_size() for e in self.extras_list])
        )

    def get_note_ids(self) -> list[str | int]:
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
    def __init__(
        self,
        part: m21.stream.Part,
        score: m21.stream.Score,
        spannerBundle: m21.spanner.SpannerBundle,
        detail: DetailLevel = DetailLevel.Default
    ):
        """
        Extend music21 Part/PartStaff with some precomputed, easily compared information about it.

        Args:
            part (music21.stream.Part, music21.stream.PartStaff): The music21 Part/PartStaff
                to extend.
            score (music21.stream.Score): the enclosing music21 Score.
            spannerBundle (music21.spanner.SpannerBundle): a bundle of all the spanners in
                the score.
            detail (DetailLevel): What level of detail to use during the diff.
                Can be GeneralNotesOnly, AllObjects, AllObjectsWithStyle, MetadataOnly,
                GeneralNotesAndMetadata, AllObjectsAndMetadata, AllObjectsWithStyleAndMetadata,
                or Default (Default is currently equivalent to AllObjects).
        """
        self.part: int | str = part.id
        self.bar_list: list[AnnMeasure] = []
        for measure in part.getElementsByClass("Measure"):
            # create the bar objects
            ann_bar = AnnMeasure(measure, part, score, spannerBundle, detail)
            if ann_bar.n_of_voices > 0:
                self.bar_list.append(ann_bar)
        self.n_of_bars: int = len(self.bar_list)
        # Precomputed str to speed up the computation.
        # String itself is pretty long, so it is hashed
        self.precomputed_str: int = hash(self.__str__())

    def __str__(self) -> str:
        output: str = 'Part: '
        output += str([str(b) for b in self.bar_list])
        return output

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id!
        if not isinstance(other, AnnPart):
            return False

        if len(self.bar_list) != len(other.bar_list):
            return False

        return all(b[0] == b[1] for b in zip(self.bar_list, other.bar_list))

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnPart`.

        Returns:
            int: The notation size of the annotated part
        """
        return sum([b.notation_size() for b in self.bar_list])

    def __repr__(self) -> str:
        return self.bar_list.__repr__()

    def get_note_ids(self) -> list[str | int]:
        """
        Computes a list of the GeneralNote ids for this `AnnPart`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this part
        """
        notes_id = []
        for b in self.bar_list:
            notes_id.extend(b.get_note_ids())
        return notes_id


class AnnStaffGroup:
    def __init__(
        self,
        staff_group: m21.layout.StaffGroup,
        part_to_index: dict[m21.stream.Part, int],
        detail: DetailLevel = DetailLevel.Default
    ) -> None:
        """
        Take a StaffGroup and store it as an annotated object.
        """
        self.staff_group: int | str = staff_group.id
        self.name: str = staff_group.name or ''
        self.abbreviation: str = staff_group.abbreviation or ''
        self.symbol: str | None = None
        self.barTogether: bool | str | None = staff_group.barTogether

        if DetailLevel.includesStyle(detail):
            # symbol (brace, bracket, line, etc) is considered to be style
            self.symbol = staff_group.symbol

        self.part_indices: list[int] = []
        for part in staff_group:
            self.part_indices.append(part_to_index.get(part, -1))

        # sort so simple list comparison can work
        self.part_indices.sort()

        self.n_of_parts: int = len(self.part_indices)

        # precomputed representations for faster comparison
        self.precomputed_str: str = self.__str__()

    def __str__(self) -> str:
        output: str = "StaffGroup"
        if self.name and self.abbreviation:
            output += f"({self.name},{self.abbreviation})"
        elif self.name:
            output += f"({self.name})"
        elif self.abbreviation:
            output += f"(,{self.abbreviation})"
        else:
            output += "(,)"

        output += f", symbol={self.symbol}"
        output += f", barTogether={self.barTogether}"
        output += f", partIndices={self.part_indices}"
        return output

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id (or MEI ids of parts included in the group)
        if not isinstance(other, AnnStaffGroup):
            return False

        if self.name != other.name:
            return False

        if self.abbreviation != other.abbreviation:
            return False

        if self.symbol != other.symbol:
            return False

        if self.barTogether != other.barTogether:
            return False

        if self.part_indices != other.part_indices:
            return False

        return True

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnStaffGroup`.

        Returns:
            int: The notation size of the annotated staff group
        """
        # notation_size = 5 because there are 5 main visible things about a StaffGroup:
        #   name, abbreviation, symbol shape, barline type, and which parts it encloses
        return 5

    def __repr__(self) -> str:
        # does consider the MEI id!
        output: str = f"StaffGroup({self.staff_group}):"
        output += f" name={self.name}, abbrev={self.abbreviation},"
        output += f" symbol={self.symbol}, barTogether={self.barTogether}"
        output += f", partIndices={self.part_indices}"
        return output


class AnnMetadataItem:
    def __init__(
        self,
        key: str,
        value: t.Any
    ) -> None:
        self.key = key
        if isinstance(value, m21.metadata.Text):
            # Create a string representing both the text and the language, but not isTranslated,
            # since isTranslated cannot be represented in many file formats.
            self.value = str(value) + f'(language={value.language})'
        elif isinstance(value, m21.metadata.Contributor):
            # Create a string (same thing: value.name.isTranslated will differ randomly)
            # Currently I am also ignoring more than one name, and birth/death.
            self.value = str(value) + f'(role={value.role}, language={value._names[0].language})'
        else:
            self.value = value

    def __eq__(self, other) -> bool:
        if not isinstance(other, AnnMetadataItem):
            return False

        if self.key != other.key:
            return False

        if self.value != other.value:
            return False

        return True

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return self.key + ':' + str(self.value)

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnMetadataItem`.

        Returns:
            int: The notation size of the annotated metadata item
        """
        return 1


class AnnScore:
    def __init__(
        self,
        score: m21.stream.Score,
        detail: DetailLevel = DetailLevel.Default
    ) -> None:
        """
        Take a music21 score and store it as a sequence of Full Trees.
        The hierarchy is "score -> parts -> measures -> voices -> notes"
        Args:
            score (music21.stream.Score): The music21 score
            detail (DetailLevel): What level of detail to use during the diff.
                Can be GeneralNotesOnly, AllObjects, AllObjectsWithStyle, MetadataOnly,
                GeneralNotesAndMetadata, AllObjectsAndMetadata, AllObjectsWithStyleAndMetadata,
                or Default (Default is currently equivalent to AllObjects).
        """
        self.score: int | str = score.id
        self.part_list: list[AnnPart] = []
        self.staff_group_list: list[AnnStaffGroup] = []
        self.metadata_items_list: list[AnnMetadataItem] = []

        spannerBundle: m21.spanner.SpannerBundle = score.spannerBundle
        part_to_index: dict[m21.stream.Part, int] = {}

        # Before we start, transpose all notes to written pitch, both for transposing
        # instruments and Ottavas. Be careful to preserve accidental.displayStatus
        # during transposition, since we use that visibility indicator when comparing
        # accidentals.
        score.toWrittenPitch(inPlace=True, preserveAccidentalDisplay=True)

        for idx, part in enumerate(score.parts):
            # create and add the AnnPart object to part_list
            # and to part_to_index dict
            part_to_index[part] = idx
            ann_part = AnnPart(part, score, spannerBundle, detail)
            self.part_list.append(ann_part)

        self.n_of_parts: int = len(self.part_list)

        if DetailLevel.includesOtherMusicObjects(detail):
            # staffgroups are extras (a.k.a. OtherMusicObjects)
            for staffGroup in score[m21.layout.StaffGroup]:
                ann_staff_group = AnnStaffGroup(staffGroup, part_to_index, detail)
                if ann_staff_group.n_of_parts > 0:
                    self.staff_group_list.append(ann_staff_group)

        if DetailLevel.includesMetadata(detail) and score.metadata is not None:
            # m21 metadata.all() can't sort primitives, so we'll have to sort by hand.
            allItems: list[tuple[str, t.Any]] = list(
                score.metadata.all(returnPrimitives=True, returnSorted=False)
            )
            allItems.sort(key=lambda each: (each[0], str(each[1])))
            for key, value in allItems:
                if key in ('fileFormat', 'filePath', 'software'):
                    # Don't compare metadata items that are uninterestingly different.
                    continue
                if (key.startswith('raw:')
                        or key.startswith('meiraw:')
                        or key.startswith('humdrumraw:')):
                    # Don't compare verbatim/raw metadata ('meiraw:meihead',
                    # 'raw:freeform', 'humdrumraw:XXX'), it's often deleted
                    # when made obsolete by conversions/edits.
                    continue
                self.metadata_items_list.append(AnnMetadataItem(key, value))

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id!
        if not isinstance(other, AnnScore):
            return False

        if len(self.part_list) != len(other.part_list):
            return False

        return all(p[0] == p[1] for p in zip(self.part_list, other.part_list))

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnScore`.

        Returns:
            int: The notation size of the annotated score
        """
        return sum([p.notation_size() for p in self.part_list])

    def __repr__(self) -> str:
        return self.part_list.__repr__()

    def get_note_ids(self) -> list[str | int]:
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
    def _measures_from_part(self, part_number) -> list[AnnMeasure]:
        # only used by tests/test_scl.py
        if part_number not in range(0, len(self.part_list)):
            raise ValueError(
                f"parameter 'part_number' should be between 0 and {len(self.part_list) - 1}"
            )
        return self.part_list[part_number].bar_list
