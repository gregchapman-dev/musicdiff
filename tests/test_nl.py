from pathlib import Path
import music21 as m21
import converter21
from musicdiff.annotation import AnnScore, AnnNote

class TestNl:
    converter21.register()

    def test_annotNote1(self):
        n1 = m21.note.Note(nameWithOctave="D#5", quarterLength=1)
        n1.id = 344
        # create annotated note
        anote = AnnNote(n1, [], [], [])
        assert anote.__repr__() == "[('D5', 'sharp', False)],4,0,B:[],T:[],TI:[],344,[],[],[],{}"
        assert str(anote) == "[D5sharp]4"


    def test_annotNote2(self):
        n1 = m21.note.Note(nameWithOctave="E#5", quarterLength=0.5)
        n1.id = 344
        # create annotated note
        anote = AnnNote(n1, ["start"], ["start"], ['3'])
        assert (
            anote.__repr__() == "[('E5', 'sharp', False)],4,0,B:['start'],T:['start'],TI:['3'],344,[],[],[],{}"
        )
        assert str(anote) == "[E5sharp]4BsrTsr(3)"


    def test_annotNote3(self):
        n1 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n1.id = 344
        n1.tie = m21.tie.Tie("start")
        # create annotated note
        anote = AnnNote(n1, [], [], [])
        assert anote.__repr__() == "[('D5', 'None', True)],2,0,B:[],T:[],TI:[],344,[],[],[],{}"
        assert str(anote) == "[D5T]2"


    def test_annotNote_size1(self):
        n1 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n1.tie = m21.tie.Tie("start")
        # create annotated note
        anote = AnnNote(n1, [], [], [])
        assert anote.notation_size() == 2


    def test_annotNote_size2(self):
        n1 = m21.note.Note(nameWithOctave="D#5", quarterLength=1.5)
        n1.tie = m21.tie.Tie("start")
        # create annotated note
        anote = AnnNote(n1, [], [], [])
        assert anote.notation_size() == 4


    def test_noteNode_size3(self):
        d = m21.duration.Duration(1.5)
        n1 = m21.chord.Chord(["D", "F#", "A"], duration=d)
        # create annotated note
        anote = AnnNote(n1, [], [], [])
        assert anote.notation_size() == 7


    def test_noteNode_size4(self):
        n1 = m21.note.Note(nameWithOctave="D5")
        n2 = m21.note.Note(nameWithOctave="F#5")
        n2.tie = m21.tie.Tie("start")
        n3 = m21.note.Note(nameWithOctave="G#5")
        d = m21.duration.Duration(1.75)
        chord = m21.chord.Chord([n1, n2, n3], duration=d)
        # create annotated note
        anote = AnnNote(chord, [], [], [])
        assert anote.notation_size() == 12


    def test_noteNode_size5(self):
        score2_path = Path("tests/test_scores/monophonic_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        score_lin2 = AnnScore(score2)
        assert (
            score_lin2.part_list[0]
            .bar_list[6]
            .voices_list[0]
            .annot_notes[2]
            .notation_size()
            == 2
        )


    def test_scorelin1(self):
        # import score
        score1_path = Path("tests/test_scores/polyphonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        # produce a ScoreTree
        score_lin1 = AnnScore(score1)
        # number of parts
        assert len(score_lin1.part_list) == 2
        # number of measures for each part
        assert len(score_lin1.part_list[0].bar_list) == 5
        assert len(score_lin1.part_list[1].bar_list) == 5
        # number of voices for each measure in part 0
        for m in score_lin1.part_list[0].bar_list:
            assert len(m.voices_list) == 1


    def test_scorelin2(self):
        # import score
        score1_path = Path("tests/test_scores/monophonic_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        # produce a ScoreTree
        score_lin1 = AnnScore(score1)
        # number of parts
        assert len(score_lin1.part_list) == 1
        # number of measures for each part
        assert len(score_lin1.part_list[0].bar_list) == 11
        # number of voices for each measure in part 0
        for m in score_lin1.part_list[0].bar_list:
            assert len(m.voices_list) == 1


    def test_generalnotes1(self):
        # import score
        score1_path = Path("tests/test_scores/chord_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        # produce a ScoreTree
        score_lin1 = AnnScore(score1)
        # number of parts
        assert len(score_lin1.part_list) == 1
        # number of measures for each part
        assert len(score_lin1.part_list[0].bar_list) == 1
        # number of voices for each measure in part 0
        for m in score_lin1.part_list[0].bar_list:
            assert len(m.voices_list) == 1
        assert score_lin1.part_list[0].bar_list[0].voices_list[0].notation_size() == 14


    def test_ties1(self):
        # import score
        score1_path = Path("tests/test_scores/tie_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        # produce a ScoreTree
        score_lin1 = AnnScore(score1)
        # number of parts
        assert len(score_lin1.part_list) == 1
        # number of measures for each part
        assert len(score_lin1.part_list[0].bar_list) == 1
        # number of voices for each measure in part 0
        for m in score_lin1.part_list[0].bar_list:
            assert len(m.voices_list) == 1
        expected_tree_repr = "[[E4T]4Bsr,[E4]4Bcosr,[D4]4Bspsp,[C4T,E4]4Bsr,[C4]4Bcosr,[D4]4Bspsp,[E4,G4,C5]4,[E4]4Bsr,[F4T]4Bsp]"
        assert str(score_lin1.part_list[0].bar_list[0].voices_list[0]) == expected_tree_repr
        assert score_lin1.part_list[0].bar_list[0].voices_list[0].notation_size() == 27


    def test_equality_an1(self):
        n1 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n1.id = 344
        n1.tie = m21.tie.Tie("start")
        n2 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n2.id = 345
        n2.tie = m21.tie.Tie("start")
        # create annotated note
        anote1 = AnnNote(n1, [], [], [])
        anote2 = AnnNote(n2, [], [], [])
        assert anote1 == anote2
        assert repr(anote1) != repr(anote2)


    def test_equality_an2(self):
        n1 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n1.id = 344
        n1.tie = m21.tie.Tie("start")
        n2 = m21.note.Note(nameWithOctave="D5", quarterLength=2)
        n2.id = 344
        n2.tie = m21.tie.Tie("start")
        # create annotated note
        anote1 = AnnNote(n1, [], [], [])
        anote2 = AnnNote(n2, [], [], [])
        assert anote1 == anote2
        assert repr(anote1) == repr(anote2)


    def test_equality_all1(self):
        # import score1
        score1_path = Path("tests/test_scores/multivoice_score_1a.mei")
        score1 = m21.converter.parse(str(score1_path))
        # import score2
        score2_path = Path("tests/test_scores/multivoice_score_1b.mei")
        score2 = m21.converter.parse(str(score2_path))
        # create scores
        s1 = AnnScore(score1)
        s2 = AnnScore(score2)
        # select voices1
        v1 = s1.part_list[0].bar_list[0].voices_list[0]
        v2 = s2.part_list[0].bar_list[0].voices_list[0]
        # change the ids
        for an in v1.annot_notes:
            an.general_note = 344
        for an in v2.annot_notes:
            an.general_note = 345
        assert v1 == v2
        assert repr(v1) == repr(v1)
        assert repr(v2) == repr(v2)
        assert repr(v1) != repr(v2)


    def test_equality_all2(self):
        # import score1
        score1_path = Path("tests/test_scores/polyphonic_score_2b.mei")
        score1 = m21.converter.parse(str(score1_path))
        # create score
        s = AnnScore(score1)
        # select bars
        b1 = s.part_list[0].bar_list[11]
        b2 = s.part_list[0].bar_list[12]
        assert b1 == b2
        assert repr(b1) == repr(b1)
        assert repr(b2) == repr(b2)
        assert repr(b1) != repr(b2)
        # select voices
        v1 = s.part_list[0].bar_list[11].voices_list[0]
        v2 = s.part_list[0].bar_list[12].voices_list[0]
        assert v1 == v2
        assert repr(v1) == repr(v1)
        assert repr(v2) == repr(v2)
        assert repr(v1) != repr(v2)
