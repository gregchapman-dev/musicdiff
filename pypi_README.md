# musicdiff
A Python3 package (and command-line tool) for computing and visualizing (or describing) the notation differences between two music scores.

musicdiff is focused on visible notation differences, not only on audible musical differences.  For example, two tied eighth notes are considered different from a single quarter note.  And two beamed 16th notes are considered different from two unbeamed 16th notes. This makes musicdiff particularly useful for assessing the results of Optical Music Recognition software.

musicdiff is derived from: [music-score-diff](https://github.com/fosfrancesco/music-score-diff.git)
    by [Francesco Foscarin](https://github.com/fosfrancesco).

## Setup
Depends on [music21](https://pypi.org/project/music21) (version 9.1+),  [numpy](https://pypi.org/project/numpy), and [converter21](https://pypi.org/project/converter21) (version 3.3+). You also will need to configure music21 (instructions [here](https://web.mit.edu/music21/doc/usersGuide/usersGuide_01_installing.html)) to display a musical score (e.g. with MuseScore).  Requires Python 3.10+.

## Usage
On the command line:

    python3 -m musicdiff -i decoratednotesandrests lyrics style -x beams -- file1.musicxml file2.krn

    arguments:
      -i/--include  one or more named details to include in comparison (the default is allobjects,
                    a.k.a. decoratednotesandrests and otherobjects). Can be decoratednotesandrests,
                    otherobjects, allobjects, or any combination of those and/or the following:
                    notesandrests; the aforementioned note decorations: beams, tremolos, ornaments,
                    articulations, ties, slurs; the other objects: signatures, directions,
                    barlines, staffdetails, chordsymbols, ottavas, arpeggios, and lyrics; and
                    a final few details that are not found in allobjects: style, metadata, and
                    voicing.  voicing compares how notes are included in voices and chords (by
                    default this is ignored).
      -x/--exclude  one or more named details to exclude from comparison.  Can be any of the
                    named details accepted by -i/--include.
      -o/--output   one or more of three output formats: text (or t) or visual (or v) or ser (or s);
                    the default is visual). visual (or v) requests production of marked-up score
                    PDFs; text (or t) requests production of diff-like text output; ser (or s)
                    requests a JSON text output containing Symbolic Error Ratio information.

      file1         first music score file to compare (any format music21 or converter21 can parse)
      file2         second music score file to compare (any format music21 or converter21 can parse)

musicdiff is also a package, with APIs you can call in your own code. There is a high-level diff() API that the command-line tool uses (that you can tweak the behavior of), and there are also lower level APIs that you can use in projects that perhaps want to do something more complicated than just visualization in PDFs or diff-like text output.

## Documentation
You can find the musicdiff API documentation [here](https://gregchapman-dev.github.io/musicdiff).

## Citing
If you use this work in any research, please cite the relevant paper:

```
@inproceedings{foscarin2019diff,
  title={A diff procedure for music score files},
  author={Foscarin, Francesco and Jacquemard, Florent and Fournier-S’niehotta, Raphael},
  booktitle={6th International Conference on Digital Libraries for Musicology},
  pages={58--64},
  year={2019}
}
```

The paper is freely available [here](https://hal.inria.fr/hal-02267454v2/document).

## Acknowledgment
Many thanks to [Francesco Foscarin](https://github.com/fosfrancesco) for allowing me to use his [music-score-diff](https://github.com/fosfrancesco/music-score-diff.git) code, and for continuing to work with and advise me on this project.

## License
The MIT License (MIT)
Copyright (c) 2022-2025 Francesco Foscarin, Greg Chapman

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

