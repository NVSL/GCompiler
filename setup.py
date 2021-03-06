from setuptools import setup, find_packages
import os
import sys
from codecs import open

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open(os.path.join(here, 'VERSION.txt'), encoding='utf-8') as f:
    version = f.read()
    
setup(name="GCompiler",
      version=version,
      long_description=long_description,
      author="NVSL, University of California San Diego",
      packages = find_packages(),
      package_data={
          "" : ["*.mako"]
      },
      include_package_data=True,
      install_requires=["mako"],
      entry_points={
        'console_scripts': [
            'MakeLibraryLink.py = GCompiler.MakeLibraryLink:main',
            'MakeLibraryLink = GCompiler.MakeLibraryLink:main',
            ]
        },
      
)
