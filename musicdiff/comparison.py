# ------------------------------------------------------------------------------
# Purpose:       comparison is a music comparison package for use by musicdiff.
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

import copy
from collections import namedtuple
from difflib import ndiff

# import typing as t
import numpy as np

from musicdiff.annotation import AnnScore, AnnNote, AnnVoice, AnnExtra, AnnStaffGroup
from musicdiff.annotation import AnnMetadataItem
from musicdiff import M21Utils

# memoizers to speed up the recursive computation
def _memoize_inside_bars_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_extras_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_staff_groups_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_metadata_items_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_block_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_pitches_lev_diff(func):
    mem = {}

    def memoizer(original, compare_to, noteNode1, noteNode2, ids):
        key = (
            repr(original)
            + repr(compare_to)
            + repr(noteNode1)
            + repr(noteNode2)
            + repr(ids)
        )
        if key not in mem:
            mem[key] = func(original, compare_to, noteNode1, noteNode2, ids)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_beamtuplet_lev_diff(func):
    mem = {}

    def memoizer(original, compare_to, noteNode1, noteNode2, which):
        key = (
            repr(original) + repr(compare_to) + repr(noteNode1) + repr(noteNode2) + which
        )
        if key not in mem:
            mem[key] = func(original, compare_to, noteNode1, noteNode2, which)
        return copy.deepcopy(mem[key])

    return memoizer

def _memoize_generic_lev_diff(func):
    mem = {}

    def memoizer(original, compare_to, noteNode1, noteNode2, which):
        key = (
            repr(original) + repr(compare_to) + repr(noteNode1) + repr(noteNode2) + which
        )
        if key not in mem:
            mem[key] = func(original, compare_to, noteNode1, noteNode2, which)
        return copy.deepcopy(mem[key])

    return memoizer

