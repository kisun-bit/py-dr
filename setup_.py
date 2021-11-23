from setuptools import setup, find_packages

setup(
    name='cpkt',
    version='_x_version_x_',
    description='common packet',
    packages=find_packages(exclude=('other_git.*', 'demos.*', 'tests.*', 'snippets.*', 'doc.*')),
)
