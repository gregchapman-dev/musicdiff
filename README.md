# musicdiff
A Python3 package (and command-line tool) for computing and visualizing the notation differences between two music scores.

musicdiff is focused on visible notation differences, not only on audible musical differences.  For example, two tied eighth notes are considered different from a single quarter note.  And two beamed 16th notes are considered different from two unbeamed 16th notes. This makes musicdiff particularly useful for assessing the results of Optical Music Recognition software.

musicdiff is derived from: [music-score-diff](https://github.com/fosfrancesco/music-score-diff.git)
    by [Francesco Foscarin](https://github.com/fosfrancesco).

## Setup
Depends on [music21](https://pypi.org/project/music21) (version 7.2+),  [numpy](https://pypi.org/project/numpy), and [converter21](https://pypi.org/project/converter21). You also will need to configure music21 (instructions [here](https://web.mit.edu/music21/doc/usersGuide/usersGuide_01_installing.html)) to display a musical score (e.g. with MuseScore).

## Usage
On the command line:

    python3 -m musicdiff file1.musicxml file2.krn

    positional arguments:
      file1       first music score file to compare (any format music21 can parse)
      file2       second music score file to compare (any format music21 can parse)

The source for that command-line tool, which calls musicdiff's high-level diff() API, can be seen [here](musicdiff/__main__.py).  You can use it as example code for adding musicdiff capabilities to your own code.  See the documentation [here](https://gregchapman-dev.github.io/musicdiff) to find out how to customize diff()'s behavior beyond what the command line tool does.

A google colab notebook is available [here](examples/musicdiff_demo.ipynb).

If you are interested in calling lower-level musicdiff APIs to do more complicated things than just visualization in PDFs, the source for musicdiff's high-level diff() API (found [here](musicdiff/__init__.py)) is good example code to read.

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

## License
Licensed under the [MIT License](LICENSE).

## Acknowledgment
Many thanks to [Francesco Foscarin](https://github.com/fosfrancesco) for allowing me to use his [music-score-diff](https://github.com/fosfrancesco/music-score-diff.git) code, and for continuing to work with and advise me on this project.
