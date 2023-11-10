# ------------------------------------------------------------------------------
# Purpose:       m21utils is a set of music21 utilities for use by musicdiff.
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

from fractions import Fraction
import math
import sys
import copy
import typing as t
from enum import IntEnum

# import sys
import music21 as m21
from music21.common.types import OffsetQL

class DetailLevel(IntEnum):
    # Bit definitions are private:
    _GeneralNotes = 1
    _Extras = 2
    _Style = 4
    _Metadata = 8

    # Combinations are public (and supported on command line):

    # Chords, Notes, Rests, Unpitched, etc (and their beams/expressions/articulations)
    GeneralNotesOnly = _GeneralNotes

    # Add in the "extras": Clefs, TextExpressions, Key/KeySignatures, Barlines/Repeats,
    # TimeSignatures, TempoIndications, etc
    AllObjects = GeneralNotesOnly | _Extras

    # All of the above, plus typographical stuff: placement, stem direction,
    # color, italic/bold, Style, etc
    AllObjectsWithStyle = AllObjects | _Style

    # Various options that include Metadata:
    MetadataOnly = _Metadata
    GeneralNotesAndMetadata = GeneralNotesOnly | _Metadata
    AllObjectsAndMetadata = AllObjects | _Metadata
    AllObjectsWithStyleAndMetadata = AllObjectsWithStyle | _Metadata

    Default = AllObjects

    @classmethod
    def includesGeneralNotes(cls, val: int) -> bool:
        return val & cls._GeneralNotes != 0

    @classmethod
    def includesOtherMusicObjects(cls, val: int) -> bool:
        return val & cls._Extras != 0

    @classmethod
    def includesStyle(cls, val: int) -> bool:
        return val & cls._Style != 0

    @classmethod
    def includesMetadata(cls, val: int) -> bool:
        return val & cls._Metadata != 0


