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
# Copyright:     (c) 2022-2024 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------

__docformat__ = "google"

import html
from fractions import Fraction
import typing as t

import music21 as m21
from music21.common import OffsetQL, opFrac

from musicdiff import M21Utils
from musicdiff import DetailLevel

class AnnNote:
    def __init__(
        self,
        general_note: m21.note.GeneralNote,
        gap_dur: OffsetQL,
        enhanced_beam_list: list[str],
        tuplet_list: list[str],
        tuplet_info: list[str],
        parent_chord: m21.chord.ChordBase | None = None,
        chord_offset: OffsetQL | None = None,  # only set if this note is inside a chord
        detail: DetailLevel | int = DetailLevel.Default,
    ) -> None:
        """
        Extend music21 GeneralNote with some precomputed, easily compared information about it.

        Args:
            general_note (music21.note.GeneralNote): The music21 note/chord/rest to extend.
            gap_dur (OffsetQL): gap since end of last note (or since start of measure, if
                first note in measure).  Usually zero.
            enhanced_beam_list (list): A list of beaming information about this GeneralNote.
            tuplet_list (list): A list of basic tuplet info about this GeneralNote.
            tuplet_info (list): A list of detailed tuplet info about this GeneralNote.
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.general_note: int | str = general_note.id
        self.is_in_chord: bool = False
        self.note_idx_in_chord: int | None = None
        if parent_chord is not None:
            # This is what visualization uses to color the note red (chord id and note idx)
            self.general_note = parent_chord.id
            self.is_in_chord = True
            self.note_idx_in_chord = parent_chord.notes.index(general_note)

        # A lot of stuff is carried by the parent_chord (if present) or the
        # general_note (if parent_chord not present); we call that the carrier
        carrier: m21.note.GeneralNote = parent_chord or general_note

        self.gap_dur: OffsetQL = gap_dur
        self.beamings: list[str] = enhanced_beam_list
        self.tuplets: list[str] = tuplet_list
        self.tuplet_info: list[str] = tuplet_info

        self.note_offset: OffsetQL = 0.
        self.note_dur_type: str = ''
        self.note_dur_dots: int = 0
        self.note_is_grace: bool = False

        # fullNameSuffix is only for text output, it is not involved in comparison at all.
        # It is of the form "Dotted Quarter Rest", etc.
        self.fullNameSuffix: str = general_note.duration.fullName
        if isinstance(general_note, m21.note.Rest):
            self.fullNameSuffix += " Rest"
        elif isinstance(general_note, m21.chord.ChordBase):
            if parent_chord is None:
                self.fullNameSuffix += " Chord"
            else:
                # we're actually annotating one of the notes in the chord
                self.fullNameSuffix += " Note"
        elif isinstance(general_note, (m21.note.Note, m21.note.Unpitched)):
            self.fullNameSuffix += " Note"
        else:
            self.fullNameSuffix += " Note"
        self.fullNameSuffix = self.fullNameSuffix.lower()

        if not DetailLevel.includesVoicing(detail):
            # if we're comparing the individual notes, we need to make a note of
            # offset and visual duration to be used later when searching for matching
            # notes in the measures being compared.

            # offset
            if chord_offset is None:
                self.note_offset = general_note.offset
            else:
                self.note_offset = chord_offset

            # visual duration and graceness
            self.note_dur_type = carrier.duration.type
            self.note_dur_dots = carrier.duration.dots
            self.note_is_grace = carrier.duration.isGrace

        self.styledict: dict = {}

        if DetailLevel.includesStyle(detail):
            # we will take style from the individual note, and then override with
            # style from the chord (following music21's MusicXML exporter).
            if M21Utils.has_style(general_note):
                self.styledict = M21Utils.obj_to_styledict(general_note, detail)

            if parent_chord is not None:
                if M21Utils.has_style(parent_chord):
                    parentstyledict = M21Utils.obj_to_styledict(parent_chord, detail)
                    for k, v in parentstyledict.items():
                        self.styledict[k] = v

        self.noteshape: str = 'normal'
        self.noteheadFill: bool | None = None
        self.noteheadParenthesis: bool = False
        self.stemDirection: str = 'unspecified'
        if DetailLevel.includesStyle(detail) and isinstance(general_note, m21.note.NotRest):
            if t.TYPE_CHECKING:
                # because general_note is NotRest, parent_chord must also be (might be
                # a chord instead of a note, but that still works)
                assert isinstance(carrier, m21.note.NotRest)
            self.stemDirection = carrier.stemDirection

            if parent_chord is None:
                self.noteshape = general_note.notehead
                self.noteheadFill = general_note.noteheadFill
                self.noteheadParenthesis = general_note.noteheadParenthesis
            else:
                # try general_note first, but if nothing about note head is specified,
                # go with whatever parent_chord says.
                if (general_note.notehead != 'normal'
                        or general_note.noteheadParenthesis
                        or general_note.noteheadFill is not None):
                    self.noteheadParenthesis = general_note.noteheadParenthesis
                    self.noteshape = general_note.notehead
                    self.noteheadFill = general_note.noteheadFill
                else:
                    self.noteshape = parent_chord.notehead
                    self.noteheadFill = parent_chord.noteheadFill
                    self.noteheadParenthesis = parent_chord.noteheadParenthesis

        # compute the representation of NoteNode as in the paper
        # pitches is a list  of elements, each one is (pitchposition, accidental, tied)
        self.pitches: list[tuple[str, str, bool]]
        if isinstance(general_note, m21.chord.ChordBase):
            notes: tuple[m21.note.NotRest, ...] = general_note.notes
            if hasattr(general_note, "sortDiatonicAscending"):
                # PercussionChords don't have this, Chords do
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

        dur: m21.duration.Duration = carrier.duration
        # note head
        type_number = Fraction(
            M21Utils.get_type_num(dur)
        )
        self.note_head: int | Fraction
        if type_number >= 4:
            self.note_head = 4
        else:
            self.note_head = type_number
        # dots
        self.dots: int = dur.dots
        # graceness
        self.graceType: str = ''
        self.graceSlash: bool | None = False
        if isinstance(dur, m21.duration.AppoggiaturaDuration):
            self.graceType = 'acc'
            self.graceSlash = dur.slash
        elif isinstance(dur, m21.duration.GraceDuration):
            # might be accented or unaccented.  duration.slash isn't always reliable
            # (historically), but we can use it as a fallback.
            # Check duration.stealTimePrevious and duration.stealTimeFollowing first.
            if dur.stealTimePrevious is not None:
                self.graceType = 'unacc'
            elif dur.stealTimeFollowing is not None:
                self.graceType = 'acc'
            elif dur.slash is True:
                self.graceType = 'unacc'
            elif dur.slash is False:
                self.graceType = 'acc'
            else:
                # by default, GraceDuration with no other indications (slash is None)
                # is assumed to be unaccented.
                self.graceType = 'unacc'
            self.graceSlash = dur.slash

        # The following (articulations, expressions) only occur once per chord
        # or standalone note, so we only want to annotate them once.  We annotate them
        # on standalone notes (of course), and on the first note of a parent_chord.
        self.articulations: list[str] = []
        self.expressions: list[str] = []

        if self.note_idx_in_chord is None or self.note_idx_in_chord == 0:
            # articulations
            if DetailLevel.includesArticulations(detail):
                self.articulations = [
                    M21Utils.articulation_to_string(a, detail) for a in carrier.articulations
                ]
                if self.articulations:
                    self.articulations.sort()

            if DetailLevel.includesOrnaments(detail):
                # expressions (tremolo, arpeggio, textexp have their own detail bits, though)
                for a in carrier.expressions:
                    if not DetailLevel.includesTremolos(detail):
                        if isinstance(a, m21.expressions.Tremolo):
                            continue
                    if not DetailLevel.includesArpeggios(detail):
                        if isinstance(a, m21.expressions.ArpeggioMark):
                            continue
                    if not DetailLevel.includesDirections(detail):
                        if isinstance(a, m21.expressions.TextExpression):
                            continue
                    self.expressions.append(
                        M21Utils.expression_to_string(a, detail)
                    )
                if self.expressions:
                    self.expressions.sort()

        # precomputed/cached representations for faster comparison
        self.precomputed_str: str = self.__str__()
        self._cached_notation_size: int | None = None

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnNote`.

        Returns:
            int: The notation size of the annotated note
        """
        if self._cached_notation_size is None:
            size: int = 0
            # add for the pitches
            for pitch in self.pitches:
                size += M21Utils.pitch_size(pitch)
            # add for the notehead (quarter, half, semibreve, breve, etc)
            size += 1
            # add for the dots
            size += self.dots * len(self.pitches)  # one dot for each note if it's a chord
            # add for the beams/flags
            size += len(self.beamings)
            # add for the tuplets
            size += len(self.tuplets)
            size += len(self.tuplet_info)
            # add for the articulations
            size += len(self.articulations)
            # add for the expressions
            size += len(self.expressions)
            # add 1 if it's a gracenote, and 1 more if there's a grace slash
            if self.graceType:
                size += 1
                if self.graceSlash is True:
                    size += 1
            # add 1 for abnormal note shape (diamond, etc)
            if self.noteshape != 'normal':
                size += 1
            # add 1 for abnormal note fill
            if self.noteheadFill is not None:
                size += 1
            # add 1 if there's a parenthesis around the note
            if self.noteheadParenthesis:
                size += 1
            # add 1 if stem direction is specified
            if self.stemDirection != 'unspecified':
                size += 1
            # add 1 if there is an empty space before this note
            if self.gap_dur != 0:
                size += 1
            # add 1 for any other style info (in future might count the style entries)
            if self.styledict:
                size += 1

            self._cached_notation_size = size

        return self._cached_notation_size

    def get_identifying_string(self, name: str = "") -> str:
        string: str = ""
        if self.fullNameSuffix.endswith("rest"):
            string = self.fullNameSuffix
        elif self.fullNameSuffix.endswith("note"):
            string = self.pitches[0][0]
            if self.pitches[0][1] != "None":
                string += " " + self.pitches[0][1]
            string += " (" + self.fullNameSuffix + ")"
        elif self.fullNameSuffix.endswith("chord"):
            string = "["
            for p in self.pitches:  # add for pitches
                string += p[0]  # pitch name and octave
                if p[1] != "None":
                    string += " " + p[1]  # pitch accidental
                string += ","
            string = string[:-1]  # delete the last comma
            string += "] (" + self.fullNameSuffix + ")"
        return string

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = self.get_identifying_string(name)
        if name == "pitch":
            # this is only for "pitch", not for "" (pitches are in identifying string)
            if self.fullNameSuffix.endswith("chord"):
                string += f", pitch[{idx}]={self.pitches[idx][0]}"
            return string

        if name == "accid":
            # this is only for "accid" (indexed in a chord), not for "", or for "accid" on a note
            # (accidental is in identifying string)
            if self.fullNameSuffix.endswith("chord"):
                string += f", accid[{idx}]={self.pitches[idx][1]}"
            return string

        if name == "head":
            # this is only for "head", not for "" (head is implied by identifying string)
            if self.note_head == 4:
                string += ", head=normal"
            else:
                string += f", head={m21.duration.typeFromNumDict[float(self.note_head)]}"
            if name:
                return string

        if name == "dots":
            # this is only for "dots", not for "" (dots is in identifying string)
            string += f", dots={self.dots}"
            return string

        if not name or name == "flagsbeams":
            numBeams: int = len(self.beamings)
            # Flags are implied by identifying string, so do not belong when name=="".
            # And "no beams" is boring for name=="".  Non-zero beams, though, we always
            # want to see.
            if numBeams == 0:
                if name:
                    string += ", no flags/beams"
                    return string
            elif all(b == "partial" for b in self.beamings):
                if name:
                    if numBeams == 1:
                        string += f", {numBeams} flag"
                    else:
                        string += f", {numBeams} flags"
                    return string
            else:
                # it's beams, not flags
                if numBeams == 1:
                    string += f", {numBeams} beam="
                else:
                    string += f", {numBeams} beams=["
                for i, b in enumerate(self.beamings):
                    if i > 0:
                        string += ", "
                    string += b
                if numBeams > 1:
                    string += "]"
                if name:
                    return string

        if not name or name == "tuplet":
            if name or self.tuplets:
                string += ", tuplets=["
                for i, (tup, ti) in enumerate(zip(self.tuplets, self.tuplet_info)):
                    if i > 0:
                        string += ", "
                    if ti != "":
                        ti = "(" + ti + ")"
                    string += tup + ti

                string += "]"
                if name:
                    return string

        if not name or name == "tie":
            if self.pitches[idx][2]:
                string += ", tied"
            elif name:
                string += ", not tied"
            if name:
                return string


        if not name or name == "grace":
            if not name:
                if self.graceType:
                    string += f", grace={self.graceType}"
            else:
                string += f", grace={self.graceType}"
            if name:
                return string

        if not name or name == "graceslash":
            if self.graceType:
                if self.graceSlash:
                    string += ", with grace slash"
                else:
                    string += ", with no grace slash"
            if name:
                return string

        if not name or name == "noteshape":
            if not name:
                if self.noteshape != "normal":
                    string += f", noteshape={self.noteshape}"
            else:
                string += f", noteshape={self.noteshape}"
            if name:
                return string

        if not name or name == "notefill":
            if not name:
                if self.noteheadFill is not None:
                    string += f", noteheadFill={self.noteheadFill}"
            else:
                string += f", noteheadFill={self.noteheadFill}"
            if name:
                return string

        if not name or name == "noteparen":
            if not name:
                if self.noteheadParenthesis:
                    string += f", noteheadParenthesis={self.noteheadParenthesis}"
            else:
                string += f", noteheadParenthesis={self.noteheadParenthesis}"
            if name:
                return string

        if not name or name == "stemdir":
            if not name:
                if self.stemDirection != "unspecified":
                    string += f", stemDirection={self.stemDirection}"
            else:
                string += f", stemDirection={self.stemDirection}"
            if name:
                return string

        if not name or name == "spacebefore":
            if not name:
                if self.gap_dur != 0:
                    string += f", spacebefore={self.gap_dur}"
            else:
                string += f", spacebefore={self.gap_dur}"
            if name:
                return string

        if not name or name == "artic":
            if name or self.articulations:
                string += ", articulations=["
                for i, artic in enumerate(self.articulations):
                    if i > 0:
                        string += ", "
                    string += artic
                string += "]"
            if name:
                return string

        if not name or name == "expression":
            if name or self.expressions:
                string += ", expressions=["
                for i, exp in enumerate(self.expressions):
                    if i > 0:
                        string += ", "
                    string += exp
                string += "]"
            if name:
                return string

        if not name or name == "style":
            if name or self.styledict:
                allOfThem: bool = False
                changedKeys: list[str] = []
                if changedStr:
                    changedKeys = changedStr.split(",")
                else:
                    changedKeys = [str(k) for k in self.styledict]
                    allOfThem = True

                if allOfThem:
                    string += ", style={"
                else:
                    string += ", changedStyle={"

                needsComma: bool = False
                for i, k in enumerate(changedKeys):
                    if k in self.styledict:
                        if needsComma:
                            string += ", "
                        string += f"{k}:{self.styledict[k]}"
                        needsComma = True
                string += "}"
            if name:
                return string

        return string

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the general note.
        return (
            f"GeneralNote({self.general_note}),G:{self.gap_dur},"
            + f"P:{self.pitches},H:{self.note_head},D:{self.dots},"
            + f"B:{self.beamings},T:{self.tuplets},TI:{self.tuplet_info},"
            + f"A:{self.articulations},E:{self.expressions},"
            + f"S:{self.styledict}"
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
                string += "/"
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
                elif tup == "startStop":
                    string += "ss"
                else:
                    raise ValueError(f"Incorrect tuplet type: {tup}")

        if len(self.articulations) > 0:  # add for articulations
            for a in self.articulations:
                string += " " + a
        if len(self.expressions) > 0:  # add for expressions
            for e in self.expressions:
                string += " " + e

        if self.noteshape != "normal":
            string += f" noteshape={self.noteshape}"
        if self.noteheadFill is not None:
            string += f" noteheadFill={self.noteheadFill}"
        if self.noteheadParenthesis:
            string += f" noteheadParenthesis={self.noteheadParenthesis}"
        if self.stemDirection != "unspecified":
            string += f" stemDirection={self.stemDirection}"

        # gap_dur
        if self.gap_dur != 0:
            string += f" spaceBefore={self.gap_dur}"

        # and then the style fields
        for i, (k, v) in enumerate(self.styledict.items()):
            if i == 0:
                string += " "
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


class AnnExtra:
    def __init__(
        self,
        extra: m21.base.Music21Object,
        measure: m21.stream.Measure,
        score: m21.stream.Score,
        detail: DetailLevel | int = DetailLevel.Default
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
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.extra = extra.id
        self.offset: OffsetQL
        self.duration: OffsetQL
        self.numNotes: int = 1

        if isinstance(extra, m21.spanner.Spanner):
            self.numNotes = len(extra)
            firstNote: m21.note.GeneralNote | m21.spanner.SpannerAnchor = (
                M21Utils.getPrimarySpannerElement(extra)
            )
            lastNote: m21.note.GeneralNote | m21.spanner.SpannerAnchor = (
                extra.getLast()
            )
            self.offset = firstNote.getOffsetInHierarchy(measure)
            # to compute duration we need to use offset-in-score, since the end note might
            # be in another Measure.  Except for ArpeggioMarkSpanners, where the duration
            # doesn't matter, so we just set it to 0, rather than figuring out the longest
            # duration in all the notes/chords in the arpeggio.
            if isinstance(extra, m21.expressions.ArpeggioMarkSpanner):
                self.duration = 0.
            else:
                startOffsetInScore: OffsetQL = firstNote.getOffsetInHierarchy(score)
                try:
                    endOffsetInScore: OffsetQL = opFrac(
                        lastNote.getOffsetInHierarchy(score) + lastNote.duration.quarterLength
                    )
                except m21.sites.SitesException:
                    endOffsetInScore = startOffsetInScore
                self.duration = opFrac(endOffsetInScore - startOffsetInScore)
        elif isinstance(extra, m21.bar.Barline):
            # we ignore offset for barlines; barline offset is derived from the objects in the
            # measure, which are already being compared.
            self.offset = 0.0
            self.duration = extra.duration.quarterLength
        elif isinstance(extra, m21.harmony.ChordSymbol):
            # we ignore duration for ChordSymbols, it is often 0.0 or 1.0, and meaningless.
            self.offset = extra.getOffsetInHierarchy(measure)
            self.duration = 0.0
        else:
            self.offset = extra.getOffsetInHierarchy(measure)
            self.duration = extra.duration.quarterLength

        self.content: str = M21Utils.extra_to_string(extra, detail)
        self.styledict: dict = {}

        if DetailLevel.includesStyle(detail):
            if not isinstance(extra, m21.harmony.ChordSymbol):
                # We don't (yet) compare style of ChordSymbols, because Humdrum has no way (yet)
                # of storing that.
                if M21Utils.has_style(extra):
                    # includes extra.placement if present

                    # special case: MM with text='SMUFLNote = nnn" is being annotated as if there is
                    # no text, so none of the text style stuff should be added.
                    smuflTextSuppressed: bool = False
                    if (isinstance(extra, m21.tempo.MetronomeMark)
                            and not extra.textImplicit
                            and extra.text
                            and not self.content.startswith('MM:TX:')):
                        smuflTextSuppressed = True

                    self.styledict = M21Utils.obj_to_styledict(
                        extra,
                        detail,
                        smuflTextSuppressed=smuflTextSuppressed
                    )


        # precomputed/cached representations for faster comparison
        self.precomputed_str: str = self.__str__()
        self._cached_notation_size: int | None = None

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnExtra`.

        Returns:
            int: The notation size of the annotated extra
        """
        if self._cached_notation_size is None:
            cost: int = len(self.content)
            cost += 2  # for offset and duration
            if self.styledict:
                cost += 1  # someday we might count items in styledict
            self._cached_notation_size = cost

        return self._cached_notation_size

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = self.content
        if name == "":
            if self.duration > 0:
                string += f" dur={M21Utils.ql_to_string(self.duration)}"
            if self.numNotes != 1:
                string += f" numNotes={self.numNotes}"
            return string

        if name == "content":
            return string

        if name == "offset":
            string += f" offset={M21Utils.ql_to_string(self.offset)}"
            return string

        if name == "duration":
            string += f" dur={M21Utils.ql_to_string(self.duration)}"
            return string

        if name == "style":
            changedKeys: list[str] = changedStr.split(',')
            if not changedKeys:
                string += " changedStyle={}"
                return string

            string += " changedStyle={"

            needsComma: bool = False
            for i, k in enumerate(changedKeys):
                if k in self.styledict:
                    if needsComma:
                        string += ", "
                    string += f"{k}:{self.styledict[k]}"
                    needsComma = True
            string += "}"
            return string

        return ""  # should never get here

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the extra.
        output: str = f"Extra({self.extra}):"
        output += str(self)
        return output

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


class AnnLyric:
    def __init__(
        self,
        lyric_holder: m21.note.GeneralNote,  # note containing the lyric
        lyric: m21.note.Lyric,  # the lyric itself
        measure: m21.stream.Measure,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> None:
        """
        Extend a lyric from a music21 GeneralNote with some precomputed, easily
        compared information about it.

        Args:
            lyric_holder (music21.note.GeneralNote): The note/chord/rest containing the lyric.
            lyric (music21.note.Lyric): The music21 Lyric object to extend.
            measure (music21.stream.Measure): The music21 Measure the lyric was found in.
                If the lyric was found in a Voice, this is the Measure that the lyric was
                found in.
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.lyric_holder = lyric_holder.id

        # for comparison: lyric, number, identifier, offset, styledict
        self.lyric: str = ""
        self.number: int = 0
        self.identifier: str = ""
        self.offset = lyric_holder.getOffsetInHierarchy(measure)
        self.styledict: dict[str, str] = {}

        # ignore .syllabic and .text, what is visible is .rawText (and there
        # are several .syllabic/.text combos that create the same .rawText).
        self.lyric = lyric.rawText

        if lyric.number is not None:
            self.number = lyric.number

        if (lyric._identifier is not None
                and lyric._identifier != lyric.number
                and lyric._identifier != str(lyric.number)):
            self.identifier = lyric._identifier

        if DetailLevel.includesStyle(detail) and M21Utils.has_style(lyric):
            self.styledict = M21Utils.obj_to_styledict(lyric, detail)
            if self.styledict:
                # sort styleDict before converting to string so we can compare strings
                self.styledict = dict(sorted(self.styledict.items()))

        # precomputed/cached representations for faster comparison
        self.precomputed_str: str = self.__str__()
        self._cached_notation_size: int | None = None

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnLyric`.

        Returns:
            int: The notation size of the annotated lyric
        """
        if self._cached_notation_size is None:
            size: int = len(self.lyric)
            size += 1  # for offset
            if self.number:
                size += 1
            if self.identifier:
                size += 1
            if self.styledict:
                size += 1  # maybe someday we'll count items in styledict?
            self._cached_notation_size = size

        return self._cached_notation_size

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = f'"{self.lyric}"'
        if name == "":
            if self.number is not None:
                string += f", num={self.number}"
            if self.identifier:  # not None and != ""
                string += f", id={self.identifier}"
            if self.styledict:
                string += f" style={self.styledict}"
            return string

        if name == "rawtext":
            return string

        if name == "offset":
            string += f" offset={M21Utils.ql_to_string(self.offset)}"
            return string

        if name == "num":
            string += f", num={self.number}"
            return string

        if name == "id":
            string += f", id={self.identifier}"
            return string

        if name == "style":
            string += f" style={self.styledict}"
            return string

        return ""  # should never get here

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the general note
        # that holds the lyric, plus the lyric
        # number within that general note.
        output: str = f"Lyric({self.lyric_holder}[{self.number}]):"
        output += str(self)
        return output

    def __str__(self) -> str:
        """
        Returns:
            str: the compared representation of the AnnLyric. Does not consider music21 id.
        """
        string = (
            f"{self.lyric},num={self.number},id={self.identifier}"
            + f",off={self.offset},style={self.styledict}"
        )
        return string

    def __eq__(self, other) -> bool:
        # equality does not consider the MEI id!
        return self.precomputed_str == other.precomputed_str


class AnnVoice:
    def __init__(
        self,
        voice: m21.stream.Voice | m21.stream.Measure,
        enclosingMeasure: m21.stream.Measure,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> None:
        """
        Extend music21 Voice with some precomputed, easily compared information about it.
        Only ever called if detail includes Voicing.

        Args:
            voice (music21.stream.Voice or Measure): The music21 voice to extend. This
                can be a Measure, but only if it contains no Voices.
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.voice: int | str = voice.id
        note_list: list[m21.note.GeneralNote] = []

        if DetailLevel.includesNotesAndRests(detail):
            note_list = M21Utils.get_notes_and_gracenotes(voice)

        self.en_beam_list: list[list[str]] = []
        self.tuplet_list: list[list[str]] = []
        self.tuplet_info: list[list[str]] = []
        self.annot_notes: list[AnnNote] = []

        if note_list:
            self.en_beam_list = M21Utils.get_enhance_beamings(
                note_list,
                detail
            )  # beams ("partial" can mean partial beam or just a flag)
            self.tuplet_list = M21Utils.get_tuplets_type(
                note_list
            )  # corrected tuplets (with "start" and "continue")
            self.tuplet_info = M21Utils.get_tuplets_info(note_list)
            # create a list of notes with beaming and tuplets information attached
            self.annot_notes = []
            for i, n in enumerate(note_list):
                expectedOffsetInMeas: OffsetQL = 0
                if i > 0:
                    prevNoteStart: OffsetQL = (
                        note_list[i - 1].getOffsetInHierarchy(enclosingMeasure)
                    )
                    prevNoteDurQL: OffsetQL = (
                        note_list[i - 1].duration.quarterLength
                    )
                    expectedOffsetInMeas = opFrac(prevNoteStart + prevNoteDurQL)

                gapDurQL: OffsetQL = (
                    n.getOffsetInHierarchy(enclosingMeasure) - expectedOffsetInMeas
                )
                self.annot_notes.append(
                    AnnNote(
                        n,
                        gapDurQL,
                        self.en_beam_list[i],
                        self.tuplet_list[i],
                        self.tuplet_info[i],
                        detail=detail
                    )
                )

        self.n_of_notes: int = len(self.annot_notes)
        self.precomputed_str: str = self.__str__()
        self._cached_notation_size: int | None = None

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id!
        if not isinstance(other, AnnVoice):
            return False

        if len(self.annot_notes) != len(other.annot_notes):
            return False

        return self.precomputed_str == other.precomputed_str

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnVoice`.

        Returns:
            int: The notation size of the annotated voice
        """
        if self._cached_notation_size is None:
            self._cached_notation_size = sum([an.notation_size() for an in self.annot_notes])
        return self._cached_notation_size

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = "["
        for an in self.annot_notes:
            string += an.readable_str()
            string += ","

        if string[-1] == ",":
            # delete the last comma
            string = string[:-1]

        string += "]"
        return string

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the voice.
        string: str = f"Voice({self.voice}):"
        string += "["
        for an in self.annot_notes:
            string += repr(an)
            string += ","

        if string[-1] == ",":
            # delete the last comma
            string = string[:-1]

        string += "]"
        return string

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
        detail: DetailLevel | int = DetailLevel.Default
    ) -> None:
        """
        Extend music21 Measure with some precomputed, easily compared information about it.

        Args:
            measure (music21.stream.Measure): The music21 Measure to extend.
            part (music21.stream.Part): the enclosing music21 Part
            score (music21.stream.Score): the enclosing music21 Score.
            spannerBundle (music21.spanner.SpannerBundle): a bundle of all the spanners
                in the score.
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.measure: int | str = measure.id
        self.includes_voicing: bool = DetailLevel.includesVoicing(detail)
        self.n_of_elements: int = 0

        # for text output only (see self.readable_str())
        self.measureNumber: str = M21Utils.get_measure_number_with_suffix(measure, part)
        # if self.measureNumber == 135:
        #     print('135')

        if self.includes_voicing:
            # we make an AnnVoice for each voice in the measure
            self.voices_list: list[AnnVoice] = []
            if len(measure.voices) == 0:
                # there is a single AnnVoice (i.e. in the music21 Measure there are no voices)
                ann_voice = AnnVoice(measure, measure, detail)
                if ann_voice.n_of_notes > 0:
                    self.voices_list.append(ann_voice)
            else:  # there are multiple voices (or an array with just one voice)
                for voice in measure.voices:
                    ann_voice = AnnVoice(voice, measure, detail)
                    if ann_voice.n_of_notes > 0:
                        self.voices_list.append(ann_voice)
            self.n_of_elements = len(self.voices_list)
        else:
            # we pull up all the notes in all the voices (and split any chords into
            # individual notes)
            self.annot_notes: list[AnnNote] = []

            note_list: list[m21.note.GeneralNote] = []
            if DetailLevel.includesNotesAndRests(detail):
                note_list = M21Utils.get_notes_and_gracenotes(measure, recurse=True)

            if note_list:
                en_beam_list = M21Utils.get_enhance_beamings(
                    note_list,
                    detail
                )  # beams ("partial" can mean partial beam or just a flag)
                tuplet_list = M21Utils.get_tuplets_type(
                    note_list
                )  # corrected tuplets (with "start" and "continue")
                tuplet_info = M21Utils.get_tuplets_info(note_list)

                # create a list of notes with beaming and tuplets information attached
                self.annot_notes = []
                for i, n in enumerate(note_list):
                    if isinstance(n, m21.chord.ChordBase):
                        if isinstance(n, m21.chord.Chord):
                            n.sortDiatonicAscending(inPlace=True)
                        chord_offset: OffsetQL = n.getOffsetInHierarchy(measure)
                        for n1 in n.notes:
                            self.annot_notes.append(
                                AnnNote(
                                    n1,
                                    0.,
                                    en_beam_list[i],
                                    tuplet_list[i],
                                    tuplet_info[i],
                                    parent_chord=n,
                                    chord_offset=chord_offset,
                                    detail=detail
                                )
                            )
                    else:
                        self.annot_notes.append(
                            AnnNote(
                                n,
                                0.,
                                en_beam_list[i],
                                tuplet_list[i],
                                tuplet_info[i],
                                detail=detail
                            )
                        )

            self.n_of_elements = len(self.annot_notes)

        self.extras_list: list[AnnExtra] = []
        for extra in M21Utils.get_extras(measure, part, score, spannerBundle, detail):
            self.extras_list.append(AnnExtra(extra, measure, score, detail))
        self.n_of_elements += len(self.extras_list)

        # For correct comparison, sort the extras_list, so that any extras
        # that all have the same offset are sorted alphabetically.
        self.extras_list.sort(key=lambda e: (e.offset, str(e)))

        self.lyrics_list: list[AnnLyric] = []
        if DetailLevel.includesLyrics(detail):
            for lyric_holder in M21Utils.get_lyrics_holders(measure):
                for lyric in lyric_holder.lyrics:
                    if lyric.rawText:
                        # we ignore lyrics with no visible text
                        self.lyrics_list.append(AnnLyric(lyric_holder, lyric, measure, detail))
            self.n_of_elements += len(self.lyrics_list)

            # For correct comparison, sort the lyrics_list, so that any lyrics
            # that all have the same offset are sorted by verse number.
            if self.lyrics_list:
                self.lyrics_list.sort(key=lambda lyr: (lyr.offset, lyr.number))

        # precomputed/cached values to speed up the computation.
        # As they start to be long, they are hashed
        self.precomputed_str: int = hash(self.__str__())
        self.precomputed_repr: int = hash(self.__repr__())
        self._cached_notation_size: int | None = None

    def __str__(self) -> str:
        output: str = ''
        if self.includes_voicing:
            output += str([str(v) for v in self.voices_list])
        else:
            output += str([str(n) for n in self.annot_notes])
        if self.extras_list:
            output += ' Extras:' + str([str(e) for e in self.extras_list])
        if self.lyrics_list:
            output += ' Lyrics:' + str([str(lyr) for lyr in self.lyrics_list])
        return output

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the measure.
        output: str = f"Measure({self.measure}):"
        if self.includes_voicing:
            output += str([repr(v) for v in self.voices_list])
        else:
            output += str([repr(n) for n in self.annot_notes])
        if self.extras_list:
            output += ' Extras:' + str([repr(e) for e in self.extras_list])
        if self.lyrics_list:
            output += ' Lyrics:' + str([repr(lyr) for lyr in self.lyrics_list])
        return output

    def __eq__(self, other) -> bool:
        # equality does not consider MEI id!
        if not isinstance(other, AnnMeasure):
            return False

        if self.includes_voicing and other.includes_voicing:
            if len(self.voices_list) != len(other.voices_list):
                return False
        elif not self.includes_voicing and not other.includes_voicing:
            if len(self.annot_notes) != len(other.annot_notes):
                return False
        else:
            # shouldn't ever happen, but I guess it could if the client does weird stuff
            return False

        if len(self.extras_list) != len(other.extras_list):
            return False

        if len(self.lyrics_list) != len(other.lyrics_list):
            return False

        return self.precomputed_str == other.precomputed_str
        # return all([v[0] == v[1] for v in zip(self.voices_list, other.voices_list)])

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = f"measure {self.measureNumber}"
        return string

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnMeasure`.

        Returns:
            int: The notation size of the annotated measure
        """
        if self._cached_notation_size is None:
            if self.includes_voicing:
                self._cached_notation_size = (
                    sum([v.notation_size() for v in self.voices_list])
                    + sum([e.notation_size() for e in self.extras_list])
                    + sum([lyr.notation_size() for lyr in self.lyrics_list])
                )
            else:
                self._cached_notation_size = (
                    sum([n.notation_size() for n in self.annot_notes])
                    + sum([e.notation_size() for e in self.extras_list])
                    + sum([lyr.notation_size() for lyr in self.lyrics_list])
                )
        return self._cached_notation_size

    def get_note_ids(self) -> list[str | int]:
        """
        Computes a list of the GeneralNote ids for this `AnnMeasure`.

        Returns:
            [int]: A list containing the GeneralNote ids contained in this measure
        """
        notes_id = []
        if self.includes_voicing:
            for v in self.voices_list:
                notes_id.extend(v.get_note_ids())
        else:
            for n in self.annot_notes:
                notes_id.extend(n.get_note_ids())
        return notes_id


class AnnPart:
    def __init__(
        self,
        part: m21.stream.Part,
        score: m21.stream.Score,
        part_idx: int,
        spannerBundle: m21.spanner.SpannerBundle,
        detail: DetailLevel | int = DetailLevel.Default
    ):
        """
        Extend music21 Part/PartStaff with some precomputed, easily compared information about it.

        Args:
            part (music21.stream.Part, music21.stream.PartStaff): The music21 Part/PartStaff
                to extend.
            score (music21.stream.Score): the enclosing music21 Score.
            spannerBundle (music21.spanner.SpannerBundle): a bundle of all the spanners in
                the score.
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.part: int | str = part.id
        self.part_idx: int = part_idx
        self.bar_list: list[AnnMeasure] = []
        for measure in part.getElementsByClass("Measure"):
            # create the bar objects
            ann_bar = AnnMeasure(measure, part, score, spannerBundle, detail)
            if ann_bar.n_of_elements > 0:
                self.bar_list.append(ann_bar)
        self.n_of_bars: int = len(self.bar_list)
        # Precomputed str to speed up the computation.
        # String itself is pretty long, so it is hashed
        self.precomputed_str: int = hash(self.__str__())
        self._cached_notation_size: int | None = None

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

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = f"part {self.part_idx}"
        return string

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnPart`.

        Returns:
            int: The notation size of the annotated part
        """
        if self._cached_notation_size is None:
            self._cached_notation_size = sum([b.notation_size() for b in self.bar_list])
        return self._cached_notation_size

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the part.
        output: str = f"Part({self.part}):"
        output += str([repr(b) for b in self.bar_list])
        return output

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
        detail: DetailLevel | int = DetailLevel.Default
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
        self._cached_notation_size: int | None = None

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

        output += f", partIndices={self.part_indices}"
        if self.symbol is not None:
            output += f", symbol={self.symbol}"
        if self.barTogether is not None:
            output += f", barTogether={self.barTogether}"
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

        if self.n_of_parts != other.n_of_parts:
            # trying to avoid the more expensive part_indices array comparison
            return False

        if self.part_indices != other.part_indices:
            return False

        return True

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        string: str = f"StaffGroup{self.part_indices}"
        if name == "":
            return string

        if name == "name":
            string += f" name={self.name}"
            return string

        if name == "abbr":
            string += f" abbr={self.abbreviation}"
            return string

        if name == "sym":
            string += f" sym={self.symbol}"
            return string

        if name == "barline":
            string += f" barTogether={self.barTogether}"
            return string

        if name == "parts":
            # main string already has parts in it
            return string

        return ""

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnStaffGroup`.

        Returns:
            int: The notation size of the annotated staff group
        """
        # There are 5 main visible things about a StaffGroup:
        #   name, abbreviation, symbol shape, barline type, and which staves it encloses
        if self._cached_notation_size is None:
            size: int = len(self.name)
            size += 1  # for abbreviation
            size += 1  # for symbol shape
            size += 1  # for barline type
            size += 1  # for lowest staff index (vertical start)
            size += 1  # for highest staff index (vertical height)
            self._cached_notation_size = size
        return self._cached_notation_size

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the staff group.
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
        # Normally this would be the id of the Music21Object, but we just have a key/value
        # pair, so we just make up an id, by using our own address.  In this case, we will
        # not be looking this id up in the score, but only using it as a memo-ization key.
        self.metadata_item = id(self)
        self.key = key
        if isinstance(value, m21.metadata.Text):
            # Create a string representing both the text and the language, but not isTranslated,
            # since isTranslated cannot be represented in many file formats.
            self.value = (
                self.make_value_string(value)
                + f'(language={value.language})'
            )
            if isinstance(value, m21.metadata.Copyright):
                self.value += f' role={value.role}'
        elif isinstance(value, m21.metadata.Contributor):
            # Create a string (same thing: value.name.isTranslated will differ randomly)
            # Currently I am also ignoring more than one name, and birth/death.
            if not value._names:
                # ignore this metadata item
                self.key = ''
                self.value = ''
                return

            self.value = self.make_value_string(value)
            roleEmitted: bool = False
            if value.role:
                if value.role == 'poet':
                    # special case: many MusicXML files have the lyricist listed as the poet.
                    # We compare them as equivalent here.
                    lyr: str = 'lyricist'
                    self.key = lyr
                    self.value += f'(role={lyr}'
                else:
                    self.value += f'(role={value.role}'
                roleEmitted = True
            if value._names:
                if roleEmitted:
                    self.value += ', '
                self.value += f'language={value._names[0].language}'
            if roleEmitted:
                self.value += ')'
        else:
            # Date types
            self.value = str(value)

        self._cached_notation_size: int | None = None

    def __eq__(self, other) -> bool:
        if not isinstance(other, AnnMetadataItem):
            return False

        if self.key != other.key:
            return False

        if self.value != other.value:
            return False

        return True

    def readable_str(self, name: str = "", idx: int = 0, changedStr: str = "") -> str:
        return str(self)

    def __str__(self) -> str:
        return self.key + ':' + str(self.value)


    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # We use id(self), because there is no music21 object here.
        output: str = f"MetadataItem({self.metadata_item}):"
        output += self.key + ':' + str(self.value)
        return output

    def notation_size(self) -> int:
        """
        Compute a measure of how many symbols are displayed in the score for this `AnnMetadataItem`.

        Returns:
            int: The notation size of the annotated metadata item
        """
        if self._cached_notation_size is None:
            size: int = len(self.key)
            size += len(self.value)
            self._cached_notation_size = size
        return self._cached_notation_size

    def make_value_string(self, value: m21.metadata.Contributor | m21.metadata.Text) -> str:
        # Unescapes a bunch of stuff (and strips off leading/trailing whitespace)
        output: str = str(value)
        output = output.strip()
        output = html.unescape(output)
        return output


class AnnScore:
    def __init__(
        self,
        score: m21.stream.Score,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> None:
        """
        Take a music21 score and store it as a sequence of Full Trees.
        The hierarchy is "score -> parts -> measures -> voices -> notes"
        Args:
            score (music21.stream.Score): The music21 score
            detail (DetailLevel | int): What level of detail to use during the diff.
                Can be DecoratedNotesAndRests, OtherObjects, AllObjects, Default (currently
                AllObjects), or any combination (with | or &~) of those or NotesAndRests,
                Beams, Tremolos, Ornaments, Articulations, Ties, Slurs, Signatures,
                Directions, Barlines, StaffDetails, ChordSymbols, Ottavas, Arpeggios, Lyrics,
                Style, Metadata, or Voicing.
        """
        self.score: int | str = score.id
        self.part_list: list[AnnPart] = []
        self.staff_group_list: list[AnnStaffGroup] = []
        self.metadata_items_list: list[AnnMetadataItem] = []
        self.num_syntax_errors_fixed: int = 0

        if hasattr(score, "c21_syntax_errors_fixed"):
            self.num_syntax_errors = score.c21_syntax_errors_fixed  # type: ignore

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
            ann_part = AnnPart(part, score, idx, spannerBundle, detail)
            self.part_list.append(ann_part)

        self.n_of_parts: int = len(self.part_list)

        if DetailLevel.includesStaffDetails(detail):
            for staffGroup in score[m21.layout.StaffGroup]:
                # ignore any StaffGroup that contains all the parts, and has no symbol
                # and has no barthru (this is just a placeholder generated by some
                # file formats, and has the same meaning if it is missing).
                if len(staffGroup) == len(part_to_index):
                    if not staffGroup.symbol and not staffGroup.barTogether:
                        continue

                ann_staff_group = AnnStaffGroup(staffGroup, part_to_index, detail)
                if ann_staff_group.n_of_parts > 0:
                    self.staff_group_list.append(ann_staff_group)

            # now sort the staff_group_list in increasing order of first part index
            # (secondary sort in decreasing order of last part index)
            self.staff_group_list.sort(
                key=lambda each: (each.part_indices[0], -each.part_indices[-1])
            )

        if DetailLevel.includesMetadata(detail) and score.metadata:
            # m21 metadata.all() can't sort primitives, so we'll have to sort by hand.
            # Note: we sort metadata_items_list after the fact, because sometimes
            # (e.g. otherContributor:poet) we substitute names (e.g. lyricist:)
            allItems: list[tuple[str, t.Any]] = list(
                score.metadata.all(returnPrimitives=True, returnSorted=False)
            )
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
                if key in ('humdrum:EMD', 'humdrum:EST', 'humdrum:VTS',
                        'humdrum:RLN', 'humdrum:PUB'):
                    # Don't compare metadata items that should never be transferred
                    # from one file to another.  'humdrum:EMD' is a modification
                    # description entry, humdrum:EST is "current encoding status"
                    # (i.e. complete or some value of not complete), 'humdrum:VTS'
                    # is a checksum of the Humdrum file, 'humdrum:RLN' is the
                    # extended ASCII encoding of the Humdrum file, 'humdrum:PUB'
                    # is the publication status of the file (published or not?).
                    continue
                ami: AnnMetadataItem = AnnMetadataItem(key, value)
                if ami.key and ami.value:
                    self.metadata_items_list.append(ami)

            self.metadata_items_list.sort(key=lambda each: (each.key, str(each.value)))

        # cached notation size
        self._cached_notation_size: int | None = None

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
        if self._cached_notation_size is None:
            size: int = sum([p.notation_size() for p in self.part_list])
            size += sum([sg.notation_size() for sg in self.staff_group_list])
            size += sum([md.notation_size() for md in self.metadata_items_list])
            self._cached_notation_size = size
        return self._cached_notation_size

    def __repr__(self) -> str:
        # must include a unique id for memoization!
        # we use the music21 id of the score.
        output: str = f"Score({self.score}):"
        output += str(repr(p) for p in self.part_list)
        return output

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
