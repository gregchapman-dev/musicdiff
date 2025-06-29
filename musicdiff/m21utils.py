# ------------------------------------------------------------------------------
# Purpose:       m21utils is a set of music21 utilities for use by musicdiff.
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

from fractions import Fraction
import math
import sys
import copy
import re
import typing as t

# import sys
import music21 as m21
from music21.common import OffsetQL, opFrac

from converter21 import M21Utilities

from musicdiff import DetailLevel

class M21Utils:
    @staticmethod
    def get_beamings(
        note_list: list[m21.note.GeneralNote],
        detail: DetailLevel | int
    ) -> list[list[str]]:
        _beam_list: list[list[str]] = []
        for n in note_list:
            if n.isRest:
                _beam_list.append([])
            else:
                if t.TYPE_CHECKING:
                    assert isinstance(n, m21.note.NotRest)
                if DetailLevel.includesBeams(detail):
                    _beam_list.append(n.beams.getTypes())
                else:
                    type_num: float = M21Utils.get_type_num(n.duration)
                    nFlags: int = int(math.log(type_num / 4, 2))
                    flags: list[str] = ["partial"] * nFlags
                    _beam_list.append(flags)
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
        detail: DetailLevel | int = DetailLevel.Default
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
            # TODO: we probably need full string, symbolic, infodict for expressions.
            # For now (because some tremolos are also extras) we call symbolic here,
            # to get the one-symbol representation of the tremolo.
            return M21Utils.tremolo_to_symbolic(expr, detail=detail)

        if isinstance(expr, m21.expressions.TextExpression):
            te: str | None = M21Utils.textexp_to_string(expr, M21Utils.extra_to_kind(expr))
            return te or ''

        # all others just get expr.name
        theName = expr.name
        return theName

    @staticmethod
    def tremolo_to_string(
        expr: m21.expressions.Tremolo | m21.expressions.TremoloSpanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def tremolo_to_symbolic(
        expr: m21.expressions.Tremolo | m21.expressions.TremoloSpanner,
        kind: str = 'tremolo',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str:
        if isinstance(expr, m21.expressions.Tremolo):
            return 'bTrem'
        if isinstance(expr, m21.expressions.TremoloSpanner):
            return 'fTrem'
        return ''

    @staticmethod
    def tremolo_to_infodict(
        expr: m21.expressions.Tremolo | m21.expressions.TremoloSpanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def articulation_to_string(
        artic: m21.articulations.Articulation,
        detail: DetailLevel | int = DetailLevel.Default
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
        detail: DetailLevel | int = DetailLevel.Default
    ) -> tuple[str, str, bool]:
        note_pitch: str
        note_accidental: str
        note_tie: bool = False
        if isinstance(note, m21.note.Rest):
            note_pitch = "R"
            note_accidental = "None"
            if DetailLevel.includesStyle(detail):
                # Rest position is style, not substance
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

        if DetailLevel.includesTies(detail):
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
    def get_enhance_beamings(
        note_list: list[m21.note.GeneralNote],
        detail: DetailLevel | int
    ) -> list[list[str]]:
        """
        Create a mod_beam_list that take into account also the single notes with a type > 4
        """
        _beam_list: list[list[str]] = M21Utils.get_beamings(note_list, detail)
        _type_list: list[float] = M21Utils.get_type_nums(note_list)
        if not DetailLevel.includesBeams(detail):
            # _beam_list has "partial" for every flag, no fixups required
            return _beam_list

        # return an actual (fixed up) beam list
        _mod_beam_list: list[list[str]] = copy.copy(_beam_list)

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
        new_mod_beam_list: list[list[str]] = copy.copy(_mod_beam_list)
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
        detail: DetailLevel | int = DetailLevel.Default
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
                    # on the start note of a tuplet.  TODO: Should I pass in/use result of
                    # get_tuplets_type?  It has more (implied) starts than the actual tuplets do.
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
                else:
                    # notes that don't start a tuplet have no info that anyone looks at
                    tuplet_info_list_for_note.append("")
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
        new_tuplets_list = copy.deepcopy(tuplets_list)

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
    def get_notes_and_gracenotes(
        measureOrVoice: m21.stream.Measure | m21.stream.Voice,
        recurse: bool = False
    ) -> list[m21.note.GeneralNote]:
        """
        :param measureOrVoice: a music21 measure or voice
        :return: a list of visible notes, including grace notes, inside the measure
        """
        out: list[m21.note.GeneralNote] = []
        gnIterator: m21.stream.iterator.StreamIterator | m21.stream.iterator.RecursiveIterator
        if recurse:
            gnIterator = measureOrVoice.recurse().getElementsByClass('GeneralNote')
        else:
            gnIterator = measureOrVoice.getElementsByClass('GeneralNote')

        for n in gnIterator:
            if n.style.hideObjectOnPrint:
                continue
            if isinstance(n, m21.harmony.ChordSymbol):
                # skip ChordSymbols (they are extras, not notes)
                continue
            out.append(n)

        return out

    @staticmethod
    def get_lyrics_holders(measure: m21.stream.Measure) -> list[m21.note.GeneralNote]:
        out: list[m21.note.GeneralNote] = []
        for n in M21Utils.get_notes_and_gracenotes(measure, recurse=True):
            if n.lyrics:
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
    ) -> m21.base.Music21Object:
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
    def extra_is_ignored(
        el: m21.base.Music21Object,
        kind: str,
        measure: m21.stream.Measure,
        part: m21.stream.Part,
        score: m21.stream.Score,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> bool:
        if el.hasStyleInformation and el.style.hideObjectOnPrint:
            # we ignore all invisible objects
            return True

        if kind in ('direction', 'tempo', 'staffinfo'):
            # we ignore empty TextExpressions/MetronomeMarks/StaffLayouts
            if M21Utils.extra_to_string(el, kind, detail):
                # not empty, don't ignore
                return False
            if M21Utils.extra_to_symbolic(el, kind, detail):
                # not empty, don't ignore
                return False
            if M21Utils.extra_to_infodict(el, kind, detail):
                # not empty, don't ignore
                return False
            # definitely empty, ignore
            return True

        if kind in ('pedalbounce', 'pedalgapstart', 'pedalgapend'):
            # we ignore these if they are not in a PedalMark spanner
            for sp in el.getSpannerSites():
                # pylint: disable=no-member
                if isinstance(sp, m21.expressions.PedalMark):  # type: ignore
                    return False
                # pylint: enable=no-member
            return True

        if isinstance(el, (m21.layout.PageLayout, m21.layout.SystemLayout)):
            # we ignore PageLayouts and SystemLayouts that are not in the
            # first Part in the Score.
            if part is not score.parts[0]:
                return True
            # we also ignore (for the moment) anything that doesn't represent
            # a page break or a system break
            if not el.isNew:
                return True

        if isinstance(el, m21.bar.Barline):
            if el.type == 'none':
                # we ignore hidden barlines
                return True

            barlineOffset: OffsetQL = el.musicdiff_offset_in_measure  # type: ignore
            if ((barlineOffset in (0, measure.duration.quarterLength))
                    and el.type == 'regular'
                    and el.pause is None
                    and not el.hasStyleInformation):
                # we ignore unadorned regular left or right barlines (since
                # that's what no left or right barline at all means)
                return True

        return False

    @staticmethod
    def get_extras(
        measure: m21.stream.Measure,
        part: m21.stream.Part,
        score: m21.stream.Score,
        spannerBundle: m21.spanner.SpannerBundle,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> list[m21.base.Music21Object]:
        # returns a list of every object contained in the measure (and in the measure's
        # substreams/Voices), skipping any Streams, and GeneralNotes (which are returned
        # from get_notes_and_gracenotes).  We're looking for things like Clefs,
        # TextExpressions, and Dynamics...
        output: list[m21.base.Music21Object] = []
        initialList: list[m21.base.Music21Object]
        initialList = list(
            measure.recurse().getElementsNotOfClass(
                (m21.note.GeneralNote,
                 m21.meter.SenzaMisuraTimeSignature,  # no timesig
                 m21.spanner.SpannerAnchor,
                 m21.stream.Stream,
                 m21.spanner.Spanner)
            )
        )

        # ChordSym is derived from GeneralNote, so we have to go look for it separately
        initialList.extend(
            list(measure.recurse().getElementsByClass(m21.harmony.ChordSymbol))
        )

        # Sort the initialList by offset in measure, so we can see which clefs are
        # duplicates from different voices. We use el.musicdiff_offset_in_measure
        # later, so compute it even if list is of length 1.
        for el in initialList:
            el.musicdiff_offset_in_measure = el.getOffsetInHierarchy(measure)  # type: ignore
        if len(initialList) > 1:
            initialList.sort(key=lambda el: el.musicdiff_offset_in_measure)  # type: ignore

        # loop over the initialList, filtering out things we don't recognize or are
        # not requested in the detail argument. Also, we filter out hidden (non-printed)
        # extras.  And right/left barlines of type 'regular' with no interesting details
        # (because no right/left barline at all in music21 means a regular, uninteresting
        # barline). Note that we ignore all invisible barlines as well (el.type == 'none')
        # since they are non-printed.  We also try to de-duplicate redundant clefs.
        mostRecentClef: m21.clef.Clef | None = None
        for el in initialList:
            if not DetailLevel.objIsIncluded(el, detail):
                # ignore objects that were not requested
                continue

            kind: str = M21Utils.extra_to_kind(el)
            if kind == '':
                # skip unrecognized extras.
                continue

            if M21Utils.extra_is_ignored(el, kind, measure, part, score, detail):
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

        # Add any requested spanners that start on GeneralNotes/SpannerAnchors in this measure
        spanner_types: list[t.Type] = []
        if DetailLevel.includesSlurs(detail):
            spanner_types.append(m21.spanner.Slur)
        if DetailLevel.includesArpeggios(detail):
            spanner_types.append(m21.expressions.ArpeggioMarkSpanner)
        if DetailLevel.includesDirections(detail):
            spanner_types.append(m21.dynamics.DynamicWedge)
            if M21Utilities.m21PedalMarksSupported():
                spanner_types.append(m21.expressions.PedalMark)  # type: ignore
        if DetailLevel.includesOttavas(detail):
            spanner_types.append(m21.spanner.Ottava)
        if DetailLevel.includesTremolos(detail):
            spanner_types.append(m21.expressions.TremoloSpanner)

        spannerElementClasses: tuple[type, ...]
        if M21Utilities.m21PedalMarksSupported():
            spannerElementClasses = (
                m21.note.GeneralNote,
                m21.spanner.SpannerAnchor,
                m21.expressions.PedalBounce,  # type: ignore
                m21.expressions.PedalGapStart,  # type: ignore
                m21.expressions.PedalGapEnd,  # type: ignore
            )
        else:
            spannerElementClasses = (
                m21.note.GeneralNote,
                m21.spanner.SpannerAnchor
            )

        for gn in measure.recurse().getElementsByClass(spannerElementClasses):
            spannerList: list[m21.spanner.Spanner] = gn.getSpannerSites(spanner_types)
            for sp in spannerList:
                if sp not in spannerBundle:
                    continue
                if M21Utils.getPrimarySpannerElement(sp) is gn:
                    output.append(sp)

        if DetailLevel.includesDirections(detail):
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
    def extra_to_kind(extra: m21.base.Music21Object) -> str:
        if isinstance(extra, m21.clef.Clef):
            return 'clef'
        if isinstance(extra, m21.meter.TimeSignature):
            return 'timesig'
        if isinstance(extra, m21.tempo.TempoIndication):
            return 'tempo'
        if isinstance(extra, m21.bar.Barline):
            if isinstance(extra, m21.bar.Repeat):
                return 'repeat'
            return 'barline'
        if isinstance(extra, m21.spanner.Ottava):
            return 'ottava'
        if isinstance(extra, m21.key.KeySignature):
            return 'keysig'
        if isinstance(extra, m21.expressions.TextExpression):
            return 'direction'
        if isinstance(extra, m21.dynamics.Dynamic):
            return 'dynamic'
        if isinstance(extra, m21.dynamics.Crescendo):
            return 'crescendo'
        if isinstance(extra, m21.dynamics.Diminuendo):
            return 'diminuendo'
        if isinstance(extra, m21.spanner.Slur):
            return 'slur'
        if isinstance(extra, (m21.expressions.ArpeggioMark, m21.expressions.ArpeggioMarkSpanner)):
            return 'arpeggio'
        if isinstance(extra, m21.harmony.ChordSymbol):
            return 'chordsym'
        if isinstance(extra, m21.spanner.RepeatBracket):
            return 'ending'
        if isinstance(extra, m21.layout.StaffLayout):
            return 'staffinfo'
        if isinstance(extra, m21.layout.SystemLayout):
            return 'systembreak'
        if isinstance(extra, m21.layout.PageLayout):
            return 'pagebreak'
        if isinstance(extra, (m21.expressions.Tremolo, m21.expressions.TremoloSpanner)):
            return 'tremolo'
        if isinstance(extra, m21.expressions.RehearsalMark):
            return 'rehearsalmark'

        if not M21Utilities.m21PedalMarksSupported():
            return ''

        # pylint: disable=no-member
        if isinstance(extra, m21.expressions.PedalMark):  # type: ignore
            return 'pedalmark'
        # the following pedal objects will be ignored if they are not contained in a
        # PedalMark spanner.
        if (isinstance(extra, m21.expressions.PedalBounce)  # type: ignore
                and M21Utils.is_in_pedalmark(extra)):
            return 'pedalbounce'
        if (isinstance(extra, m21.expressions.PedalGapStart)  # type: ignore
                and M21Utils.is_in_pedalmark(extra)):
            return 'pedalgapstart'
        if (isinstance(extra, m21.expressions.PedalGapEnd)  # type: ignore
                and M21Utils.is_in_pedalmark(extra)):
            return 'pedalgapend'
        # pylint: enable=no-member

        return ''

    # pylint: disable=no-member
    @staticmethod
    def get_enclosing_pedalmark(
        # pt: m21.expressions.PedalTransition
        pt: m21.base.Music21Object
    ) -> m21.spanner.Spanner | None:  # m21.expressions.PedalMark | None:
        if not M21Utilities.m21PedalMarksSupported():
            return None

        pm: m21.expressions.PedalMark | None = None  # type: ignore
        ss: list[m21.spanner.Spanner] = (
            pt.getSpannerSites((m21.expressions.PedalMark,))  # type: ignore
        )
        if ss:
            if t.TYPE_CHECKING:
                assert isinstance(ss[0], m21.expressions.PedalMark)  # type: ignore
            pm = ss[0]
        return pm

    @staticmethod
    def is_in_pedalmark(
        # pt: m21.expressions.PedalTransition
        pt: m21.base.Music21Object
    ) -> bool:  # type: ignore
        if not M21Utilities.m21PedalMarksSupported():
            return False

        return M21Utils.get_enclosing_pedalmark(pt) is not None
    # pylint: enable=no-member

    @staticmethod
    def extra_to_symbolic(
        extra: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if kind == 'clef':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.clef.Clef)
            return M21Utils.clef_to_symbolic(extra, kind, detail)
        if kind == 'timesig':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.meter.TimeSignature)
            return M21Utils.timesig_to_symbolic(extra, kind, detail)
        if kind == 'tempo':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.tempo.TempoIndication)
            return M21Utils.tempo_to_symbolic(extra, kind, detail)
        if kind in ('barline', 'repeat'):
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.bar.Barline)
            return M21Utils.barline_to_symbolic(extra, kind, detail)
        if kind == 'ottava':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.spanner.Ottava)
            return M21Utils.ottava_to_symbolic(extra, kind, detail)
        if kind == 'keysig':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.key.KeySignature)
            return M21Utils.keysig_to_symbolic(extra, kind, detail)
        if kind == 'direction':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.TextExpression)
            return M21Utils.textexp_to_symbolic(extra, kind, detail)
        if kind == 'dynamic':
            if t.TYPE_CHECKING:
                assert isinstance(extra, (m21.dynamics.Dynamic, m21.dynamics.DynamicWedge))
            return M21Utils.dynamic_to_symbolic(extra, kind, detail)
        if kind == 'slur':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.spanner.Slur)
            return M21Utils.slur_to_symbolic(extra, kind, detail)
        if kind == 'arpeggio':
            if t.TYPE_CHECKING:
                assert isinstance(
                    extra,
                    (m21.expressions.ArpeggioMark, m21.expressions.ArpeggioMarkSpanner)
                )
            return M21Utils.arpeggio_to_symbolic(extra, kind, detail)
        if kind == 'chordsym':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.harmony.ChordSymbol)
            return M21Utils.chordsym_to_symbolic(extra, kind, detail)
        if kind == 'ending':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.spanner.RepeatBracket)
            return M21Utils.repeatbracket_to_symbolic(extra, kind, detail)
        if kind == 'staffinfo':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.layout.StaffLayout)
            return M21Utils.staffinfo_to_symbolic(extra, kind, detail)
        if kind == 'systembreak':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.layout.SystemLayout)
            return M21Utils.systembreak_to_symbolic(extra, kind, detail)
        if kind == 'pagebreak':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.layout.PageLayout)
            return M21Utils.pagebreak_to_symbolic(extra, kind, detail)
        if kind == 'tremolo':
            if t.TYPE_CHECKING:
                assert isinstance(extra, (m21.expressions.Tremolo, m21.expressions.TremoloSpanner))
            return M21Utils.tremolo_to_symbolic(extra, kind, detail)
        if kind == 'rehearsalmark':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.RehearsalMark)
            return M21Utils.rehearsalmark_to_symbolic(extra, kind, detail)
        if not M21Utilities.m21PedalMarksSupported():
            return None

        if kind == 'pedalmark':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalMark)  # type: ignore
            return M21Utils.pedalmark_to_symbolic(extra, kind, detail)
        if kind == 'pedalbounce':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalBounce)  # type: ignore
            return M21Utils.pedalbounce_to_symbolic(extra, kind, detail)
        if kind == 'pedalgapstart':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalGapStart)  # type: ignore
            return M21Utils.pedalgapstart_to_symbolic(extra, kind, detail)
        if kind == 'pedalgapend':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalGapEnd)  # type: ignore
            return M21Utils.pedalgapend_to_symbolic(extra, kind, detail)

        return None

    @staticmethod
    def extra_to_infodict(
        extra: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        if kind == 'clef':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.clef.Clef)
            return M21Utils.clef_to_infodict(extra, kind, detail)
        if kind == 'timesig':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.meter.TimeSignature)
            return M21Utils.timesig_to_infodict(extra, kind, detail)
        if kind == 'tempo':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.tempo.TempoIndication)
            return M21Utils.tempo_to_infodict(extra, kind, detail)
        if kind in ('barline', 'repeat'):
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.bar.Barline)
            return M21Utils.barline_to_infodict(extra, kind, detail)
        if kind == 'ottava':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.spanner.Ottava)
            return M21Utils.ottava_to_infodict(extra, kind, detail)
        if kind == 'keysig':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.key.KeySignature)
            return M21Utils.keysig_to_infodict(extra, kind, detail)
        if kind == 'direction':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.TextExpression)
            return M21Utils.textexp_to_infodict(extra, kind, detail)
        if kind == 'dynamic':
            if t.TYPE_CHECKING:
                assert isinstance(extra, (m21.dynamics.Dynamic, m21.dynamics.DynamicWedge))
            return M21Utils.dynamic_to_infodict(extra, kind, detail)
        if kind == 'slur':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.spanner.Slur)
            return M21Utils.slur_to_infodict(extra, kind, detail)
        if kind == 'arpeggio':
            if t.TYPE_CHECKING:
                assert isinstance(
                    extra,
                    (m21.expressions.ArpeggioMark, m21.expressions.ArpeggioMarkSpanner)
                )
            return M21Utils.arpeggio_to_infodict(extra, kind, detail)
        if kind == 'chordsym':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.harmony.ChordSymbol)
            return M21Utils.chordsym_to_infodict(extra, kind, detail)
        if kind == 'ending':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.spanner.RepeatBracket)
            return M21Utils.repeatbracket_to_infodict(extra, kind, detail)
        if kind == 'staffinfo':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.layout.StaffLayout)
            return M21Utils.staffinfo_to_infodict(extra, kind, detail)
        if kind == 'systembreak':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.layout.SystemLayout)
            return M21Utils.systembreak_to_infodict(extra, kind, detail)
        if kind == 'pagebreak':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.layout.PageLayout)
            return M21Utils.pagebreak_to_infodict(extra, kind, detail)
        if kind == 'tremolo':
            if t.TYPE_CHECKING:
                assert isinstance(extra, (m21.expressions.Tremolo, m21.expressions.TremoloSpanner))
            return M21Utils.tremolo_to_infodict(extra, kind, detail)
        if kind == 'rehearsalmark':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.RehearsalMark)
            return M21Utils.rehearsalmark_to_infodict(extra, kind, detail)

        if not M21Utilities.m21PedalMarksSupported():
            return {}

        if kind == 'pedalmark':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalMark)  # type: ignore
            return M21Utils.pedalmark_to_infodict(extra, kind, detail)
        if kind == 'pedalbounce':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalBounce)  # type: ignore
            return M21Utils.pedalbounce_to_infodict(extra, kind, detail)
        if kind == 'pedalgapstart':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalGapStart)  # type: ignore
            return M21Utils.pedalgapstart_to_infodict(extra, kind, detail)
        if kind == 'pedalgapend':
            if t.TYPE_CHECKING:
                assert isinstance(extra, m21.expressions.PedalGapEnd)  # type: ignore
            return M21Utils.pedalgapend_to_infodict(extra, kind, detail)

        return {}

    @staticmethod
    def extra_to_offset_and_duration(
        extra: m21.base.Music21Object,
        kind: str,
        measure: m21.stream.Measure,
        score: m21.stream.Score,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> tuple[OffsetQL | None, OffsetQL | None]:
        offset: OffsetQL | None = None
        duration: OffsetQL | None = None

        if isinstance(extra, m21.spanner.Spanner):
            firstNote: m21.base.Music21Object = M21Utils.getPrimarySpannerElement(extra)
            lastNote: m21.base.Music21Object = extra.getLast()

            offset = firstNote.getOffsetInHierarchy(measure)
            # to compute duration we need to use offset-in-score, since the end note might
            # be in another Measure.  Except for arpeggios, where the duration
            # isn't relevant.
            if kind != 'arpeggio':
                startOffsetInScore: OffsetQL = firstNote.getOffsetInHierarchy(score)
                try:
                    endOffsetInScore: OffsetQL = opFrac(
                        lastNote.getOffsetInHierarchy(score) + lastNote.duration.quarterLength
                    )
                except m21.sites.SitesException:
                    endOffsetInScore = startOffsetInScore
                duration = opFrac(endOffsetInScore - startOffsetInScore)
        elif kind in ('barline', 'repeat'):
            # we ignore offset and duration for barlines and repeats; barline offset is
            # derived from the objects in the measure, which are already being compared.
            pass
        elif kind in ('chordsym', 'ending', 'direction',
                'clef', 'keysig', 'timesig', 'tempo', 'dynamic',
                'staffinfo', 'systembreak', 'pagebreak',
                'rehearsalmark', 'pedalbounce',
                'pedalgapstart', 'pedalgapend'):
            # we ignore duration for ChordSymbols, it is often 0.0 or 1.0, and meaningless.
            # we also ignore duration for endings (RepeatBrackets).  We count how many measures
            # instead.  Several other things just don't have duration (timesig, dynamic, etc).
            # Note that 'dynamic' does not include 'crescendo' and 'diminuendo', just 'fff' et al.
            offset = extra.getOffsetInHierarchy(measure)
        else:
            offset = extra.getOffsetInHierarchy(measure)
            duration = extra.duration.quarterLength

        return offset, duration

    @staticmethod
    def clef_to_string(
        clef: m21.clef.Clef,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def clef_to_symbolic(
        clef: m21.clef.Clef,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        # sign(str), line(int), octaveChange(int == # octaves to shift up(+) or down(-))
        sign: str = '' if clef.sign is None else clef.sign
        line: str = '0' if clef.line is None else f'{clef.line}'
        octave: str = '' if clef.octaveChange == 0 else f'{8 * clef.octaveChange:+}'
        output: str = f'{sign}{line}{octave}'
        return output

    @staticmethod
    def clef_to_infodict(
        clef: m21.clef.Clef,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def timesig_to_string(
        timesig: m21.meter.TimeSignature,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def timesig_to_symbolic(
        timesig: m21.meter.TimeSignature,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def timesig_to_infodict(
        timesig: m21.meter.TimeSignature,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}

        if not timesig.symbol:
            output['numerator'] = f'{timesig.numerator}'
            output['denominator'] = f'{timesig.denominator}'
        elif timesig.symbol in ('common', 'cut'):
            output['symbol'] = f'{timesig.symbol}'
        elif timesig.symbol == 'single-number':
            output['numerator'] = f'{timesig.numerator}'
        else:
            output['numerator'] = f'{timesig.numerator}'
            output['denominator'] = f'{timesig.denominator}'

        return output

    @staticmethod
    def tempo_to_string(
        mm: m21.tempo.TempoIndication,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        # pylint: disable=protected-access
        # We need direct access to mm._textExpression and mm._tempoText, to avoid
        # the extra formatting that referencing via the .text property will perform.
        output: str | None = None
        if isinstance(mm, m21.tempo.TempoText):
            if mm._textExpression is None:
                output = None
            else:
                output = f'{M21Utils.extra_to_string(mm._textExpression, kind, detail)}'
            return output

        if isinstance(mm, m21.tempo.MetricModulation):
            # convert to MetronomeMark
            mm = mm.newMetronome

        # mm must be a MetronomeMark if we get here.
        if t.TYPE_CHECKING:
            assert isinstance(mm, m21.tempo.MetronomeMark)

        # ignore "playback only" metronome marks (they are not printed)
        if not mm.text and (not mm.number or mm.numberImplicit):
            return None

        # special case: numberImplicit is True, and non-implicit text is of the form:
        # SMUFLNoteCode = nnn (with no leading text).
        # We annotate this just like f'{mm.referent.fullName}={float(mm.number)}',
        # but getting the fullName and number from parsing the text.
        if mm.numberImplicit is True and mm.textImplicit is False:
            noteFullName: str | None = None
            number: float | int | None = None
            noteFullName, number = M21Utils.parse_note_equal_num(mm.text)
            if noteFullName is not None and number is not None:
                # not a string, it's symbolic
                return None

        if mm.textImplicit is True or mm._tempoText is None:
            # not a string, it's symbolic
            return None

        if mm.numberImplicit is True or mm.number is None:
            if mm._tempoText is None:
                output = None
            else:
                output = f'{M21Utils.tempo_to_string(mm._tempoText, kind, detail)}'
            return output

        # it's both a string (_tempoText) and symbolic (fullName=number)
        output = f'{M21Utils.tempo_to_string(mm._tempoText, kind, detail)}'
        return output
        # pylint: enable=protected-access

    @staticmethod
    def tempo_to_symbolic(
        mm: m21.tempo.TempoIndication,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        output: str | None = ''
        if isinstance(mm, m21.tempo.TempoText):
            # just text, no symbolic
            return None

        if isinstance(mm, m21.tempo.MetricModulation):
            # convert to MetronomeMark
            mm = mm.newMetronome

        # mm must be a MetronomeMark if we get here.
        if t.TYPE_CHECKING:
            assert isinstance(mm, m21.tempo.MetronomeMark)

        # ignore "playback only" metronome marks (they are not printed)
        if not mm.text and (not mm.number or mm.numberImplicit):
            return None

        # special case: numberImplicit is True, and non-implicit text is of the form:
        # SMUFLNoteCode = nnn (with no leading text).
        # We annotate this just like f'{mm.referent.fullName}={float(mm.number)}',
        # but getting the fullName and number from parsing the text.
        if mm.numberImplicit is True and mm.textImplicit is False:
            noteFullName: str | None = None
            number: float | int | None = None
            noteFullName, number = M21Utils.parse_note_equal_num(mm.text)
            if noteFullName is not None and number is not None:
                output = f'{noteFullName}={float(number)}'
                return output

        if mm.textImplicit is True or mm._tempoText is None:
            if mm.referent is None or mm.number is None:
                output = None
            else:
                output = f'{mm.referent.fullName}={float(mm.number)}'
            return output

        if mm.numberImplicit is True or mm.number is None:
            return None

        # it's both a string (_tempoText) and symbolic (fullName=number)
        output = f'{mm.referent.fullName}={float(mm.number)}'
        return output

    @staticmethod
    def tempo_to_infodict(
        mm: m21.tempo.TempoIndication,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def parse_note_equal_num(text: str | None) -> tuple[str | None, float | int | None]:
        if not text:
            return None, None

        from converter21.shared import SharedConstants
        THIN_SPACE: str = chr(0x2009)
        HAIR_SPACE: str = chr(0x200A)
        NBSP: str = chr(0x00A0)
        SPACES: tuple[str, ...] = (' ', '\t', THIN_SPACE, HAIR_SPACE, NBSP)

        # First strip out any spaces (including NBSP, THINSPACE,  and HAIRSPACE)
        # (look for any SMUFL notes at the same time; bail if you find none)
        smuflNoteFound: bool = False
        strippedText: str = ''
        for i, char in enumerate(text):
            if not smuflNoteFound:
                if char in SharedConstants.SMUFL_METRONOME_MARK_NOTE_CHARS_TO_HUMDRUM_NOTE_NAME:
                    smuflNoteFound = True

            if char in SPACES:
                # skip all types of spaces
                continue

            strippedText += char

        if not smuflNoteFound:
            return None, None

        # The entire string must now be:
        # 1-5 SMUFL chars (quad-dotted note would be five chars), '=', int or float
        PATTERN: str = r'^(.{1,5})=(\d+(?:\.\d*)?)$'
        m = re.match(PATTERN, strippedText)
        if m is None:
            return None, None

        smuflNote: str | None = None
        num: float | None = None
        try:
            smuflNote = m.group(1)
            num = float(m.group(2))
        except Exception:
            return None, None

        if not smuflNote:
            return None, None

        # smuflNote must be a single note (SMUFL) char followed by a series of
        # (SMUFL) metAugmentationDot chars
        for i, char in enumerate(smuflNote):
            if i == 0:
                if char not in (
                    SharedConstants.SMUFL_METRONOME_MARK_NOTE_CHARS_TO_MUSIC21_FULL_NAME
                ):
                    return None, None
                continue

            if char != SharedConstants.SMUFL_NAME_TO_UNICODE_CHAR['metAugmentationDot']:
                return None, None

        fullName: str = (
            SharedConstants.SMUFL_METRONOME_MARK_NOTE_CHARS_TO_MUSIC21_FULL_NAME[smuflNote[0]]
        )

        if len(smuflNote) == 2:
            fullName = 'Dotted ' + fullName
        elif len(smuflNote) == 3:
            fullName = 'Double Dotted ' + fullName
        elif len(smuflNote) == 4:
            fullName = 'Triple Dotted ' + fullName
        elif len(smuflNote) == 5:
            fullName = 'Quadruple Dotted ' + fullName

        return fullName, num

    @staticmethod
    def barline_to_string(
        barline: m21.bar.Barline,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def barline_to_symbolic(
        barline: m21.bar.Barline,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return f'{barline.type}'

    @staticmethod
    def barline_to_infodict(
        barline: m21.bar.Barline,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        # each element is one symbol
        output: dict[str, str] = {}

        # for all Barlines: type, fermata
        # for Repeat Barlines: direction, times
        if isinstance(barline.pause, m21.expressions.Fermata):
            output['fermata'] = f'type={barline.pause.type}'  # e.g. 'inverted'
            if barline.pause.shape != 'normal':
                # weird shape counts as another symbol
                output['fermatashape'] = f'{barline.pause.shape}'

        if isinstance(barline, m21.bar.Repeat):
            # add the Repeat fields (direction, times)
            if barline.direction is not None:
                output['repeatdirection'] = f'{barline.direction}'
            if barline.times is not None:
                output['repeatcount'] = f'{barline.times}'
        return output

    @staticmethod
    def ottava_to_string(
        ottava: m21.spanner.Ottava,
        kind: str = 'ottava',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def ottava_to_symbolic(
        ottava: m21.spanner.Ottava,
        kind: str = 'ottava',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        output: str = f'{ottava.type}'
        return output

    @staticmethod
    def ottava_to_infodict(
        ottava: m21.spanner.Ottava,
        kind: str = 'ottava',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def keysig_to_string(
        keysig: m21.key.Key | m21.key.KeySignature,
        kind: str = 'keysig',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def keysig_to_symbolic(
        keysig: m21.key.Key | m21.key.KeySignature,
        kind: str = 'keysig',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    FLAT_NAMES: list[str] = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
    SHARP_NAMES: list[str] = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

    @staticmethod
    def keysig_to_infodict(
        keysig: m21.key.Key | m21.key.KeySignature,
        kind: str = 'keysig',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        if keysig.sharps == 0:
            # can't ignore this, because it might be displayed
            # with naturals, but music21 can't tell.  Give it one
            # symbol.
            output['flats/sharps'] = 'none'
        elif keysig.sharps < 0:
            for i in range(0, -keysig.sharps):
                output[f'flat{i}'] = M21Utils.FLAT_NAMES[i % 7]
        else:
            for i in range(0, keysig.sharps):
                output[f'sharp{i}'] = M21Utils.SHARP_NAMES[i % 7]

        return output

    @staticmethod
    def textexp_to_string(
        textexp: m21.expressions.TextExpression,
        kind: str = 'direction',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if textexp.content is None:
            return None
        return textexp.content.strip()

    @staticmethod
    def textexp_to_symbolic(
        textexp: m21.expressions.TextExpression,
        kind: str = 'direction',
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def textexp_to_infodict(
        textexp: m21.expressions.TextExpression,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def dynamic_to_string(
        dynamic: m21.dynamics.Dynamic | m21.dynamics.DynamicWedge,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def dynamic_to_symbolic(
        dynamic: m21.dynamics.Dynamic | m21.dynamics.DynamicWedge,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if isinstance(dynamic, m21.dynamics.Dynamic):
            return f'{dynamic.value.strip()}'
        if isinstance(dynamic, m21.dynamics.DynamicWedge):
            if isinstance(dynamic, m21.dynamics.Crescendo):
                return None
            if isinstance(dynamic, m21.dynamics.Diminuendo):
                return None
            return 'wedge'  # shouldn't happen
        return None  # shouldn't happen

    @staticmethod
    def dynamic_to_infodict(
        dynamic: m21.dynamics.Dynamic | m21.dynamics.DynamicWedge,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def rehearsalmark_to_string(
        expr: m21.expressions.RehearsalMark,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if expr.content is None:
            return None
        return expr.content.strip()

    @staticmethod
    def rehearsalmark_to_symbolic(
        expr: m21.expressions.RehearsalMark,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str:
        return ''

    @staticmethod
    def rehearsalmark_to_infodict(
        expr: m21.expressions.RehearsalMark,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    # pylint: disable=no-member
    @staticmethod
    def pedalmark_to_string(
        # expr: m21.expressions.PedalMark,
        expr: m21.spanner.Spanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return ''

    @staticmethod
    def pedalmark_to_symbolic(
        # expr: m21.expressions.PedalMark,
        expr: m21.spanner.Spanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str:
        return ''

    @staticmethod
    def pedalmark_to_infodict(
        # expr: m21.expressions.PedalMark,
        expr: m21.spanner.Spanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        if expr.pedalType != m21.expressions.PedalType.Unspecified:  # type: ignore
            output['pedalType'] = expr.pedalType  # type: ignore

        if expr.startForm in (  # type: ignore
                m21.expressions.PedalForm.PedalName,  # type: ignore
                m21.expressions.PedalForm.Ped):  # type: ignore
            if expr.startForm == m21.expressions.PedalForm.PedalName:  # type: ignore
                if expr.pedalType == m21.expressions.PedalType.Sostenuto:  # type: ignore
                    output['start'] = 'Sost.'
                else:
                    output['start'] = 'Ped.'
            elif expr.startForm == m21.expressions.PedalForm.Ped:  # type: ignore
                output['start'] = 'Ped.'

            if expr.continueLine in (  # type: ignore
                    m21.expressions.PedalLine.Line,   # type: ignore
                    m21.expressions.PedalLine.Dashed):  # type: ignore
                if expr.continueLine in m21.expressions.PedalLine.Dashed:  # type: ignore
                    output['line'] = expr.continueLine  # type: ignore
                output['end'] = 'line'
            else:
                output['end'] = '*'
        elif expr.startForm == m21.expressions.PedalForm.VerticalLine:  # type: ignore
            output['start'] = 'line'
            output['end'] = 'line'
            if expr.continueLine in (  # type: ignore
                    m21.expressions.PedalLine.Dashed,   # type: ignore
                    m21.expressions.PedalLine.NoLine):  # type: ignore
                # only annotate unexpected continueLine
                output['line'] = expr.continueLine  # type: ignore
        else:
            # startForm is unspecified or makes no sense, so ignored.
            # Either way, we have nothing to annotate about visual form.
            # output['start'] = 'unspecified'
            # output['end'] = 'unspecified'
            pass

        if expr.abbreviated:  # type: ignore
            output['abbreviated'] = 'yes'
        return output

    @staticmethod
    def pedalbounce_to_string(
        # expr: m21.expressions.PedalBounce,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return ''

    @staticmethod
    def pedalbounce_to_symbolic(
        # expr: m21.expressions.PedalBounce,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str:
        return ''

    @staticmethod
    def pedalbounce_to_infodict(
        # expr: m21.expressions.PedalBounce,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        pm = M21Utils.get_enclosing_pedalmark(expr)
        if pm is not None:
            bounceUp: m21.expressions.PedalForm = expr.bounceUp  # type: ignore
            bounceDown: m21.expressions.PedalForm = expr.bounceDown  # type: ignore
            if m21.expressions.PedalForm.SlantedLine in (bounceUp, bounceDown):  # type: ignore
                output['bounce'] = 'caret'
            elif bounceUp == m21.expressions.PedalForm.NoMark:  # type: ignore
                if (pm.pedalType == m21.expressions.PedalType.Sostenuto  # type: ignore
                        and pm.pedalForm == m21.expressions.PedalName):  # type: ignore
                    output['bounceDown'] = 'Sost.'
                else:
                    output['bounceDown'] = 'Ped.'
            else:
                output['bounceUp'] = '*'
                if (pm.pedalType == m21.expressions.PedalType.Sostenuto  # type: ignore
                        and pm.pedalForm == m21.expressions.PedalName):  # type: ignore
                    output['bounceDown'] = 'Sost.'
                else:
                    output['bounceDown'] = 'Ped.'

        return output

    @staticmethod
    def pedalgapstart_to_string(
        # expr: m21.expressions.PedalGapStart,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return ''

    @staticmethod
    def pedalgapstart_to_symbolic(
        # expr: m21.expressions.PedalGapStart,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str:
        output: str = ''
        pm = M21Utils.get_enclosing_pedalmark(expr)
        if pm is not None:
            output = 'PedalGapStart'
        return output

    @staticmethod
    def pedalgapstart_to_infodict(
        # expr: m21.expressions.PedalGapStart,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def pedalgapend_to_string(
        # expr: m21.expressions.PedalGapEnd,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return ''

    @staticmethod
    def pedalgapend_to_symbolic(
        # expr: m21.expressions.PedalGapEnd,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str:
        output: str = ''
        pm = M21Utils.get_enclosing_pedalmark(expr)
        if pm is not None:
            output = 'PedalGapEnd'
        return output

    @staticmethod
    def pedalgapend_to_infodict(
        # expr: m21.expressions.PedalGapEnd,
        expr: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}
    # pylint: enable=no-member

    @staticmethod
    def notestyle_to_dict(
        style: m21.style.NoteStyle,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}

        # if style.stemStyle is not None:
        #     output['stemstyle'] = M21Utils.genericstyle_to_dict(style.stemStyle)

        if style.accidentalStyle is not None:
            output['accidstyle'] = M21Utils.genericstyle_to_dict(style.accidentalStyle)

        if style.noteSize:
            output['size'] = style.noteSize

        return output

    @staticmethod
    def textstyle_to_dict(
        style: m21.style.TextStyle,
        detail: DetailLevel | int = DetailLevel.Default,
        smuflTextSuppressed: bool = False,
        fontSizeSuppressed: bool = True
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}

        if isinstance(style, m21.style.TextStylePlacement) and style.placement:
            output['placement'] = style.placement

        # ignore fontSize and fontFamily, Humdrum can't represent it.
        # if style.fontFamily and not smuflTextSuppressed:
        #     output['fontFamily'] = style.fontFamily
        if not fontSizeSuppressed:
            # actually Humdrum has fontSize for rehearsal marks now, and maybe
            # text expressions someday.
            if style.fontSize is not None:
                output['fontSize'] = style.fontSize

        # normalize 'bold', since sometimes it's fontStyle='bold'/'bolditalic',
        # and sometimes it's fontWeight='bold' + fontStyle='italic' or 'normal'
        fontStyle = style.fontStyle
        fontWeight = style.fontWeight
        if fontStyle == 'bold':
            fontStyle = None
            fontWeight = 'bold'
        elif fontStyle == 'bolditalic':
            fontStyle = 'italic'
            fontWeight = 'bold'
        if fontStyle is not None and fontStyle != 'normal':
            output['fontStyle'] = fontStyle
        if fontWeight is not None and fontWeight != 'normal':
            output['fontWeight'] = fontWeight

        # if style.letterSpacing is not None and style.letterSpacing != 'normal':
        #     output['letterSpacing'] = style.letterSpacing
        # if style.lineHeight:
        #     output['lineHeight'] = style.lineHeight
        # if style.textDirection:
        #     output['textDirection'] = style.textDirection
        # if style.textRotation:
        #     output['textRotation'] = style.textRotation
        # if style.language:
        #     output['language'] = style.language
        # if style.textDecoration:
        #     output['textDecoration'] = style.textDecoration
        if style.justify:
            output['justify'] = style.justify
        # if style.alignHorizontal:
        #     output['alignHorizontal'] = style.alignHorizontal
        if style.alignVertical:
            output['alignVertical'] = style.alignVertical

        return output

    @staticmethod
    def genericstyle_to_dict(
        style: m21.style.Style,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}
        if style.size is not None:
            output['size'] = style.size
        # if style.relativeX is not None:
            # output['relX'] = style.relativeX
        # if style.relativeY is not None:
            # output['relY'] = style.relativeY
        # if style.absoluteX is not None:
            # output['absX'] = style.absoluteX
        # if style.absoluteY is not None:
            # output['absY'] = style.absoluteY
        if style.enclosure is not None:
            output['encl'] = style.enclosure
        if style.fontRepresentation is not None:
            output['fontrep'] = style.fontRepresentation
        if style.color is not None:
            output['color'] = style.color
        # if style.units != 'tenths':
            # output['units'] = style.units
        # if style.hideObjectOnPrint:
            # output['hidden'] = True
        return output

    @staticmethod
    def specificstyle_to_dict(
        style: m21.style.Style,
        detail: DetailLevel | int = DetailLevel.Default,
        smuflTextSuppressed: bool = False,
        fontSizeSuppressed: bool = True
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        if isinstance(style, m21.style.NoteStyle):
            return M21Utils.notestyle_to_dict(style, detail)
        if isinstance(style, m21.style.TextStyle):
            # includes TextStylePlacement
            return M21Utils.textstyle_to_dict(
                style,
                detail,
                smuflTextSuppressed=smuflTextSuppressed,
                fontSizeSuppressed=fontSizeSuppressed
            )
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
        detail: DetailLevel | int = DetailLevel.Default,
        smuflTextSuppressed: bool = False
    ) -> dict:
        if not DetailLevel.includesStyle(detail):
            return {}

        output: dict = {}
        if obj.hasStyleInformation:
            output = M21Utils.genericstyle_to_dict(obj.style, detail)
            specific = M21Utils.specificstyle_to_dict(
                obj.style,
                detail,
                smuflTextSuppressed=smuflTextSuppressed,
                fontSizeSuppressed=(
                    smuflTextSuppressed
                    or not isinstance(obj, m21.expressions.RehearsalMark)
                )
            )
            for k, v in specific.items():
                output[k] = v

        if hasattr(obj, 'placement') and obj.placement is not None:
            if 'placement' in output:
                # style was a TextStylePlacement, with placement specified
                print('placement specified twice, taking the one in .style', file=sys.stderr)
            else:
                output['placement'] = obj.placement

        if obj.hasStyleInformation and 'placement' not in output:
            # no placement yet, use style.absoluteY (if present and non-zero), but
            # only if obj or style has a .placement field (notes don't, for instance)
            if hasattr(obj, 'placement') or hasattr(obj.style, 'placement'):
                if obj.style.absoluteY is not None:
                    if obj.style.absoluteY > 0:
                        output['placement'] = 'above'
                    elif obj.style.absoluteY < 0:
                        output['placement'] = 'below'

        # One last style thing: lyric placement=='below' and lyric justify=='left
        # should be ignored, since that's where lyrics go by default (and there
        # are file formats (Humdrum) that don't let you specify anything different:
        if isinstance(obj, m21.note.Lyric):
            if output.get('placement') == 'below':
                del output['placement']
            if output.get('justify') == 'left':
                del output['justify']

        return output

    @staticmethod
    def slur_to_string(
        slur: m21.spanner.Slur,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def slur_to_symbolic(
        slur: m21.spanner.Slur,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def slur_to_infodict(
        slur: m21.spanner.Slur,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def arpeggio_to_string(
        arp: m21.expressions.ArpeggioMark | m21.expressions.ArpeggioMarkSpanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def arpeggio_to_symbolic(
        arp: m21.expressions.ArpeggioMark | m21.expressions.ArpeggioMarkSpanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return f'{arp.type}'

    @staticmethod
    def arpeggio_to_infodict(
        arp: m21.expressions.ArpeggioMark | m21.expressions.ArpeggioMarkSpanner,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        if isinstance(arp, m21.expressions.ArpeggioMarkSpanner):
            if len(arp) > 1:
                output['arpeggiospanlength'] = f'{len(arp)}'
        return output

    @staticmethod
    def chordsym_to_string(
        cs: m21.harmony.ChordSymbol,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def chordsym_to_symbolic(
        cs: m21.harmony.ChordSymbol,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if isinstance(cs, m21.harmony.NoChord):
            printedStr: str = cs.chordKindStr
            if printedStr:
                printedStr = ' ("' + printedStr + '")'
            return f'N.C.{printedStr}'

        root: str = cs.root().name
        bass: str = cs.bass().name
        if bass == root:
            bass = ''
        else:
            bass = '/' + bass

        pitches: list[str] = [p.name for p in cs.pitches]
        # We don't care about order beyond which is bass
        pitches = sorted(pitches)
        # But let's start with root for readability
        rootedPitches: list[str] = []
        rootIndex: int = pitches.index(root)
        for i in range(0, len(pitches)):
            idx: int = rootIndex + i
            idx %= len(pitches)  # wrap around
            rootedPitches.append(pitches[idx])

        pitchStr: str = ''
        if pitches:
            pitchStr = ','.join(rootedPitches)
        if pitchStr:
            pitchStr = ': [' + pitchStr + ']'

        # This one is for checking I made the right chordKind (as well), which is
        # important for checking my importers/exporters, but not really for
        # assessing OMR.
        # return f'CSYM:{root} {cs.chordKind}({cs.chordKindStr}){bass}{pitchStr}'

        if cs.chordKindStr:
            return f'{root}{cs.chordKindStr}{bass}{pitchStr}'
        else:
            # no chordKindStr, so make one up.  Simplify the chord symbol first
            # (look for a better chordKind that has fewer chordStepModifications)
            simplerCS: m21.harmony.ChordSymbol = copy.deepcopy(cs)
            M21Utilities.simplifyChordSymbol(simplerCS)
            chordKindStr: str = M21Utilities.convertChordSymbolFigureToPrintableText(
                simplerCS.findFigure(), removeNoteNames=True
            )
            return f'{root}{chordKindStr}{bass}{pitchStr}'

    @staticmethod
    def chordsym_to_infodict(
        cs: m21.harmony.ChordSymbol,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def repeatbracket_to_string(
        rb: m21.spanner.RepeatBracket,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if rb.overrideDisplay:
            return f'{rb.overrideDisplay}'
        else:
            return f'{rb.number}'

    @staticmethod
    def repeatbracket_to_symbolic(
        rb: m21.spanner.RepeatBracket,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def repeatbracket_to_infodict(
        rb: m21.spanner.RepeatBracket,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        output['measurecount'] = f'{len(rb)}'
        return output

    @staticmethod
    def staffinfo_to_string(
        sl: m21.layout.StaffLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def staffinfo_to_symbolic(
        sl: m21.layout.StaffLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def staffinfo_to_infodict(
        sl: m21.layout.StaffLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        if sl.staffLines is not None:
            output['lines'] = f'{sl.staffLines}'
        if DetailLevel.includesStyle(detail):
            if sl.staffSize is not None:
                output['size'] = f'{sl.staffSize:.3g}%'
        return output

    @staticmethod
    def systembreak_to_string(
        sb: m21.layout.SystemLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def systembreak_to_symbolic(
        sb: m21.layout.SystemLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return 'systembreak'

    @staticmethod
    def systembreak_to_infodict(
        sb: m21.layout.SystemLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def pagebreak_to_string(
        sb: m21.layout.PageLayout,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        return None

    @staticmethod
    def pagebreak_to_symbolic(
        sb: m21.layout.PageLayout,
        kind: str,
        detail: DetailLevel | int
    ) -> str | None:
        return 'pagebreak'

    @staticmethod
    def pagebreak_to_infodict(
        sb: m21.layout.PageLayout,
        kind: str,
        detail: DetailLevel | int
    ) -> dict[str, str]:
        return {}

    @staticmethod
    def extra_to_string(
        extra: m21.base.Music21Object,
        kind: str,
        detail: DetailLevel | int = DetailLevel.Default
    ) -> str | None:
        if isinstance(extra, m21.spanner.Slur):
            return M21Utils.slur_to_string(extra, kind, detail)
        if isinstance(extra, (m21.key.Key, m21.key.KeySignature)):
            return M21Utils.keysig_to_string(extra, kind, detail)
        if isinstance(extra, m21.expressions.TextExpression):
            return M21Utils.textexp_to_string(extra, kind, detail)
        if isinstance(extra, (m21.dynamics.Dynamic, m21.dynamics.DynamicWedge)):
            return M21Utils.dynamic_to_string(extra, kind, detail)
        if isinstance(extra, m21.clef.Clef):
            return M21Utils.clef_to_string(extra, kind, detail)
        if isinstance(extra, m21.meter.TimeSignature):
            return M21Utils.timesig_to_string(extra, kind, detail)
        if isinstance(extra, m21.tempo.TempoIndication):
            return M21Utils.tempo_to_string(extra, kind, detail)
        if isinstance(extra, m21.bar.Barline):
            return M21Utils.barline_to_string(extra, kind, detail)
        if isinstance(extra, m21.spanner.Ottava):
            return M21Utils.ottava_to_string(extra, kind, detail)
        if isinstance(extra, m21.spanner.RepeatBracket):
            return M21Utils.repeatbracket_to_string(extra, kind, detail)
        if isinstance(extra, m21.expressions.TremoloSpanner):
            return M21Utils.tremolo_to_string(extra, kind, detail)
        if isinstance(extra, m21.expressions.RehearsalMark):
            return M21Utils.rehearsalmark_to_string(extra, kind, detail)
        if isinstance(extra,
                (m21.expressions.ArpeggioMark, m21.expressions.ArpeggioMarkSpanner)):
            return M21Utils.arpeggio_to_string(extra, kind, detail)
        if isinstance(extra, m21.harmony.ChordSymbol):
            return M21Utils.chordsym_to_string(extra, kind, detail)
        if isinstance(extra, m21.layout.StaffLayout):
            return M21Utils.staffinfo_to_string(extra, kind, detail)
        if isinstance(extra, m21.layout.SystemLayout):
            return M21Utils.systembreak_to_string(extra, kind, detail)
        if isinstance(extra, m21.layout.PageLayout):
            return M21Utils.pagebreak_to_string(extra, kind, detail)

        if not M21Utilities.m21PedalMarksSupported():
            # print(f'Unexpected extra: {extra.classes[0]}', file=sys.stderr)
            return ''

        # pylint: disable=no-member
        if isinstance(extra, m21.expressions.PedalMark):  # type: ignore
            return M21Utils.pedalmark_to_string(extra, kind, detail)
        if isinstance(extra, m21.expressions.PedalBounce):  # type: ignore
            return M21Utils.pedalbounce_to_string(extra, kind, detail)
        if isinstance(extra, m21.expressions.PedalGapStart):  # type: ignore
            return M21Utils.pedalgapstart_to_string(extra, kind, detail)
        if isinstance(extra, m21.expressions.PedalGapEnd):  # type: ignore
            return M21Utils.pedalgapend_to_string(extra, kind, detail)
        # pylint: enable=no-member

        # print(f'Unexpected extra: {extra.classes[0]}', file=sys.stderr)
        return ''

    @staticmethod
    def has_style(obj: m21.base.Music21Object | m21.style.StyleMixin) -> bool:
        output: bool = hasattr(obj, 'placement') and obj.placement is not None
        output = output or obj.hasStyleInformation
        return output

    @staticmethod
    def get_part_index(part: m21.stream.Part, score: m21.stream.Score) -> int:
        # return -1 if part not in score
        partIdx: int = -1
        if part is None:
            return partIdx

        for i, p in enumerate(score.parts):
            if p is part:
                partIdx = i
                break

        return partIdx

#     @staticmethod
#     def get_measure_number(meas: m21.stream.Measure, part: m21.stream.Part) -> int:
#         output: int = meas.number
#         if output:
#             return output
#
#         # fall back to measure index within part
#         for i, m in enumerate(part[m21.stream.Measure]):
#             if m is meas:
#                 output = i
#                 break
#
#         return output

    @staticmethod
    def get_measure_number_with_suffix(meas: m21.stream.Measure, part: m21.stream.Part) -> str:
        output: str = meas.measureNumberWithSuffix()
        if output:
            return output

        # fall back to measure index within part
        for i, m in enumerate(part[m21.stream.Measure]):
            if m is meas:
                output = str(i)
                break

        return output

    @staticmethod
    def get_beats(offset: OffsetQL, ts: m21.meter.TimeSignature) -> OffsetQL:
        wholeNotes: OffsetQL = opFrac(offset / 4.0)
        beats: OffsetQL = opFrac(wholeNotes * float(ts.denominator))
        beats = opFrac(beats + 1.0)
        return beats

    @staticmethod
    def ql_to_string(ql: OffsetQL) -> str:
        if isinstance(ql, float):
            return str(ql)

        # It's a Fraction, print as a mixed fraction if necessary
        num: int = ql.numerator
        den: int = ql.denominator
        wholeNum: int = int(num / den)
        if wholeNum < 0:
            # wholeNum has the negative sign, remove it from num
            num = abs(num)
        if wholeNum:
            num -= abs(wholeNum) * den
            return f"{wholeNum} {num}/{den}"
        return f"{num}/{den}"
