from pathlib import Path

import music21 as m21
import converter21

from musicdiff import Comparison
from musicdiff.annotation import AnnScore, AnnNote
from musicdiff import DetailLevel

class TestScl:
    converter21.register()

    def test_non_common_subsequences_myers1(self):
        original = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        compare_to = [0, 0, 2, 3, 4, 5, 6, 4, 5, 9, 10]
        # since repr and str of integers are the same thing,
        # we just duplicate the values in a new column
        original = [[e, e] for e in original]
        compare_to = [[e, e] for e in compare_to]
        non_common_subsequences = Comparison._non_common_subsequences_myers(original, compare_to)
        expected_result = [
            {"original": [1], "compare_to": [0, 0]},
            {"original": [7, 8], "compare_to": [4, 5]},
        ]
        assert non_common_subsequences == expected_result


    def test_non_common_subsequences_myers2(self):
        original = [0, 1, 2, 3]
        compare_to = [5, 7, 8, 6, 3]
        # since repr and str of integers are the same thing,
        # we just duplicate the values in a new column
        original = [[e, e] for e in original]
        compare_to = [[e, e] for e in compare_to]
        non_common_subsequences = Comparison._non_common_subsequences_myers(original, compare_to)
        expected_result = [{"original": [0, 1, 2], "compare_to": [5, 7, 8, 6]}]
        assert non_common_subsequences == expected_result


    def test_non_common_subsequences_myers3(self):
        original = [0, 1, 2, 3, 4]
        compare_to = [0, 1, 2]
        # since repr and str of integers are the same thing,
        # we just duplicate the values in a new column
        original = [[e, e] for e in original]
        compare_to = [[e, e] for e in compare_to]
        non_common_subsequences = Comparison._non_common_subsequences_myers(original, compare_to)
        expected_result = [{"original": [3, 4], "compare_to": []}]
        assert non_common_subsequences == expected_result


    def test_non_common_subsequences_myers4(self):
        original = [0, 1, 2]
        compare_to = [0, 1, 2]
        # since repr and str of integers are the same thing,
        # we just duplicate the values in a new column
        original = [[e, e] for e in original]
        compare_to = [[e, e] for e in compare_to]
        non_common_subsequences = Comparison._non_common_subsequences_myers(original, compare_to)
        # keep just one integer for easy comparison
        for s in non_common_subsequences:
            for k in s.keys():
                s[k] = [e[0] for e in s[k]]
        expected_result = []
        assert non_common_subsequences == expected_result


    def test_non_common_subsequences_bars1(self):
        # import scores
        score1_path = Path("tests/test_scores/polyphonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/polyphonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_tree1 = AnnScore(score1)
        score_tree2 = AnnScore(score2)
        # compute the non common_subsequences for part 0
        part = 0
        ncs = Comparison._non_common_subsequences_of_measures(
            score_tree1.part_list[part].bar_list, score_tree2.part_list[part].bar_list
        )
        assert len(ncs) == 1


    def test_non_common_subsequences_bars2(self):
        # import scores
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_tree1 = AnnScore(score1)
        score_tree2 = AnnScore(score2)
        # compute the non common_subsequences for part 0
        part = 0
        non_common_subsequences = Comparison._non_common_subsequences_of_measures(
            score_tree1.part_list[part].bar_list, score_tree2.part_list[part].bar_list
        )
        expected_non_common1 = {
            "original": [score_tree1.part_list[0].bar_list[1]],
            "compare_to": [score_tree2.part_list[0].bar_list[1]],
        }
        expected_non_common2 = {
            "original": [
                score_tree1.part_list[0].bar_list[5],
                score_tree1.part_list[0].bar_list[6],
                score_tree1.part_list[0].bar_list[7],
                score_tree1.part_list[0].bar_list[8],
            ],
            "compare_to": [
                score_tree2.part_list[0].bar_list[5],
                score_tree2.part_list[0].bar_list[6],
                score_tree2.part_list[0].bar_list[7],
            ],
        }
        assert len(non_common_subsequences) == 2
        assert non_common_subsequences[0] == expected_non_common1
        assert non_common_subsequences[1] == expected_non_common2


    def test_non_common_subsequences_bars3(self):
        # import scores
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build Score
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the non common_subsequences for part 0
        part = 0
        non_common_subsequences = Comparison._non_common_subsequences_of_measures(
            score_lin1.part_list[part].bar_list, score_lin2.part_list[part].bar_list
        )
        expected_non_common1 = {
            "original": [score_lin1.part_list[0].bar_list[1]],
            "compare_to": [score_lin2.part_list[0].bar_list[1]],
        }
        expected_non_common2 = {
            "original": [
                score_lin1.part_list[0].bar_list[5],
                score_lin1.part_list[0].bar_list[6],
                score_lin1.part_list[0].bar_list[7],
                score_lin1.part_list[0].bar_list[8],
            ],
            "compare_to": [
                score_lin2.part_list[0].bar_list[5],
                score_lin2.part_list[0].bar_list[6],
                score_lin2.part_list[0].bar_list[7],
            ],
        }
        assert len(non_common_subsequences) == 2
        assert non_common_subsequences[0] == expected_non_common1
        assert non_common_subsequences[1] == expected_non_common2


    def test_pitches_diff1(self):
        n1 = m21.note.Note(nameWithOctave="D#5", quarterLength=1)
        n2 = m21.note.Note(nameWithOctave="D--5", quarterLength=1)
        # create AnnotatedNotes
        note1 = AnnNote(n1, 0., [], [], [])
        note2 = AnnNote(n2, 0., [], [], [])
        # pitches to compare
        pitch1 = note1.pitches[0]
        pitch2 = note2.pitches[0]
        # compare
        op_list, cost = Comparison._pitches_diff(pitch1, pitch2, note1, note2, (0, 0))
        assert cost == 1
        assert op_list == [("accidentedit", note1, note2, 1, (0, 0))]


    def test_pitches_diff2(self):
        n1 = m21.note.Note(nameWithOctave="E5", quarterLength=2)
        n2 = m21.note.Note(nameWithOctave="D--5", quarterLength=1)
        note1 = AnnNote(n1, 0., [], [], [])
        note2 = AnnNote(n2, 0., [], [], [])
        # pitches to compare
        pitch1 = note1.pitches[0]
        pitch2 = note2.pitches[0]
        # compare
        op_list, cost = Comparison._pitches_diff(pitch1, pitch2, note1, note2, (0, 0))
        assert cost == 2
        assert len(op_list) == 2
        assert ("accidentins", note1, note2, 1, (0, 0)) in op_list
        assert ("pitchnameedit", note1, note2, 1, (0, 0)) in op_list


    def test_pitches_diff3(self):
        n1 = m21.note.Note(nameWithOctave="D--5", quarterLength=2)
        n1.tie = m21.tie.Tie("start")
        n2 = m21.note.Rest(quarterLength=0.5)
        note1 = AnnNote(n1, 0., [], [], [])
        note2 = AnnNote(n2, 0., [], [], [])
        # pitches to compare
        pitch1 = note1.pitches[0]
        pitch2 = note2.pitches[0]
        # compare
        op_list, cost = Comparison._pitches_diff(pitch1, pitch2, note1, note2, (0, 0))
        assert cost == 3
        assert len(op_list) == 3
        assert ("accidentdel", note1, note2, 1, (0, 0)) in op_list
        assert ("pitchtypeedit", note1, note2, 1, (0, 0)) in op_list
        assert ("tiedel", note1, note2, 1, (0, 0)) in op_list


    def test_pitches_diff4(self):
        n1 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n1.tie = m21.tie.Tie("start")
        n2 = m21.note.Note(nameWithOctave="D#5", quarterLength=3)
        n2.tie = m21.tie.Tie("start")
        note1 = AnnNote(n1, 0., [], [], [])
        note2 = AnnNote(n2, 0., [], [], [])
        # pitches to compare
        pitch1 = note1.pitches[0]
        pitch2 = note2.pitches[0]
        # compare
        op_list, cost = Comparison._pitches_diff(pitch1, pitch2, note1, note2, (0, 0))
        assert cost == 1
        assert len(op_list) == 1
        assert ("accidentins", note1, note2, 1, (0, 0)) in op_list


    def test_block_diff1(self):
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        score_lin2 = AnnScore(score2, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        # compute the blockdiff between all the bars (just for test,
        # in practise we will run on non common subseq)
        op_list, cost = Comparison._block_diff_lin(
            score_lin1._measures_from_part(0), score_lin2._measures_from_part(0)
        )
        assert cost == 11
        assert len(op_list) == 6


    def test_block_diff2(self):
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the blockdiff between all the bars (just for test,
        # in practise we will run on non common subseq)
        op_list, cost = Comparison._block_diff_lin(
            score_lin1._measures_from_part(0), score_lin2._measures_from_part(0)
        )
        assert cost == 11
        assert len(op_list) == 6


    def test_multivoice_annotated_scores_diff1(self):
        score1_path = Path("tests/test_scores/multivoice_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/multivoice_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        score_lin2 = AnnScore(score2, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        # compute the complete score diff, including the voice- and chord-membership of notes
        op_list, cost = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        assert cost == 14
        assert len(op_list) == 5


    def test_multivoice_annotated_scores_diff2(self):
        score1_path = Path("tests/test_scores/multivoice_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/multivoice_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the complete score diff, ignoring voice/chord membership of notes
        op_list, cost = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        assert cost == 14
        assert len(op_list) == 7


    def test_annotated_scores_diff1(self):
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        score_lin2 = AnnScore(score2, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        # compute the complete score diff, including the voice- and chord-membership of notes
        op_list, cost = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        assert cost == 11
        assert len(op_list) == 6


    def test_annotated_scores_diff2(self):
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the complete score diff, ignoring voice/chord membership of notes
        op_list, cost = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        assert cost == 23
        assert len(op_list) == 9


    def test_musicxml_articulation_diff1(self):
        score1_path = Path("tests/test_scores/musicxml/articulation_score_1a.xml")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/musicxml/articulation_score_1b.xml")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        score_lin2 = AnnScore(score2, detail=DetailLevel.AllObjects | DetailLevel.Voicing)
        # compute the complete score diff, including the voice- and chord-membership of notes
        op_list, cost = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        assert cost == 10
        assert len(op_list) == 10


    def test_musicxml_articulation_diff2(self):
        score1_path = Path("tests/test_scores/musicxml/articulation_score_1a.xml")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/musicxml/articulation_score_1b.xml")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the complete score diff, ignoring voice/chord membership of notes
        op_list, cost = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        assert cost == 10
        assert len(op_list) == 10
