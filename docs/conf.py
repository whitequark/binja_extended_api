#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath('..'))

extensions = ['sphinx.ext.autosummary', 'sphinx.ext.autodoc', 'sphinx.ext.viewcode']
templates_path = ['_templates']
autosummary_generate = True
source_suffix = '.rst'
master_doc = 'index'
project = 'Binary Ninja Extended API'
author = 'whitequark'
copyright = '2018, whitequark'
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
