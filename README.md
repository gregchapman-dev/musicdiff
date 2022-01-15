# musicdiff
A Python3 package for computing and visualizing the differences between two music scores.

musicdiff is derived from: [music-score-diff](https://github.com/fosfrancesco/music-score-diff.git)
    by [Francesco Foscarin](https://github.com/fosfrancesco).

## Setup
Depends on music21 and numpy. You also will need to configure music21 to display a musical score (e.g. with MuseScore).

## Usage
An example music file comparison tool based on musicdiff's high-level API musicdiff.diff() is available in [comparescores.py](comparescores.py).  You can use it directly, or as example code for adding musicdiff capabilities to your own code.  The source for musicdiff.diff() (found [here](musicdiff/__init__.py)) is good example code to read if you want to call the lower-level musicdiff APIs to get the list of diffs and then do interesting things with that list.

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
