# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

with open("README.md","r") as fh:
  long_description = fh.read()

setup(
  url = "https://github.com/charles-turner-1/ExcellAint",
  author="Charles Turner",
  author_email='charlesturner0987@gmail.com',
  classifiers=[
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
  install_requires=["polars>=0.20","inquirer>=3.2"],
  extras_require = {"dev": ["pytest>=3.7",],},
  description="A Python toolbox for dealing with some of the oddities that Excel can introduce into your dates.",
  py_modules=["excellaint"],
  package_dir={'': 'src'},
  license="MIT license",
  include_package_data=True,
  name='excellaint',
  version='0.0.1',
  zip_safe=False,
  long_description=long_description,
  long_description_content_type="text/markdown",
)