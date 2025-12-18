# ------------------------------------------------------------------------------
# Purpose:       comparison is a music comparison package for use by musicdiff.
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

__docformat__ = "google"

import copy
from collections import namedtuple
from difflib import ndiff
from pathlib import Path

# import typing as t
import numpy as np

from music21.common import OffsetQL
from musicdiff.annotation import AnnScore, AnnNote, AnnVoice, AnnExtra, AnnLyric
from musicdiff.annotation import AnnStaffGroup, AnnMetadataItem
from musicdiff import M21Utils

class EvaluationMetrics:
    def __init__(
        self,
        gt_path: Path,
        pred_path: Path,
        gt_numsyms: int,
        pred_numsyms: int,
        omr_edit_distance: int,
        edit_distances_dict: dict[str, int],
        omr_ned: float
    ):
        self.gt_path: Path = gt_path
        self.pred_path: Path = pred_path
        self.gt_numsyms: int = gt_numsyms
        self.pred_numsyms: int = pred_numsyms
        self.omr_edit_distance: int = omr_edit_distance
        self.edit_distances_dict: dict[str, int] = edit_distances_dict
        self.omr_ned: float = omr_ned

# memoizers to speed up the recursive computation
def _memoize_notes_set_distance(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_extras_set_distance(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_staff_groups_set_distance(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_metadata_items_set_distance(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_inside_bars_diff_lin(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_lyrics_diff_lin(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_block_diff_lin(func):
    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_pitches_lev_diff(func):
    def memoizer(original, compare_to, noteNode1, noteNode2, ids):
        key = (
            repr(original)
            + repr(compare_to)
            + repr(noteNode1)
            + repr(noteNode2)
            + repr(ids)
        )
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to, noteNode1, noteNode2, ids)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_beamtuplet_lev_diff(func):
    def memoizer(original, compare_to, noteNode1, noteNode2, which):
        key = (
            repr(original) + repr(compare_to) + repr(noteNode1) + repr(noteNode2) + which
        )
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to, noteNode1, noteNode2, which)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

def _memoize_generic_lev_diff(func):
    def memoizer(original, compare_to, noteNode1, noteNode2, which):
        key = (
            repr(original) + repr(compare_to) + repr(noteNode1) + repr(noteNode2) + which
        )
        if key not in Comparison._memoizer_mem:
            Comparison._memoizer_mem[key] = func(original, compare_to, noteNode1, noteNode2, which)
        return copy.deepcopy(Comparison._memoizer_mem[key])

    return memoizer

class Comparison:
    _memoizer_mem: dict = {}

    @staticmethod
    def _clear_memoizer_caches():
        Comparison._memoizer_mem = {}

    @staticmethod
    def _myers_diff(a_lines, b_lines):
        # Myers algorithm for LCS of bars (instead of the recursive algorithm in section 3.2)
        # This marks the farthest-right point along each diagonal in the edit
        # graph, along with the history that got it there
        Frontier = namedtuple("Frontier", ["x", "history"])
        frontier = {1: Frontier(0, [])}

        a_max = len(a_lines)
        b_max = len(b_lines)
        for d in range(0, a_max + b_max + 1):
            for k in range(-d, d + 1, 2):
                # This determines whether our next search point will be going down
                # in the edit graph, or to the right.
                #
                # The intuition for this is that we should go down if we're on the
                # left edge (k == -d) to make sure that the left edge is fully
                # explored.
                #
                # If we aren't on the top (k != d), then only go down if going down
                # would take us to territory that hasn't sufficiently been explored
                # yet.
                go_down = k == -d or (k != d and frontier[k - 1].x < frontier[k + 1].x)

                # Figure out the starting point of this iteration. The diagonal
                # offsets come from the geometry of the edit grid - if you're going
                # down, your diagonal is lower, and if you're going right, your
                # diagonal is higher.
                if go_down:
                    old_x, history = frontier[k + 1]
                    x = old_x
                else:
                    old_x, history = frontier[k - 1]
                    x = old_x + 1

                # We want to avoid modifying the old history, since some other step
                # may decide to use it.
                history = history[:]
                y = x - k

                # We start at the invalid point (0, 0) - we should only start building
                # up history when we move off of it.
                if 1 <= y <= b_max and go_down:
                    history.append((1, b_lines[y - 1][1]))  # add comparetostep
                elif 1 <= x <= a_max:
                    history.append((0, a_lines[x - 1][1]))  # add originalstep

                # Chew up as many diagonal moves as we can - these correspond to common lines,
                # and they're considered "free" by the algorithm because we want to maximize
                # the number of these in the output.
                while x < a_max and y < b_max and a_lines[x][0] == b_lines[y][0]:
                    x += 1
                    y += 1
                    history.append((2, a_lines[x - 1][1]))  # add equal step

                if x >= a_max and y >= b_max:
                    # If we're here, then we've traversed through the bottom-left corner,
                    # and are done.
                    return np.array(history)

                frontier[k] = Frontier(x, history)

        assert False, "Could not find edit script"

    @staticmethod
    def _non_common_subsequences_myers(original, compare_to):
        # Both original and compare_to are list of lists, or numpy arrays with 2 columns.
        # This is necessary because bars need two representation at the same time.
        # One without the id (for comparison), and one with the id (to retrieve the bar
        # at the end).

        # get the list of operations
        op_list = Comparison._myers_diff(
            np.array(original, dtype=np.int64), np.array(compare_to, dtype=np.int64)
        )[::-1]
        # retrieve the non common subsequences
        non_common_subsequences = []
        non_common_subsequences.append({"original": [], "compare_to": []})
        ind = 0
        for op in op_list[::-1]:
            if op[0] == 2:  # equal
                non_common_subsequences.append({"original": [], "compare_to": []})
                ind += 1
            elif op[0] == 0:  # original step
                non_common_subsequences[ind]["original"].append(op[1])
            elif op[0] == 1:  # compare to step
                non_common_subsequences[ind]["compare_to"].append(op[1])
        # remove the empty dict from the list
        non_common_subsequences = [
            s for s in non_common_subsequences if s != {"original": [], "compare_to": []}
        ]
        return non_common_subsequences

    @staticmethod
    def _non_common_subsequences_of_measures(original_m, compare_to_m):
        # Take the hash for each measure to run faster comparison
        # We need two hashes: one that is independent of the IDs (precomputed_str, for comparison),
        # and one that contains the IDs (precomputed_repr, to retrieve the correct measure after
        # computation)
        original_int = [[o.precomputed_str, o.precomputed_repr] for o in original_m]
        compare_to_int = [[c.precomputed_str, c.precomputed_repr] for c in compare_to_m]
        ncs = Comparison._non_common_subsequences_myers(original_int, compare_to_int)
        # retrieve the original pointers to measures
        new_out = []
        for e in ncs:
            new_out.append({})
            for k in e.keys():
                new_out[-1][k] = []
                for repr_hash in e[k]:
                    if k == "original":
                        new_out[-1][k].append(
                            next(m for m in original_m if m.precomputed_repr == repr_hash)
                        )
                    else:
                        new_out[-1][k].append(
                            next(m for m in compare_to_m if m.precomputed_repr == repr_hash)
                        )

        return new_out

    @staticmethod
    @_memoize_pitches_lev_diff
    def _pitches_levenshtein_diff(
        original: list[tuple[str, str, bool]],
        compare_to: list[tuple[str, str, bool]],
        noteNode1: AnnNote,
        noteNode2: AnnNote,
        ids: tuple[int, int]
    ):
        """
        Compute the levenshtein distance between two sequences of pitches.
        Arguments:
            original {list} -- list of pitches
            compare_to {list} -- list of pitches
            noteNode1 {annotatedNote} --for referencing
            noteNode2 {annotatedNote} --for referencing
            ids {tuple} -- a tuple of 2 elements with the indices of the notes considered
        """
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            op_list, cost = Comparison._pitches_levenshtein_diff(
                original, compare_to[1:], noteNode1, noteNode2, (ids[0], ids[1] + 1)
            )
            op_list.append(
                ("inspitch", noteNode1, noteNode2, M21Utils.pitch_size(compare_to[0]), ids)
            )
            cost += M21Utils.pitch_size(compare_to[0])
            return op_list, cost

        if len(compare_to) == 0:
            op_list, cost = Comparison._pitches_levenshtein_diff(
                original[1:], compare_to, noteNode1, noteNode2, (ids[0] + 1, ids[1])
            )
            op_list.append(
                ("delpitch", noteNode1, noteNode2, M21Utils.pitch_size(original[0]), ids)
            )
            cost += M21Utils.pitch_size(original[0])
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost_dict = {}
        op_list_dict = {}
        # del-pitch
        op_list_dict["delpitch"], cost_dict["delpitch"] = Comparison._pitches_levenshtein_diff(
            original[1:], compare_to, noteNode1, noteNode2, (ids[0] + 1, ids[1])
        )
        cost_dict["delpitch"] += M21Utils.pitch_size(original[0])
        op_list_dict["delpitch"].append(
            ("delpitch", noteNode1, noteNode2, M21Utils.pitch_size(original[0]), ids)
        )
        # ins-pitch
        op_list_dict["inspitch"], cost_dict["inspitch"] = Comparison._pitches_levenshtein_diff(
            original, compare_to[1:], noteNode1, noteNode2, (ids[0], ids[1] + 1)
        )
        cost_dict["inspitch"] += M21Utils.pitch_size(compare_to[0])
        op_list_dict["inspitch"].append(
            ("inspitch", noteNode1, noteNode2, M21Utils.pitch_size(compare_to[0]), ids)
        )
        # edit-pitch
        op_list_dict["editpitch"], cost_dict["editpitch"] = Comparison._pitches_levenshtein_diff(
            original[1:], compare_to[1:], noteNode1, noteNode2, (ids[0] + 1, ids[1] + 1)
        )
        if original[0] == compare_to[0]:  # to avoid perform the pitch_diff
            pitch_diff_op_list = []
            pitch_diff_cost = 0
        else:
            pitch_diff_op_list, pitch_diff_cost = Comparison._pitches_diff(
                original[0], compare_to[0], noteNode1, noteNode2, (ids[0], ids[1])
            )
        cost_dict["editpitch"] += pitch_diff_cost
        op_list_dict["editpitch"].extend(pitch_diff_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost_dict, key=lambda k: cost_dict[k])
        out = op_list_dict[min_key], cost_dict[min_key]
        return out

    @staticmethod
    def _pitches_diff(pitch1, pitch2, noteNode1, noteNode2, ids):
        """
        Compute the differences between two pitch (definition from the paper).
        a pitch consist of a tuple: pitch name (letter+number), accidental, tie.
        param : pitch1. The music_notation_repr tuple of note1
        param : pitch2. The music_notation_repr tuple of note2
        param : noteNode1. The noteNode where pitch1 belongs
        param : noteNode2. The noteNode where pitch2 belongs
        param : ids. (id_from_note1,id_from_note2) The indices of the notes in case of a chord
        Returns:
            [list] -- the list of differences
            [int] -- the cost of diff
        """
        cost = 0
        op_list = []
        # add for pitch name differences
        if pitch1[0] != pitch2[0]:
            cost += 1
            # TODO: select the note in a more precise way in case of a chord
            # rest to note
            if (pitch1[0][0] == "R") != (pitch2[0][0] == "R"):  # xor
                op_list.append(("pitchtypeedit", noteNode1, noteNode2, 1, ids))
            else:  # they are two notes
                op_list.append(("pitchnameedit", noteNode1, noteNode2, 1, ids))

        # add for the accidentals
        if pitch1[1] != pitch2[1]:  # if the accidental is different
            if pitch1[1] == "None":
                assert pitch2[1] != "None"
                cost += 1
                op_list.append(("accidentins", noteNode1, noteNode2, 1, ids))
            elif pitch2[1] == "None":
                assert pitch1[1] != "None"
                cost += 1
                op_list.append(("accidentdel", noteNode1, noteNode2, 1, ids))
            else:  # a different type of alteration is present
                cost += 2  # delete then add
                op_list.append(("accidentedit", noteNode1, noteNode2, 2, ids))
        # add for the ties
        if pitch1[2] != pitch2[2]:
            # exclusive or. Add if one is tied and not the other.
            # probably to revise for chords
            cost += 1
            if pitch1[2]:
                assert not pitch2[2]
                op_list.append(("tiedel", noteNode1, noteNode2, 1, ids))
            elif pitch2[2]:
                assert not pitch1[2]
                op_list.append(("tieins", noteNode1, noteNode2, 1, ids))
        return op_list, cost

    @staticmethod
    @_memoize_block_diff_lin
    def _block_diff_lin(original, compare_to):
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            op_list, cost = Comparison._block_diff_lin(original, compare_to[1:])
            cost += compare_to[0].notation_size()
            op_list.append(("insbar", None, compare_to[0], compare_to[0].notation_size()))
            return op_list, cost

        if len(compare_to) == 0:
            op_list, cost = Comparison._block_diff_lin(original[1:], compare_to)
            cost += original[0].notation_size()
            op_list.append(("delbar", original[0], None, original[0].notation_size()))
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost_dict = {}
        op_list_dict = {}
        # del-bar
        op_list_dict["delbar"], cost_dict["delbar"] = Comparison._block_diff_lin(
            original[1:], compare_to
        )
        cost_dict["delbar"] += original[0].notation_size()
        op_list_dict["delbar"].append(
            ("delbar", original[0], None, original[0].notation_size())
        )
        # ins-bar
        op_list_dict["insbar"], cost_dict["insbar"] = Comparison._block_diff_lin(
            original, compare_to[1:]
        )
        cost_dict["insbar"] += compare_to[0].notation_size()
        op_list_dict["insbar"].append(
            ("insbar", None, compare_to[0], compare_to[0].notation_size())
        )
        # edit-bar
        op_list_dict["editbar"], cost_dict["editbar"] = Comparison._block_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # to avoid performing the _voices_coupling_recursive/_notes_set_distance
            # if it's not needed
            inside_bar_op_list = []
            inside_bar_cost = 0
        else:
            # diff the bar extras (like _notes_set_distance, but with lists of AnnExtras
            # instead of lists of AnnNotes)
            extras_op_list, extras_cost = Comparison._extras_set_distance(
                original[0].extras_list, compare_to[0].extras_list
            )

            # diff the bar lyrics (with lists of AnnLyrics instead of lists of AnnExtras)
            lyrics_op_list, lyrics_cost = Comparison._lyrics_diff_lin(
                original[0].lyrics_list, compare_to[0].lyrics_list
            )

            if original[0].includes_voicing:
                # run the voice coupling algorithm, and add to inside_bar_op_list
                # and inside_bar_cost
                inside_bar_op_list, inside_bar_cost = (
                    Comparison._voices_coupling_recursive(
                        original[0].voices_list, compare_to[0].voices_list
                    )
                )
            else:
                # run the set distance algorithm, and add to inside_bar_op_list
                # and inside_bar_cost
                inside_bar_op_list, inside_bar_cost = Comparison._notes_set_distance(
                    original[0].annot_notes, compare_to[0].annot_notes
                )

            inside_bar_op_list.extend(extras_op_list)
            inside_bar_cost += extras_cost
            inside_bar_op_list.extend(lyrics_op_list)
            inside_bar_cost += lyrics_cost

        cost_dict["editbar"] += inside_bar_cost
        op_list_dict["editbar"].extend(inside_bar_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost_dict, key=lambda k: cost_dict[k])
        out = op_list_dict[min_key], cost_dict[min_key]
        return out

    @staticmethod
    @_memoize_lyrics_diff_lin
    def _lyrics_diff_lin(original, compare_to):
        # original and compare to are two lists of AnnLyric
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            cost = 0
            op_list, cost = Comparison._lyrics_diff_lin(original, compare_to[1:])
            op_list.append(("lyricins", None, compare_to[0], compare_to[0].notation_size()))
            cost += compare_to[0].notation_size()
            return op_list, cost

        if len(compare_to) == 0:
            cost = 0
            op_list, cost = Comparison._lyrics_diff_lin(original[1:], compare_to)
            op_list.append(("lyricdel", original[0], None, original[0].notation_size()))
            cost += original[0].notation_size()
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # lyricdel
        op_list["lyricdel"], cost["lyricdel"] = Comparison._lyrics_diff_lin(
            original[1:], compare_to
        )
        cost["lyricdel"] += original[0].notation_size()
        op_list["lyricdel"].append(
            ("lyricdel", original[0], None, original[0].notation_size())
        )
        # lyricins
        op_list["lyricins"], cost["lyricins"] = Comparison._lyrics_diff_lin(
            original, compare_to[1:]
        )
        cost["lyricins"] += compare_to[0].notation_size()
        op_list["lyricins"].append(
            ("lyricins", None, compare_to[0], compare_to[0].notation_size())
        )
        # lyricsub
        op_list["lyricsub"], cost["lyricsub"] = Comparison._lyrics_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # avoid call another function if they are equal
            lyricsub_op, lyricsub_cost = [], 0
        else:
            lyricsub_op, lyricsub_cost = (
                Comparison._annotated_lyric_diff(original[0], compare_to[0])
            )
        cost["lyricsub"] += lyricsub_cost
        op_list["lyricsub"].extend(lyricsub_op)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    def _strings_levenshtein_distance(str1: str, str2: str):
        counter: dict = {"+": 0, "-": 0}
        distance: int = 0
        for edit_code in ndiff(str1, str2):
            if edit_code[0] == " ":
                distance += max(counter.values())
                counter = {"+": 0, "-": 0}
            else:
                counter[edit_code[0]] += 1
        distance += max(counter.values())
        return distance

    @staticmethod
    def _areDifferentEnough(off1: OffsetQL | None, off2: OffsetQL | None) -> bool:
        if off1 == off2:
            return False

        # this should never happen, but...
        if off1 is None or off2 is None:
            if off1 is None and off2 is not None:
                return True
            if off1 is not None and off2 is None:
                return True
            return False  # both are None, therefore not different at all

        diff: OffsetQL = off1 - off2
        if diff < 0:
            diff = -diff

        if diff > 0.0001:
            return True
        return False

    @staticmethod
    def _annotated_extra_diff(annExtra1: AnnExtra, annExtra2: AnnExtra):
        """
        Compute the differences between two annotated extras.
        Each annotated extra consists of three values: content, offset, and duration
        """
        cost = 0
        op_list = []

        # add for the content
        if annExtra1.content != annExtra2.content:
            content_cost: int = (
                Comparison._strings_levenshtein_distance(
                    annExtra1.content or '',
                    annExtra2.content or ''
                )
            )
            cost += content_cost
            op_list.append(("extracontentedit", annExtra1, annExtra2, content_cost))

        # add for the symbolic (cost 2: delete one symbol, add the other)
        if annExtra1.symbolic != annExtra2.symbolic:
            cost += 2
            op_list.append(("extrasymboledit", annExtra1, annExtra2, 2))

        # add for the infodict
        if annExtra1.infodict != annExtra2.infodict:
            info_cost: int = 0
            # handle everything in annExtra1 (whether or not it is in annExtra2)
            for k, v in annExtra1.infodict.items():
                if k not in annExtra2.infodict:
                    # not in annExtra2: delete a symbol
                    info_cost += 1
                elif v != annExtra2.infodict[k]:
                    # different in annExtra2: delete a symbol, add a symbol
                    info_cost += 2
            # handle everything in annExtra2 that is not in annExtra1
            for k in annExtra2.infodict:
                if k not in annExtra1.infodict:
                    # add a symbol
                    info_cost += 1
            cost += info_cost
            op_list.append(("extrainfoedit", annExtra1, annExtra2, info_cost))

        # add for the offset
        # Note: offset here is a float, and some file formats have only four
        # decimal places of precision.  So we should not compare exactly here.
        if Comparison._areDifferentEnough(annExtra1.offset, annExtra2.offset):
            cost += 1
            op_list.append(("extraoffsetedit", annExtra1, annExtra2, 1))

        # add for the duration
        # Note: duration here is a float, and some file formats have only four
        # decimal places of precision.  So we should not compare exactly here.
        if Comparison._areDifferentEnough(annExtra1.duration, annExtra2.duration):
            cost += 1
            op_list.append(("extradurationedit", annExtra1, annExtra2, 1))

        # add for the style
        if annExtra1.styledict != annExtra2.styledict:
            cost += 1  # someday we might count different items in the styledict
            op_list.append(("extrastyleedit", annExtra1, annExtra2, 1))

        return op_list, cost

    @staticmethod
    def _annotated_lyric_diff(annLyric1: AnnLyric, annLyric2: AnnLyric):
        """
        Compute the differences between two annotated lyrics.
        Each annotated lyric consists of five values: lyric, verse_id, offset, duration,
        and styledict.
        """
        cost = 0
        op_list = []

        # add for the content
        if annLyric1.lyric != annLyric2.lyric:
            content_cost: int = (
                Comparison._strings_levenshtein_distance(annLyric1.lyric, annLyric2.lyric)
            )
            cost += content_cost
            op_list.append(("lyricedit", annLyric1, annLyric2, content_cost))

        # add for the number
        if annLyric1.number != annLyric2.number:
            number_cost: int
            if annLyric1.number == 0 or annLyric2.number == 0:
                # add or delete number
                number_cost = 1
            else:
                # add and delete number
                number_cost = 2
            cost += number_cost
            op_list.append(("lyricnumedit", annLyric1, annLyric2, number_cost))

        # add for the identifier
        if annLyric1.identifier != annLyric2.identifier:
            # someday we might do a Levenshtein distance of the two ids
            id_cost: int
            if not annLyric1.identifier or not annLyric1.identifier:
                # add or delete identifier
                id_cost = 1
            else:
                # add and delete identifier
                id_cost = 2
            cost += id_cost
            op_list.append(("lyricidedit", annLyric1, annLyric2, id_cost))

        # add for the offset
        # Note: offset here is a float, and some file formats have only four
        # decimal places of precision.  So we should not compare exactly here.
        if Comparison._areDifferentEnough(annLyric1.offset, annLyric2.offset):
            cost += 1
            op_list.append(("lyricoffsetedit", annLyric1, annLyric2, 1))

        # add for the style
        if annLyric1.styledict != annLyric2.styledict:
            cost += 1  # someday we might count different items in the styledict
            op_list.append(("lyricstyleedit", annLyric1, annLyric2, 1))

        return op_list, cost

    @staticmethod
    def _annotated_metadata_item_diff(
        annMetadataItem1: AnnMetadataItem,
        annMetadataItem2: AnnMetadataItem
    ):
        """
        Compute the differences between two annotated metadata items.
        Each annotated metadata item has two values: key: str, value: t.Any,
        """
        cost = 0
        op_list = []

        # we don't compare items that don't have the same key.
        if annMetadataItem1.key != annMetadataItem2.key:
            raise ValueError('unexpected comparison of metadata items with different keys')

        # add for the value
        if annMetadataItem1.value != annMetadataItem2.value:
            value_cost: int = (
                Comparison._strings_levenshtein_distance(
                    str(annMetadataItem1.value),
                    str(annMetadataItem2.value)
                )
            )
            cost += value_cost
            op_list.append(
                ("mditemvalueedit", annMetadataItem1, annMetadataItem2, value_cost)
            )

        return op_list, cost

    @staticmethod
    def _annotated_staff_group_diff(annStaffGroup1: AnnStaffGroup, annStaffGroup2: AnnStaffGroup):
        """
        Compute the differences between two annotated staff groups.
        Each annotated staff group consists of five values: name, abbreviation,
        symbol, barTogether, part_indices.
        """
        cost = 0
        op_list = []

        # add for the name
        if annStaffGroup1.name != annStaffGroup2.name:
            name_cost: int = (
                Comparison._strings_levenshtein_distance(
                    annStaffGroup1.name,
                    annStaffGroup2.name
                )
            )
            cost += name_cost
            op_list.append(("staffgrpnameedit", annStaffGroup1, annStaffGroup2, name_cost))

        # add for the abbreviation
        if annStaffGroup1.abbreviation != annStaffGroup2.abbreviation:
            abbreviation_cost: int = (
                Comparison._strings_levenshtein_distance(
                    annStaffGroup1.abbreviation,
                    annStaffGroup2.abbreviation
                )
            )
            cost += abbreviation_cost
            op_list.append((
                "staffgrpabbreviationedit",
                annStaffGroup1,
                annStaffGroup2,
                abbreviation_cost
            ))

        # add for the symbol
        if annStaffGroup1.symbol != annStaffGroup2.symbol:
            symbol_cost: int
            if not annStaffGroup1.symbol or not annStaffGroup2.symbol:
                # add or delete symbol
                symbol_cost = 1
            else:
                # add and delete symbol
                symbol_cost = 2
            cost += symbol_cost
            op_list.append(
                ("staffgrpsymboledit", annStaffGroup1, annStaffGroup2, symbol_cost)
            )

        # add for barTogether
        if annStaffGroup1.barTogether != annStaffGroup2.barTogether:
            barTogether_cost: int = 1
            cost += barTogether_cost
            op_list.append(
                ("staffgrpbartogetheredit", annStaffGroup1, annStaffGroup2, barTogether_cost)
            )

        # add for partIndices (sorted list of int)
        if annStaffGroup1.part_indices != annStaffGroup2.part_indices:
            partIndices_cost: int = 0
            if annStaffGroup1.part_indices[0] != annStaffGroup2.part_indices[0]:
                partIndices_cost += 1  # vertical start
            if annStaffGroup1.part_indices[-1] != annStaffGroup2.part_indices[-1]:
                partIndices_cost += 1  # vertical height
            if partIndices_cost == 0:
                # should never get here, but we have to have a cost
                partIndices_cost = 1
            cost += partIndices_cost
            op_list.append(
                ("staffgrppartindicesedit", annStaffGroup1, annStaffGroup2, partIndices_cost)
            )

        return op_list, cost

    @staticmethod
    @_memoize_inside_bars_diff_lin
    def _inside_bars_diff_lin(original, compare_to):
        # original and compare to are two lists of annotatedNote
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            cost = 0
            op_list, cost = Comparison._inside_bars_diff_lin(original, compare_to[1:])
            op_list.append(("noteins", None, compare_to[0], compare_to[0].notation_size()))
            cost += compare_to[0].notation_size()
            return op_list, cost

        if len(compare_to) == 0:
            cost = 0
            op_list, cost = Comparison._inside_bars_diff_lin(original[1:], compare_to)
            op_list.append(("notedel", original[0], None, original[0].notation_size()))
            cost += original[0].notation_size()
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # notedel
        op_list["notedel"], cost["notedel"] = Comparison._inside_bars_diff_lin(
            original[1:], compare_to
        )
        cost["notedel"] += original[0].notation_size()
        op_list["notedel"].append(
            ("notedel", original[0], None, original[0].notation_size())
        )
        # noteins
        op_list["noteins"], cost["noteins"] = Comparison._inside_bars_diff_lin(
            original, compare_to[1:]
        )
        cost["noteins"] += compare_to[0].notation_size()
        op_list["noteins"].append(
            ("noteins", None, compare_to[0], compare_to[0].notation_size())
        )
        # notesub
        op_list["notesub"], cost["notesub"] = Comparison._inside_bars_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # avoid call another function if they are equal
            notesub_op, notesub_cost = [], 0
        else:
            notesub_op, notesub_cost = Comparison._annotated_note_diff(original[0], compare_to[0])
        cost["notesub"] += notesub_cost
        op_list["notesub"].extend(notesub_op)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    def _annotated_note_diff(annNote1: AnnNote, annNote2: AnnNote):
        """
        Compute the differences between two annotated notes.
        Each annotated note consist in a 5tuple (pitches, notehead, dots, beamings, tuplets)
        where pitches is a list.
        Arguments:
            noteNode1 {[AnnNote]} -- original AnnNote
            noteNode2 {[AnnNote]} -- compare_to AnnNote
        """
        cost = 0
        op_list = []
        # add for the pitches
        # if they are equal
        if annNote1.pitches == annNote2.pitches:
            op_list_pitch, cost_pitch = [], 0
        else:
            # pitches diff is computed using Levenshtein distances (they are already ordered)
            op_list_pitch, cost_pitch = Comparison._pitches_levenshtein_diff(
                annNote1.pitches, annNote2.pitches, annNote1, annNote2, (0, 0)
            )
        op_list.extend(op_list_pitch)
        cost += cost_pitch
        # add for the notehead
        if annNote1.note_head != annNote2.note_head:
            # delete one note head, add the other (this isn't noteshape, this is
            # just quarter-note note head vs half-note note head, etc)
            cost += 2
            op_list.append(("headedit", annNote1, annNote2, 2))
        # add for the dots
        if annNote1.dots != annNote2.dots:
            # add one for each added (or deleted) dot
            dots_diff = abs(annNote1.dots - annNote2.dots)
            cost += dots_diff
            if annNote1.dots > annNote2.dots:
                op_list.append(("dotdel", annNote1, annNote2, dots_diff))
            else:
                op_list.append(("dotins", annNote1, annNote2, dots_diff))
        if annNote1.graceType != annNote2.graceType:
            # accented vs unaccented vs not a grace note (delete the wrong, add the right)
            cost += 2
            op_list.append(("graceedit", annNote1, annNote2, 2))
        if annNote1.graceSlash != annNote2.graceSlash:
            # add or delete the slash
            cost += 1
            op_list.append(("graceslashedit", annNote1, annNote2, 1))
        # add for the beamings
        if annNote1.beamings != annNote2.beamings:
            beam_op_list, beam_cost = Comparison._beamtuplet_levenshtein_diff(
                annNote1.beamings, annNote2.beamings, annNote1, annNote2, "beam"
            )
            op_list.extend(beam_op_list)
            cost += beam_cost
        # add for the tuplet types
        if annNote1.tuplets != annNote2.tuplets:
            tuplet_op_list, tuplet_cost = Comparison._beamtuplet_levenshtein_diff(
                annNote1.tuplets, annNote2.tuplets, annNote1, annNote2, "tuplet"
            )
            op_list.extend(tuplet_op_list)
            cost += tuplet_cost
        # add for the tuplet info
        if annNote1.tuplet_info != annNote2.tuplet_info:
            tuplet_info_op_list, tuplet_info_cost = Comparison._beamtuplet_levenshtein_diff(
                annNote1.tuplet_info, annNote2.tuplet_info, annNote1, annNote2, "tuplet"
            )
            op_list.extend(tuplet_info_op_list)
            cost += tuplet_info_cost
        # add for the articulations
        if annNote1.articulations != annNote2.articulations:
            artic_op_list, artic_cost = Comparison._generic_levenshtein_diff(
                annNote1.articulations,
                annNote2.articulations,
                annNote1,
                annNote2,
                "articulation",
            )
            op_list.extend(artic_op_list)
            cost += artic_cost
        # add for the expressions
        if annNote1.expressions != annNote2.expressions:
            expr_op_list, expr_cost = Comparison._generic_levenshtein_diff(
                annNote1.expressions,
                annNote2.expressions,
                annNote1,
                annNote2,
                "expression",
            )
            op_list.extend(expr_op_list)
            cost += expr_cost

        # add for gap from previous note or start of measure if first note in measure
        # (i.e. horizontal position shift)
        if annNote1.gap_dur != annNote2.gap_dur:
            # in all cases, the edit is a simple horizontal shift of the note
            cost += 1
            if annNote1.gap_dur == 0:
                op_list.append(("insspace", annNote1, annNote2, 1))
            elif annNote2.gap_dur == 0:
                op_list.append(("delspace", annNote1, annNote2, 1))
            else:
                # neither is zero
                op_list.append(("editspace", annNote1, annNote2, 1))

        # add for noteshape
        if annNote1.noteshape != annNote2.noteshape:
            # always delete existing note shape and add the new one
            cost += 2
            op_list.append(("editnoteshape", annNote1, annNote2, 2))
        # add for noteheadFill
        if annNote1.noteheadFill != annNote2.noteheadFill:
            # always delete existing note fill and add the new one
            cost += 2
            op_list.append(("editnoteheadfill", annNote1, annNote2, 2))
        # add for noteheadParenthesis (True or False)
        if annNote1.noteheadParenthesis != annNote2.noteheadParenthesis:
            # always either add or delete parentheses
            cost += 1
            op_list.append(("editnoteheadparenthesis", annNote1, annNote2, 1))
        # add for stemDirection
        if annNote1.stemDirection != annNote2.stemDirection:
            stemdir_cost: int
            if annNote1.stemDirection == 'noStem' or annNote2.stemDirection == 'noStem':
                # gonna add a stem
                stemdir_cost = 1
            else:
                # gonna change a stem (add then delete)
                stemdir_cost = 2
            cost += stemdir_cost
            op_list.append(("editstemdirection", annNote1, annNote2, stemdir_cost))
        # add for the styledict
        if annNote1.styledict != annNote2.styledict:
            cost += 1
            op_list.append(("editstyle", annNote1, annNote2, 1))

        return op_list, cost

    @staticmethod
    @_memoize_beamtuplet_lev_diff
    def _beamtuplet_levenshtein_diff(original, compare_to, note1, note2, which):
        """
        Compute the levenshtein distance between two sequences of beaming or tuples.
        Arguments:
            original {list} -- list of strings (start, stop, continue or partial)
            compare_to {list} -- list of strings (start, stop, continue or partial)
            note1 {AnnNote} -- the note for referencing in the score
            note2 {AnnNote} -- the note for referencing in the score
            which -- a string: "beam" or "tuplet" depending what we are comparing
        """
        if which not in ("beam", "tuplet"):
            raise ValueError("Argument 'which' must be either 'beam' or 'tuplet'")

        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            op_list, cost = Comparison._beamtuplet_levenshtein_diff(
                original, compare_to[1:], note1, note2, which
            )
            op_list.append(("ins" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        if len(compare_to) == 0:
            op_list, cost = Comparison._beamtuplet_levenshtein_diff(
                original[1:], compare_to, note1, note2, which
            )
            op_list.append(("del" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # delwhich
        op_list["del" + which], cost["del" + which] = Comparison._beamtuplet_levenshtein_diff(
            original[1:], compare_to, note1, note2, which
        )
        cost["del" + which] += 1
        op_list["del" + which].append(("del" + which, note1, note2, 1))
        # inswhich
        op_list["ins" + which], cost["ins" + which] = Comparison._beamtuplet_levenshtein_diff(
            original, compare_to[1:], note1, note2, which
        )
        cost["ins" + which] += 1
        op_list["ins" + which].append(("ins" + which, note1, note2, 1))
        # editwhich
        op_list["edit" + which], cost["edit" + which] = Comparison._beamtuplet_levenshtein_diff(
            original[1:], compare_to[1:], note1, note2, which
        )
        if original[0] == compare_to[0]:
            beam_diff_op_list = []
            beam_diff_cost = 0
        else:
            beam_diff_op_list, beam_diff_cost = [("edit" + which, note1, note2, 1)], 1
        cost["edit" + which] += beam_diff_cost
        op_list["edit" + which].extend(beam_diff_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    @_memoize_generic_lev_diff
    def _generic_levenshtein_diff(original, compare_to, note1, note2, which):
        """
        Compute the Levenshtein distance between two generic sequences of symbols
        (e.g., articulations).
        Arguments:
            original {list} -- list of strings
            compare_to {list} -- list of strings
            note1 {AnnNote} -- the note for referencing in the score
            note2 {AnnNote} -- the note for referencing in the score
            which -- a string: e.g. "articulation" depending what we are comparing
        """
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            op_list, cost = Comparison._generic_levenshtein_diff(
                original, compare_to[1:], note1, note2, which
            )
            op_list.append(("ins" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        if len(compare_to) == 0:
            op_list, cost = Comparison._generic_levenshtein_diff(
                original[1:], compare_to, note1, note2, which
            )
            op_list.append(("del" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # delwhich
        op_list["del" + which], cost["del" + which] = Comparison._generic_levenshtein_diff(
            original[1:], compare_to, note1, note2, which
        )
        cost["del" + which] += 1
        op_list["del" + which].append(("del" + which, note1, note2, 1))
        # inswhich
        op_list["ins" + which], cost["ins" + which] = Comparison._generic_levenshtein_diff(
            original, compare_to[1:], note1, note2, which
        )
        cost["ins" + which] += 1
        op_list["ins" + which].append(("ins" + which, note1, note2, 1))
        # editwhich
        op_list["edit" + which], cost["edit" + which] = Comparison._generic_levenshtein_diff(
            original[1:], compare_to[1:], note1, note2, which
        )
        if original[0] == compare_to[0]:  # to avoid perform the diff
            generic_diff_op_list = []
            generic_diff_cost = 0
        else:
            generic_diff_op_list, generic_diff_cost = (
                [("edit" + which, note1, note2, 1)],
                1,
            )
        cost["edit" + which] += generic_diff_cost
        op_list["edit" + which].extend(generic_diff_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    @_memoize_notes_set_distance
    def _notes_set_distance(original: list[AnnNote], compare_to: list[AnnNote]):
        """
        Gather up pairs of matching notes (using pitch, offset, graceness, and visual duration, in
        that order of importance).  If you can't find an exactly matching note, try again without
        visual duration.
        original [list] -- a list of AnnNote (which are never chords)
        compare_to [list] -- a list of AnnNote (which are never chords)
        """
        paired_notes: list[tuple[AnnNote, AnnNote]] = []
        unpaired_orig_notes: list[AnnNote] = []
        unpaired_comp_notes: list[AnnNote] = copy.copy(compare_to)

        for orig_n in original:
            fallback: AnnNote | None = None
            fallback_i: int = -1
            found_it: bool = False
            for i, comp_n in enumerate(unpaired_comp_notes):
                if orig_n.pitches[0][0] != comp_n.pitches[0][0]:
                    # this pitch comparison (1) assumes the note is not a chord
                    # (because we don't do chords when Voicing is not set, and
                    # we only call _notes_set_distance when Voicing is not set),
                    # and (2) only compares the visual position of the note (we
                    # are ignoring the accidental here).  This is so that an
                    # accidental change will show up as a pitch edit, not a
                    # note remove/insert.
                    continue
                if Comparison._areDifferentEnough(orig_n.note_offset, comp_n.note_offset):
                    continue
                if orig_n.note_is_grace != comp_n.note_is_grace:
                    continue
                if fallback is None:
                    fallback = comp_n
                    fallback_i = i

                if orig_n.note_dur_type != comp_n.note_dur_type:
                    continue
                if orig_n.note_dur_dots != comp_n.note_dur_dots:
                    continue

                # found a perfect match
                paired_notes.append((orig_n, comp_n))

                # remove comp_n from unpaired_comp_notes
                unpaired_comp_notes.pop(i)  # remove(comp_n) would sometimes get the wrong one

                found_it = True
                break

            if found_it:
                # on to the next original note
                continue

            # did we find a fallback (matched except for duration)?
            if fallback is not None:
                paired_notes.append((orig_n, fallback))
                unpaired_comp_notes.pop(fallback_i)
                continue

            # we found nothing
            unpaired_orig_notes.append(orig_n)

        # compute the cost and the op_list
        cost: int = 0
        op_list: list = []

        # notedel
        if unpaired_orig_notes:
            for an in unpaired_orig_notes:
                cost += an.notation_size()
                op_list.append(("notedel", an, None, an.notation_size(), an.note_idx_in_chord))

        # noteins
        if unpaired_comp_notes:
            for an in unpaired_comp_notes:
                cost += an.notation_size()
                op_list.append(("noteins", None, an, an.notation_size(), an.note_idx_in_chord))

        # notesub
        if paired_notes:
            for ano, anc in paired_notes:
                if ano == anc:
                    # if equal, avoid _annotated_note_diff call
                    notesub_op, notesub_cost = [], 0
                else:
                    notesub_op, notesub_cost = (
                        Comparison._annotated_note_diff(ano, anc)
                    )
                cost += notesub_cost
                op_list.extend(notesub_op)

        return op_list, cost

    @staticmethod
    @_memoize_extras_set_distance
    def _extras_set_distance(original: list[AnnExtra], compare_to: list[AnnExtra]):
        """
        Gather up pairs of matching extras (using kind, offset, and visual duration, in
        that order of importance).  If you can't find an exactly matching extra, try again
        without visual duration.
        original [list] -- a list of AnnExtras
        compare_to [list] -- a list of AnnExtras
        """
        paired_extras: list[tuple[AnnExtra, AnnExtra]] = []
        unpaired_orig_extras: list[AnnExtra] = []
        unpaired_comp_extras: list[AnnExtra] = copy.copy(compare_to)

        for orig_x in original:
            fallback: AnnExtra | None = None
            fallback_i: int = -1
            found_it: bool = False
            for i, comp_x in enumerate(unpaired_comp_extras):
                # kind and offset are required for pairing
                if orig_x.kind != comp_x.kind:
                    continue
                if Comparison._areDifferentEnough(orig_x.offset, comp_x.offset):
                    continue
                if fallback is None:
                    fallback = comp_x
                    fallback_i = i

                # duration is preferred for pairing
                if Comparison._areDifferentEnough(orig_x.duration, comp_x.duration):
                    continue

                # there are a few kind-specific elements that are also preferred:
                #   'direction'/'ending': content (visible text)
                #   'keysig'/'timesig'/'clef': symbolic (there are sometimes two
                #       simultaneous keysigs, timesigs, or clefs, and we don't
                #       want to confuse which one is which, producing a diff where
                #       there actually isn't one)
                #   'slur': placements (because there are often two identical slurs
                #       whose only difference is 'above' vs 'below', producing a diff
                #       where there actually isn't one)
                if orig_x.kind in ('direction', 'ending'):
                    if orig_x.content != comp_x.content:
                        continue
                if orig_x.kind == 'clef':
                    if orig_x.symbolic != comp_x.symbolic:
                        continue
                if orig_x.kind in ('keysig', 'timesig'):
                    if orig_x.infodict != comp_x.infodict:
                        continue
                if orig_x.kind == 'slur':
                    orig_placement: str = orig_x.styledict.get('placement', '')
                    comp_placement: str = comp_x.styledict.get('placement', '')
                    if orig_placement != comp_placement:
                        continue

                # found a perfect match
                paired_extras.append((orig_x, comp_x))

                # remove comp_n from unpaired_comp_extras
                unpaired_comp_extras.pop(i)  # remove(comp_n) would sometimes get the wrong one

                found_it = True
                break

            if found_it:
                # on to the next original extra
                continue

            # did we find a fallback (matched except for duration)?
            if fallback is not None:
                paired_extras.append((orig_x, fallback))
                unpaired_comp_extras.pop(fallback_i)
                continue

            # we found nothing
            unpaired_orig_extras.append(orig_x)

        # compute the cost and the op_list
        cost: int = 0
        op_list: list = []

        # extradel
        for extra in unpaired_orig_extras:
            cost += extra.notation_size()
            op_list.append(("extradel", extra, None, extra.notation_size()))

        # extrains
        for extra in unpaired_comp_extras:
            cost += extra.notation_size()
            op_list.append(("extrains", None, extra, extra.notation_size()))

        # extrasub
        if paired_extras:
            for extrao, extrac in paired_extras:
                if extrao == extrac:
                    # if equal, avoid _annotated_extra_diff call
                    extrasub_op, extrasub_cost = [], 0
                else:
                    extrasub_op, extrasub_cost = (
                        Comparison._annotated_extra_diff(extrao, extrac)
                    )
                cost += extrasub_cost
                op_list.extend(extrasub_op)

        return op_list, cost

    @staticmethod
    @_memoize_metadata_items_set_distance
    def _metadata_items_set_distance(
        original: list[AnnMetadataItem],
        compare_to: list[AnnMetadataItem]
    ):
        """
        Gather up pairs of matching metadata_items (using key and value).  If you can't find
        an exactly matching metadata_item, try again without value.
        original [list] -- a list of AnnMetadataItems
        compare_to [list] -- a list of AnnMetadataItems
        """
        paired_metadata_items: list[tuple[AnnMetadataItem, AnnMetadataItem]] = []
        unpaired_orig_metadata_items: list[AnnMetadataItem] = []
        unpaired_comp_metadata_items: list[AnnMetadataItem] = copy.copy(compare_to)

        # first look for perfect matches
        for orig_mdi in original:
            found_it: bool = False
            for i, comp_mdi in enumerate(unpaired_comp_metadata_items):
                # key is required for perfect match
                if orig_mdi.key != comp_mdi.key:
                    continue

                # value is required for perfect match
                if orig_mdi.value != comp_mdi.value:
                    continue

                # found a perfect match
                paired_metadata_items.append((orig_mdi, comp_mdi))

                # remove comp_mdi from unpaired_comp_metadata_items
                unpaired_comp_metadata_items.pop(i)

                found_it = True
                break

            if found_it:
                # on to the next original metadata_item
                continue

            # we found no perfect match
            unpaired_orig_metadata_items.append(orig_mdi)

        # now look among the unpaired remainders for key match only
        remove_unpaired_orig_items: list[AnnMetadataItem] = []
        for orig_mdi in unpaired_orig_metadata_items:
            for comp_idx, comp_mdi in enumerate(unpaired_comp_metadata_items):
                # key is required for key-only match
                if orig_mdi.key != comp_mdi.key:
                    continue

                # found a key-only match
                paired_metadata_items.append((orig_mdi, comp_mdi))

                # remove comp_mdi from unpaired_comp_metadata_items
                unpaired_comp_metadata_items.pop(comp_idx)

                # make a note of unpaired_orig_metadata_item to remove later
                remove_unpaired_orig_items.append(orig_mdi)
                break

        for remove_mdi in remove_unpaired_orig_items:
            unpaired_orig_metadata_items.remove(remove_mdi)

        # compute the cost and the op_list
        cost: int = 0
        op_list: list = []

        # mditemdel
        for metadata_item in unpaired_orig_metadata_items:
            cost += metadata_item.notation_size()
            op_list.append(("mditemdel", metadata_item, None, metadata_item.notation_size()))

        # mditemins
        for metadata_item in unpaired_comp_metadata_items:
            cost += metadata_item.notation_size()
            op_list.append(("mditemins", None, metadata_item, metadata_item.notation_size()))

        # mditemsub
        if paired_metadata_items:
            for metadata_itemo, metadata_itemc in paired_metadata_items:
                if metadata_itemo == metadata_itemc:
                    # if equal, avoid _annotated_metadata_item_diff call
                    metadata_itemsub_op, metadata_itemsub_cost = [], 0
                else:
                    metadata_itemsub_op, metadata_itemsub_cost = (
                        Comparison._annotated_metadata_item_diff(metadata_itemo, metadata_itemc)
                    )
                cost += metadata_itemsub_cost
                op_list.extend(metadata_itemsub_op)

        return op_list, cost

    @staticmethod
    @_memoize_staff_groups_set_distance
    def _staff_groups_set_distance(
        original: list[AnnStaffGroup],
        compare_to: list[AnnStaffGroup]
    ):
        """
        Gather up pairs of matching staffgroups (using start_index and end_index, in
        that order of importance).  If you can't find an exactly matching staffgroup,
        try again without end_index.
        original [list] -- a list of AnnStaffGroups
        compare_to [list] -- a list of AnnStaffGroups
        """
        paired_staff_groups: list[tuple[AnnStaffGroup, AnnStaffGroup]] = []
        unpaired_orig_staff_groups: list[AnnStaffGroup] = []
        unpaired_comp_staff_groups: list[AnnStaffGroup] = copy.copy(compare_to)

        for orig_sg in original:
            fallback: AnnStaffGroup | None = None
            fallback_i: int = -1
            found_it: bool = False
            for i, comp_sg in enumerate(unpaired_comp_staff_groups):
                # start index is required for pairing
                if orig_sg.part_indices[0] != comp_sg.part_indices[0]:
                    continue
                if fallback is None:
                    fallback = comp_sg
                    fallback_i = i

                # end index and symbol (brace, bracket, etc) is preferred for pairing
                if orig_sg.part_indices[-1] != comp_sg.part_indices[-1]:
                    continue
                if orig_sg.symbol != comp_sg.symbol:
                    continue

                # found a perfect match
                paired_staff_groups.append((orig_sg, comp_sg))

                # remove comp_n from unpaired_comp_staff_groups
                unpaired_comp_staff_groups.pop(i)

                found_it = True
                break

            if found_it:
                # on to the next original staff_group
                continue

            # did we find a fallback (matched except for duration)?
            if fallback is not None:
                paired_staff_groups.append((orig_sg, fallback))
                unpaired_comp_staff_groups.pop(fallback_i)
                continue

            # we found nothing
            unpaired_orig_staff_groups.append(orig_sg)

        # compute the cost and the op_list
        cost: int = 0
        op_list: list = []

        # staffgrpdel
        for staff_group in unpaired_orig_staff_groups:
            cost += staff_group.notation_size()
            op_list.append(("staffgrpdel", staff_group, None, staff_group.notation_size()))

        # staffgrpins
        for staff_group in unpaired_comp_staff_groups:
            cost += staff_group.notation_size()
            op_list.append(("staffgrpins", None, staff_group, staff_group.notation_size()))

        # staffgrpsub
        if paired_staff_groups:
            for staff_groupo, staff_groupc in paired_staff_groups:
                if staff_groupo == staff_groupc:
                    # if equal, avoid _annotated_staff_group_diff call
                    staff_groupsub_op, staff_groupsub_cost = [], 0
                else:
                    staff_groupsub_op, staff_groupsub_cost = (
                        Comparison._annotated_staff_group_diff(staff_groupo, staff_groupc)
                    )
                cost += staff_groupsub_cost
                op_list.extend(staff_groupsub_op)

        return op_list, cost

    @staticmethod
    def _voices_coupling_recursive(original: list[AnnVoice], compare_to: list[AnnVoice]):
        """
        Compare all the possible voices permutations, considering also deletion and
        insertion (equation on office lens).
        original [list] -- a list of Voice
        compare_to [list] -- a list of Voice
        """
        if len(original) == 0 and len(compare_to) == 0:  # stop the recursion
            return [], 0

        if len(original) == 0:
            # insertion
            op_list, cost = Comparison._voices_coupling_recursive(original, compare_to[1:])
            # add for the inserted voice
            op_list.append(("voiceins", None, compare_to[0], compare_to[0].notation_size()))
            cost += compare_to[0].notation_size()
            return op_list, cost

        if len(compare_to) == 0:
            # deletion
            op_list, cost = Comparison._voices_coupling_recursive(original[1:], compare_to)
            # add for the deleted voice
            op_list.append(("voicedel", original[0], None, original[0].notation_size()))
            cost += original[0].notation_size()
            return op_list, cost

        cost = {}
        op_list = {}
        # deletion
        op_list["voicedel"], cost["voicedel"] = Comparison._voices_coupling_recursive(
            original[1:], compare_to
        )
        op_list["voicedel"].append(
            ("voicedel", original[0], None, original[0].notation_size())
        )
        cost["voicedel"] += original[0].notation_size()
        for i, c in enumerate(compare_to):
            # substitution
            (
                op_list["voicesub" + str(i)],
                cost["voicesub" + str(i)],
            ) = Comparison._voices_coupling_recursive(
                original[1:], compare_to[:i] + compare_to[i + 1:]
            )
            if (
                compare_to[0] != original[0]
            ):  # add the cost of the sub and the operations from inside_bar_diff
                op_list_inside_bar, cost_inside_bar = Comparison._inside_bars_diff_lin(
                    original[0].annot_notes, c.annot_notes
                )  # compute the distance from original[0] and compare_to[i]
                op_list["voicesub" + str(i)].extend(op_list_inside_bar)
                cost["voicesub" + str(i)] += cost_inside_bar
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    def annotated_scores_diff(score1: AnnScore, score2: AnnScore) -> tuple[list[tuple], int]:
        '''
        Compare two annotated scores, computing an operations list and the cost of applying those
        operations to the first score to generate the second score.

        Args:
            score1 (`musicdiff.annotation.AnnScore`): The first annotated score to compare.
            score2 (`musicdiff.annotation.AnnScore`): The second annotated score to compare.

        Returns:
            list[tuple], int: The operations list and the cost
        '''
        # Clear all memoizer caches, in case we are called again with different scores.
        # The cached results are no longer valid.
        Comparison._clear_memoizer_caches()

        op_list_total: list[tuple] = []
        cost_total: int = 0

        if score1.n_of_parts == score2.n_of_parts:
            n_of_parts = score1.n_of_parts
        else:
            # The two scores have differing number of parts.  For now, assume that
            # the parts are in the same order in both scores, and that the missing
            # parts are the ones that should have been at the end of the smaller
            # score. In future we could do something like we do with voices, where
            # we try all the combinations and compare the most-similar pairs of
            # parts, and the rest are considered to be the extra parts (deleted
            # from score1, or inserted into score2).
            n_of_parts = min(score1.n_of_parts, score2.n_of_parts)
            if score1.n_of_parts > score2.n_of_parts:
                # score1 has more parts that must be deleted
                for part_idx in range(score2.n_of_parts, score1.n_of_parts):
                    deleted_part = score1.part_list[part_idx]
                    op_list_total.append(
                        (
                            "delpart",
                            deleted_part,
                            None,
                            deleted_part.notation_size()
                        )
                    )
                    cost_total += deleted_part.notation_size()
            else:
                # score2 has more parts that must be inserted
                for part_idx in range(score1.n_of_parts, score2.n_of_parts):
                    inserted_part = score2.part_list[part_idx]
                    op_list_total.append(
                        (
                            "inspart",
                            None,
                            inserted_part,
                            inserted_part.notation_size()
                        )
                    )
                    cost_total += inserted_part.notation_size()

        # iterate over parts that exist in both scores
        for p_number in range(n_of_parts):
            # compute non-common-subseq
            ncs = Comparison._non_common_subsequences_of_measures(
                score1.part_list[p_number].bar_list,
                score2.part_list[p_number].bar_list,
            )
            # compute blockdiff
            for subseq in ncs:
                op_list_block, cost_block = Comparison._block_diff_lin(
                    subseq["original"], subseq["compare_to"]
                )
                op_list_total.extend(op_list_block)
                cost_total += cost_block

        # compare the staff groups
        groups_op_list, groups_cost = Comparison._staff_groups_set_distance(
            score1.staff_group_list, score2.staff_group_list
        )
        op_list_total.extend(groups_op_list)
        cost_total += groups_cost

        # compare the metadata items
        mditems_op_list, mditems_cost = Comparison._metadata_items_set_distance(
            score1.metadata_items_list, score2.metadata_items_list
        )
        op_list_total.extend(mditems_op_list)
        cost_total += mditems_cost

        # Add the cost of any syntax errors in score1 that were fixed during parsing.
        # Ignore enough syntax errors to keep OMR-NED <= 1.0, for consistency.
        total_syms: int = score1.notation_size() + score2.notation_size()
        cost_plus_errors: int = cost_total + score1.num_syntax_errors_fixed
        if cost_plus_errors > total_syms:
            adjustment: int = cost_plus_errors - total_syms
            score1.num_syntax_errors_fixed -= adjustment

        cost_total += score1.num_syntax_errors_fixed

        return op_list_total, cost_total
