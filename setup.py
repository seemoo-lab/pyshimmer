# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2020  Lukas Magel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from setuptools import setup


def load_readme() -> str:
    with open("README.rst") as readme_file:
        return readme_file.read()


setup(
    name='pyshimmer',
    author='Lukas Magel',
    url='https://github.com/seemoo-lab/pyshimmer',
    license='GPL-3.0-or-later',
    description='API for Shimmer sensor devices',
    long_description=load_readme(),

    packages=['pyshimmer'],
    install_requires=['pyserial>=3.4', 'numpy>=1.15'],

    setup_requires=['setuptools_scm'],
    use_scm_version=True,
)
