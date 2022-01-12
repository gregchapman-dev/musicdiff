# ------------------------------------------------------------------------------
# Purpose:       comparison is a music comparison package for use by musicdiff.
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

import copy

# from numba import njit, jit, types
import numpy as np
from typing import List, Dict, Any, Tuple
from collections import namedtuple

from musicdiff import notation as nlin
from musicdiff import m21utils as m21u

# memoizers to speed up the recursive computation
def memoize_inside_bars_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer


def memoize_block_diff_lin(func):
    mem = {}

    def memoizer(original, compare_to):
        key = repr(original) + repr(compare_to)
        if key not in mem:
            mem[key] = func(original, compare_to)
        return copy.deepcopy(mem[key])

    return memoizer


def memoize_lcs_diff(func):
    mem = {}

    def memoizer(original, compare_to):
        key = str(hash(str(original))) + str(hash(str(compare_to)))
        if key not in mem:
            mem[key] = func(original, compare_to)
        return mem[key]

    return memoizer


def memoize_pitches_lev_diff(func):
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


def memoize_beamtuplet_lev_diff(func):
    mem = {}

    def memoizer(original, compare_to, noteNode1, noteNode2, type):
        key = (
            repr(original) + repr(compare_to) + repr(noteNode1) + repr(noteNode2) + type
        )
        if key not in mem:
            mem[key] = func(original, compare_to, noteNode1, noteNode2, type)
        return copy.deepcopy(mem[key])

    return memoizer


def memoize_generic_lev_diff(func):
    mem = {}

    def memoizer(original, compare_to, noteNode1, noteNode2, type):
        key = (
            repr(original) + repr(compare_to) + repr(noteNode1) + repr(noteNode2) + type
        )
        if key not in mem:
            mem[key] = func(original, compare_to, noteNode1, noteNode2, type)
        return copy.deepcopy(mem[key])

    return memoizer


def myers_diff(a_lines, b_lines):
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
            else:
                frontier[k] = Frontier(x, history)

    assert False, "Could not find edit script"


# algorithm in section 3.2
# INPUT: two lists of Bar (one list from one part of the first score and one list from one part of the second score)
# OUTPUT: the allignment between the two lists
# @memoize_lcs_diff
def lcs_diff(original: List[nlin.Bar], compare_to: List[nlin.Bar]) -> Tuple[Any, int]:
    if len(original) == 0 and len(compare_to) == 0:
        cost = 0
        return [], cost
    elif len(original) == 0:
        cost = 0
        op_list = []
        # iterate on the rest instead of go recurively (for performances)
        for e in compare_to[::-1]:  # reverse to simulate the recurstion
            op_list.append(("comparetostep", None, e, 0))
        return op_list, cost
    elif len(compare_to) == 0:
        cost = 0
        op_list = []
        # iterate on the rest instead of go recurively (for performances)
        for e in original[::-1]:  # reverse to simulate the recurstion
            op_list.append(("originalstep", e, None, 0))
        return op_list, cost
    elif original[0] == compare_to[0]:
        op_list, cost = lcs_diff(original[1:], compare_to[1:])
        cost += 1
        op_list.append(("equal", original[0], compare_to[0], 1))
        return op_list, cost
    else:
        # compute the cost and the op_list for the many possibilities of recursion
        cost_dict = {}
        op_list = {}
        # original-step
        op_list["originalstep"], cost_dict["originalstep"] = lcs_diff(
            original[1:], compare_to
        )
        cost_dict["originalstep"] += 0
        op_list["originalstep"].append(("originalstep", original[0], None, 0))
        # compare_to-step
        op_list["comparetostep"], cost_dict["comparetostep"] = lcs_diff(
            original, compare_to[1:]
        )
        cost_dict["comparetostep"] += 0
        op_list["comparetostep"].append(("comparetostep", None, compare_to[0], 0))

        # compute the maximum of the possibilities
        max_key = max(cost_dict, key=lambda k: cost_dict[k])
        out = op_list[max_key], cost_dict[max_key]
        return out


