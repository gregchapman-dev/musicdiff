from pathlib import Path

import music21 as m21
import converter21

from musicdiff.annotation import AnnScore
from musicdiff import Comparison
from musicdiff import Visualization

class TestScoreVisualization:
    converter21.register()

    def test_scorevis1(self):
        score1_path = Path("tests/test_scores/tie_score_2a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/tie_score_2b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the complete score diff
        op_list, _ = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        Visualization.mark_diffs(score1, score2, op_list)
        # Visualization.show_diffs(score1, score2)


    def test_scorevis2(self):
        score1_path = Path("tests/test_scores/polyphonic_score_2a.mei")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/polyphonic_score_2b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the complete score diff
        op_list, _ = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        Visualization.mark_diffs(score1, score2, op_list)
        # Visualization.show_diffs(score1, score2)


    def test_scorevis3(self):
        score1_path = Path("tests/test_scores/musicxml/articulation_score_1a.xml")
        score1 = m21.converter.parse(str(score1_path))
        score2_path = Path("tests/test_scores/musicxml/articulation_score_1b.xml")
        score2 = m21.converter.parse(str(score2_path))
        # build ScoreTrees
        score_lin1 = AnnScore(score1)
        score_lin2 = AnnScore(score2)
        # compute the complete score diff
        op_list, _ = Comparison.annotated_scores_diff(score_lin1, score_lin2)
        Visualization.mark_diffs(score1, score2, op_list)
        # Visualization.show_diffs(score1, score2)

