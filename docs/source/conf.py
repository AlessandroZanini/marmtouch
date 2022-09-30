# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

working_directory = Path(__file__).resolve().parents[2]
simulated_packages = working_directory/'dev'/'simulated_packages'
sys.path.append(working_directory.as_posix())
sys.path.append(simulated_packages.as_posix())

import marmtouch

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'marmtouch'
copyright = '2022, Janahan Selvanayagam'
author = 'Janahan Selvanayagam'
release = marmtouch.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc','sphinx_click','sphinx.ext.napoleon']
rst_epilog = """
.. role:: item
.. role:: time
.. role:: opt
"""

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_css_files = [
    'colours.css',
]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
