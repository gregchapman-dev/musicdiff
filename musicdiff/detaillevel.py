# ------------------------------------------------------------------------------
# Purpose:       detaillevel defines the levels of detail that can be requested
#                of musicdiff.
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

from enum import IntEnum
import typing as t

import music21 as m21

_typesCache: dict[int, tuple[t.Type, ...]] = {}


class DetailLevel(IntEnum):
    # Bit definitions (can be |'ed together, as well as &~'ed to turn off options):

    # notes, rests (without any decorations: beams/ties/ornaments/articulations/etc)
    NotesAndRests = 1

    # beams (if not requested, beams are treated exactly like flags)
    # Note that if NotesAndRests are not also requested, no beams differences will be found.
    Beams = 1 << 1

    # tremolos (fingered and bowed)
    # Note that if NotesAndRests are not also requested, no tremolo differences will be found.
    Tremolos = 1 << 2

    # trills, turns, mordents, fermatas, etc
    # Note that if NotesAndRests are not also requested, no expression differences will be found.
    Ornaments = 1 << 3

    # staccato, tenuto, spiccato, etc
    # Note that if NotesAndRests are not also requested, no articulation differences will be found.
    Articulations = 1 << 4

    # ties
    # Note that if NotesAndRests are not also requested, no tie differences will be found.
    Ties = 1 << 5

    # slurs
    Slurs = 1 << 6

    # decorated notes and rests (a combination of all of the above)
    DecoratedNotesAndRests = (
        NotesAndRests | Beams | Tremolos | Ornaments | Articulations | Ties | Slurs
    )

    # clefs, key signatures, time signatures
    Signatures = 1 << 7

    # tempos, metronome marks, dynamics, alternate endings, and other directions
    Directions = 1 << 8

    # bar lines (includes repeat-style bar lines)
    Barlines = 1 << 9

    # staff details (lines in staff, staff groups)
    StaffDetails = 1 << 10

    # chord symbols (jazz chords, roman-style chords, etc)
    ChordSymbols = 1 << 11

    # 8va, 8vb, etc
    Ottavas = 1 << 12

    # arpeggios
    Arpeggios = 1 << 13

    # Lyrics
    Lyrics = 1 << 14

    # other objects (everything above that isn't in DecoratedNotesAndRests)
    OtherObjects = (
        Signatures | Directions | Barlines | StaffDetails
        | ChordSymbols | Ottavas | Arpeggios | Lyrics
    )

    # all objects = decorated notes and other musical objects
    AllObjects = DecoratedNotesAndRests | OtherObjects

    # A few extra details that are not a part of any combination. These must be added
    # by hand if you want them.

    # Typographical stuff: stem direction, note shape, color, italic/bold, etc
    Style = 1 << 15

    # Metadata: title, composer, etc
    Metadata = 1 << 16

    # By default, we ignore which voice and chord each note is in, and just compare the
    # individual notes (and rests) themselves.  If Voicing is turned on, we compare which
    # voice and which chord each note is in.
    # Note that comparison of voices is done with no consideration of voice ordering or
    # voice ids; we compare the best matching pairs of voices.
    Voicing = 1 << 17

    # default detail level is all objects:
    Default = AllObjects

    # checkers for each individual bit
    @classmethod
    def includesNotesAndRests(cls, val: int) -> bool:
        return val & cls.NotesAndRests != 0

    @classmethod
    def includesBeams(cls, val: int) -> bool:
        return val & cls.Beams != 0

    @classmethod
    def includesTremolos(cls, val: int) -> bool:
        return val & cls.Tremolos != 0

    @classmethod
    def includesOrnaments(cls, val: int) -> bool:
        return val & cls.Ornaments != 0

    @classmethod
    def includesArticulations(cls, val: int) -> bool:
        return val & cls.Articulations != 0

    @classmethod
    def includesTies(cls, val: int) -> bool:
        return val & cls.Ties != 0

    @classmethod
    def includesSlurs(cls, val: int) -> bool:
        return val & cls.Slurs != 0

    @classmethod
    def includesSignatures(cls, val: int) -> bool:
        return val & cls.Signatures != 0

    @classmethod
    def includesDirections(cls, val: int) -> bool:
        return val & cls.Directions != 0

    @classmethod
    def includesBarlines(cls, val: int) -> bool:
        return val & cls.Barlines != 0

    @classmethod
    def includesStaffDetails(cls, val: int) -> bool:
        return val & cls.StaffDetails != 0

    @classmethod
    def includesChordSymbols(cls, val: int) -> bool:
        return val & cls.ChordSymbols != 0

    @classmethod
    def includesOttavas(cls, val: int) -> bool:
        return val & cls.Ottavas != 0

    @classmethod
    def includesArpeggios(cls, val: int) -> bool:
        return val & cls.Arpeggios != 0

    @classmethod
    def includesLyrics(cls, val: int) -> bool:
        return val & cls.Lyrics != 0

    @classmethod
    def includesStyle(cls, val: int) -> bool:
        return val & cls.Style != 0

    @classmethod
    def includesMetadata(cls, val: int) -> bool:
        return val & cls.Metadata != 0

    @classmethod
    def includesVoicing(cls, val: int) -> bool:
        return val & cls.Voicing != 0

    @classmethod
    def _included_m21_types(cls, val: int) -> tuple[t.Type, ...]:
        # Not all types go in here, just the ones where we will have pulled
        # a bunch of objects, and then have to filter them.  So far, that's
        # just the non-GeneralNote objects that we pull from a measure
        # for the extras list (including all spanners).  We don't have
        # to put GeneralNotes here, or anything that we would only find in
        # gn.expressions (a.k.a. DetailLevel.Ornaments) or gn.articulations
        # (a.k.a. DetailLevel.Articulations).
        if val not in _typesCache:
            typesList: list[t.Type] = []
            if cls.includesTremolos(val):
                typesList.extend([
                    m21.expressions.Tremolo,
                    m21.expressions.TremoloSpanner
                ])

            if cls.includesSlurs(val):
                typesList.append(m21.spanner.Slur)

            if cls.includesSignatures(val):
                typesList.extend([
                    m21.clef.Clef,
                    m21.key.KeySignature,
                    m21.meter.TimeSignature,
                ])

            if cls.includesStaffDetails(val):
                typesList.extend([
                    m21.layout.StaffLayout,
                    m21.layout.StaffGroup
                ])

            if cls.includesDirections(val):
                typesList.extend([
                    m21.expressions.TextExpression,
                    m21.tempo.TempoIndication,
                    m21.dynamics.Dynamic,
                    m21.dynamics.DynamicWedge,
                    m21.spanner.RepeatBracket  # e.g. first and second endings
                    # TODO: here is where one might add some currently unsupported directions
                    # TODO: like m21.repeat.RepeatExpression (Coda, Segno, Fine, DaCapo,
                    # TODO: DaCapoAlFine, etc)
                ])

            if cls.includesBarlines(val):
                typesList.extend([
                    m21.bar.Barline,
                    m21.bar.Repeat
                ])

            if cls.includesOttavas(val):
                typesList.append(m21.spanner.Ottava)

            if cls.includesArpeggios(val):
                typesList.extend([
                    m21.expressions.ArpeggioMark,
                    m21.expressions.ArpeggioMarkSpanner
                ])

            if cls.includesChordSymbols(val):
                typesList.append(m21.harmony.ChordSymbol)

            if cls.includesStyle(val):
                # we have to add these here, because they are style-only (no substance)
                typesList.extend([
                    m21.layout.SystemLayout,
                    m21.layout.PageLayout
                ])

            _typesCache[val] = tuple(typesList)

        return _typesCache[val]

    @classmethod
    def objIsIncluded(cls, obj: m21.base.Music21Object, val: int) -> bool:
        types: tuple[t.Type, ...] = cls._included_m21_types(val)

        # We have to check ChordSymbol by hand, since ChordSymbol is derived
        # from GeneralNote, and should ONLY be included if ChordSymbol is in
        # the list, NOT just because GeneralNote is in the list.
        # I would note that GeneralNote is currently _never_ in the list,
        # but I leave this code in place so that we don't break something
        # unexpectedly if we put GeneralNote in the list in the future.
        if isinstance(obj, m21.harmony.ChordSymbol):
            return m21.harmony.ChordSymbol in types

        return isinstance(obj, types)