class M21Utils:
    @staticmethod
    def get_beamings(note_list: list[m21.note.GeneralNote]) -> list[list[str]]:
        _beam_list: list[list[str]] = []
        for n in note_list:
            if n.isRest:
                _beam_list.append([])
            else:
                if t.TYPE_CHECKING:
                    assert isinstance(n, m21.note.NotRest)
                _beam_list.append(n.beams.getTypes())
        return _beam_list


    @staticmethod
    def generalNote_to_string(gn: m21.note.GeneralNote) -> str:
        """
        Return the NoteString with R or N, notehead number and dots.
        Does not consider the ties (because of music21 ties encoding).
        Arguments:
            gn {music21 general note} -- [description]
        Returns:
            String -- the noteString
        """
        out_string = ""
        # add generalNote type (Rest or Note)
        if gn.isRest:
            out_string += "R"
        else:
            out_string += "N"
        # add notehead information (4,2,1,1/2, etc...).
        # 4 means a black note, 2 white, 1 whole etc...
        type_number = Fraction(m21.duration.convertTypeToNumber(gn.duration.type))
        if type_number >= 4:
            out_string += "4"
        else:
            out_string += str(type_number)
        # add the dot
        n_of_dots = gn.duration.dots
        for _ in range(n_of_dots):
            out_string += "*"
        return out_string

    @staticmethod
    def expression_to_string(
        expr: m21.expressions.Expression,
        detail: DetailLevel = DetailLevel.Default
    ) -> str:
        theName: str = ''
        placement: str | None = None

        # we customize name a bit for Turn/GeneralMordent/Trill, because we only want to
        # know about visible accidentals (i.e. with displayStatus == True).
        if isinstance(expr, m21.expressions.Turn):
            theName = expr.__class__.__name__
            theName = m21.common.camelCaseToHyphen(theName, replacement=' ')

            if expr.delay == m21.common.enums.OrnamentDelay.DEFAULT_DELAY:
                theName = 'delayed ' + theName
            elif isinstance(expr.delay, (float, Fraction)):
                theName = f'delayed(delayQL={expr.delay}) ' + theName

            upperAccidentalIsVisible: bool = (
                expr.upperAccidental is not None
                and expr.upperAccidental.displayStatus is True
            )
            if not upperAccidentalIsVisible:
                # check if someone (e.g. makeAccidentals) decided it should be visible anyway
                upperAccidentalIsVisible = (
                    expr.upperOrnamentalPitch is not None
                    and expr.upperOrnamentalPitch.accidental is not None
                    and expr.upperOrnamentalPitch.accidental.displayStatus is True
                )

            lowerAccidentalIsVisible: bool = (
                expr.lowerAccidental is not None
                and expr.lowerAccidental.displayStatus is True
            )
            if not lowerAccidentalIsVisible:
                # check if someone (e.g. makeAccidentals) decided it should be visible anyway
                lowerAccidentalIsVisible = (
                    expr.lowerOrnamentalPitch is not None
                    and expr.lowerOrnamentalPitch.accidental is not None
                    and expr.lowerOrnamentalPitch.accidental.displayStatus is True
                )

            if upperAccidentalIsVisible or lowerAccidentalIsVisible:
                theName += ' ('
                if upperAccidentalIsVisible:
                    if t.TYPE_CHECKING:
                        assert expr.upperAccidental is not None
                    theName += 'upper=' + expr.upperAccidental.name
                    if lowerAccidentalIsVisible:
                        theName += ', '
                if lowerAccidentalIsVisible:
                    if t.TYPE_CHECKING:
                        assert expr.lowerAccidental is not None
                    theName += 'lower=' + expr.lowerAccidental.name
                theName += ')'

            # if diffing style, include placement (None, "above", "below")
            if DetailLevel.includesStyle(detail):
                placement = None
                if hasattr(expr, 'placement'):
                    placement = getattr(expr, 'placement')
                elif expr.hasStyleInformation and hasattr(expr.style, 'placement'):
                    placement = getattr(expr.style, 'placement')
                if placement is not None:
                    theName = theName + '(' + placement + ')'

            return theName

        if isinstance(expr, (m21.expressions.GeneralMordent, m21.expressions.Trill)):
            theName = expr.__class__.__name__
            theName = m21.common.camelCaseToHyphen(theName, replacement=' ')

            accidentalIsVisible: bool = (
                expr.accidental is not None and expr.accidental.displayStatus is True
            )
            if not accidentalIsVisible:
                # check if someone (e.g. makeAccidentals) decided it should be visible anyway
                accidentalIsVisible = (
                    expr.ornamentalPitch is not None
                    and expr.ornamentalPitch.accidental is not None
                    and expr.ornamentalPitch.accidental.displayStatus is True
                )

            if accidentalIsVisible:
                if t.TYPE_CHECKING:
                    assert expr.accidental is not None
                theName += f' ({expr.accidental.name})'

            # if diffing style, include placement (None, "above", "below")
            if DetailLevel.includesStyle(detail):
                placement = None
                if hasattr(expr, 'placement'):
                    placement = getattr(expr, 'placement')
                elif expr.hasStyleInformation and hasattr(expr.style, 'placement'):
                    placement = getattr(expr.style, 'placement')
                if placement is not None:
                    theName = theName + '(' + placement + ')'

            return theName

        if isinstance(expr, m21.expressions.Tremolo):
            return M21Utils.tremolo_to_string(expr, detail)

        # all others just get expr.name
        theName = expr.name
        return theName

    @staticmethod
    def tremolo_to_string(
        expr: m21.expressions.Tremolo | m21.expressions.TremoloSpanner,
        detail: DetailLevel = DetailLevel.Default
    ) -> str:
        if isinstance(expr, m21.expressions.Tremolo):
            return 'bTrem'
        if isinstance(expr, m21.expressions.TremoloSpanner):
            return 'fTrem'
        return ''

    @staticmethod
    def articulation_to_string(
        artic: m21.articulations.Articulation,
        detail: DetailLevel = DetailLevel.Default
    ) -> str:
        theName: str = artic.name

        # if diffing style, include placement (None, "above", "below")
        if DetailLevel.includesStyle(detail):
            placement: str | None = None
            if hasattr(artic, 'placement'):
                placement = getattr(artic, 'placement')
            elif artic.hasStyleInformation and hasattr(artic.style, 'placement'):
                placement = getattr(artic.style, 'placement')
            if placement is not None:
                theName = theName + '(' + placement + ')'

        return theName

    @staticmethod
    def note2tuple(
        note: m21.note.Note | m21.note.Unpitched | m21.note.Rest,
        detail: DetailLevel = DetailLevel.Default
    ) -> tuple[str, str, bool]:
        note_pitch: str
        note_accidental: str
        note_tie: bool = False
        if isinstance(note, m21.note.Rest):
            note_pitch = "R"
            note_accidental = "None"
            if DetailLevel.includesStyle(detail):
                # Rest position is style, not substance, but check
                # that rest-position comparison hasn't been turned off
                TURN_OFF_REST_POSITION_COMPARISON: int = 0x10000000
                if detail & TURN_OFF_REST_POSITION_COMPARISON == 0:
                    # rest.stepShift is the number of lines/spaces above/below middle of staff.
                    # We can use it directly in our annotation.
                    if note.stepShift > 0:
                        note_pitch = f"R+{note.stepShift}"
                    elif note.stepShift < 0:
                        note_pitch = f"R{note.stepShift}"

        elif isinstance(note, m21.note.Unpitched):
            # use the displayName (e.g. 'G4') with no accidental
            note_pitch = note.displayName
            note_accidental = "None"
        else:
            # pitch name (including octave, but not accidental)
            note_pitch = note.pitch.step + str(note.pitch.octave)

            # note_accidental is only set to non-'None' if the accidental will
            # be visible in the printed score.
            note_accidental = "None"
            if note.pitch.accidental is None:
                pass
            elif note.pitch.accidental.displayStatus is not None:
                if note.pitch.accidental.displayStatus is True:
                    note_accidental = note.pitch.accidental.name
            else:
                # note.pitch.accidental.displayStatus was not set.
                # This can happen when there are no measures in the test data.
                # We will guess, based on displayType.
                # displayType can be 'normal', 'always', 'never', 'unless-repeated',
                # 'if-absolutely-necessary', 'even-tied'
                displayType: str | None = note.pitch.accidental.displayType
                if displayType is None:
                    displayType = "normal"

                if displayType in ("always", "even-tied"):
                    note_accidental = note.pitch.accidental.name
                elif displayType == "never":
                    note_accidental = "None"
                elif displayType in ("normal", "if-absolutely-necessary"):
                    # Complete guess: the accidental will be displayed
                    # This will be wrong if this is not the first such note in the measure.
                    note_accidental = note.pitch.accidental.name
                elif displayType == "unless-repeated":
                    # Guess that the note is not repeated
                    note_accidental = note.pitch.accidental.name

            # TODO: we should append editorial style info to note_accidental here ('paren', etc)

        # add tie information (Unpitched has this, too, but not Rest, and not meaningfully in
        # Chord either)
        if isinstance(note, (m21.note.Rest, m21.chord.ChordBase)):
            note_tie = False
        else:
            note_tie = note.tie is not None and note.tie.type in ("start", "continue")
        return (note_pitch, note_accidental, note_tie)


    @staticmethod
    def pitch_size(pitch: tuple[str, str, bool]) -> int:
        """Compute the size of a pitch.
        Arguments:
            pitch {[triple]} -- a triple (pitchname,accidental,tie)
        """
        size = 0
        # add for the pitchname
        size += 1
        # add for the accidental
        if not pitch[1] == "None":
            size += 1
        # add for the tie
        if pitch[2]:
            size += 1
        return size


    @staticmethod
    def generalNote_info(gn: m21.note.GeneralNote) -> dict[str, int | str | list]:
        """
        Get a json of informations about a general note.
        The fields of the json are
        type: ("chord", "rest", or "note"),
        pitches: list of pitch strings
        noteHead (also for rests): string
        dots: integer
        For rests the pitch is set to ['A0'].
        Does not consider the ties (because of music21 ties encoding).
        Arguments:
            gn {music21 general note} -- the general note to have the information
        """
        # pitches and type info
        pitches: list[tuple[str, m21.pitch.Accidental | None]]
        gn_type: str
        if isinstance(gn, m21.chord.ChordBase):
            gnPitches: tuple[m21.pitch.Pitch, ...] = gn.pitches
            if hasattr(gn, "sortDiatonicAscending"):
                gnPitches = gn.sortDiatonicAscending().pitches
            pitches = [
                (p.step + str(p.octave), p.accidental)
                for p in gnPitches
            ]
            gn_type = "chord"
        elif gn.isRest:
            pitches = [("A0", None)]  # pitch is set to ["A0"] for rests
            gn_type = "rest"
        elif isinstance(gn, m21.note.Note):
            pitches = [
                (gn.pitch.step + str(gn.pitch.octave), gn.pitch.accidental)
            ]  # a list with  one pitch inside
            gn_type = "note"
        else:
            raise TypeError("The generalNote must be a Chord, a Rest or a Note")

        # notehead information (4,2,1,1/2, etc...). 4 means a black note, 2 white, 1 whole etc...
        type_number = Fraction(m21.duration.convertTypeToNumber(gn.duration.type))
        if type_number >= 4:
            note_head = "4"
        else:
            note_head = str(type_number)

        gn_info: dict[str, int | str | list] = {
            "type": gn_type,
            "pitches": pitches,
            "noteHead": note_head,
            "dots": gn.duration.dots,
        }
        return gn_info


    # def get_ties(note_list):
    #     _general_ties_list = []
    #     for n in note_list:
    #         if n.tie == None:
    #             _general_ties_list.append(None)
    #         else:
    #             _general_ties_list.append(n.tie.type)
    #     # keep only the information of when a note is tied to the previous
    #     # (also we solve the bad notation of having a start and a not specified
    #     # stop, that can happen in music21)
    #     _ties_list = [False] * len(_general_ties_list)
    #     for i, t in enumerate(_general_ties_list):
    #         if t == 'start' and i < len(_ties_list) - 1:
    #             _ties_list[i + 1] = True
    #         elif t == 'continue' and i < len(_ties_list) - 1:
    #             _ties_list[i + 1] = True
    #             if i == 0: # we can have a continue in first note if tie is from previous bar
    #                 _ties_list[i] = True
    #         elif t == 'stop':
    #             if i == 0: # we can have a stop in first note if tie is from previous bar
    #                 _ties_list[i] = True
    #             else:
    #                 # assert (_ties_list[i] == True)  # don't reject wrong scores
    #                 _ties_list[i] = True
    #     return _ties_list


    @staticmethod
    def get_type_num(duration: m21.duration.Duration) -> float:
        typeStr: str = duration.type
        if typeStr == 'complex':
            typeStr = m21.duration.quarterLengthToClosestType(duration.quarterLength)[0]
        typeNum: float = m21.duration.convertTypeToNumber(typeStr)
        return typeNum

    @staticmethod
    def get_type_nums(note_list: list[m21.note.GeneralNote]) -> list[float]:
        _type_list: list[float] = []
        for n in note_list:
            _type_list.append(M21Utils.get_type_num(n.duration))
        return _type_list


    @staticmethod
    def get_rest_or_note(note_list: list[m21.note.GeneralNote]) -> list[str]:
        _rest_or_note: list[str] = []
        for n in note_list:
            if n.isRest:
                _rest_or_note.append("R")
            else:
                _rest_or_note.append("N")
        return _rest_or_note


    @staticmethod
    def get_enhance_beamings(note_list: list[m21.note.GeneralNote]) -> list[list[str]]:
        """
        Create a mod_beam_list that take into account also the single notes with a type > 4
        """
        _beam_list: list[list[str]] = M21Utils.get_beamings(note_list)
        _type_list: list[float] = M21Utils.get_type_nums(note_list)
        _mod_beam_list: list[list[str]] = M21Utils.get_beamings(note_list)
        # add informations for rests and notes not grouped
        for i, n in enumerate(_beam_list):
            if len(n) == 0:
                rangeEnd: int | None = None
                if _type_list[i] != 0:
                    rangeEnd = int(math.log(_type_list[i] / 4, 2))
                if rangeEnd is None:
                    continue

                for ii in range(0, rangeEnd):
                    if (
                        note_list[i].isRest
                        and len(_beam_list) > i + 1
                        and len(_beam_list[i + 1]) > ii
                        and (
                            _beam_list[i + 1][ii] == "continue"
                            or _beam_list[i + 1][ii] == "stop"
                        )
                    ):  # in case of "beamed" rests, the next note is beamed at the same level):
                        _mod_beam_list[i].append("continue")
                    else:
                        _mod_beam_list[i].append("partial")
        # change the single "start" and "stop" with partial (since MEI parser is
        # not working properly)
        new_mod_beam_list: list[list[str]] = _mod_beam_list.copy()
        max_beam_len: int = max([len(t) for t in _mod_beam_list])
        for beam_depth in range(max_beam_len):
            for note_index in range(len(_mod_beam_list)):
                if (
                    M21Utils.safe_get(
                        _mod_beam_list[note_index], beam_depth
                    ) == "start"
                    and M21Utils.safe_get(
                        M21Utils.safe_get(_mod_beam_list, note_index + 1), beam_depth
                    ) is None
                ):
                    new_mod_beam_list[note_index][beam_depth] = "partial"
                elif (
                    M21Utils.safe_get(
                        _mod_beam_list[note_index], beam_depth
                    ) == "stop"
                    and M21Utils.safe_get(
                        M21Utils.safe_get(_mod_beam_list, note_index - 1), beam_depth
                    ) is None
                ):
                    new_mod_beam_list[note_index][beam_depth] = "partial"
                elif (
                    M21Utils.safe_get(
                        _mod_beam_list[note_index], beam_depth
                    ) == "continue"
                    and M21Utils.safe_get(
                        M21Utils.safe_get(_mod_beam_list, note_index - 1), beam_depth
                    ) is None
                    and M21Utils.safe_get(
                        M21Utils.safe_get(_mod_beam_list, note_index + 1), beam_depth
                    ) is None
                ):
                    new_mod_beam_list[note_index][beam_depth] = "partial"
                elif (
                    M21Utils.safe_get(
                        _mod_beam_list[note_index], beam_depth
                    ) == "continue"
                    and M21Utils.safe_get(
                        M21Utils.safe_get(_mod_beam_list, note_index - 1), beam_depth
                    ) is None
                    and M21Utils.safe_get(
                        M21Utils.safe_get(_mod_beam_list, note_index + 1), beam_depth
                    ) is not None
                ):
                    new_mod_beam_list[note_index][beam_depth] = "start"

        return new_mod_beam_list


    @staticmethod
    def get_dots(note_list: list[m21.note.GeneralNote]) -> list[int]:
        return [n.duration.dots for n in note_list]


    @staticmethod
    def get_durations(note_list: list[m21.note.GeneralNote]) -> list[Fraction]:
        return [Fraction(n.duration.quarterLength) for n in note_list]


    @staticmethod
    def get_norm_durations(note_list: list[m21.note.GeneralNote]) -> list[Fraction]:
        dur_list = M21Utils.get_durations(note_list)
        sum_dur_list = sum(dur_list)
        if sum_dur_list == 0:
            raise ValueError("It's not possible to normalize the durations if the sum is 0")
        return [d / sum_dur_list for d in dur_list]  # normalize the duration


    @staticmethod
    def get_tuplets(
        note_list: list[m21.note.GeneralNote]
    ) -> list[tuple[m21.duration.Tuplet, ...]]:
        return [n.duration.tuplets for n in note_list]


    @staticmethod
    def get_tuplets_info(
        note_list: list[m21.note.GeneralNote],
        detail: DetailLevel = DetailLevel.Default
    ) -> list[list[str]]:
        """
        for each note return a list of tuple(str, str) with the tuplet type string and a string
        representation of what is visible.
        """
        str_list: list[list[str]] = []
        for n in note_list:
            tuplet_info_list_for_note: list[str] = []
            for tup in n.duration.tuplets:
                if tup.type == "start":
                    # music21 only pays attention to number and bracket visibility/placement
                    # on the start note of a tuplet.
                    if tup.tupletActualShow in ("number", "both"):
                        if tup.tupletNormalShow in ("number", "both"):
                            new_info = str(tup.numberNotesActual) + ":" + str(tup.numberNotesNormal)
                        else:  # just a number for the tuplets
                            new_info = str(tup.numberNotesActual)
                    else:
                        if tup.tupletNormalShow in ("number", "both"):
                            new_info = ":" + str(tup.numberNotesNormal)
                        else:  # no number shown
                            new_info = ""
                    # if the brackets are drawn explicitly, add B
                    if tup.bracket:
                        new_info = new_info + "B"
                    # if diffing style, include placement (None, "above", "below")
                    if DetailLevel.includesStyle(detail):
                        if tup.placement is not None:
                            new_info = new_info + tup.placement
                    tuplet_info_list_for_note.append(new_info)
            str_list.append(tuplet_info_list_for_note)
        return str_list


    @staticmethod
    def get_tuplets_type(
        note_list: list[m21.note.GeneralNote]
    ) -> list[list[str]]:
        """
        for each note return a list of tuple(str, str), with the first string filled in with
        the type of the tuplets for the note
        """
        tuplets_list: list[list[str | None]] = [
            [tup.type for tup in n.duration.tuplets] for n in note_list  # type: ignore
        ]
        new_tuplets_list = tuplets_list.copy()

        # now correct the missing of "start" and add "continue" for clarity
        max_tupl_len = max([len(t) for t in tuplets_list])
        for ii in range(max_tupl_len):
            start_index = None
            # stop_index = None
            for i, note_tuplets in enumerate(tuplets_list):
                if len(note_tuplets) > ii:
                    if note_tuplets[ii] == "start":
                        # Some medieval music has weirdly nested triplets that
                        # end up in music21 with two starts in a row.
                        start_index = ii
                    elif note_tuplets[ii] is None:
                        # replace any None with "start" or "continue"
                        if start_index is None:
                            start_index = ii
                            new_tuplets_list[i][ii] = "start"
                        else:
                            new_tuplets_list[i][ii] = "continue"
                    elif note_tuplets[ii] in ("stop", "startStop"):
                        start_index = None
                    else:
                        raise TypeError("Invalid tuplet type")
        # we have replaced any None with "start" or "continue"
        return t.cast(list[list[str]], new_tuplets_list)


    @staticmethod
    def get_notes(
        measureOrVoice: m21.stream.Measure | m21.stream.Voice,
        allowGraceNotes=False
    ) -> list[m21.note.GeneralNote]:
        """
        :param measureOrVoice: a music21 measure or voice
        :return: a list of (visible) notes, eventually excluding grace notes, inside the measure
        """
        out = []
        if allowGraceNotes:
            for n in measureOrVoice.getElementsByClass('GeneralNote'):
                if not n.style.hideObjectOnPrint:
                    out.append(n)
        else:
            for n in measureOrVoice.getElementsByClass('GeneralNote'):
                if not n.style.hideObjectOnPrint and n.duration.quarterLength != 0:
                    out.append(n)
        return out


    @staticmethod
    def get_notes_and_gracenotes(
        measureOrVoice: m21.stream.Measure | m21.stream.Voice
    ) -> list[m21.note.GeneralNote]:
        """
        :param measureOrVoice: a music21 measure or voice
        :return: a list of visible notes, including grace notes, inside the measure
        """
        out: list[m21.note.GeneralNote] = []
        for n in measureOrVoice.getElementsByClass('GeneralNote'):
            if not n.style.hideObjectOnPrint:
                out.append(n)
        return out

    @staticmethod
    def getHighestDiatonicNoteOrChord(
        arpeggio: m21.expressions.ArpeggioMarkSpanner
    ) -> m21.note.NotRest:
        if hasattr(arpeggio, 'musicdiff_cached_highest_diatonic_element'):
            return arpeggio.musicdiff_cached_highest_diatonic_element  # type: ignore

        origSpannedList: list[m21.note.NotRest] = arpeggio.getSpannedElements()
        nrList: list[m21.note.NotRest] = copy.deepcopy(origSpannedList)
        highestNoteOrChord: m21.note.NotRest
        highestNote: m21.note.Note
        for i, (nr, origSpanned) in enumerate(zip(nrList, origSpannedList)):
            currentNote: m21.note.Note
            if isinstance(nr, m21.chord.Chord):
                # set currentNote to the highest diatonic note in the chord
                nr.sortDiatonicAscending()
                currentNote = nr.notes[-1]
            else:
                if t.TYPE_CHECKING:
                    # because you don't see arpeggios on Unpitched
                    assert isinstance(nr, m21.note.Note)
                currentNote = nr
            if i == 0:
                highestNote = currentNote
                highestNoteOrChord = origSpanned
            elif currentNote.pitch.diatonicNoteNum > highestNote.pitch.diatonicNoteNum:
                highestNote = currentNote
                highestNoteOrChord = origSpanned

        arpeggio.musicdiff_cached_highest_diatonic_element = highestNoteOrChord  # type: ignore
        return highestNoteOrChord

    @staticmethod
    def getPrimarySpannerElement(
        sp: m21.spanner.Spanner
    ) -> m21.note.GeneralNote | m21.spanner.SpannerAnchor:
        # returns sp.getFirst() except if the spanner is ArpeggioMarkSpanner, in
        # which case it returns the element that contains the highest diatonic
        # pitch.
        if not isinstance(sp, m21.expressions.ArpeggioMarkSpanner):
            return sp.getFirst()
        return M21Utils.getHighestDiatonicNoteOrChord(sp)

    @staticmethod
    def clefs_are_equivalent(
        clef1: m21.clef.Clef | None,
        clef2: m21.clef.Clef | None
    ) -> bool:
        if not isinstance(clef1, m21.clef.Clef):
            return False
        if not isinstance(clef2, m21.clef.Clef):
            return False

        if clef1.sign != clef2.sign:
            return False
        if clef1.line != clef2.line:
            return False
        if clef1.octaveChange != clef2.octaveChange:
            return False

        return True

    @staticmethod
    def get_extras(
        measure: m21.stream.Measure,
        part: m21.stream.Part,
        spannerBundle: m21.spanner.SpannerBundle,
        detail: DetailLevel = DetailLevel.Default
    ) -> list[m21.base.Music21Object]:
        # returns a list of every object contained in the measure (and in the measure's
        # substreams/Voices), skipping any Streams, and GeneralNotes (which are returned
        # from get_notes/get_notes_and_gracenotes).  We're looking for things like Clefs,
        # TextExpressions, and Dynamics...
        output: list[m21.base.Music21Object] = []
        initialList: list[m21.base.Music21Object]
        initialList = list(
            measure.recurse().getElementsNotOfClass(
                (m21.note.GeneralNote,
                 m21.spanner.SpannerAnchor,
                 m21.stream.Stream,
                 m21.spanner.Spanner)
            )
        )

        # Sort the initialList by offset in measure, so we can see which clefs are
        # duplicates from different voices.
        if len(initialList) > 1:
            for el in initialList:
                el.musicdiff_offset_in_measure = el.getOffsetInHierarchy(measure)  # type: ignore
            initialList.sort(key=lambda el: el.musicdiff_offset_in_measure)  # type: ignore

        # loop over the initialList, filtering out (and complaining about) things we
        # don't recognize.  Also, we filter out hidden (non-printed) extras.  And
        # barlines of type 'none' (also not printed).
        # We also try to de-duplicate redundant clefs.
        mostRecentClef: m21.clef.Clef | None = None
        for el in initialList:
            # we ignore hidden extras
            if el.hasStyleInformation and el.style.hideObjectOnPrint:
                continue
            if isinstance(el, m21.bar.Barline) and el.type == 'none':
                continue
            if M21Utils.extra_to_string(el, detail) == '':
                continue
            if isinstance(el, m21.clef.Clef):
                # If this clef is the same as the most recent clef seen in this
                # measure (i.e. with no different clef between them), ignore
                # this one.  It not, use this one, and make a note of it as the
                # most recent clef.

                # Clef __eq__ compares class, sign, line, and octaveShift.
                # I don't want to include class in this, since I would like
                # clef.TrebleClef() == clef.GClef(line=2) to evaluate to True.
                if M21Utils.clefs_are_equivalent(el, mostRecentClef):
                    # ignore this clef
                    continue

                mostRecentClef = el

            output.append(el)

        # Add any interesting spanners that start on GeneralNotes/SpannerAnchors in this measure
        spanner_types = (
            m21.expressions.ArpeggioMarkSpanner,
            m21.dynamics.DynamicWedge,
            m21.spanner.Ottava,
            m21.expressions.TremoloSpanner
        )

        spannerElementClasses = (m21.note.GeneralNote, m21.spanner.SpannerAnchor)

        for gn in measure.recurse().getElementsByClass(spannerElementClasses):
            spannerList: list[m21.spanner.Spanner] = gn.getSpannerSites(spanner_types)
            for sp in spannerList:
                if sp not in spannerBundle:
                    continue
                if M21Utils.getPrimarySpannerElement(sp) is gn:
                    output.append(sp)
                    if not isinstance(sp, m21.spanner.Ottava):
                        continue

        # Add any RepeatBracket spanners that start on this measure
        rbList: list[m21.spanner.Spanner] = measure.getSpannerSites([m21.spanner.RepeatBracket])
        for rb in rbList:
            if rb not in spannerBundle:
                continue
            if rb.isFirst(measure):
                output.append(rb)

        return output

    @staticmethod
    def fillOttava(
        ottava: m21.spanner.Ottava,
        searchStream: m21.stream.Stream,
        *,
        includeEndBoundary: bool = False,
        mustFinishInSpan: bool = False,
        mustBeginInSpan: bool = True,
        includeElementsThatEndAtStart: bool = False
    ) -> None:
        if ottava.filledStatus is True:
            # Don't fill twice.
            return

        if ottava.getFirst() is None:
            # no spanned elements?  Nothing to fill.
            return

        endElement: m21.base.Music21Object | None = None
        if len(ottava) > 1:
            # Start and end elements are different, we can't just append everything, we need
            # to save off the end element, remove it, add everything, then add the end element
            # again.  Note that if there are actually more than 2 elements before we start
            # filling, the new intermediate elements will come after the existing ones,
            # regardless of offset.  But first and last will still be the same two elements
            # as before, which is the most important thing.
            endElement = ottava.getLast()
            if t.TYPE_CHECKING:
                assert endElement is not None
            ottava.spannerStorage.remove(endElement)

        try:
            startOffsetInHierarchy: OffsetQL = ottava.getFirst().getOffsetInHierarchy(searchStream)
        except m21.sites.SitesException:
            # print('start element not in searchStream')
            if endElement is not None:
                ottava.addSpannedElements(endElement)
            return

        endOffsetInHierarchy: OffsetQL
        if endElement is not None:
            try:
                endOffsetInHierarchy = (
                    endElement.getOffsetInHierarchy(searchStream) + endElement.quarterLength
                )
            except m21.sites.SitesException:
                # print('end element not in searchStream')
                ottava.addSpannedElements(endElement)
                return
        else:
            endOffsetInHierarchy = (
                ottava.getLast().getOffsetInHierarchy(searchStream)
                + ottava.getLast().quarterLength
            )

        for foundElement in (searchStream
                .recurse()
                .getElementsByOffsetInHierarchy(
                    startOffsetInHierarchy,
                    endOffsetInHierarchy,
                    includeEndBoundary=includeEndBoundary,
                    mustFinishInSpan=mustFinishInSpan,
                    mustBeginInSpan=mustBeginInSpan,
                    includeElementsThatEndAtStart=includeElementsThatEndAtStart)
                .getElementsByClass(m21.note.NotRest)):
            if endElement is None or foundElement is not endElement:
                ottava.addSpannedElements(foundElement)

        if endElement is not None:
            # add it back in as the end element
            ottava.addSpannedElements(endElement)

        ottava.filledStatus = True  # type: ignore

    @staticmethod
    def note_to_string(note: m21.note.GeneralNote) -> str:
        if note.isRest:
            _str = "R"
        else:
            _str = "N"
        return _str

    @staticmethod
    def safe_get(indexable, idx):
        if indexable is None:
            out = None
        elif 0 <= idx < len(indexable):
            out = indexable[idx]
        else:
            out = None
        return out

    @staticmethod
    def clef_to_string(clef: m21.clef.Clef) -> str:
        # sign(str), line(int), octaveChange(int == # octaves to shift up(+) or down(-))
        sign: str = '' if clef.sign is None else clef.sign
        line: str = '0' if clef.line is None else f'{clef.line}'
        octave: str = '' if clef.octaveChange == 0 else f'{8 * clef.octaveChange:+}'
        output: str = f'CL:{sign}{line}{octave}'
        return output

    @staticmethod
    def timesig_to_string(timesig: m21.meter.TimeSignature) -> str:
        output: str = ''

        if not timesig.symbol:
            output = f'TS:{timesig.numerator}/{timesig.denominator}'
        elif timesig.symbol in ('common', 'cut'):
            output = f'TS:{timesig.symbol}'
        elif timesig.symbol == 'single-number':
            output = f'TS:{timesig.numerator}'
        else:
            output = f'TS:{timesig.numerator}/{timesig.denominator}'

        return output

    @staticmethod
    def tempo_to_string(mm: m21.tempo.TempoIndication) -> str:
        # pylint: disable=protected-access
        # We need direct access to mm._textExpression and mm._tempoText, to avoid
        # the extra formatting that referencing via the .text property will perform.
        output: str = ''
        if isinstance(mm, m21.tempo.TempoText):
            if mm._textExpression is None:
                output = 'MM:'
            else:
                output = f'MM:{M21Utils.extra_to_string(mm._textExpression)}'
            return output

        if isinstance(mm, m21.tempo.MetricModulation):
            # convert to MetronomeMark
            mm = mm.newMetronome

        # mm must be a MetronomeMark if we get here.
        if t.TYPE_CHECKING:
            assert isinstance(mm, m21.tempo.MetronomeMark)
        if mm.textImplicit is True or mm._tempoText is None:
            if mm.referent is None or mm.number is None:
                output = 'MM:'
            else:
                output = f'MM:{mm.referent.fullName}={float(mm.number)}'
            return output

        if mm.numberImplicit is True or mm.number is None:
            if mm._tempoText is None:
                output = 'MM:'
            else:
                # no 'MM:' prefix, TempoText adds their own
                output = f'{M21Utils.tempo_to_string(mm._tempoText)}'
            return output

        # no 'MM:' prefix, TempoText adds their own
        output = (
            f'{M21Utils.tempo_to_string(mm._tempoText)}'
            + f' {mm.referent.fullName}={float(mm.number)}'
        )
        return output
        # pylint: enable=protected-access

    @staticmethod
    def barline_to_string(barline: m21.bar.Barline) -> str:
        # for all Barlines: type, pause
        # for Repeat Barlines: direction, times
        pauseStr: str = ''
        if barline.pause is not None:
            if isinstance(barline.pause, m21.expressions.Fermata):
                pauseStr = f' with fermata({barline.pause.type},{barline.pause.shape})'
            else:
                pauseStr = ' with pause (non-fermata)'

        output: str = f'{barline.type}{pauseStr}'
        if not isinstance(barline, m21.bar.Repeat):
            return f'BL:{output}'

        # add the Repeat fields (direction, times)
        if barline.direction is not None:
            output += f' direction={barline.direction}'
        if barline.times is not None:
            output += f' times={barline.times}'
        return f'RPT:{output}'

    @staticmethod
    def ottava_to_string(ottava: m21.spanner.Ottava) -> str:
        output: str = f'OTT:{ottava.type}'
        return output

    @staticmethod
    def keysig_to_string(keysig: m21.key.Key | m21.key.KeySignature) -> str:
        output: str = f'KS:{keysig.sharps}'
        return output

    @staticmethod
    def textexp_to_string(textexp: m21.expressions.TextExpression) -> str:
        output: str = f'TX:{textexp.content}'
        return output

    @staticmethod
    def dynamic_to_string(dynamic: m21.dynamics.Dynamic) -> str:
        output: str = f'DY:{dynamic.value}'
        return output

    @staticmethod
    def notestyle_to_dict(
        style: m21.style.NoteStyle,
        detail: DetailLevel = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}

        if style.stemStyle is not None:
            output['stemstyle'] = M21Utils.genericstyle_to_dict(style.stemStyle)

        if style.accidentalStyle is not None:
            output['accidstyle'] = M21Utils.genericstyle_to_dict(style.accidentalStyle)

        if style.noteSize:
            output['size'] = style.noteSize

        return output

    @staticmethod
    def textstyle_to_dict(
        style: m21.style.TextStyle,
        detail: DetailLevel = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}

        if isinstance(style, m21.style.TextStylePlacement) and style.placement:
            output['placement'] = style.placement
        if style.fontFamily:
            output['fontFamily'] = style.fontFamily
        if style.fontSize is not None:
            output['fontSize'] = style.fontSize
        if style.fontStyle is not None and style.fontStyle != 'normal':
            output['fontStyle'] = style.fontStyle
        if style.fontWeight is not None and style.fontWeight != 'normal':
            output['fontWeight'] = style.fontWeight
        if style.letterSpacing is not None and style.letterSpacing != 'normal':
            output['letterSpacing'] = style.letterSpacing
        if style.lineHeight:
            output['lineHeight'] = style.lineHeight
        if style.textDirection:
            output['textDirection'] = style.textDirection
        if style.textRotation:
            output['textRotation'] = style.textRotation
        if style.language:
            output['language'] = style.language
        if style.textDecoration:
            output['textDecoration'] = style.textDecoration
        if style.justify:
            output['justify'] = style.justify
        if style.alignHorizontal:
            output['alignHorizontal'] = style.alignHorizontal
        if style.alignVertical:
            output['alignVertical'] = style.alignVertical

        return output

    @staticmethod
    def genericstyle_to_dict(
        style: m21.style.Style,
        detail: DetailLevel = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}
        if style.size is not None:
            output['size'] = style.size
        if style.relativeX is not None:
            output['relX'] = style.relativeX
        if style.relativeY is not None:
            output['relY'] = style.relativeY
        if style.absoluteX is not None:
            output['absX'] = style.absoluteX
        if style.absoluteY is not None:
            output['absY'] = style.absoluteY
        if style.enclosure is not None:
            output['encl'] = style.enclosure
        if style.fontRepresentation is not None:
            output['fontrep'] = style.fontRepresentation
        if style.color is not None:
            output['color'] = style.color
        if style.units != 'tenths':
            output['units'] = style.units
        if style.hideObjectOnPrint:
            output['hidden'] = True
        return output

    @staticmethod
    def specificstyle_to_dict(
        style: m21.style.Style,
        detail: DetailLevel = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        if isinstance(style, m21.style.NoteStyle):
            return M21Utils.notestyle_to_dict(style, detail)
        if isinstance(style, m21.style.TextStyle):
            # includes TextStylePlacement
            return M21Utils.textstyle_to_dict(style, detail)
        if isinstance(style, m21.style.BezierStyle):
            return {}  # M21Utils.bezierstyle_to_dict(style, detail)
        if isinstance(style, m21.style.LineStyle):
            return {}  # M21Utils.linestyle_to_dict(style, detail)
        if isinstance(style, m21.style.BeamStyle):
            return {}  # M21Utils.beamstyle_to_dict(style, detail)
        return {}

    @staticmethod
    def obj_to_styledict(
        obj: m21.base.Music21Object | m21.style.StyleMixin,
        detail: DetailLevel = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}
        if obj.hasStyleInformation:
            output = M21Utils.genericstyle_to_dict(obj.style, detail)
            specific = M21Utils.specificstyle_to_dict(obj.style, detail)
            for k, v in specific.items():
                output[k] = v

        if hasattr(obj, 'placement') and obj.placement is not None:
            if 'placement' in output:
                # style was a TextStylePlacement, with placement specified
                print('placement specified twice, taking the one in .style', file=sys.stderr)
            else:
                output['placement'] = obj.placement

        return output

    @staticmethod
    def dynwedge_to_string(dynwedge: m21.dynamics.DynamicWedge) -> str:
        output: str = ''
        if isinstance(dynwedge, m21.dynamics.Crescendo):
            output = '<'
        elif isinstance(dynwedge, m21.dynamics.Diminuendo):
            output = '>'
        else:
            output = 'wedge'
        return f'DY:{output}'

    @staticmethod
    def arpeggiomark_to_string(
        arp: m21.expressions.ArpeggioMark | m21.expressions.ArpeggioMarkSpanner
    ) -> str:
        if isinstance(arp, m21.expressions.ArpeggioMark):
            return f'ARP:{arp.type}'
        if isinstance(arp, m21.expressions.ArpeggioMarkSpanner):
            return f'ARPS:{arp.type}:len={len(arp)}'
        return ''

    @staticmethod
    def repeatbracket_to_string(rb: m21.spanner.RepeatBracket) -> str:
        if rb.overrideDisplay:
            return f'END:{rb.number,rb.overrideDisplay}:len={len(rb)}'
        else:
            return f'END:{rb.number}:len={len(rb)}'

    @staticmethod
    def stafflayout_to_string(
        sl: m21.layout.StaffLayout,
        detail: DetailLevel = DetailLevel.Default
    ) -> str:
        output: str = ''
        if sl.staffLines is not None:
            if not output:
                output = 'STAFF:'
            output += f'lines={sl.staffLines}'
        if DetailLevel.includesStyle(detail):
            if sl.staffSize is not None:
                if not output:
                    output = 'STAFF:'
                else:
                    output += ','
                output += f'size={sl.staffSize:.2g}%'
        return output

    @staticmethod
    def systemlayout_to_string(sb: m21.layout.SystemLayout) -> str:
        if sb.isNew:
            return 'SB'
        return ''

    @staticmethod
    def pagelayout_to_string(pb: m21.layout.PageLayout) -> str:
        if pb.isNew:
            if pb.pageNumber is not None:
                return f'PB:num={pb.pageNumber}'
            return 'PB'
        return ''

    @staticmethod
    def extra_to_string(
        extra: m21.base.Music21Object,
        detail: DetailLevel = DetailLevel.Default
    ) -> str:
        if isinstance(extra, (m21.key.Key, m21.key.KeySignature)):
            return M21Utils.keysig_to_string(extra)
        if isinstance(extra, m21.expressions.TextExpression):
            return M21Utils.textexp_to_string(extra)
        if isinstance(extra, m21.dynamics.Dynamic):
            return M21Utils.dynamic_to_string(extra)
        if isinstance(extra, m21.dynamics.DynamicWedge):
            return M21Utils.dynwedge_to_string(extra)
        if isinstance(extra, m21.clef.Clef):
            return M21Utils.clef_to_string(extra)
        if isinstance(extra, m21.meter.TimeSignature):
            return M21Utils.timesig_to_string(extra)
        if isinstance(extra, m21.tempo.TempoIndication):
            return M21Utils.tempo_to_string(extra)
        if isinstance(extra, m21.bar.Barline):
            return M21Utils.barline_to_string(extra)
        if isinstance(extra, m21.spanner.Ottava):
            return M21Utils.ottava_to_string(extra)
        if isinstance(extra, m21.spanner.RepeatBracket):
            return M21Utils.repeatbracket_to_string(extra)
        if isinstance(extra, m21.expressions.TremoloSpanner):
            return M21Utils.tremolo_to_string(extra)
        if isinstance(extra, m21.layout.StaffLayout):
            return M21Utils.stafflayout_to_string(extra, detail)
        if isinstance(
                extra,
                (m21.expressions.ArpeggioMark, m21.expressions.ArpeggioMarkSpanner)):
            return M21Utils.arpeggiomark_to_string(extra)

        # Page breaks and system breaks are only paid attention to at
        # DetailLevel.AllObjectsWithStyle, because they are entirely
        # style, no substance.
        if DetailLevel.includesStyle(detail):
            if isinstance(extra, m21.layout.SystemLayout):
                return M21Utils.systemlayout_to_string(extra)
            if isinstance(extra, m21.layout.PageLayout):
                return M21Utils.pagelayout_to_string(extra)

        # print(f'Unexpected extra: {extra.classes[0]}', file=sys.stderr)
        return ''

    @staticmethod
    def has_style(obj: m21.base.Music21Object | m21.style.StyleMixin) -> bool:
        output: bool = hasattr(obj, 'placement') and obj.placement is not None
        output = output or obj.hasStyleInformation
        return output