# @memoize_lcs_diff
# @jit(
#     types.Tuple((types.int64[:, :], types.int64))(types.int64[:, :], types.int64[:, :]),
#     nopython=True,
# )
# def lcs_diff_jit(original, compare_to):
#     if len(original) == 0 and len(compare_to) == 0:
#         cost = 0
#         op_list = np.zeros((0, 4), dtype=np.int64)
#         return op_list, cost
#     elif len(original) == 0:  # add compareto steps till the end
#         cost = 0
#         # iterate on the rest instead of go recursively (for performances)
#         op_list = np.zeros((0, 4), dtype=np.int64)
#         for e in compare_to[::-1]:  # reverse to simulate the recurstion
#             op_list = np.append(
#                 op_list, np.array([1, -1, e[1], 0]).reshape(1, 4), axis=0
#             )
#         return op_list, cost
#     elif len(compare_to) == 0:  # add original steps till the end
#         cost = 0
#         op_list = np.zeros((0, 4), dtype=np.int64)
#         # iterate on the rest instead of go recursively (for performances)
#         for e in original[::-1]:  # reverse to simulate the recurstion
#             op_list = np.append(
#                 op_list, np.array([0, e[1], -1, 0]).reshape(1, 4), axis=0
#             )
#         return op_list, cost
#     elif (
#         original[0, 0] == compare_to[0, 0]
#     ):  # compare the precomputed_str (no ids). index 2 for "equal" step
#         op_list, cost = lcs_diff_jit(original[1:], compare_to[1:])
#         cost += 1
#         op_list = np.append(
#             op_list,
#             np.array([2, original[0, 1], compare_to[0, 1], 1]).reshape(1, 4),
#             axis=0,
#         )
#         return op_list, cost
#     else:
#         # compute the cost and the op_list for the many possibilities of recursion
#         # index 0 is for original_step, index 1 is for  comparetostep
#         cost_original = 0
#         cost_compare = 0
#         op_list_original = np.zeros((0, 4), dtype=np.int64)
#         op_list_compare = np.zeros((0, 4), dtype=np.int64)
#         # original-step
#         op_list_original, cost_original = lcs_diff_jit(original[1:], compare_to)
#         cost_original += 0
#         op_list_original = np.append(
#             op_list_original, np.array([0, original[0, 1], -1, 0]).reshape(1, 4), axis=0
#         )
#         # compare_to-step
#         op_list_compare, cost_compare = lcs_diff_jit(original, compare_to[1:])
#         cost_compare += 0
#         op_list_compare = np.append(
#             op_list_compare,
#             np.array([1, -1, compare_to[0, 1], 0]).reshape(1, 4),
#             axis=0,
#         )

#         # compute the maximum of the possibilities, 0 is for original_step, index 1 is for  comparetostep
#         if cost_original > cost_compare:
#             return op_list_original, cost_original
#         else:
#             return op_list_compare, cost_compare


# # get the list of non common subsequence from the algorithm lcs_diff
# # that will be used to proceed further
# def non_common_subsequences(original, compare_to):
#     ### Both original and compare_to are list of lists, or numpy arrays with 2 columns.
#     ### This is necessary because bars need two representation at the same time.
#     ### One without the id (for comparison), and one with the id (to retrieve the bar at the end)
#     # get the list of operations
#     op_list, __ = lcs_diff_jit(
#         np.array(original, dtype=np.int64), np.array(compare_to, dtype=np.int64)
#     )
#     # retrieve the non common subsequences
#     non_common_subsequences = []
#     non_common_subsequences.append({"original": [], "compare_to": []})
#     ind = 0
#     for op in op_list[::-1]:
#         if op[0] == 2:  # equal
#             non_common_subsequences.append({"original": [], "compare_to": []})
#             ind += 1
#         elif op[0] == 0:  # original step
#             non_common_subsequences[ind]["original"].append(op[1])
#         elif op[0] == 1:  # compare to step
#             non_common_subsequences[ind]["compare_to"].append(op[2])
#     # remove the empty dict from the list
#     non_common_subsequences = [
#         s for s in non_common_subsequences if s != {"original": [], "compare_to": []}
#     ]
#     return non_common_subsequences


