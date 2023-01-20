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

from setuptools import setup, find_packages
import pathlib

musicdiffversion = '2.0.1'

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'pypi_README.md').read_text(encoding='utf-8')

if __name__ == '__main__':
    setup(
        name='musicdiff',
        version=musicdiffversion,

        description='A music score notation diff package',
        long_description=long_description,
        long_description_content_type='text/markdown',

        url='https://github.com/gregchapman-dev/musicdiff',

        author='Greg Chapman',
        author_email='gregc@mac.com',

        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3 :: Only',
            'Operating System :: OS Independent',
            'Natural Language :: English',
        ],

        keywords=[
            'music',
            'score',
            'notation',
            'diff',
            'compare',
            'OMR',
            'Optical Music Recognition',
            'assessment',
            'comparison',
            'music21',
        ],

        packages=find_packages(),

        python_requires='>=3.9',

        install_requires=[
            'music21>=8.1',
            'numpy',
            'converter21>=2.0'
        ],

        project_urls={
            'Documentation': 'https://gregchapman-dev.github.io/musicdiff',
            'Source': 'https://github.com/gregchapman-dev/musicdiff',
            'Bug Reports': 'https://github.com/gregchapman-dev/musicdiff/issues',
        }
    )
