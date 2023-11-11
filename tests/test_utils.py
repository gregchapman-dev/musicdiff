import music21 as m21
from musicdiff import M21Utils

def test_note2tuple1():
    n = m21.note.Note(nameWithOctave='D#5')
    expected_tuple = ("D5","sharp",False)
    assert(M21Utils.note2tuple(n) == expected_tuple )

def test_note2tuple2():
    n = m21.note.Note(nameWithOctave='D--5')
    expected_tuple = ("D5","double-flat",False)
    assert(M21Utils.note2tuple(n) == expected_tuple )

def test_note2tuple3():
    n = m21.note.Note(nameWithOctave='D--5')
    n.tie = m21.tie.Tie('start')
    expected_tuple = ("D5","double-flat",True)
    assert(M21Utils.note2tuple(n) == expected_tuple )

def test_note2tuple4():
    n = m21.note.Note(nameWithOctave='D--5')
    n.tie = m21.tie.Tie('stop')
    expected_tuple = ("D5","double-flat",False)
    assert(M21Utils.note2tuple(n) == expected_tuple )