class Comparison:
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
    def _pitches_leveinsthein_diff(
        original: list[tuple[str, str, bool]],
        compare_to: list[tuple[str, str, bool]],
        noteNode1: AnnNote,
        noteNode2: AnnNote,
        ids: tuple[int, int]
    ):
        """
        Compute the leveinsthein distance between two sequences of pitches.
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
            cost = M21Utils.pitch_size(compare_to[0])
            op_list, cost = Comparison._pitches_leveinsthein_diff(
                original, compare_to[1:], noteNode1, noteNode2, (ids[0], ids[1] + 1)
            )
            op_list.append(
                ("inspitch", noteNode1, noteNode2, M21Utils.pitch_size(compare_to[0]), ids)
            )
            cost += M21Utils.pitch_size(compare_to[0])
            return op_list, cost

        if len(compare_to) == 0:
            cost = M21Utils.pitch_size(original[0])
            op_list, cost = Comparison._pitches_leveinsthein_diff(
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
        op_list_dict["delpitch"], cost_dict["delpitch"] = Comparison._pitches_leveinsthein_diff(
            original[1:], compare_to, noteNode1, noteNode2, (ids[0] + 1, ids[1])
        )
        cost_dict["delpitch"] += M21Utils.pitch_size(original[0])
        op_list_dict["delpitch"].append(
            ("delpitch", noteNode1, noteNode2, M21Utils.pitch_size(original[0]), ids)
        )
        # ins-pitch
        op_list_dict["inspitch"], cost_dict["inspitch"] = Comparison._pitches_leveinsthein_diff(
            original, compare_to[1:], noteNode1, noteNode2, (ids[0], ids[1] + 1)
        )
        cost_dict["inspitch"] += M21Utils.pitch_size(compare_to[0])
        op_list_dict["inspitch"].append(
            ("inspitch", noteNode1, noteNode2, M21Utils.pitch_size(compare_to[0]), ids)
        )
        # edit-pitch
        op_list_dict["editpitch"], cost_dict["editpitch"] = Comparison._pitches_leveinsthein_diff(
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
            cost += 1
            if pitch1[1] == "None":
                assert pitch2[1] != "None"
                op_list.append(("accidentins", noteNode1, noteNode2, 1, ids))
            elif pitch2[1] == "None":
                assert pitch1[1] != "None"
                op_list.append(("accidentdel", noteNode1, noteNode2, 1, ids))
            else:  # a different tipe of alteration is present
                op_list.append(("accidentedit", noteNode1, noteNode2, 1, ids))
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
        ):  # to avoid performing the _voices_coupling_recursive if it's not needed
            inside_bar_op_list = []
            inside_bar_cost = 0
        else:
            # diff the bar extras (like _inside_bars_diff_lin, but with lists of AnnExtras
            # instead of lists of AnnNotes)
            extras_op_list, extras_cost = Comparison._extras_diff_lin(
                original[0].extras_list, compare_to[0].extras_list
            )

            # run the voice coupling algorithm, and add to inside_bar_op_list and inside_bar_cost
            inside_bar_op_list, inside_bar_cost = Comparison._voices_coupling_recursive(
                original[0].voices_list, compare_to[0].voices_list
            )
            inside_bar_op_list.extend(extras_op_list)
            inside_bar_cost += extras_cost
        cost_dict["editbar"] += inside_bar_cost
        op_list_dict["editbar"].extend(inside_bar_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost_dict, key=lambda k: cost_dict[k])
        out = op_list_dict[min_key], cost_dict[min_key]
        return out

    @staticmethod
    @_memoize_extras_diff_lin
    def _extras_diff_lin(original, compare_to):
        # original and compare to are two lists of AnnExtra
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            cost = 0
            op_list, cost = Comparison._extras_diff_lin(original, compare_to[1:])
            op_list.append(("extrains", None, compare_to[0], compare_to[0].notation_size()))
            cost += compare_to[0].notation_size()
            return op_list, cost

        if len(compare_to) == 0:
            cost = 0
            op_list, cost = Comparison._extras_diff_lin(original[1:], compare_to)
            op_list.append(("extradel", original[0], None, original[0].notation_size()))
            cost += original[0].notation_size()
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # extradel
        op_list["extradel"], cost["extradel"] = Comparison._extras_diff_lin(
            original[1:], compare_to
        )
        cost["extradel"] += original[0].notation_size()
        op_list["extradel"].append(
            ("extradel", original[0], None, original[0].notation_size())
        )
        # extrains
        op_list["extrains"], cost["extrains"] = Comparison._extras_diff_lin(
            original, compare_to[1:]
        )
        cost["extrains"] += compare_to[0].notation_size()
        op_list["extrains"].append(
            ("extrains", None, compare_to[0], compare_to[0].notation_size())
        )
        # extrasub
        op_list["extrasub"], cost["extrasub"] = Comparison._extras_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # avoid call another function if they are equal
            extrasub_op, extrasub_cost = [], 0
        else:
            extrasub_op, extrasub_cost = (
                Comparison._annotated_extra_diff(original[0], compare_to[0])
            )
        cost["extrasub"] += extrasub_cost
        op_list["extrasub"].extend(extrasub_op)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    @_memoize_metadata_items_diff_lin
    def _metadata_items_diff_lin(original, compare_to):
        # original and compare to are two lists of tuple[str, t.Any]
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            cost = 0
            op_list, cost = Comparison._metadata_items_diff_lin(original, compare_to[1:])
            op_list.append(("mditemins", None, compare_to[0], compare_to[0].notation_size()))
            cost += compare_to[0].notation_size()
            return op_list, cost

        if len(compare_to) == 0:
            cost = 0
            op_list, cost = Comparison._metadata_items_diff_lin(original[1:], compare_to)
            op_list.append(("mditemdel", original[0], None, original[0].notation_size()))
            cost += original[0].notation_size()
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # mditemdel
        op_list["mditemdel"], cost["mditemdel"] = Comparison._metadata_items_diff_lin(
            original[1:], compare_to
        )
        cost["mditemdel"] += original[0].notation_size()
        op_list["mditemdel"].append(
            ("mditemdel", original[0], None, original[0].notation_size())
        )
        # mditemins
        op_list["mditemins"], cost["mditemins"] = Comparison._metadata_items_diff_lin(
            original, compare_to[1:]
        )
        cost["mditemins"] += compare_to[0].notation_size()
        op_list["mditemins"].append(
            ("mditemins", None, compare_to[0], compare_to[0].notation_size())
        )
        # mditemsub
        op_list["mditemsub"], cost["mditemsub"] = Comparison._metadata_items_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # avoid call another function if they are equal
            mditemsub_op, mditemsub_cost = [], 0
        else:
            mditemsub_op, mditemsub_cost = (
                Comparison._annotated_metadata_item_diff(original[0], compare_to[0])
            )
        cost["mditemsub"] += mditemsub_cost
        op_list["mditemsub"].extend(mditemsub_op)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    @_memoize_staff_groups_diff_lin
    def _staff_groups_diff_lin(original, compare_to):
        # original and compare to are two lists of AnnStaffGroup
        if len(original) == 0 and len(compare_to) == 0:
            return [], 0

        if len(original) == 0:
            cost = 0
            op_list, cost = Comparison._staff_groups_diff_lin(original, compare_to[1:])
            op_list.append(("staffgrpins", None, compare_to[0], compare_to[0].notation_size()))
            cost += compare_to[0].notation_size()
            return op_list, cost

        if len(compare_to) == 0:
            cost = 0
            op_list, cost = Comparison._staff_groups_diff_lin(original[1:], compare_to)
            op_list.append(("staffgrpdel", original[0], None, original[0].notation_size()))
            cost += original[0].notation_size()
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # staffgrpdel
        op_list["staffgrpdel"], cost["staffgrpdel"] = Comparison._staff_groups_diff_lin(
            original[1:], compare_to
        )
        cost["staffgrpdel"] += original[0].notation_size()
        op_list["staffgrpdel"].append(
            ("staffgrpdel", original[0], None, original[0].notation_size())
        )
        # staffgrpins
        op_list["staffgrpins"], cost["staffgrpins"] = Comparison._staff_groups_diff_lin(
            original, compare_to[1:]
        )
        cost["staffgrpins"] += compare_to[0].notation_size()
        op_list["staffgrpins"].append(
            ("staffgrpins", None, compare_to[0], compare_to[0].notation_size())
        )
        # staffgrpsub
        op_list["staffgrpsub"], cost["staffgrpsub"] = Comparison._staff_groups_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # avoid call another function if they are equal
            staffgrpsub_op, staffgrpsub_cost = [], 0
        else:
            staffgrpsub_op, staffgrpsub_cost = (
                Comparison._annotated_staff_group_diff(original[0], compare_to[0])
            )
        cost["staffgrpsub"] += staffgrpsub_cost
        op_list["staffgrpsub"].extend(staffgrpsub_op)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out

    @staticmethod
    def _strings_leveinshtein_distance(str1: str, str2: str):
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
    def _areDifferentEnough(flt1: float, flt2: float) -> bool:
        diff: float = flt1 - flt2
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
                Comparison._strings_leveinshtein_distance(annExtra1.content, annExtra2.content)
            )
            cost += content_cost
            op_list.append(("extracontentedit", annExtra1, annExtra2, content_cost))

        # add for the offset
        # Note: offset here is a float, and some file formats have only four
        # decimal places of precision.  So we should not compare exactly here.
        if Comparison._areDifferentEnough(annExtra1.offset, annExtra2.offset):
            # offset is in quarter-notes, so let's make the cost in quarter-notes as well.
            # min cost is 1, though, don't round down to zero.
            offset_cost: int = int(min(1, abs(annExtra1.offset - annExtra2.offset)))
            cost += offset_cost
            op_list.append(("extraoffsetedit", annExtra1, annExtra2, offset_cost))

        # add for the duration
        # Note: duration here is a float, and some file formats have only four
        # decimal places of precision.  So we should not compare exactly here.
        if Comparison._areDifferentEnough(annExtra1.duration, annExtra2.duration):
            # duration is in quarter-notes, so let's make the cost in quarter-notes as well.
            duration_cost = int(min(1, abs(annExtra1.duration - annExtra2.duration)))
            cost += duration_cost
            op_list.append(("extradurationedit", annExtra1, annExtra2, duration_cost))

        # add for the style
        if annExtra1.styledict != annExtra2.styledict:
            cost += 1
            op_list.append(("extrastyleedit", annExtra1, annExtra2, 1))

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

        # add for the key
        if annMetadataItem1.key != annMetadataItem2.key:
            key_cost: int = (
                Comparison._strings_leveinshtein_distance(
                    annMetadataItem1.key,
                    annMetadataItem2.key
                )
            )
            cost += key_cost
            op_list.append(("mditemkeyedit", annMetadataItem1, annMetadataItem2, key_cost))

        # add for the value
        if annMetadataItem1.value != annMetadataItem2.value:
            value_cost: int = (
                Comparison._strings_leveinshtein_distance(
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
                Comparison._strings_leveinshtein_distance(annStaffGroup1.name, annStaffGroup2.name)
            )
            cost += name_cost
            op_list.append(("staffgrpnameedit", annStaffGroup1, annStaffGroup2, name_cost))

        # add for the abbreviation
        if annStaffGroup1.abbreviation != annStaffGroup2.abbreviation:
            abbreviation_cost: int = (
                Comparison._strings_leveinshtein_distance(
                    annStaffGroup1.abbreviation,
                    annStaffGroup2.abbreviation
                )
            )
            cost += abbreviation_cost
            op_list.append(
                ("staffgrpabbreviationedit", annStaffGroup1, annStaffGroup2, abbreviation_cost)
            )

        # add for the symbol
        if annStaffGroup1.symbol != annStaffGroup2.symbol:
            symbol_cost: int = 1
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
            parts1: str = str(annStaffGroup1.part_indices)
            parts2: str = str(annStaffGroup2.part_indices)
            partIndices_cost: int = (
                Comparison._strings_leveinshtein_distance(
                    parts1,
                    parts2
                )
            )
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
            # pitches diff is computed using leveinshtein differences (they are already ordered)
            op_list_pitch, cost_pitch = Comparison._pitches_leveinsthein_diff(
                annNote1.pitches, annNote2.pitches, annNote1, annNote2, (0, 0)
            )
        op_list.extend(op_list_pitch)
        cost += cost_pitch
        # add for the notehead
        if annNote1.note_head != annNote2.note_head:
            cost += 1
            op_list.append(("headedit", annNote1, annNote2, 1))
        # add for the dots
        if annNote1.dots != annNote2.dots:
            dots_diff = abs(annNote1.dots - annNote2.dots)  # add one for each dot
            cost += dots_diff
            if annNote1.dots > annNote2.dots:
                op_list.append(("dotdel", annNote1, annNote2, dots_diff))
            else:
                op_list.append(("dotins", annNote1, annNote2, dots_diff))
        if annNote1.graceType != annNote2.graceType:
            cost += 1
            op_list.append(("graceedit", annNote1, annNote2, 1))
        if annNote1.graceSlash != annNote2.graceSlash:
            cost += 1
            op_list.append(("graceslashedit", annNote1, annNote2, 1))
        # add for the beamings
        if annNote1.beamings != annNote2.beamings:
            beam_op_list, beam_cost = Comparison._beamtuplet_leveinsthein_diff(
                annNote1.beamings, annNote2.beamings, annNote1, annNote2, "beam"
            )
            op_list.extend(beam_op_list)
            cost += beam_cost
        # add for the tuplets
        if annNote1.tuplets != annNote2.tuplets:
            tuplet_op_list, tuplet_cost = Comparison._beamtuplet_leveinsthein_diff(
                annNote1.tuplets, annNote2.tuplets, annNote1, annNote2, "tuplet"
            )
            op_list.extend(tuplet_op_list)
            cost += tuplet_cost
        # add for the articulations
        if annNote1.articulations != annNote2.articulations:
            artic_op_list, artic_cost = Comparison._generic_leveinsthein_diff(
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
            expr_op_list, expr_cost = Comparison._generic_leveinsthein_diff(
                annNote1.expressions,
                annNote2.expressions,
                annNote1,
                annNote2,
                "expression",
            )
            op_list.extend(expr_op_list)
            cost += expr_cost
        # add for the lyrics
        if annNote1.lyrics != annNote2.lyrics:
            lyr_op_list, lyr_cost = Comparison._generic_leveinsthein_diff(
                annNote1.lyrics,
                annNote2.lyrics,
                annNote1,
                annNote2,
                "lyric",
            )
            op_list.extend(lyr_op_list)
            cost += lyr_cost

        # add for noteshape
        if annNote1.noteshape != annNote2.noteshape:
            cost += 1
            op_list.append(("editnoteshape", annNote1, annNote2, 1))
        # add for noteheadFill
        if annNote1.noteheadFill != annNote2.noteheadFill:
            cost += 1
            op_list.append(("editnoteheadfill", annNote1, annNote2, 1))
        # add for noteheadParenthesis
        if annNote1.noteheadParenthesis != annNote2.noteheadParenthesis:
            cost += 1
            op_list.append(("editnoteheadparenthesis", annNote1, annNote2, 1))
        # add for stemDirection
        if annNote1.stemDirection != annNote2.stemDirection:
            cost += 1
            op_list.append(("editstemdirection", annNote1, annNote2, 1))
        # add for the styledict
        if annNote1.styledict != annNote2.styledict:
            cost += 1
            op_list.append(("editstyle", annNote1, annNote2, 1))

        return op_list, cost

    @staticmethod
    @_memoize_beamtuplet_lev_diff
    def _beamtuplet_leveinsthein_diff(original, compare_to, note1, note2, which):
        """
        Compute the leveinsthein distance between two sequences of beaming or tuples.
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
            op_list, cost = Comparison._beamtuplet_leveinsthein_diff(
                original, compare_to[1:], note1, note2, which
            )
            op_list.append(("ins" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        if len(compare_to) == 0:
            op_list, cost = Comparison._beamtuplet_leveinsthein_diff(
                original[1:], compare_to, note1, note2, which
            )
            op_list.append(("del" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # del-pitch
        op_list["del" + which], cost["del" + which] = Comparison._beamtuplet_leveinsthein_diff(
            original[1:], compare_to, note1, note2, which
        )
        cost["del" + which] += 1
        op_list["del" + which].append(("del" + which, note1, note2, 1))
        # ins-pitch
        op_list["ins" + which], cost["ins" + which] = Comparison._beamtuplet_leveinsthein_diff(
            original, compare_to[1:], note1, note2, which
        )
        cost["ins" + which] += 1
        op_list["ins" + which].append(("ins" + which, note1, note2, 1))
        # edit-pitch
        op_list["edit" + which], cost["edit" + which] = Comparison._beamtuplet_leveinsthein_diff(
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
    def _generic_leveinsthein_diff(original, compare_to, note1, note2, which):
        """
        Compute the leveinsthein distance between two generic sequences of symbols
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
            op_list, cost = Comparison._generic_leveinsthein_diff(
                original, compare_to[1:], note1, note2, which
            )
            op_list.append(("ins" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        if len(compare_to) == 0:
            op_list, cost = Comparison._generic_leveinsthein_diff(
                original[1:], compare_to, note1, note2, which
            )
            op_list.append(("del" + which, note1, note2, 1))
            cost += 1
            return op_list, cost

        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # del-pitch
        op_list["del" + which], cost["del" + which] = Comparison._generic_leveinsthein_diff(
            original[1:], compare_to, note1, note2, which
        )
        cost["del" + which] += 1
        op_list["del" + which].append(("del" + which, note1, note2, 1))
        # ins-pitch
        op_list["ins" + which], cost["ins" + which] = Comparison._generic_leveinsthein_diff(
            original, compare_to[1:], note1, note2, which
        )
        cost["ins" + which] += 1
        op_list["ins" + which].append(("ins" + which, note1, note2, 1))
        # edit-pitch
        op_list["edit" + which], cost["edit" + which] = Comparison._generic_leveinsthein_diff(
            original[1:], compare_to[1:], note1, note2, which
        )
        if original[0] == compare_to[0]:  # to avoid perform the pitch_diff
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
        # for now just working with equal number of parts that are already pairs
        # TODO : extend to different number of parts
        assert score1.n_of_parts == score2.n_of_parts
        n_of_parts = score1.n_of_parts
        op_list_total, cost_total = [], 0
        # iterate for all parts in the score
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
        groups_op_list, groups_cost = Comparison._staff_groups_diff_lin(
            score1.staff_group_list, score2.staff_group_list
        )
        op_list_total.extend(groups_op_list)
        cost_total += groups_cost

        # compare the metadata items
        mditems_op_list, mditems_cost = Comparison._metadata_items_diff_lin(
            score1.metadata_items_list, score2.metadata_items_list
        )
        op_list_total.extend(mditems_op_list)
        cost_total += mditems_cost

        return op_list_total, cost_total
