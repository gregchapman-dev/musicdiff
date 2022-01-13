# ------------------------------------------------------------------------------
# Purpose:       musicdiff is a package for comparing music scores using music21.
#
# Authors:       Greg Chapman <gregc@mac.com>
#                musicdiff is derived from:
#                   https://github.com/fosfrancesco/music-score-diff.git
#                   by Francesco Foscarin <foscarin.francesco@gmail.com>
#
# Copyright:     (c) 2022 Francesco Foscarin, Greg Chapman
# License:       MIT, see LICENSE
# ------------------------------------------------------------------------------

import setuptools

musicdiffversion = '0.9.0'

if __name__ == '__main__':
    setuptools.setup(
        name='musicdiff',
        version=musicdiffversion,
        author='Greg Chapman',
        author_email='gregc@mac.com',
        url='https://github.com/gregchapman-dev/musicdiff',
        license='MIT',
        python_requires='>=3.7',
        description='music score diff package',
        long_description=open('README.md').read(),
        packages=setuptools.find_packages(),
        install_requires=[
            'music21',
            'numpy'
        ],
    )