def non_common_subsequences_myers(original, compare_to):
    ### Both original and compare_to are list of lists, or numpy arrays with 2 columns.
    ### This is necessary because bars need two representation at the same time.
    ### One without the id (for comparison), and one with the id (to retrieve the bar at the end)
    # get the list of operations
    op_list = myers_diff(
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


def non_common_subsequences_of_measures(original_m, compare_to_m):
    # Take the hash for each measure to run faster comparison
    # We need to hashes: one that is independent of the IDs (precomputed_str, for comparison),
    # and one that contains the IDs (precomputed_repr, to retrieve the correct measure after computation)
    original_int = [[o.precomputed_str, o.precomputed_repr] for o in original_m]
    compare_to_int = [[c.precomputed_str, c.precomputed_repr] for c in compare_to_m]
    ncs = non_common_subsequences_myers(original_int, compare_to_int)
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


# old function without numba
# def non_common_subsequences(original, compare_to):
#     # get the list of operations
#     op_list, __ = lcs_diff_jit(original, compare_to)
#     # retrieve the non common subsequences
#     non_common_subsequences = []
#     non_common_subsequences.append({"original": [], "compare_to": []})
#     ind = 0
#     for op in op_list[::-1]:
#         if op[0] == "equal":
#             non_common_subsequences.append({"original": [], "compare_to": []})
#             ind += 1
#         elif op[0] == "originalstep":
#             non_common_subsequences[ind]["original"].append(op[1])
#         elif op[0] == "comparetostep":
#             non_common_subsequences[ind]["compare_to"].append(op[2])
#     # remove the empty dict from the list
#     non_common_subsequences = [
#         s for s in non_common_subsequences if s != {"original": [], "compare_to": []}
#     ]
#     return non_common_subsequences


@memoize_pitches_lev_diff
def pitches_leveinsthein_diff(original, compare_to, noteNode1, noteNode2, ids):
    """Compute the leveinsthein distance between two sequences of pitches
    Arguments:
        original {list} -- list of pitches
        compare_to {list} -- list of pitches
        noteNode1 {annotatedNote} --for referencing
        noteNode2 {annotatedNote} --for referencing
        ids {tuple} -- a tuple of 2 elements with the indices of the notes considered
    """
    if len(original) == 0 and len(compare_to) == 0:
        return [], 0
    elif len(original) == 0:
        cost = m21u.pitch_size(compare_to[0])
        op_list, cost = pitches_leveinsthein_diff(
            original, compare_to[1:], noteNode1, noteNode2, (ids[0], ids[1] + 1)
        )
        op_list.append(
            ("inspitch", noteNode1, noteNode2, m21u.pitch_size(compare_to[0]), ids)
        )
        cost += m21u.pitch_size(compare_to[0])
        return op_list, cost
    elif len(compare_to) == 0:
        cost = m21u.pitch_size(original[0])
        op_list, cost = pitches_leveinsthein_diff(
            original[1:], compare_to, noteNode1, noteNode2, (ids[0] + 1, ids[1])
        )
        op_list.append(
            ("delpitch", noteNode1, noteNode2, m21u.pitch_size(original[0]), ids)
        )
        cost += m21u.pitch_size(original[0])
        return op_list, cost
    else:
        # compute the cost and the op_list for the many possibilities of recursion
        cost_dict = {}
        op_list_dict = {}
        # del-pitch
        op_list_dict["delpitch"], cost_dict["delpitch"] = pitches_leveinsthein_diff(
            original[1:], compare_to, noteNode1, noteNode2, (ids[0] + 1, ids[1])
        )
        cost_dict["delpitch"] += m21u.pitch_size(original[0])
        op_list_dict["delpitch"].append(
            ("delpitch", noteNode1, noteNode2, m21u.pitch_size(original[0]), ids)
        )
        # ins-pitch
        op_list_dict["inspitch"], cost_dict["inspitch"] = pitches_leveinsthein_diff(
            original, compare_to[1:], noteNode1, noteNode2, (ids[0], ids[1] + 1)
        )
        cost_dict["inspitch"] += m21u.pitch_size(compare_to[0])
        op_list_dict["inspitch"].append(
            ("inspitch", noteNode1, noteNode2, m21u.pitch_size(compare_to[0]), ids)
        )
        # edit-pitch
        op_list_dict["editpitch"], cost_dict["editpitch"] = pitches_leveinsthein_diff(
            original[1:], compare_to[1:], noteNode1, noteNode2, (ids[0] + 1, ids[1] + 1)
        )
        if original[0] == compare_to[0]:  # to avoid perform the pitch_diff
            pitch_diff_op_list = []
            pitch_diff_cost = 0
        else:
            pitch_diff_op_list, pitch_diff_cost = pitches_diff(
                original[0], compare_to[0], noteNode1, noteNode2, (ids[0], ids[1])
            )
        cost_dict["editpitch"] += pitch_diff_cost
        op_list_dict["editpitch"].extend(pitch_diff_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost_dict, key=lambda k: cost_dict[k])
        out = op_list_dict[min_key], cost_dict[min_key]
        return out


def pitches_diff(pitch1, pitch2, noteNode1, noteNode2, ids):
    """compute the differences between two pitch (definition from the paper).
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
    if pitch1[2] != pitch2[2]:  # exclusive or. Add if one is tied and not the other
        ################probably to revise for chords
        cost += 1
        if pitch1[2]:
            assert not pitch2[2]
            op_list.append(("tiedel", noteNode1, noteNode2, 1, ids))
        elif pitch2[2]:
            assert not pitch1[2]
            op_list.append(("tieins", noteNode1, noteNode2, 1, ids))
    return op_list, cost


@memoize_block_diff_lin
def block_diff_lin(original, compare_to):
    if len(original) == 0 and len(compare_to) == 0:
        return [], 0
    elif len(original) == 0:
        op_list, cost = block_diff_lin(original, compare_to[1:])
        cost += compare_to[0].notation_size()
        op_list.append(("insbar", None, compare_to[0], compare_to[0].notation_size()))
        return op_list, cost
    elif len(compare_to) == 0:
        op_list, cost = block_diff_lin(original[1:], compare_to)
        cost += original[0].notation_size()
        op_list.append(("delbar", original[0], None, original[0].notation_size()))
        return op_list, cost
    else:
        # compute the cost and the op_list for the many possibilities of recursion
        cost_dict = {}
        op_list_dict = {}
        # del-bar
        op_list_dict["delbar"], cost_dict["delbar"] = block_diff_lin(
            original[1:], compare_to
        )
        cost_dict["delbar"] += original[0].notation_size()
        op_list_dict["delbar"].append(
            ("delbar", original[0], None, original[0].notation_size())
        )
        # ins-bar
        op_list_dict["insbar"], cost_dict["insbar"] = block_diff_lin(
            original, compare_to[1:]
        )
        cost_dict["insbar"] += compare_to[0].notation_size()
        op_list_dict["insbar"].append(
            ("insbar", None, compare_to[0], compare_to[0].notation_size())
        )
        # edit-bar
        op_list_dict["editbar"], cost_dict["editbar"] = block_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # to avoid perform the inside_bars_diff_lin if it's not needed
            inside_bar_op_list = []
            inside_bar_cost = 0
        else:
            # run the voice coupling algorithm
            inside_bar_op_list, inside_bar_cost = voices_coupling_recursive(
                original[0].voices_list, compare_to[0].voices_list
            )
        cost_dict["editbar"] += inside_bar_cost
        op_list_dict["editbar"].extend(inside_bar_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost_dict, key=lambda k: cost_dict[k])
        out = op_list_dict[min_key], cost_dict[min_key]
        return out


@memoize_inside_bars_diff_lin
def inside_bars_diff_lin(original, compare_to):
    # original and compare to are two lists of annotatedNote
    if len(original) == 0 and len(compare_to) == 0:
        return [], 0
    elif len(original) == 0:
        cost = 0
        op_list, cost = inside_bars_diff_lin(original, compare_to[1:])
        op_list.append(("noteins", None, compare_to[0], compare_to[0].notation_size()))
        cost += compare_to[0].notation_size()
        return op_list, cost
    elif len(compare_to) == 0:
        cost = 0
        op_list, cost = inside_bars_diff_lin(original[1:], compare_to)
        op_list.append(("notedel", original[0], None, original[0].notation_size()))
        cost += original[0].notation_size()
        return op_list, cost
    else:
        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # notedel
        op_list["notedel"], cost["notedel"] = inside_bars_diff_lin(
            original[1:], compare_to
        )
        cost["notedel"] += original[0].notation_size()
        op_list["notedel"].append(
            ("notedel", original[0], None, original[0].notation_size())
        )
        # noteins
        op_list["noteins"], cost["noteins"] = inside_bars_diff_lin(
            original, compare_to[1:]
        )
        cost["noteins"] += compare_to[0].notation_size()
        op_list["noteins"].append(
            ("noteins", None, compare_to[0], compare_to[0].notation_size())
        )
        # notesub
        op_list["notesub"], cost["notesub"] = inside_bars_diff_lin(
            original[1:], compare_to[1:]
        )
        if (
            original[0] == compare_to[0]
        ):  # avoid call another function if they are equal
            notesub_op, notesub_cost = [], 0
        else:
            notesub_op, notesub_cost = annotated_note_diff(original[0], compare_to[0])
        cost["notesub"] += notesub_cost
        op_list["notesub"].extend(notesub_op)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out


def annotated_note_diff(annNote1, annNote2):
    """compute the differences between two annotated notes (in NotationLinear)
    Each annotated note consist in a 5tuple (pitches, notehead, dots, beamings, tuplets) where pitches is a list
    Arguments:
        noteNode1 {[AnnotatedNote]} -- original AnnotatedNote
        noteNode2 {[AnnotatedNote]} -- compare_to AnnotatedNote
    """
    cost = 0
    op_list = []
    # add for the pitches
    # if they are equal
    if annNote1.pitches == annNote2.pitches:
        op_list_pitch, cost_pitch = [], 0
    else:
        # pitches diff is computed using leveinshtein differences (they are already ordered)
        op_list_pitch, cost_pitch = pitches_leveinsthein_diff(
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
    # add for the beamings
    if annNote1.beamings != annNote2.beamings:
        beam_op_list, beam_cost = beamtuplet_leveinsthein_diff(
            annNote1.beamings, annNote2.beamings, annNote1, annNote2, "beam"
        )
        op_list.extend(beam_op_list)
        cost += beam_cost
    # add for the tuplets
    if annNote1.tuplets != annNote2.tuplets:
        tuplet_op_list, tuplet_cost = beamtuplet_leveinsthein_diff(
            annNote1.tuplets, annNote2.tuplets, annNote1, annNote2, "tuplet"
        )
        op_list.extend(tuplet_op_list)
        cost += tuplet_cost
    # add for the articulations
    if annNote1.articulations != annNote2.articulations:
        artic_op_list, artic_cost = generic_leveinsthein_diff(
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
        expr_op_list, expr_cost = generic_leveinsthein_diff(
            annNote1.expressions,
            annNote2.expressions,
            annNote1,
            annNote2,
            "expression",
        )
        op_list.extend(expr_op_list)
        cost += expr_cost

    return op_list, cost


@memoize_beamtuplet_lev_diff
def beamtuplet_leveinsthein_diff(original, compare_to, note1, note2, type):
    """Compute the leveinsthein distance between two sequences of beaming or tuples
    Arguments:
        original {list} -- list of strings (start, stop, continue or partial)
        compare_to {list} -- list of strings (start, stop, continue or partial)
        note1 {AnnotatedNote} -- the note for referencing in the score
        note2 {AnnotatedNote} -- the note for referencing in the score
        type -- a string: "beam" or "tuplet" depending what we are comparing
    """
    if not (type == "beam" or type == "tuplet"):
        raise Exception("Argument type must be either 'beam' or 'tuplet'")
    if len(original) == 0 and len(compare_to) == 0:
        return [], 0
    elif len(original) == 0:
        op_list, cost = beamtuplet_leveinsthein_diff(
            original, compare_to[1:], note1, note2, type
        )
        op_list.append(("ins" + type, note1, note2, 1))
        cost += 1
        return op_list, cost
    elif len(compare_to) == 0:
        op_list, cost = beamtuplet_leveinsthein_diff(
            original[1:], compare_to, note1, note2, type
        )
        op_list.append(("del" + type, note1, note2, 1))
        cost += 1
        return op_list, cost
    else:
        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # del-pitch
        op_list["del" + type], cost["del" + type] = beamtuplet_leveinsthein_diff(
            original[1:], compare_to, note1, note2, type
        )
        cost["del" + type] += 1
        op_list["del" + type].append(("del" + type, note1, note2, 1))
        # ins-pitch
        op_list["ins" + type], cost["ins" + type] = beamtuplet_leveinsthein_diff(
            original, compare_to[1:], note1, note2, type
        )
        cost["ins" + type] += 1
        op_list["ins" + type].append(("ins" + type, note1, note2, 1))
        # edit-pitch
        op_list["edit" + type], cost["edit" + type] = beamtuplet_leveinsthein_diff(
            original[1:], compare_to[1:], note1, note2, type
        )
        if original[0] == compare_to[0]:  # to avoid perform the pitch_diff
            beam_diff_op_list = []
            beam_diff_cost = 0
        else:
            beam_diff_op_list, beam_diff_cost = [("edit" + type, note1, note2, 1)], 1
        cost["edit" + type] += beam_diff_cost
        op_list["edit" + type].extend(beam_diff_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out


@memoize_generic_lev_diff
def generic_leveinsthein_diff(original, compare_to, note1, note2, type):
    """Compute the leveinsthein distance between two generic sequences of symbols (e.g., articulations)
    Arguments:
        original {list} -- list of strings
        compare_to {list} -- list of strings
        note1 {AnnotatedNote} -- the note for referencing in the score
        note2 {AnnotatedNote} -- the note for referencing in the score
        type -- a string: e.g. "articulation" depending what we are comparing
    """
    if len(original) == 0 and len(compare_to) == 0:
        return [], 0
    elif len(original) == 0:
        op_list, cost = generic_leveinsthein_diff(
            original, compare_to[1:], note1, note2, type
        )
        op_list.append(("ins" + type, note1, note2, 1))
        cost += 1
        return op_list, cost
    elif len(compare_to) == 0:
        op_list, cost = generic_leveinsthein_diff(
            original[1:], compare_to, note1, note2, type
        )
        op_list.append(("del" + type, note1, note2, 1))
        cost += 1
        return op_list, cost
    else:
        # compute the cost and the op_list for the many possibilities of recursion
        cost = {}
        op_list = {}
        # del-pitch
        op_list["del" + type], cost["del" + type] = generic_leveinsthein_diff(
            original[1:], compare_to, note1, note2, type
        )
        cost["del" + type] += 1
        op_list["del" + type].append(("del" + type, note1, note2, 1))
        # ins-pitch
        op_list["ins" + type], cost["ins" + type] = generic_leveinsthein_diff(
            original, compare_to[1:], note1, note2, type
        )
        cost["ins" + type] += 1
        op_list["ins" + type].append(("ins" + type, None, compare_to[0], 1))
        # edit-pitch
        op_list["edit" + type], cost["edit" + type] = generic_leveinsthein_diff(
            original[1:], compare_to[1:], note1, note2, type
        )
        if original[0] == compare_to[0]:  # to avoid perform the pitch_diff
            generic_diff_op_list = []
            generic_diff_cost = 0
        else:
            generic_diff_op_list, generic_diff_cost = (
                [("edit" + type, note1, note2, 1)],
                1,
            )
        cost["edit" + type] += generic_diff_cost
        op_list["edit" + type].extend(generic_diff_op_list)
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out


def voices_coupling_recursive(original: List, compare_to):
    """compare all the possible voices permutations, considering also deletion and insertion (equation on office lens)
    original [list] -- a list of Voice
    compare_to [list] -- a list of Voice
    """
    if len(original) == 0 and len(compare_to) == 0:  # stop the recursion
        return [], 0
    elif len(original) == 0:
        # insertion
        op_list, cost = voices_coupling_recursive(original, compare_to[1:])
        # add for the inserted voice
        op_list.append(("voiceins", None, compare_to[0], compare_to[0].notation_size()))
        cost += compare_to[0].notation_size()
        return op_list, cost
    elif len(compare_to) == 0:
        # deletion
        op_list, cost = voices_coupling_recursive(original[1:], compare_to)
        # add for the deleted voice
        op_list.append(("voicedel", original[0], None, original[0].notation_size()))
        cost += original[0].notation_size()
        return op_list, cost
    else:
        cost = {}
        op_list = {}
        # deletion
        op_list["voicedel"], cost["voicedel"] = voices_coupling_recursive(
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
            ) = voices_coupling_recursive(
                original[1:], compare_to[:i] + compare_to[i + 1 :]
            )
            if (
                compare_to[0] != original[0]
            ):  # add the cost of the sub and the operations from inside_bar_diff
                op_list_inside_bar, cost_inside_bar = inside_bars_diff_lin(
                    original[0].annot_notes, c.annot_notes
                )  # compute the distance from original[0] and compare_to[i]
                op_list["voicesub" + str(i)].extend(op_list_inside_bar)
                cost["voicesub" + str(i)] += cost_inside_bar
        # compute the minimum of the possibilities
        min_key = min(cost, key=cost.get)
        out = op_list[min_key], cost[min_key]
        return out


def complete_scorelin_diff(score_lin1, score_lin2):
    # for now just working with equal number of parts that are already paires
    # TODO : extend to different number of parts
    assert score_lin1.n_of_parts == score_lin2.n_of_parts
    n_of_parts = score_lin1.n_of_parts
    op_list_total, cost_total = [], 0
    # iterate for all parts in the score
    for p_number in range(n_of_parts):
        # compute non-common-subseq
        ncs = non_common_subsequences_of_measures(
            score_lin1.part_list[p_number].bar_list,
            score_lin2.part_list[p_number].bar_list,
        )
        # compute blockdiff
        for subseq in ncs:
            op_list_block, cost_block = block_diff_lin(
                subseq["original"], subseq["compare_to"]
            )
            op_list_total.extend(op_list_block)
            cost_total += cost_block
    return op_list_total, cost_total


def op_list2json(op_list):
    operations = []
    for op in op_list:
        # bar
        if op[0] == "insbar":
            assert type(op[2]) == nlin.Bar
            operations.append(
                {
                    "operation": "insbar",
                    "reference_score1": None,
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "delbar":
            assert type(op[1]) == nlin.Bar
            operations.append(
                {
                    "operation": "delbar",
                    "reference_score1": op[1],
                    "reference_score2": None,
                    "info": None,
                }
            )
        # voices
        elif op[0] == "voiceins":
            assert type(op[2]) == nlin.Voice
            operations.append(
                {
                    "operation": "insvoice",
                    "reference_score1": None,
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "voicedel":
            assert type(op[1]) == nlin.Voice
            operations.append(
                {
                    "operation": "delvoice",
                    "reference_score1": op[1],
                    "reference_score2": None,
                    "info": None,
                }
            )
        # note
        elif op[0] == "noteins":
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "insnote",
                    "reference_score1": None,
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "notedel":
            assert type(op[1]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "delnote",
                    "reference_score1": op[1],
                    "reference_score2": None,
                    "info": None,
                }
            )
        # pitch
        elif op[0] == "pitchnameedit":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "subpitchname",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "inspitch":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "inspitch",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "delpitch":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "delpitch",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "headedit":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "subnotehead",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        # beam
        elif op[0] == "insbeam":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "insbeam",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "delbeam":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "delbeam",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "editbeam":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "subbeam",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        # accident
        elif op[0] == "accidentins":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "insaccidental",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "accidentdel":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "delaccidental",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "accidentedit":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "subaccidental",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "dotins":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "insdot",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "dotdel":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "deldot",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        # tuplets TODO
        elif op[0] == "instuplet":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "instuplet",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "deltuplet":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "deltuplet",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "edittuplet":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "subtuplet",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "tieins":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "instie",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        elif op[0] == "tiedel":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            assert len(op) == 5  # the indices must be there
            operations.append(
                {
                    "operation": "deltie",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": (op[4][0], op[4][1]),
                }
            )
        # expression
        elif op[0] == "insexpression":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "insexpression",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "delexpression":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "delexpression",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "editexpression":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "subexpression",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        # articulation
        elif op[0] == "insarticulation":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "insarticulation",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "delarticulation":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "delarticulation",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        elif op[0] == "editarticulation":
            assert type(op[1]) == nlin.AnnotatedNote
            assert type(op[2]) == nlin.AnnotatedNote
            operations.append(
                {
                    "operation": "subarticulation",
                    "reference_score1": op[1],
                    "reference_score2": op[2],
                    "info": None,
                }
            )
        else:
            print(
                "Annotation type {} not yet supported for visualization".format(op[0])
            )
    return operations

